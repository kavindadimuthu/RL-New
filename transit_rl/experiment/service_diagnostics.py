"""EXP-004 observation-only diagnostics; production environment is unchanged."""
from collections import Counter
import math

from ..environment.passenger_assignment import PassengerAssignment, _RouteIndex
from ..environment.state import state_to_key
from ..environment.transit_environment import TransitEnvironment
from ..environment.service_plan import RouteService


def unmet_breakdown(assigner, hour, plan, actual):
    """Classify actual unmet OD using identical path rules with unlimited capacity.

    This is path eligibility, not a globally optimized throughput calculation.
    Uses a separate assigner so operational caches/counters remain untouched.
    """
    routes = [_RouteIndex(r.route, r.frequency, assigner._table(r.route),
                          assigner.cfg.waiting_time_factor) for r in plan]
    routes_at = {s: [k for k, r in enumerate(routes) if s in r.pos]
                 for s in assigner.network.stops}
    common = [[tuple(sorted(set(a.pos) & set(b.pos))) if i != j else ()
               for j, b in enumerate(routes)] for i, a in enumerate(routes)]
    no_path = capacity = eligible = 0.0
    for i, j, demand in assigner._pairs[hour - 1]:
        path = assigner._choose_path(i, j, routes, routes_at, common,
                                     lambda k, a, b: math.inf)
        unmet = float(actual.unserved_demand[i - 1, j - 1])
        if path is None:
            no_path += unmet
            if actual.assigned_demand[i - 1, j - 1] > 1e-7:
                raise AssertionError('Served OD has no capacity-free eligible path')
        else:
            eligible += demand
            capacity += unmet
    assert math.isclose(no_path + capacity, actual.unserved_passengers, abs_tol=1e-6)
    return dict(no_eligible_path_unserved=no_path, capacity_constrained_unserved=capacity,
                eligible_path_demand=eligible)


class DiagnosticEnvironment(TransitEnvironment):
    """Wrap step/finish boundaries without replacing transport or reward logic."""
    def __init__(self, *args, **kwargs):
        self.observer_agent = None
        super().__init__(*args, **kwargs)
        self.diagnostic_assigner = PassengerAssignment(self.network, self.cfg, self.od_matrices)

    def reset(self):
        self.diagnostics = []
        self._reset_counters()
        return super().reset()

    def _reset_counters(self):
        self._actions = Counter()
        self._state_visits = []
        self._action_visits = []
        self._unseen = 0
        self._rare = 0

    def step(self, action):
        if action not in self.valid_actions():
            return super().step(action)
        self._actions[action.type] += 1
        if self.observer_agent is not None:
            agent = self.observer_agent
            key = state_to_key(self.state)
            visits = agent.visits.get(key, {})
            total = sum(visits.values())
            self._state_visits.append(total)
            self._action_visits.append(visits.get(action, 0))
            self._unseen += key not in agent.q
            self._rare += total < 5
        result = super().step(action)
        if 'hour_finished' in result.info:
            discarded = tuple(result.info.get('discarded_unfinished_route', []))
            row = self.diagnostics[-1]
            row['discarded_unfinished_route'] = list(discarded)
            row['discarded_tentative_served_delta'] = None
            if discarded:
                state = row.pop('_finish_state')
                candidate = state._replace(current_route=discarded)
                frequency = self.masker.end_route_frequency(candidate)
                if frequency is not None:
                    plan = state.current_plan + (RouteService(discarded, frequency, False),)
                    tentative = self.diagnostic_assigner.assign(row['hour'], plan)
                    row['discarded_tentative_served_delta'] = (
                        tentative.served_passengers - row['served_passengers'])
            row.pop('_finish_state', None)
            self._reset_counters()
        return result

    def _finish_hour(self, forced, info):
        state = self.state
        # Independent evaluation: no operational cache, timing or RNG mutation.
        actual = self.diagnostic_assigner.assign(self.hour, self.current_plan)
        breakdown = unmet_breakdown(self.diagnostic_assigner, self.hour, self.current_plan, actual)
        capacities = [r.frequency * self.cfg.bus_capacity * self.cfg.bus_load_factor
                      for r in self.current_plan]
        peak_ratios = [peak / cap for peak, cap in zip(actual.route_peak_load, capacities)]
        row = dict(hour=self.hour, clock_hour=self.cfg.od_file_number(self.hour),
                   total_demand=actual.total_demand, served_passengers=actual.served_passengers,
                   unserved_passengers=actual.unserved_passengers, **breakdown,
                   fleet_used=self.fleet.fleet_used(self.current_plan),
                   fleet_remaining=state.fleet_remaining, route_count=len(self.current_plan),
                   routes=[list(r.route) for r in self.current_plan],
                   route_lengths=[len(r.route) for r in self.current_plan],
                   frequencies=[r.frequency for r in self.current_plan],
                   route_peak_capacity_ratios=peak_ratios,
                   saturated_route_count=sum(x >= 1 - 1e-9 for x in peak_ratios),
                   forced_finish=forced, action_counts=dict(self._actions),
                   actions=self.steps_in_hour, unseen_decisions=self._unseen,
                   rare_state_decisions_lt5=self._rare,
                   state_visits_before_decision=self._state_visits,
                   selected_action_visits_before_decision=self._action_visits,
                   _finish_state=state)
        self.diagnostics.append(row)
        return super()._finish_hour(forced, info)
