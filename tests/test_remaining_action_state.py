from dataclasses import replace
import unittest
import numpy as np

from transit_rl.agent.q_learning_agent import QLearningAgent
from transit_rl.config import ExperimentConfig
from transit_rl.data.network import build_network, load_network_from_csv
from transit_rl.data.od_loader import load_od_matrices
from transit_rl.environment.actions import Action, INCREASE_FREQUENCY, DECREASE_FREQUENCY, FINISH_PLAN
from transit_rl.environment.state import state_to_key
from transit_rl.experiment.remaining_action_state import RemainingActionEnvironment, keyed_episode
from transit_rl.experiment.service_diagnostics import DiagnosticEnvironment
from transit_rl.experiment.trainer import run_episode


class RemainingStateTests(unittest.TestCase):
    def fixture(self):
        cfg = replace(ExperimentConfig(), num_stops=3, num_hours=2, max_steps_per_hour=3,
            initial_service_plan=({'route': [1, 2], 'frequency': 4.0},))
        net = build_network([(1, 2, 5), (2, 3, 5)], 3, True)
        od = np.zeros((3, 3))
        od[0, 1] = 100
        return cfg, net, [od, od.copy()]

    def test_same_raw_state_different_deadline_has_distinct_treatment_key(self):
        cfg, net, od = self.fixture()
        env = RemainingActionEnvironment(net, od, cfg)
        raw = state_to_key(env.state)
        key = env.learning_key(env.state)
        self.assertEqual(key[:-1], raw)
        self.assertEqual(key[-1], 3)
        env.step(Action(INCREASE_FREQUENCY, 0))
        env.step(Action(DECREASE_FREQUENCY, 0))
        self.assertEqual(state_to_key(env.state), raw)
        self.assertEqual(env.learning_key(env.state)[:-1], raw)
        self.assertEqual(env.learning_key(env.state)[-1], 1)
        self.assertNotEqual(key, env.learning_key(env.state))
        env.step(Action(FINISH_PLAN))
        self.assertEqual(env.learning_key(env.state)[-1], 3)

    def test_fixed_actions_preserve_physics_reward_and_hour_end(self):
        cfg, net, od = self.fixture()
        a, b = DiagnosticEnvironment(net, od, cfg), RemainingActionEnvironment(net, od, cfg)
        for _ in range(2):
            for action in [Action(INCREASE_FREQUENCY, 0), Action(DECREASE_FREQUENCY, 0), Action(FINISH_PLAN)]:
                self.assertEqual(a.valid_actions(), b.valid_actions())
                self.assertEqual(a.step(action), b.step(action))
        self.assertEqual(a.hourly_records, b.hourly_records)
        self.assertEqual(a.hourly_plans, b.hourly_plans)
        self.assertTrue(a.done and b.done)

    def test_treatment_training_and_diagnostics_use_same_key(self):
        cfg, net, od = self.fixture()
        env = RemainingActionEnvironment(net, od, cfg)
        agent = QLearningAgent(cfg, 2034)
        env.observer_agent = agent
        _, _, steps, unseen = keyed_episode(env, agent, True)
        self.assertEqual(sum(r['unseen_decisions'] for r in env.diagnostics), unseen)
        self.assertEqual(sum(sum(v.values()) for v in agent.visits.values()), steps)
        self.assertTrue(all(len(k) == 7 and 1 <= k[-1] <= 3 for k in agent.q))

    def test_forced_finish_resets_remaining_actions(self):
        cfg, net, od = self.fixture()
        env = RemainingActionEnvironment(net, od, cfg)
        for action in [Action(INCREASE_FREQUENCY, 0), Action(DECREASE_FREQUENCY, 0), Action(INCREASE_FREQUENCY, 0)]:
            result = env.step(action)
        self.assertTrue(env.hourly_records[0]['forced_finish'])
        self.assertEqual(result.next_state.hour, 2)
        self.assertEqual(env.learning_key(result.next_state)[-1], 3)

    def test_control_loop_matches_production_learning_exactly(self):
        cfg = replace(ExperimentConfig(), num_episodes=300)
        net = load_network_from_csv(cfg.links_path, cfg.num_stops, cfg.links_are_bidirectional, cfg.input_stop_id_base)
        od = load_od_matrices(cfg.od_dir, cfg.od_filename_pattern, cfg.num_hours, cfg.num_stops, cfg.od_file_numbers())
        left, right = DiagnosticEnvironment(net, od, cfg), DiagnosticEnvironment(net, od, cfg)
        a, b = QLearningAgent(cfg, 2034), QLearningAgent(cfg, 2034)
        left.observer_agent, right.observer_agent = a, b
        for _ in range(2):
            self.assertEqual(run_episode(left, a, True), keyed_episode(right, b, True))
            self.assertEqual(a.q, b.q)
            self.assertEqual(a.visits, b.visits)
            self.assertEqual(a.rng.getstate(), b.rng.getstate())
            self.assertEqual(left.diagnostics, right.diagnostics)
            a.decay_epsilon()
            b.decay_epsilon()
            self.assertEqual(a.epsilon, b.epsilon)


if __name__ == '__main__':
    unittest.main()
