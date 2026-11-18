"""EXP-004 S9: one-step linear Q versus episodic every-visit return regression."""
import math
import numpy as np
from .linear_q import LinearQAgent


class ReturnAgent(LinearQAgent):
    def observe(self, key, action):
        """Same exact-key diagnostic presence timing as the TD control, no value update."""
        row = self.q.setdefault(key, {})
        if action not in row:
            self._num_pairs += 1
        row[action] = 0.0
        visits = self.visits.setdefault(key, {})
        visits[action] = visits.get(action, 0)+1

    def update_return(self, key, action, target):
        if not math.isfinite(target):
            raise FloatingPointError('Nonfinite realized return')
        error = target-self.q_value(key, action)
        index = self.encoder.type_index[action.type]
        proposed = self.weights[index]+self.alpha*error*self.encoder.features(key, action)
        if not np.all(np.isfinite(proposed)) or np.linalg.norm(proposed)>10000:
            raise FloatingPointError('Registered linear weight stability guard exceeded')
        self.weights[index] = proposed
        return float(error)

    def snapshot(self):
        value = super().snapshot()
        value.update(model='linear_every_visit_on_policy_return_regression',
                     update_order='chronological_after_episode', bootstrap=False)
        return value


def comparison_episode(env, agent, monte_carlo):
    """Collect one day. MC holds weights fixed during collection; epsilon fixed per day."""
    state = env.reset()
    key = env.learning_key(state)
    valid = env.valid_actions()
    total, steps, unseen = 0.0, 0, 0
    trajectory, audit = [], []
    while True:
        if key not in agent.q:
            unseen += 1
        action = agent.select_action(key, valid, greedy=False)
        result = env.step(action)
        total += result.reward
        steps += 1
        row = dict(step=steps, hour=key[0], action=action._asdict(), reward=result.reward,
                   done=result.done, q_at_collection=agent.q_value(key, action))
        if monte_carlo:
            agent.observe(key, action)
            trajectory.append((key, action, result.reward))
        else:
            next_key = None if result.done else env.learning_key(result.next_state)
            next_valid = [] if result.done else env.valid_actions()
            error = agent.update(key, action, result.reward, next_key, next_valid, result.done)
            row.update(q_before_update=row['q_at_collection'], target=row['q_at_collection']+error, td_error=error)
        audit.append(row)
        if result.done:
            break
        key = env.learning_key(result.next_state)
        valid = env.valid_actions()
    if monte_carlo:
        returns, accumulated = [], 0.0
        for _, _, reward in reversed(trajectory):
            accumulated = reward+agent.gamma*accumulated
            returns.append(accumulated)
        returns.reverse()
        assert math.isclose(returns[0], total, abs_tol=1e-8)  # gamma=1 registered
        for (key, action, _), target, row in zip(trajectory, returns, audit):
            before = agent.q_value(key, action)
            error = agent.update_return(key, action, target)
            row.update(q_before_update=before, target=target, td_error=error)
    return total, env.hourly_records, steps, unseen, audit
