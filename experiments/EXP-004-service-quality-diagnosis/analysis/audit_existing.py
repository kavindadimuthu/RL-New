"""Retrospective analysis only; no training, third-party packages or overwrites."""
import argparse
import csv
import hashlib
import json
import math
import platform
import statistics
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
STUDY = Path(__file__).resolve().parents[1]


def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT, text=True).strip()


def audit():
    hashes, models = {}, []

    def read(path):
        raw = path.read_bytes()
        relative = path.relative_to(ROOT).as_posix()
        hashes[relative] = hashlib.sha256(raw).hexdigest()
        blob = subprocess.check_output(['git', 'show', 'HEAD:' + relative], cwd=ROOT)
        if blob != raw:
            raise ValueError('Input differs from committed bytes: ' + relative)
        return raw.decode('utf-8-sig')

    fields = ['served_demand_ratio', 'unseen_fraction', 'average_fleet_used',
              'forced_hour_finishes', 'steps']
    for seed in (2027, 2028, 2029):
        run = f'EXP-002-S2-A-seed{seed}-run01'
        path = ROOT / 'experiments/EXP-002-evaluation-frequency-repeat/evidence/equal_episodes' / run
        records = json.loads(read(path / 'evaluations.json'))
        final = records[-1]
        assert final['episode'] == 300
        values = final['evaluations']
        assert len(values) == 3 and sorted(v['seed'] for v in values) == [7000, 7001, 7002]
        for v in values:
            assert all(math.isfinite(v[k]) for k in fields)
            assert 0 <= v['served_demand_ratio'] <= 1 and 0 <= v['unseen_fraction'] <= 1
            assert math.isclose(v['served_passengers'] + v['unserved_passengers'],
                                v['total_demand'], abs_tol=1e-6)
            assert math.isclose(v['served_passengers'] / v['total_demand'],
                                v['served_demand_ratio'], abs_tol=1e-12)
        models.append(dict(training_seed=seed, evaluation_seeds=[v['seed'] for v in values],
                           means={k: statistics.mean(v[k] for v in values) for k in fields}))
    demand = []
    files = sorted((ROOT / 'transit_rl/data/input/od').glob('od_hour_*.csv'))
    assert len(files) == 24
    for path in files:
        rows = [[float(x) for x in row] for row in csv.reader(
            line for line in read(path).splitlines() if line.strip() and not line.startswith('#'))]
        assert len(rows) == 15 and all(len(row) == 15 for row in rows)
        assert all(math.isfinite(x) and x >= 0 for row in rows for x in row)
        total = sum(map(sum, rows))
        diagonal = sum(rows[i][i] for i in range(15))
        demand.append(dict(file=path.name, total=total, diagonal=diagonal,
                           off_diagonal=total-diagonal))
    return dict(status='completed', study_id='EXP-004-service-quality-diagnosis',
                analysis_type='retrospective; not a new model run',
                timestamp=datetime.now(timezone.utc).isoformat(), execution_commit=git('rev-parse', 'HEAD'),
                working_tree_status=git('status', '--short'), command=sys.argv,
                python=sys.version, platform=platform.platform(), models=models,
                mean_of_model_means={k: statistics.mean(m['means'][k] for m in models) for k in fields},
                hourly_demand=demand, source_sha256=hashes,
                limitations=['Same training demand; only 300-episode historical runs.',
                             'No causal attribution or achievable-service bound.',
                             'Evaluation ties are not independent trained models.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # Reserve unique directory before analysis; failures are preserved.
    args.output.mkdir(parents=True, exist_ok=False)
    try:
        result = audit()
    except BaseException as error:
        (args.output / 'failure.json').write_text(json.dumps(
            dict(status='failed', error=repr(error)), indent=2), encoding='utf-8')
        raise
    (args.output / 'audit.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result['mean_of_model_means'], indent=2))


if __name__ == '__main__':
    main()
