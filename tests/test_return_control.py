from dataclasses import replace
import unittest
from unittest.mock import patch
import numpy as np
from tests import test_linear_q as fixtures
from transit_rl.experiment.linear_q import LinearQAgent
from transit_rl.experiment.return_control import ReturnAgent,comparison_episode
from transit_rl.experiment.remaining_action_state import keyed_episode
from transit_rl.experiment.service_baseline import learner_digest,evaluate
from transit_rl.environment.actions import Action,INCREASE_FREQUENCY
from pathlib import Path
import tempfile


class ReturnControlTests(unittest.TestCase):
    def test_mc_waits_for_terminal_and_uses_every_actual_suffix(self):
        cfg,net,env=fixtures.LinearQTests().fixture()
        agent=ReturnAgent(cfg,2034,net)
        original=agent.update_return
        calls=[]
        def update(key,action,target):
            self.assertTrue(env.done)
            calls.append(target)
            return original(key,action,target)
        with patch.object(agent,'update_return',side_effect=update):
            total,_,steps,_,audit=comparison_episode(env,agent,True)
        self.assertEqual(len(calls),steps)
        self.assertAlmostEqual(calls[0],total)
        future=0
        for row in reversed(audit):
            future+=row['reward']
            self.assertAlmostEqual(row['target'],future)
        self.assertAlmostEqual(audit[-1]['target'],audit[-1]['reward'])
        self.assertTrue(all(row['q_at_collection']==0 for row in audit))
        self.assertEqual(sum(sum(v.values()) for v in agent.visits.values()),steps)

    def test_control_reproduces_original_td_loop(self):
        cfg,net,left=fixtures.LinearQTests().fixture()
        _,_,right=fixtures.LinearQTests().fixture()
        a,b=LinearQAgent(cfg,2034,net),LinearQAgent(cfg,2034,net)
        self.assertEqual(keyed_episode(left,a,True),comparison_episode(right,b,False)[:4])
        np.testing.assert_array_equal(a.weights,b.weights)
        self.assertEqual(learner_digest(a),learner_digest(b))

    def test_initial_random_physics_match_and_returns_do_not_cross_days(self):
        cfg,net,left=fixtures.LinearQTests().fixture()
        _,_,right=fixtures.LinearQTests().fixture()
        a,b=LinearQAgent(cfg,2034,net),ReturnAgent(cfg,2034,net)
        self.assertEqual(comparison_episode(left,a,False)[:4],comparison_episode(right,b,True)[:4])
        self.assertEqual(a.rng.getstate(),b.rng.getstate())
        _,_,_,_,audit=comparison_episode(right,b,True)
        self.assertAlmostEqual(audit[0]['target'],sum(r['reward'] for r in audit))

    def test_return_update_is_gradient_not_max_record_and_evaluation_is_read_only(self):
        cfg,net,env=fixtures.LinearQTests().fixture()
        agent=ReturnAgent(cfg,0,net);key=env.learning_key(env.state);action=Action(INCREASE_FREQUENCY,0)
        agent.observe(key,action)
        agent.update_return(key,action,1)
        first=agent.q_value(key,action)
        agent.update_return(key,action,-1)
        self.assertLess(agent.q_value(key,action),first)
        before=learner_digest(agent)
        with tempfile.TemporaryDirectory() as directory:
            self.assertTrue(evaluate(agent,cfg,net,env.od_matrices,0,Path(directory),type(env))['learner_unchanged'])
        self.assertEqual(before,learner_digest(agent))
        with self.assertRaises(FloatingPointError):
            agent.update_return(key,action,float('nan'))
