"""Checks that observing training preserves learning, including hour boundaries."""
import unittest
from dataclasses import replace
import numpy as np
from transit_rl.config import ExperimentConfig
from transit_rl.data.network import build_network
from transit_rl.agent.q_learning_agent import QLearningAgent
from transit_rl.environment.transit_environment import TransitEnvironment
from transit_rl.experiment.trainer import run_episode
from transit_rl.visualizer import VisualSession


class VisualizerModelTests(unittest.TestCase):
    def setUp(self):
        self.cfg=replace(ExperimentConfig(),num_stops=3,num_hours=2,od_start_file_hour=0,
                         max_route_length=3,max_routes=2,max_steps_per_hour=12)
        self.network=build_network([(1,2,5),(2,3,5)],3,True)
        self.od=[np.array([[0,20,50],[20,0,20],[50,20,0]],dtype=float) for _ in range(2)]

    def test_observation_preserves_two_training_episodes(self):
        viewer=VisualSession(self.cfg,seed=2024,target=2,network=self.network,od=self.od)
        env=TransitEnvironment(self.network,self.od,self.cfg)
        agent=QLearningAgent(self.cfg,2024)
        expected=[]
        for _ in range(2):
            expected.append(run_episode(env,agent,train=True)[0])
            agent.decay_epsilon()
        while not viewer.finished:
            event=viewer.step()
            if event['hour_finished']:
                self.assertEqual(event['fleet_used'],event['metrics']['total_fleet_used'])
                self.assertFalse(event['route'])
        self.assertEqual(viewer.agent.q,agent.q)
        self.assertEqual(viewer.agent.visits,agent.visits)
        self.assertEqual(viewer.agent.rng.getstate(),agent.rng.getstate())
        self.assertEqual([c['reward'] for c in viewer.curves],expected)
        self.assertAlmostEqual(viewer.agent.epsilon,agent.epsilon)
        self.assertEqual(len(viewer.completed_history),viewer.steps)

    def test_evaluation_does_not_update_q_or_visits(self):
        session=VisualSession(self.cfg,target=1,network=self.network,od=self.od)
        while not session.finished:
            session.step(greedy=True)
        self.assertEqual(session.agent.q,{})
        self.assertEqual(session.agent.visits,{})
        self.assertEqual(session.agent.epsilon,self.cfg.initial_epsilon)

    def test_fast_capture_off_preserves_training(self):
        a=VisualSession(self.cfg,target=1,network=self.network,od=self.od)
        b=VisualSession(self.cfg,target=1,network=self.network,od=self.od)
        while not a.finished: a.step(capture=True)
        while not b.finished: b.step(capture=False)
        self.assertEqual(a.agent.q,b.agent.q)
        self.assertEqual(a.curves,b.curves)


if __name__=='__main__':
    unittest.main()
