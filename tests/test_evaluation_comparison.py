"""Compare schedules on fixed actions, without running a learning experiment."""
from dataclasses import replace
import random
import unittest
from unittest.mock import patch
import json
from pathlib import Path
import tempfile

import numpy as np

from transit_rl.config import ExperimentConfig
from transit_rl.data.network import build_network
from transit_rl.environment.actions import Action
from transit_rl.experiment.evaluation_comparison import (
    CountedEnvironment, MODES, build_plan, epsilon_at_fraction, evaluate, make_config,
)
from transit_rl.agent.q_learning_agent import QLearningAgent
from transit_rl.experiment.trainer import run_episode


class EvaluationComparisonTests(unittest.TestCase):
    def environments(self, **overrides):
        network = build_network([(1, 2, 8), (2, 3, 2), (3, 4, 3), (1, 4, 5)], 4, True)
        od = np.full((4, 4), 100.0)
        np.fill_diagonal(od, 0)
        return [CountedEnvironment(network, [od, od * 2], make_config(
            mode, num_stops=4, num_hours=2, od_start_file_hour=0,
            max_route_length=4, **overrides)) for mode in MODES]

    def replay(self, envs, actions):
        totals = [0.0] * len(envs)
        for action in actions:
            self.assertTrue(all(e.state == envs[0].state for e in envs))
            self.assertTrue(all(e.valid_actions() == envs[0].valid_actions() for e in envs))
            for i, env in enumerate(envs):
                totals[i] += env.step(action).reward
        for env, total in zip(envs, totals):
            self.assertAlmostEqual(total, sum(r['total_reward'] for r in env.hourly_records))
            for row in env.hourly_records:
                self.assertAlmostEqual(row['rl_reward_in_hour'], row['total_reward'])
        # Feedback timing differs; final records and passenger outcomes agree.
        for env in envs[1:]:
            for actual, expected in zip(env.hourly_records, envs[0].hourly_records):
                for key in actual:
                    if key == 'rl_reward_in_hour':
                        self.assertAlmostEqual(actual[key], expected[key])
                    else:
                        self.assertEqual(actual[key], expected[key], key)
        return totals

    def test_committed_changes_and_inherited_hour_preserve_daily_objective(self):
        envs = self.environments()
        actions = [Action('ADD_STOP', 1), Action('ADD_STOP', 2), Action('ADD_STOP', 3),
                   Action('REMOVE_LAST_STOP'), Action('ADD_STOP', 3), Action('END_ROUTE'),
                   Action('INCREASE_FREQUENCY', 0), Action('DECREASE_FREQUENCY', 0),
                   Action('KEEP_ROUTE', 0), Action('ADD_STOP', 3), Action('ADD_STOP', 4),
                   Action('END_ROUTE'), Action('REMOVE_ROUTE', 1), Action('FINISH_PLAN'),
                   Action('FINISH_PLAN')]
        self.replay(envs, actions)
        self.assertTrue(all(e.done for e in envs))
        self.assertGreater(envs[0].evaluation_requests, envs[1].evaluation_requests)
        self.assertGreater(envs[1].evaluation_requests, envs[2].evaluation_requests)
        self.assertEqual(envs[2].evaluation_requests, 2)

    def test_uncommitted_stops_trigger_no_assignment_in_B_or_C(self):
        envs = self.environments()
        before = [e.evaluation_requests for e in envs]
        for env in envs:
            first = env.step(Action('ADD_STOP', 1))
            second = env.step(Action('ADD_STOP', 2))
            if env.cfg.reward_mode != 'dense':
                self.assertEqual(first.reward + second.reward, 0)
        self.assertGreater(envs[0].evaluation_requests, before[0])
        self.assertEqual(envs[1].evaluation_requests, before[1])
        self.assertEqual(envs[2].evaluation_requests, before[2])
        for env in envs:
            env.step(Action('END_ROUTE'))
        self.assertGreater(envs[1].evaluation_requests, before[1])
        self.assertEqual(envs[2].evaluation_requests, before[2])

    def test_forced_discard_preserves_return(self):
        self.replay(self.environments(max_steps_per_hour=2),
                    [Action('ADD_STOP', 1), Action('ADD_STOP', 2),
                     Action('ADD_STOP', 3), Action('ADD_STOP', 4)])

    def test_forced_committed_change_preserves_return(self):
        self.replay(self.environments(max_steps_per_hour=1,
                    initial_service_plan=({'route': [1, 2], 'frequency': 4},)),
                    [Action('INCREASE_FREQUENCY', 0), Action('DECREASE_FREQUENCY', 0)])

    def test_many_fixed_action_sequences_conserve_returns(self):
        for seed in range(10):
            envs = self.environments(max_steps_per_hour=15)
            rng = random.Random(seed)
            actions = []
            # Generate actions on a separate copy so replay begins from reset.
            source = self.environments(max_steps_per_hour=15)[0]
            while not source.done:
                action = rng.choice(source.valid_actions())
                actions.append(action)
                source.step(action)
            self.replay(envs, actions)

    def test_default_mode_and_schedule_are_unchanged(self):
        self.assertEqual(ExperimentConfig().reward_mode, 'dense')
        with self.assertRaises(ValueError):
            make_config('B_committed', discount_factor=0.99)
        cfg = make_config('A_dense')
        self.assertEqual(epsilon_at_fraction(cfg, 0), 1)
        self.assertAlmostEqual(epsilon_at_fraction(cfg, 0.8), 0.05)
        self.assertAlmostEqual(epsilon_at_fraction(cfg, 1), 0.05)
        plan = build_plan()
        for wave in plan['learning_waves']:
            self.assertEqual({item['mode'] for item in wave}, set(MODES))
            self.assertEqual(len({item['seed'] for item in wave}), 1)

    def test_common_evaluation_preserves_training_q_rng_and_cache(self):
        for env in self.environments(max_steps_per_hour=8):
            agent = QLearningAgent(env.cfg, 2024)
            run_episode(env, agent, train=True)
            rng = agent.rng.getstate()
            q = {key: dict(row) for key, row in agent.q.items()}
            visits = {key: dict(row) for key, row in agent.visits.items()}
            counts = env.assigner.cache_hits, env.assigner.cache_misses, env.evaluation_requests
            results = evaluate(agent, env.cfg, env.network, env.od_matrices, [6000, 6001])
            self.assertEqual(len(results), 2)
            self.assertEqual(agent.rng.getstate(), rng)
            self.assertEqual(agent.q, q)
            self.assertEqual(agent.visits, visits)
            self.assertEqual(counts, (env.assigner.cache_hits, env.assigner.cache_misses,
                                      env.evaluation_requests))

    def test_failed_worker_retains_original_run_identity(self):
        from transit_rl.experiment.evaluation_comparison import run_job
        with tempfile.TemporaryDirectory() as folder:
            job=dict(output=str(Path(folder)/'run'),study_id='test',run_id='test-run01',phase='timing',
                     mode='A_dense',seed=2027,evaluation_seeds=[7000],code_commit='test-sha',command='test')
            with patch('transit_rl.experiment.evaluation_comparison._run_job_impl',side_effect=ValueError('test failure')):
                with self.assertRaises(ValueError):
                    run_job(job)
            manifest=json.loads((Path(job['output'])/'manifest.json').read_text())
            self.assertEqual(manifest['status'],'failed')
            self.assertEqual(manifest['run_id'],'test-run01')
            self.assertIn('test failure',manifest['error'])
            self.assertIsNotNone(manifest['started_at'])
            self.assertIsNotNone(manifest['finished_at'])
            with self.assertRaises(FileExistsError):
                run_job(job)


if __name__ == '__main__':
    unittest.main()
