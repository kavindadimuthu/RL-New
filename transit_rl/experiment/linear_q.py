"""EXP-004 S5: normalized linear semi-gradient Q, no candidate-plan scoring."""
import math
from collections import OrderedDict

import numpy as np

from ..agent.q_learning_agent import QLearningAgent
from ..environment.actions import (ACTION_TYPES, ADD_STOP, REMOVE_LAST_STOP, END_ROUTE,
    INCREASE_FREQUENCY, DECREASE_FREQUENCY, KEEP_ROUTE, REMOVE_ROUTE)
from ..environment.frequency import FleetCalculator

FEATURE_NAMES = (
    'bias', 'hour_fraction', 'clock_sin', 'clock_cos', 'remaining_fraction',
    'fleet_remaining_fraction', 'route_count_fraction', 'partial_length_fraction',
    'kept_fraction', 'plan_frequency_fraction', 'stop_coverage_fraction',
    'direct_od_coverage_fraction', 'covered_endpoints_demand_fraction', 'demand_scale',
    'partial_direct_demand_fraction', 'previous_route_count_fraction',
    'previous_frequency_fraction', 'route_set_change_proxy',
    'target_length_fraction', 'target_frequency_fraction', 'target_buses_fraction',
    'target_direct_demand_fraction', 'target_demand_pressure_proxy',
    'target_stop_demand_fraction', 'target_stop_degree_fraction', 'target_stop_covered',
    'target_route_travel_fraction', 'target_route_in_previous', 'target_kept',
    'frequency_delta_fraction', 'bus_delta_fraction', 'remaining_times_target_length')


class FeatureEncoder:
    def __init__(self, network, cfg):
        self.network, self.cfg = network, cfg
        self.fleet = FleetCalculator(network, cfg)
        self.max_degree = max(len(n) for n in network.neighbours)
        times = network.travel_time[np.isfinite(network.travel_time)]
        self.max_link = float(times.max())
        self.contexts = OrderedDict()  # two decisions only, not a growing learned table
        self.type_index = {name: i for i, name in enumerate(ACTION_TYPES)}

    def context(self, key):
        if len(key) != 7:
            raise ValueError('S5 requires the full original key plus remaining actions')
        cached = self.contexts.get(key)
        if cached is not None:
            self.contexts.move_to_end(key)
            return cached
        cfg = self.cfg
        hour, raw_od, partial, plan, previous, remaining_fleet, budget = key
        od = np.array(raw_od, dtype=float)
        if cfg.ignore_od_diagonal:
            np.fill_diagonal(od, 0)
        demand = float(od.sum())
        denominator = max(demand, 1.0)
        covered = sorted({s for r in plan for s in r.route})
        mask = np.zeros(od.shape, dtype=bool)
        for r in plan:
            for i, a in enumerate(r.route):
                for b in r.route[i+1:]:
                    mask[a-1, b-1] = True
                    if cfg.routes_are_bidirectional:
                        mask[b-1, a-1] = True
        current_routes = {min(r.route, r.route[::-1]) if cfg.routes_are_bidirectional else r.route for r in plan}
        prior_routes = {min(r.route, r.route[::-1]) if cfg.routes_are_bidirectional else r.route for r in previous}
        c = dict(od=od, demand=demand, denominator=denominator, covered=set(covered),
                 prior_routes=prior_routes, route_mass={}, features={}, batches={})
        def mass(route):
            return self.route_mass(c, route)
        endpoints = sum(float(od[a-1, b-1]) for a in covered for b in covered)
        clock = cfg.od_file_number(hour)
        c['base'] = [1.0, (hour-1)/max(cfg.num_hours-1, 1),
            math.sin(2*math.pi*clock/24), math.cos(2*math.pi*clock/24),
            budget/cfg.max_steps_per_hour, remaining_fleet/cfg.max_fleet,
            len(plan)/cfg.max_routes, len(partial)/cfg.max_route_length,
            sum(r.kept for r in plan)/cfg.max_routes,
            sum(r.frequency for r in plan)/(cfg.max_routes*cfg.max_frequency),
            len(covered)/self.network.num_stops, float(od[mask].sum())/denominator,
            endpoints/denominator,
            demand/(demand+cfg.max_fleet*cfg.bus_capacity*cfg.bus_load_factor),
            mass(partial)/denominator, len(previous)/cfg.max_routes,
            sum(r.frequency for r in previous)/(cfg.max_routes*cfg.max_frequency),
            len(current_routes.symmetric_difference(prior_routes))/(2*cfg.max_routes)]
        self.contexts[key] = c
        if len(self.contexts) > 2:
            self.contexts.popitem(last=False)
        return c

    def route_mass(self, context, route):
        if route not in context['route_mass']:
            od = context['od']
            value = sum(float(od[a-1, b-1]) for i, a in enumerate(route) for b in route[i+1:])
            if self.cfg.routes_are_bidirectional:
                value += sum(float(od[b-1, a-1]) for i, a in enumerate(route) for b in route[i+1:])
            context['route_mass'][route] = value
        return context['route_mass'][route]

    def features(self, key, action):
        c = self.context(key)
        if action in c['features']:
            return c['features'][action]
        cfg = self.cfg
        _, _, partial, plan, _, remaining_fleet, budget = key
        route, frequency, kept, delta, bus_delta = (), 0.0, False, 0.0, 0.0
        if action.type in (ADD_STOP, END_ROUTE, REMOVE_LAST_STOP):
            route = partial + (action.arg,) if action.type == ADD_STOP else partial
            f = self.fleet.initial_frequency_for_new_route(route, remaining_fleet)
            frequency = cfg.initial_route_frequency if f is None else f
            if action.type == END_ROUTE:
                delta = frequency
                bus_delta = self.fleet.buses_required(route, frequency)
        elif action.type in (INCREASE_FREQUENCY, DECREASE_FREQUENCY, KEEP_ROUTE, REMOVE_ROUTE):
            record = plan[action.arg]
            route, frequency, kept = record.route, record.frequency, record.kept
            if action.type in (INCREASE_FREQUENCY, DECREASE_FREQUENCY):
                delta = cfg.frequency_step if action.type == INCREASE_FREQUENCY else -cfg.frequency_step
                bus_delta = (self.fleet.buses_required(route, frequency+delta)
                             - self.fleet.buses_required(route, frequency))
            elif action.type == REMOVE_ROUTE:
                delta, bus_delta = -frequency, -self.fleet.buses_required(route, frequency)
        mass = self.route_mass(c, route)
        stop = route[-1] if route else None
        stop_mass = (float(c['od'][stop-1, :].sum()+c['od'][:, stop-1].sum())
                     if stop is not None else 0.0)
        canonical = min(route, route[::-1]) if cfg.routes_are_bidirectional else route
        capacity = frequency*cfg.bus_capacity*cfg.bus_load_factor
        target = [len(route)/cfg.max_route_length, frequency/cfg.max_frequency,
            min(self.fleet.buses_required(route, frequency)/cfg.max_fleet, 1.0),
            mass/c['denominator'], mass/(mass+capacity) if mass+capacity else 0.0,
            stop_mass/(2*c['denominator']),
            len(self.network.neighbours[stop-1])/self.max_degree if stop is not None else 0.0,
            float(stop in c['covered']),
            self.fleet.one_way_time(route)/(max(cfg.max_route_length-1, 1)*self.max_link),
            float(canonical in c['prior_routes']), float(kept), delta/cfg.max_frequency,
            max(-1.0, min(bus_delta/cfg.max_fleet, 1.0)),
            (budget/cfg.max_steps_per_hour)*(len(route)/cfg.max_route_length)]
        raw = np.asarray(c['base']+target, dtype=np.float64)
        if len(raw) != len(FEATURE_NAMES) or not np.all(np.isfinite(raw)):
            raise ValueError('Invalid feature vector')
        result = raw/np.linalg.norm(raw)
        result.flags.writeable = False
        c['features'][action] = result
        return result

    def batch(self, key, actions):
        context = self.context(key)
        names = tuple(actions)
        if names not in context['batches']:
            context['batches'][names] = (np.stack([self.features(key, a) for a in actions]),
                np.array([self.type_index[a.type] for a in actions], dtype=int))
        return context['batches'][names]


class LinearQAgent(QLearningAgent):
    """q/visits retain exact-key audit presence only; weights hold learned values."""
    def __init__(self, cfg, seed, network):
        super().__init__(cfg, seed)
        self.encoder = FeatureEncoder(network, cfg)
        self.weights = np.zeros((len(ACTION_TYPES), len(FEATURE_NAMES)), dtype=np.float64)
        self.greedy_audit = dict(decisions=0, unseen_exact_key=0, unseen_unique_best=0,
                                 unseen_tied_best=0, unseen_single_valid=0)

    def values(self, key, actions):
        matrix, indices = self.encoder.batch(key, actions)
        values = self.q0 + np.einsum('ij,ij->i', matrix, self.weights[indices])
        if not np.all(np.isfinite(values)) or float(np.abs(values).max()) > 1000:
            raise FloatingPointError('Registered linear Q stability guard exceeded')
        return values

    def q_value(self, key, action):
        return float(self.values(key, [action])[0])

    def max_q(self, key, valid_actions):
        return float(self.values(key, valid_actions).max()) if valid_actions else self.q0

    def greedy_action(self, key, valid_actions):
        values = self.values(key, valid_actions)
        best = float(values.max())
        ties = [a for a, value in zip(valid_actions, values) if value == best]
        self.greedy_audit['decisions'] += 1
        if key not in self.q:
            self.greedy_audit['unseen_exact_key'] += 1
            category = ('unseen_single_valid' if len(valid_actions) == 1 else
                        'unseen_unique_best' if len(ties) == 1 else 'unseen_tied_best')
            self.greedy_audit[category] += 1
        if key not in self.q and len(valid_actions) == 1:
            return self.rng.choice(ties)  # same forced-choice RNG use as unseen tabular rows
        return ties[0] if len(ties) == 1 else self.rng.choice(ties)

    def update(self, key, action, reward, next_key, next_valid_actions, done):
        target = reward if done or not next_valid_actions else reward + self.gamma*self.max_q(next_key, next_valid_actions)
        error = target-self.q_value(key, action)
        index = self.encoder.type_index[action.type]
        proposed = self.weights[index] + self.alpha*error*self.encoder.features(key, action)
        if not np.all(np.isfinite(proposed)) or np.linalg.norm(proposed) > 10000:
            raise FloatingPointError('Registered linear weight stability guard exceeded')
        self.weights[index] = proposed
        row = self.q.setdefault(key, {})
        if action not in row:
            self._num_pairs += 1
        row[action] = 0.0  # audit presence, never used for prediction or export
        visits = self.visits.setdefault(key, {})
        visits[action] = visits.get(action, 0)+1
        return float(error)

    def snapshot(self):
        return dict(model='linear_semigradient_q', normalization='unit_L2_per_action',
            feature_names=list(FEATURE_NAMES), action_types=list(ACTION_TYPES),
            weights=self.weights.tolist(), q_offset=self.q0, epsilon=self.epsilon,
            parameter_count=int(self.weights.size), complete_resume_checkpoint=False)
