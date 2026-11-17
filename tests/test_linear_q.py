from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
from transit_rl.agent.q_learning_agent import QLearningAgent
from transit_rl.config import ExperimentConfig
from transit_rl.data.network import build_network
from transit_rl.environment.actions import Action, INCREASE_FREQUENCY, FINISH_PLAN
from transit_rl.experiment.remaining_action_state import RemainingActionEnvironment, keyed_episode
from transit_rl.experiment.linear_q import LinearQAgent, FeatureEncoder, FEATURE_NAMES
from transit_rl.experiment.service_baseline import learner_digest, evaluate


class LinearQTests(unittest.TestCase):
    def fixture(self):
        cfg = replace(ExperimentConfig(), num_stops=3, num_hours=2, max_steps_per_hour=8,
            initial_service_plan=({'route': [1, 2], 'frequency': 4.0},))
        net = build_network([(1, 2, 5), (2, 3, 5)], 3, True)
        od = np.zeros((3, 3))
        od[0, 1], od[0, 2] = 200, 100
        return cfg, net, RemainingActionEnvironment(net, [od, od.copy()], cfg)

    def test_features_are_pure_finite_unit_vectors(self):
        cfg, net, env = self.fixture()
        encoder = FeatureEncoder(net, cfg)
        key = env.learning_key(env.state)
        original = env.state
        with patch('transit_rl.environment.passenger_assignment.PassengerAssignment.assign', side_effect=AssertionError('Feature lookahead')):
            for action in env.valid_actions():
                vector = encoder.features(key, action)
                self.assertEqual(vector.shape, (32,))
                self.assertEqual(len(FEATURE_NAMES), 32)
                self.assertTrue(np.all(np.isfinite(vector)))
                self.assertAlmostEqual(float(np.linalg.norm(vector)), 1)
                self.assertFalse(vector.flags.writeable)
                np.testing.assert_array_equal(vector, encoder.features(key, action))
        self.assertEqual(original, env.state)

    def test_unit_gradient_update_and_sharing(self):
        cfg, net, env = self.fixture()
        agent = LinearQAgent(cfg, 10, net)
        key = env.learning_key(env.state)
        action = Action(INCREASE_FREQUENCY, 0)
        self.assertEqual(agent.q_value(key, action), 0)
        self.assertEqual(agent.update(key, action, 1, None, [], True), 1)
        self.assertAlmostEqual(agent.q_value(key, action), cfg.learning_rate)
        other = key[:-1] + (key[-1]-1,)
        self.assertNotIn(other, agent.q)
        self.assertGreater(agent.q_value(other, action), 0)
        self.assertEqual(agent.q_value(other, Action(FINISH_PLAN)), 0)
        self.assertEqual(agent.greedy_action(other, [Action(FINISH_PLAN), action]), action)
        self.assertEqual(agent.greedy_audit['unseen_unique_best'], 1)
        self.assertEqual(agent.visits[key][action], 1)

    def test_action_mask_and_single_valid_audit(self):
        cfg, net, env = self.fixture()
        agent = LinearQAgent(cfg, 11, net)
        action = Action(FINISH_PLAN)
        self.assertEqual(agent.select_action(env.learning_key(env.state), [action], greedy=True), action)
        self.assertEqual(agent.greedy_audit['unseen_single_valid'], 1)
        self.assertEqual(agent.weights.shape, (8, 32))

    def test_zero_evaluation_and_first_random_physics_match_table(self):
        cfg, net, a = self.fixture()
        _, _, b = self.fixture()
        left, right = QLearningAgent(cfg, 2034), LinearQAgent(cfg, 2034, net)
        self.assertEqual(keyed_episode(a, left, False), keyed_episode(b, right, False))
        self.assertEqual(left.rng.getstate(), right.rng.getstate())
        left, right = QLearningAgent(cfg, 2034), LinearQAgent(cfg, 2034, net)
        self.assertEqual(keyed_episode(a, left, True)[:3], keyed_episode(b, right, True)[:3])
        self.assertEqual(left.rng.getstate(), right.rng.getstate())

    def test_stability_guard_fails_instead_of_clipping(self):
        cfg, net, env = self.fixture()
        agent = LinearQAgent(cfg, 0, net)
        agent.weights.fill(2000)
        with self.assertRaises(FloatingPointError):
            agent.max_q(env.learning_key(env.state), env.valid_actions())

    def test_digest_and_read_only_evaluation_include_weights(self):
        cfg, net, env = self.fixture()
        agent = LinearQAgent(cfg, 0, net)
        before = learner_digest(agent)
        agent.weights[0, 0] = .01
        self.assertNotEqual(before, learner_digest(agent))
        before = learner_digest(agent)
        with tempfile.TemporaryDirectory() as directory:
            value = evaluate(agent, cfg, net, env.od_matrices, 0, Path(directory), RemainingActionEnvironment)
            self.assertTrue(value['learner_unchanged'])
        self.assertEqual(before, learner_digest(agent))
        self.assertEqual(len(agent.encoder.contexts), 0)


if __name__ == '__main__':
    unittest.main()
