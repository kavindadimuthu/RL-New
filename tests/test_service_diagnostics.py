import unittest
from dataclasses import replace

import numpy as np

from transit_rl.agent.q_learning_agent import QLearningAgent
from transit_rl.config import ExperimentConfig
from transit_rl.data.network import build_network, load_network_from_csv
from transit_rl.data.od_loader import load_od_matrices
from transit_rl.environment.actions import Action, ADD_STOP
from transit_rl.environment.passenger_assignment import PassengerAssignment
from transit_rl.environment.service_plan import RouteService
from transit_rl.environment.transit_environment import TransitEnvironment
from transit_rl.experiment.service_diagnostics import DiagnosticEnvironment, unmet_breakdown
from transit_rl.experiment.trainer import run_episode
from transit_rl.experiment.service_baseline import learner_digest, diagnostic_summary


class DiagnosticTests(unittest.TestCase):
    def test_learner_digest_detects_mutation(self):
        agent = QLearningAgent(ExperimentConfig(), 99)
        before = learner_digest(agent)
        agent.q[('state',)] = {Action(ADD_STOP, 1): 3.0}
        self.assertNotEqual(before, learner_digest(agent))
        before = learner_digest(agent)
        agent.visits[('state',)] = {Action(ADD_STOP, 1): 1}
        self.assertNotEqual(before, learner_digest(agent))
        before = learner_digest(agent)
        agent.rng.random()
        self.assertNotEqual(before, learner_digest(agent))

    def fixture(self):
        cfg = replace(ExperimentConfig(), num_stops=4, num_hours=1)
        net = build_network([(1, 2, 5), (2, 3, 5), (3, 4, 5)], 4, True)
        od = np.zeros((4, 4))
        od[0, 1] = 150
        od[0, 3] = 40
        return cfg, net, [od]

    def test_missing_connection_and_capacity_are_separate(self):
        cfg, net, od = self.fixture()
        assigner = PassengerAssignment(net, cfg, od)
        plan = (RouteService((1, 2), 1, False),)
        actual = assigner.assign(1, plan)
        result = unmet_breakdown(assigner, 1, plan, actual)
        self.assertEqual(result['no_eligible_path_unserved'], 40)
        self.assertEqual(result['capacity_constrained_unserved'], 100)

    def test_transfers_and_trip_limit_use_operational_path_rules(self):
        cfg, net, od = self.fixture()
        plan = (RouteService((1, 2), 4, False), RouteService((2, 3, 4), 4, False))
        for limited in (False, True):
            settings = replace(cfg, max_acceptable_trip_minutes=1 if limited else None)
            assigner = PassengerAssignment(net, settings, od)
            result = unmet_breakdown(assigner, 1, plan, assigner.assign(1, plan))
            self.assertEqual(result['no_eligible_path_unserved'], 190 if limited else 0)

    def test_forced_discard_is_recorded(self):
        cfg, net, od = self.fixture()
        env = DiagnosticEnvironment(net, od, replace(cfg, max_steps_per_hour=2))
        env.step(Action(ADD_STOP, 1))
        result = env.step(Action(ADD_STOP, 2))
        self.assertTrue(result.done)
        row = env.diagnostics[0]
        self.assertEqual(row['discarded_unfinished_route'], [1, 2])
        self.assertEqual(row['discarded_tentative_served_delta'], 150)
        self.assertEqual(sum(row['action_counts'].values()), 2)
        self.assertNotIn('_finish_state', row)
        summary = diagnostic_summary(env.diagnostics)
        self.assertAlmostEqual(summary['served_ratio'] + summary['no_path_demand_share']
                               + summary['capacity_demand_share'], 1)
        self.assertEqual(summary['forced_finishes'], 1)
        self.assertIsNone(summary['voluntary_served_ratio'])

    def test_real_two_episode_learning_is_unchanged(self):
        cfg = replace(ExperimentConfig(), num_episodes=300)
        net = load_network_from_csv(cfg.links_path, cfg.num_stops,
                                    cfg.links_are_bidirectional, cfg.input_stop_id_base)
        od = load_od_matrices(cfg.od_dir, cfg.od_filename_pattern, cfg.num_hours,
                             cfg.num_stops, cfg.od_file_numbers())
        baseline = TransitEnvironment(net, od, cfg)
        observed = DiagnosticEnvironment(net, od, cfg)
        a, b = QLearningAgent(cfg, 2034), QLearningAgent(cfg, 2034)
        observed.observer_agent = b
        traces = [[], []]
        for env, trace in zip((baseline, observed), traces):
            original = env.step
            def traced(action, original=original, trace=trace):
                result = original(action)
                trace.append((action, result.reward, result.next_state, result.done, result.info))
                return result
            env.step = traced
        for _ in range(2):
            left = run_episode(baseline, a, True)
            right = run_episode(observed, b, True)
            self.assertEqual(left, right)
            self.assertEqual(traces[0], traces[1])
            self.assertEqual(a.q, b.q)
            self.assertEqual(a.visits, b.visits)
            self.assertEqual(a.rng.getstate(), b.rng.getstate())
            self.assertEqual(baseline.hourly_plans, observed.hourly_plans)
            self.assertEqual(baseline.assigner.cache_hits, observed.assigner.cache_hits)
            self.assertEqual(baseline.assigner.cache_misses, observed.assigner.cache_misses)
            self.assertEqual(len(observed.diagnostics), 24)
            for row in observed.diagnostics:
                self.assertEqual(row['actions'], sum(row['action_counts'].values()))
                self.assertEqual(row['actions'], len(row['state_visits_before_decision']))
                self.assertAlmostEqual(row['served_passengers'] + row['no_eligible_path_unserved']
                                       + row['capacity_constrained_unserved'], row['total_demand'])
            a.decay_epsilon()
            b.decay_epsilon()
            self.assertEqual(a.epsilon, b.epsilon)


if __name__ == '__main__':
    unittest.main()
