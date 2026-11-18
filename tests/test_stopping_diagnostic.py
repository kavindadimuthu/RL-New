import unittest
from tests import test_linear_q as fixtures
from transit_rl.environment.actions import Action, FINISH_PLAN, ADD_STOP, END_ROUTE
from transit_rl.experiment.stopping_diagnostic import returns_to_go, replay, stop_continuation


class StoppingDiagnosticTests(unittest.TestCase):
    def test_suffix_is_remaining_reward_not_whole_day_reward(self):
        for actual, expected in zip(returns_to_go([-.2,.5,-.1]), [.2,.4,-.1]):
            self.assertAlmostEqual(actual, expected)

    def test_stop_continuation_replays_prefix_without_counting_its_rewards(self):
        _,_,env=fixtures.LinearQTests().fixture()
        env.reset()
        prefix=[Action(ADD_STOP,2),Action(ADD_STOP,3),Action(END_ROUTE)]
        prefix_rewards=replay(env,prefix)
        after=stop_continuation(env,prefix)
        self.assertTrue(env.done)
        self.assertAlmostEqual(sum(prefix_rewards)+after['remaining_return'],after['daily']['daily_plan_reward'])

    def test_invalid_fixed_action_is_rejected(self):
        _,_,env=fixtures.LinearQTests().fixture()
        with self.assertRaises(AssertionError):
            replay(env,[Action(END_ROUTE)])
