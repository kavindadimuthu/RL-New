"""EXP-004 S4 observation-only treatment; transport state and dynamics unchanged."""
from .service_diagnostics import DiagnosticEnvironment


class RemainingActionEnvironment(DiagnosticEnvironment):
    def learning_key(self, state):
        remaining = self.cfg.max_steps_per_hour - self.steps_in_hour
        if not 1 <= remaining <= self.cfg.max_steps_per_hour:
            raise ValueError('Learning key requested outside active decision boundary')
        return super().learning_key(state) + (remaining,)


def keyed_episode(env, agent, train):
    """Same Q-learning loop as trainer.run_episode; use env's registered key."""
    state = env.reset()
    key = env.learning_key(state)
    valid = env.valid_actions()
    total, steps, unseen = 0.0, 0, 0
    while True:
        if key not in agent.q:
            unseen += 1
        action = agent.select_action(key, valid, greedy=not train)
        result = env.step(action)
        steps += 1
        total += result.reward
        if result.done:
            if train:
                agent.update(key, action, result.reward, None, [], True)
            break
        next_key = env.learning_key(result.next_state)
        next_valid = env.valid_actions()
        if train:
            agent.update(key, action, result.reward, next_key, next_valid, False)
        key, valid = next_key, next_valid
    return total, env.hourly_records, steps, unseen
