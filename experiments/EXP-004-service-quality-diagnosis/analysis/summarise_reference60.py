"""Registered Stage3 strict-action control; reuse frozen Stage2 accounting."""
import argparse
import json
from pathlib import Path
import runpy

STUDY = Path(__file__).resolve().parents[1]


def analyse(directory):
    prior_analysis = runpy.run_path(str(STUDY / 'analysis/summarise_reference.py'))
    value = prior_analysis['analyse'](directory)
    manifest = json.loads((directory / 'manifest.json').read_text())
    plan = json.loads((directory / 'service-plan.json').read_text())
    search = [json.loads(line) for line in (directory / 'search-hours.jsonl').read_text().splitlines()]
    assert manifest['stage'] == 'S3-reference60' and manifest['accepted_action_limit'] == 60
    assert plan['replay_action_limit'] == plan['original_action_limit'] == 60
    assert plan['hours'][0]['previous_service_plan'] == []
    assert value['hours_exceeding_original_action_limit'] == []
    assert all(s['action_count'] <= 60 and s['within_original_60_actions'] for s in search)
    assert all(s['action_budget_exhausted'] == (s['action_count'] == 60) for s in search)
    previous = STUDY / 'evidence/S2-reference-run01'
    original = json.loads((previous / 'manifest.json').read_text())
    for key in ('max_search_requests_per_hour', 'max_accepted_edits_per_hour', 'replacement_rounds'):
        assert manifest[key] == original[key]
    assert (directory / 'route-candidates.json').read_bytes() == (previous / 'route-candidates.json').read_bytes()
    stage2 = json.loads((STUDY / 'reference-verification.json').read_text())
    value.update(stage='S3-reference60', strict_original_action_budget=True,
        stage2_reference=stage2['reference'],
        difference_from_stage2_percentage_points=(value['reference']['served_ratio']-stage2['reference']['served_ratio'])*100,
        skipped_over_budget_edit_encounters=sum(s['skipped_action_budget'] for s in search),
        hours_exhausting_action_budget=[s['hour'] for s in search if s['action_budget_exhausted']],
        same_candidate_pool_and_search_knobs=True)
    value['limitations'] = ['Single deterministic fixed-demand control; no independent seed repetitions.',
        'Same accepted-action budget; candidate search/compute/information differ from RL.',
        'Whole day replanned from empty, not inherited from the extended first-hour reference.',
        'No global optimality, held-out generalization or causal learning diagnosis.',
        'Observed differences from RL do not isolate state, reward or exploration effects.']
    return value


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
