"""Registered stage-2 accounting, fairness qualification and comparison."""
import argparse
from datetime import datetime
import hashlib
import json
import math
from pathlib import Path

STUDY = Path(__file__).resolve().parents[1]


def analyse(directory):
    manifest = json.loads((directory / 'manifest.json').read_text())
    assert manifest['status'] == 'completed' and manifest['completed_hours'] == 24
    assert manifest['replay_verified'] and manifest['sleep_scope_exited']
    assert not manifest['working_tree_status'].strip()
    cfg = json.loads((directory / 'config.json').read_text())
    baseline_root = STUDY / 'evidence/S1-baseline-run01/EXP-004-S1-baseline-seed2034-run01'
    baseline_cfg = json.loads((baseline_root / 'config.json').read_text())
    assert {k: v for k, v in cfg.items() if k not in ('data_dir', 'results_dir')} == {
        k: v for k, v in baseline_cfg.items() if k not in ('data_dir', 'results_dir')}
    hashes = json.loads((directory / 'source-input-sha256.json').read_text())
    baseline_hashes = json.loads((baseline_root / 'source-input-sha256.json').read_text())
    comparable = [k for k in baseline_hashes if k.startswith(('transit_rl/environment/',
        'transit_rl/data/', 'transit_rl/agent/')) or k == 'transit_rl/config.py']
    assert all(hashes[k] == baseline_hashes[k] for k in comparable)
    assert (directory / 'requirements-lock.txt').read_text() == (baseline_root / 'requirements-lock.txt').read_text()
    plan = json.loads((directory / 'service-plan.json').read_text())
    search = [json.loads(line) for line in (directory / 'search-hours.jsonl').read_text().splitlines()]
    assert len(search) == len(plan['hours']) == len(plan['diagnostics']) == 24
    over_budget = []
    for hour, (s, actual, diagnostic) in enumerate(zip(search, plan['hours'], plan['diagnostics']), 1):
        assert s['hour'] == actual['hour'] == diagnostic['hour'] == hour
        assert actual['clock_hour'] == (8+hour-1) % 24
        assert s['routes'] == actual['routes'] and s['frequencies'] == actual['frequencies']
        assert len(actual['routes']) <= cfg['max_routes']
        canonical = set()
        for route, frequency in zip(actual['routes'], actual['frequencies']):
            assert cfg['min_route_length'] <= len(route) <= cfg['max_route_length']
            assert len(set(route)) == len(route)
            key = min(tuple(route), tuple(reversed(route)))
            assert key not in canonical
            canonical.add(key)
            assert cfg['min_frequency'] <= frequency <= cfg['max_frequency']
            assert abs((frequency-cfg['min_frequency'])/cfg['frequency_step'] -
                       round((frequency-cfg['min_frequency'])/cfg['frequency_step'])) < 1e-9
        assert sum(actual['buses_per_route']) == s['fleet_used'] == actual['total_fleet_used'] <= 99
        assert s['action_count'] == len(s['actions']) == actual['rl_steps_in_hour'] == diagnostic['actions']
        assert s['actions'][-1]['type'] == 'FINISH_PLAN' and not actual['forced_finish']
        assert s['requests'] <= 2000 and s['edits'] <= 120
        assert math.isclose(s['original_score'], actual['total_reward'], abs_tol=1e-9)
        assert math.isclose(s['served'], actual['served_passengers'], abs_tol=1e-6)
        assert all(b['score'] > a['score'] + 1e-12 for a, b in zip(s['accepted'], s['accepted'][1:]))
        assert math.isclose(diagnostic['served_passengers'] + diagnostic['no_eligible_path_unserved']
                            + diagnostic['capacity_constrained_unserved'], actual['total_demand'], abs_tol=1e-6)
        assert all(0 <= x <= 1+1e-8 for x in diagnostic['route_peak_capacity_ratios'])
        assert s['within_original_60_actions'] == (s['action_count'] <= 60)
        if s['action_count'] > 60:
            over_budget.append(hour)
    assert over_budget == plan['hours_exceeding_original_action_limit']
    assert sum(s['requests'] for s in search) == manifest['search_evaluation_requests']
    assert sum(s['action_count'] for s in search) == plan['actions']
    daily, rows = plan['daily'], plan['diagnostics']
    demand = sum(r['total_demand'] for r in rows)
    served = sum(r['served_passengers'] for r in rows)
    assert math.isclose(served, daily['served_passengers'], abs_tol=1e-6)
    assert math.isclose(served/demand, daily['served_demand_ratio'], abs_tol=1e-12)
    reference = dict(served_ratio=served/demand,
        no_path_demand_share=sum(r['no_eligible_path_unserved'] for r in rows)/demand,
        capacity_demand_share=sum(r['capacity_constrained_unserved'] for r in rows)/demand,
        average_fleet=daily['average_fleet_used'], reward=daily['daily_plan_reward'],
        mean_route_count=sum(r['route_count'] for r in rows)/24)
    for label, subset in [('peak', [r for r in rows if r['clock_hour'] in (8, 9, 16, 17)]),
                          ('other', [r for r in rows if r['clock_hour'] not in (8, 9, 16, 17)])]:
        reference[label + '_served_ratio'] = sum(r['served_passengers'] for r in subset)/sum(r['total_demand'] for r in subset)
    baseline = json.loads((STUDY / 'baseline-verification.json').read_text())['final_three_model_summary']
    utc = (datetime.fromisoformat(manifest['finished_at']) - datetime.fromisoformat(manifest['started_at'])).total_seconds()
    return dict(status='verified', execution_commit=manifest['code_commit'], reference=reference,
        baseline={k: baseline[k] for k in reference},
        served_percentage_point_difference=(reference['served_ratio']-baseline['served_ratio']['mean'])*100,
        hours_exceeding_original_action_limit=over_budget,
        max_actions_in_hour=max(s['action_count'] for s in search), total_accepted_actions=plan['actions'],
        search_requests=manifest['search_evaluation_requests'],
        hours_reaching_evaluation_budget=[s['hour'] for s in search if s['evaluation_budget_reached']],
        hours_reaching_edit_budget=[s['hour'] for s in search if s['edit_budget_reached']],
        total_elapsed_seconds=manifest['total_elapsed_seconds'], utc_span_seconds=utc,
        clock_gap_seconds=utc-manifest['total_elapsed_seconds'],
        maximum_recorded_working_mb=max(s['working_mb'] for s in search),
        same_transport_config_data_production_sources=True,
        checksums={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(directory.iterdir()) if p.is_file()},
        limitations=['One deterministic heuristic, not three independent trials.',
                     'Same fixed demand; no held-out or optimality claim.',
                     'Different search/learning budgets; not equal-compute superiority evidence.',
                     'Any over-60 traces use an extended replay deadline; not identical action budget.',
                     'Greedy assignment influences capacity classification.'])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = analyse(args.directory)
    with args.output.open('x', encoding='utf-8') as file:
        json.dump(result, file, indent=2)
        file.write('\n')
    print(json.dumps({k: v for k, v in result.items() if k != 'checksums'}, indent=2))
