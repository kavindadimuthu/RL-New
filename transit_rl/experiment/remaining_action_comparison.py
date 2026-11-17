"""EXP-004 S4: three serial seed waves, two fresh A/B CPU workers per wave."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', action='store_true')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.run:
        parser.error('--run required')
    status = subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT, text=True)
    if status.strip():
        raise RuntimeError('Requires clean isolated execution tree')
    args.output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    manifest = dict(stage='S4-remaining-actions', status='running',
        code_commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        started_at=datetime.now(timezone.utc).isoformat(), waves=[], workers=2, command=sys.argv)
    def save():
        (args.output / 'study-manifest.json').write_text(json.dumps(manifest, indent=2)+'\n', encoding='utf-8')
    save()

    def launch(method, seed):
        out = args.output / f'EXP-004-S4-{method}-seed{seed}-run01'
        command = [sys.executable, '-m', 'transit_rl.experiment.service_baseline', '--run',
                   '--method', method, '--seed', str(seed), '--output', str(out)]
        subprocess.run(command, cwd=ROOT, check=True)
        child = json.loads((out / 'manifest.json').read_text())
        if child['status'] != 'completed':
            raise RuntimeError(f'Incomplete {method}/{seed}: ' + child['status'])
        return dict(method=method, seed=seed, status=child['status'])

    try:
        for seed in (2034, 2035, 2036):
            wave = dict(seed=seed, started_at=datetime.now(timezone.utc).isoformat())
            manifest['waves'].append(wave)
            save()
            with ThreadPoolExecutor(max_workers=2) as executor:
                futures = [executor.submit(launch, method, seed) for method in ('A', 'B')]
                wave['results'] = [f.result() for f in futures]
            wave['finished_at'] = datetime.now(timezone.utc).isoformat()
            save()
        manifest['status'] = 'completed'
    except BaseException as error:
        manifest.update(status='failed', error=repr(error))
        raise
    finally:
        manifest['finished_at'] = datetime.now(timezone.utc).isoformat()
        manifest['total_elapsed_seconds'] = time.perf_counter()-started
        save()


if __name__ == '__main__':
    main()
