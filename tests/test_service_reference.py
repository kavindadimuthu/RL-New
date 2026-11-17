import unittest
from dataclasses import replace

import numpy as np

from transit_rl.config import ExperimentConfig
from transit_rl.data.network import build_network, route_is_physical_path
from transit_rl.environment.transit_environment import TransitEnvironment
from transit_rl.experiment.service_reference import ReferencePlanner, shortest_path_candidates, direct_mass


class ReferenceTests(unittest.TestCase):
    def fixture(self):
        cfg = replace(ExperimentConfig(), num_stops=4, num_hours=2, max_routes=2,
                      max_route_length=4, max_fleet=10)
        net = build_network([(1, 2, 5), (2, 3, 5), (3, 4, 5)], 4, True)
        od = np.zeros((4, 4))
        od[0, 3], od[1, 2], od[3, 0] = 300, 80, 120
        return cfg, net, [od, od.copy()]

    def test_candidates_are_connected_bounded_and_unique(self):
        cfg, net, od = self.fixture()
        routes = shortest_path_candidates(net, cfg)
        self.assertEqual(len(routes), 6)
        self.assertEqual(len(routes), len(set(routes)))
        for route in routes:
            self.assertTrue(route_is_physical_path(net, route))
            self.assertTrue(2 <= len(route) <= 4)
            self.assertEqual(len(route), len(set(route)))
        self.assertEqual(direct_mass((1, 2, 3, 4), od[0], True), 500)
        self.assertEqual(direct_mass((1, 2, 3, 4), od[0], False), 380)

    def test_reference_is_deterministic_monotone_feasible_and_replayable(self):
        cfg, net, od = self.fixture()
        routes = shortest_path_candidates(net, cfg)
        traces = []
        for repeat in range(2):
            env = TransitEnvironment(net, od, cfg)
            planner = ReferencePlanner(env, routes, max_evaluations=150)
            previous, results = (), []
            for hour in (1, 2):
                result = planner.plan_hour(hour, previous)
                self.assertLessEqual(result['requests'], 150)
                self.assertLessEqual(result['edits'], 120)
                self.assertLessEqual(len(result['plan']), 2)
                self.assertLessEqual(env.fleet.fleet_used(result['plan']), 10)
                scores = [r['score'] for r in result['accepted']]
                self.assertTrue(all(b > a for a, b in zip(scores, scores[1:])))
                previous = result['plan']
                results.append(result)
            replay = TransitEnvironment(net, od, replace(cfg, max_steps_per_hour=500))
            rewards = 0
            for hour, result in enumerate(results, 1):
                for action in result['actions']:
                    rewards += replay.step(action).reward
                self.assertEqual(replay.hourly_plans[hour], result['plan'])
                self.assertAlmostEqual(replay.hourly_records[-1]['total_reward'],
                                       result['evaluation'].reward['total_reward'])
                self.assertAlmostEqual(replay.hourly_records[-1]['served_passengers'],
                                       result['evaluation'].assignment.served_passengers)
            self.assertTrue(replay.done)
            self.assertGreater(replay.hourly_records[0]['served_passengers'], 0)
            self.assertAlmostEqual(rewards, sum(r['total_reward'] for r in replay.hourly_records))
            traces.append([(r['plan'], r['actions'], r['requests']) for r in results])
        self.assertEqual(traces[0], traces[1])

    def test_tiny_search_budget_is_respected(self):
        cfg, net, od = self.fixture()
        env = TransitEnvironment(net, od, cfg)
        result = ReferencePlanner(env, shortest_path_candidates(net, cfg), max_evaluations=1).plan_hour(1, ())
        self.assertEqual(result['requests'], 1)
        self.assertEqual(result['edits'], 0)
        self.assertEqual(result['plan'], ())
        self.assertTrue(result['evaluation_budget_reached'])

    def test_action_budget_reserves_finish_and_never_commits_partial_edit(self):
        cfg, net, od = self.fixture()
        candidates = shortest_path_candidates(net, cfg)
        with self.assertRaises(ValueError):
            ReferencePlanner(TransitEnvironment(net, od, cfg), candidates, action_limit=0)
        for limit in (1, 2, 3, 4, 6, 60):
            settings = replace(cfg, max_steps_per_hour=limit)
            planning = TransitEnvironment(net, od, settings)
            planner = ReferencePlanner(planning, candidates, max_evaluations=150, action_limit=limit)
            replay = TransitEnvironment(net, od, settings)
            previous = ()
            for hour in (1, 2):
                result = planner.plan_hour(hour, previous)
                self.assertLessEqual(len(result['actions']), limit)
                self.assertEqual(result['actions'][-1].type, 'FINISH_PLAN')
                for action in result['actions']:
                    step = replay.step(action)
                self.assertFalse(replay.hourly_records[-1]['forced_finish'])
                self.assertEqual(replay.hourly_plans[hour], result['plan'])
                self.assertFalse(replay.current_route)
                previous = result['plan']
            self.assertTrue(replay.done)


if __name__ == '__main__':
    unittest.main()
