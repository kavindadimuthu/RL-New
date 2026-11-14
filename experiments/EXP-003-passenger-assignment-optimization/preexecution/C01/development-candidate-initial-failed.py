"""EXP-003 C01: experimental capacity-query fast paths; not the default.

Only one- and two-element floating load segments bypass NumPy's general
reduction. The assignment method below is copied from the frozen baseline,
with only its local capacity-peak call replaced. Keep allocation order intact.
"""
import numpy as np

from ..environment.passenger_assignment import AssignmentResult, PassengerAssignment, _RouteIndex
from ..environment.service_plan import ServicePlan


def _segment_peak(values):
    """Match float(values.max()), including NaNs, empty and unusual arrays."""
    if values.ndim != 1 or values.dtype.kind != 'f':
        return float(values.max())
    size=values.size
    if size==1:
        return float(values[0])
    if size==2:
        first,second=values[0],values[1]
        if first!=first or second!=second:
            return float(values.max())
        # NumPy's two-element maximum keeps the latter value on equality,
        # including its signed-zero behavior.
        return float(first if first>second else second)
    return float(values.max())


class C01PassengerAssignment(PassengerAssignment):
    """Experimental selectable backend; no result or persistent-cache changes."""

    def _assign_uncached(self, hour: int, plan: ServicePlan) -> AssignmentResult:
        cfg, n = self.cfg, self.network.num_stops
        routes = [_RouteIndex(rs.route, rs.frequency, self._table(rs.route), cfg.waiting_time_factor)
                  for rs in plan]
        R = len(routes)
        capacities = [r.frequency * cfg.bus_capacity * cfg.bus_load_factor for r in routes]
        routes_at: Dict[int, List[int]] = {s: [] for s in self.network.stops}
        for k, r in enumerate(routes):
            for s in r.pos:
                routes_at[s].append(k)
        common = [[tuple(sorted(set(routes[a].pos) & set(routes[b].pos))) if a != b else () for b in range(R)]
                  for a in range(R)]
        penalty = cfg.transfer_penalty_minutes

        assigned = np.zeros((n, n))
        unserved = np.zeros((n, n))
        direct_m = np.zeros((n, n))
        transfer_m = np.zeros((n, n))
        fwd_load = [np.zeros(max(len(r.stops) - 1, 0)) for r in routes]
        bwd_load = [np.zeros(max(len(r.stops) - 1, 0)) for r in routes]

        def leg_load(k: int, a: int, b: int) -> np.ndarray:
            pa, pb = routes[k].pos[a], routes[k].pos[b]
            return fwd_load[k][pa:pb] if pa < pb else bwd_load[k][pb:pa]

        def available(k: int, a: int, b: int) -> float:
            return max(0.0, capacities[k] - _segment_peak(leg_load(k, a, b)))

        tot_ivt = tot_wait = tot_pen = 0.0
        n_direct = n_one = n_two = n_unserved = 0.0
        total_demand = 0.0

        for i, j, d in self._pairs[hour - 1]:
            total_demand += d
            remaining = d
            while remaining > 0:
                chosen = self._choose_path(i, j, routes, routes_at, common, available)
                if chosen is None:
                    break
                legs = chosen[4]
                amount = min(remaining, min(available(k, a, b) / share
                                           for (k, a, b), share in legs))
                _, n_tr, ivt, wait, legs = chosen
                tot_ivt += amount * ivt
                tot_wait += amount * wait
                tot_pen += amount * n_tr * penalty
                assigned[i - 1, j - 1] += amount
                if n_tr == 0:
                    n_direct += amount
                    direct_m[i - 1, j - 1] += amount
                else:
                    transfer_m[i - 1, j - 1] += amount
                    if n_tr == 1:
                        n_one += amount
                    else:
                        n_two += amount
                for (k, a, b), share in legs:
                    leg_load(k, a, b)[:] += amount * share
                remaining = max(0.0, remaining - amount)
            n_unserved += remaining
            unserved[i - 1, j - 1] = remaining

        # ---- actual boarded loads (overload should be zero within rounding) -
        overload = 0.0
        peaks = []
        for k, r in enumerate(routes):
            capacity = capacities[k]
            pf = float(fwd_load[k].max()) if fwd_load[k].size else 0.0
            pb = float(bwd_load[k].max()) if bwd_load[k].size else 0.0
            overload += max(0.0, pf - capacity) + max(0.0, pb - capacity)
            peaks.append(max(pf, pb))

        served = total_demand - n_unserved
        for arr in (assigned, unserved, direct_m, transfer_m):
            arr.setflags(write=False)
        return AssignmentResult(
            total_demand=total_demand,
            served_passengers=served,
            total_in_vehicle_time=tot_ivt,
            total_waiting_time=tot_wait,
            total_transfer_penalty_time=tot_pen,
            total_passenger_travel_time=tot_ivt + tot_wait,
            direct_passengers=n_direct,
            one_transfer_passengers=n_one,
            two_transfer_passengers=n_two,
            unserved_passengers=n_unserved,
            overload_passengers=overload,
            average_waiting_time=tot_wait / served if served > 0 else 0.0,
            average_travel_time=(tot_ivt + tot_wait) / served if served > 0 else 0.0,
            assigned_demand=assigned,
            unserved_demand=unserved,
            direct_demand=direct_m,
            transfer_demand=transfer_m,
            route_peak_load=tuple(peaks),
        )
