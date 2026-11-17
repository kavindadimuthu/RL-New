"""EXP-004 deterministic demand-guided feasible reference, not a new RL policy."""
import heapq

from ..environment.actions import (Action, ADD_STOP, END_ROUTE, FINISH_PLAN,
    INCREASE_FREQUENCY, DECREASE_FREQUENCY, REMOVE_ROUTE)
from ..environment.service_plan import RouteService, routes_equivalent, reset_kept_flags


def shortest_path_candidates(network, cfg):
    """One travel-time-shortest path per OD, lexical ties, reversal deduplicated."""
    routes = set()
    for origin in network.stops:
        queue, settled = [(0.0, (origin,))], set()
        while queue:
            cost, path = heapq.heappop(queue)
            stop = path[-1]
            if stop in settled:
                continue
            settled.add(stop)
            if cfg.min_route_length <= len(path) <= cfg.max_route_length:
                routes.add(min(path, path[::-1]) if cfg.routes_are_bidirectional else path)
            for nxt in network.neighbours[stop - 1]:
                if nxt not in path:
                    heapq.heappush(queue, (cost + network.link_time(stop, nxt), path + (nxt,)))
    return sorted(routes)


def direct_mass(route, residual, bidirectional):
    value = sum(float(residual[a-1, b-1]) for i, a in enumerate(route) for b in route[i+1:])
    if bidirectional:
        value += sum(float(residual[b-1, a-1]) for i, a in enumerate(route) for b in route[i+1:])
    return value


class ReferencePlanner:
    def __init__(self, env, candidates, max_evaluations=2000, max_edits=120):
        self.env, self.cfg, self.candidates = env, env.cfg, candidates
        self.max_evaluations, self.max_edits = max_evaluations, max_edits

    def plan_hour(self, hour, previous):
        self.env.hour, self.env.previous_plan = hour, previous
        plan = reset_kept_flags(previous)
        requests, edits, actions, accepted = 0, 0, [], []

        def evaluate(candidate):
            nonlocal requests
            requests += 1
            return self.env.evaluate_plan(candidate)

        current = evaluate(plan)

        def remaining():
            return requests < self.max_evaluations and edits < self.max_edits

        def rank(count):
            residual = current.assignment.unserved_demand
            return sorted(self.candidates, key=lambda r: (-direct_mass(r, residual,
                          self.cfg.routes_are_bidirectional), r))[:count]

        def exists(route, candidate):
            return any(routes_equivalent(route, r.route, self.cfg.routes_are_bidirectional) for r in candidate)

        def new_route(base, route):
            if exists(route, base):
                return None
            frequency = self.env.fleet.initial_frequency_for_new_route(route,
                            self.cfg.max_fleet - self.env.fleet.fleet_used(base))
            return None if frequency is None else RouteService(route, frequency, False)

        def construction(route):
            return [Action(ADD_STOP, stop) for stop in route] + [Action(END_ROUTE)]

        def select(options):
            best = None
            score = current.reward['total_reward']
            for candidate, trace, label in options:
                if not remaining():
                    break
                result = evaluate(candidate)
                if result.reward['total_reward'] > score + 1e-12:
                    score = result.reward['total_reward']
                    best = candidate, result, trace, label
            return best

        def accept(best):
            nonlocal plan, current, edits
            if best is None:
                return False
            plan, current, trace, label = best
            actions.extend(trace)
            edits += 1
            accepted.append(dict(edit=edits, type=label, score=current.reward['total_reward'],
                                 served=current.assignment.served_passengers, requests=requests))
            return True

        def frequency_moves():
            for k, route in enumerate(plan):
                for delta, kind in ((self.cfg.frequency_step, INCREASE_FREQUENCY),
                                    (-self.cfg.frequency_step, DECREASE_FREQUENCY)):
                    f = round(route.frequency + delta, 10)
                    if self.cfg.min_frequency <= f <= self.cfg.max_frequency:
                        candidate = plan[:k] + (route._replace(frequency=f),) + plan[k+1:]
                        if self.env.fleet.fleet_used(candidate) <= self.cfg.max_fleet:
                            yield candidate, [Action(kind, k)], 'frequency'

        def improve_frequencies():
            while remaining() and accept(select(frequency_moves())):
                pass

        # Construct up to eight routes, then allocate frequencies by original score.
        while len(plan) < self.cfg.max_routes and remaining():
            options = []
            for route in rank(24):
                added = new_route(plan, route)
                if added is not None:
                    options.append((plan + (added,), construction(route), 'add'))
            if not accept(select(options)):
                break
        improve_frequencies()

        # Up to three best-improvement removal/replacement rounds; frequency
        # refinement follows each accepted edit. Replacement appends its new route.
        for _ in range(3):
            if not remaining():
                break
            options = []
            shortlist = rank(12)
            for k in range(len(plan)):
                base = plan[:k] + plan[k+1:]
                options.append((base, [Action(REMOVE_ROUTE, k)], 'remove'))
                for route in shortlist:
                    added = new_route(base, route)
                    if added is not None:
                        options.append((base + (added,), [Action(REMOVE_ROUTE, k)] + construction(route), 'replace'))
            if not accept(select(options)):
                break
            improve_frequencies()
        actions.append(Action(FINISH_PLAN))
        return dict(plan=plan, evaluation=current, actions=actions, accepted=accepted,
                    requests=requests, edits=edits,
                    evaluation_budget_reached=requests >= self.max_evaluations,
                    edit_budget_reached=edits >= self.max_edits)
