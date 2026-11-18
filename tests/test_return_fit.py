import unittest
import numpy as np
from tests import test_linear_q as fixtures
from transit_rl.environment.actions import Action, INCREASE_FREQUENCY
from transit_rl.experiment.linear_q import LinearQAgent
from transit_rl.experiment.return_fit import fit_linear,design_vector


class ReturnFitTests(unittest.TestCase):
    def test_fit_recovers_representable_targets(self):
        x=np.array([[1.,0.],[0.,1.],[1.,1.]])
        y=x@np.array([2.,-3.])
        fit=fit_linear(x,y)
        np.testing.assert_allclose(x@fit['weights'],y,atol=1e-12)
        self.assertEqual(fit['rank'],2)

    def test_identical_features_cannot_fit_conflicting_returns(self):
        fit=fit_linear(np.array([[1.,0.],[1.,0.]]),np.array([0.,2.]))
        self.assertAlmostEqual(fit['weights'][0],1.)

    def test_ridge_and_block_design_match_actual_update(self):
        cfg,net,env=fixtures.LinearQTests().fixture()
        agent=LinearQAgent(cfg,0,net)
        key=env.learning_key(env.state); action=Action(INCREASE_FREQUENCY,0)
        x=design_vector(agent,key,action)
        agent.update(key,action,1,None,[],True)
        self.assertAlmostEqual(float(x@agent.weights.ravel()),agent.q_value(key,action))
        self.assertAlmostEqual(agent.q_value(key,action),cfg.learning_rate)
        fit=fit_linear(np.array([[1.,0.]]),np.array([2.]),.001)
        self.assertAlmostEqual(fit['weights'][0],2/1.001)
