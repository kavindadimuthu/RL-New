"""S9 registered paired waves, operational preflight or full comparison."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[2]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--preflight',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if not args.run:
        parser.error('--run required')
    if subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True).strip():
        raise RuntimeError('Clean execution checkout required')
    args.output.mkdir(parents=True,exist_ok=False)
    start=time.perf_counter()
    stage,episodes=('S9P',25) if args.preflight else ('S9',300)
    manifest=dict(study='EXP-004',stage=stage,status='running',target_episodes=episodes,
        code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
        started_at=datetime.now(timezone.utc).isoformat(),command=sys.argv,workers=2,waves=[])
    def save():
        (args.output/'study-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    save()
    def launch(method,seed):
        out=args.output/f'EXP-004-{stage}-{method}-seed{seed}-run01'
        command=[sys.executable,'-m','transit_rl.experiment.service_baseline','--run','--method','L',
                 '--return-comparison',method,'--seed',str(seed),'--episodes',str(episodes),'--output',str(out)]
        completed=subprocess.run(command,cwd=ROOT,check=False)
        return dict(method=method,seed=seed,exit_code=completed.returncode,
            status=json.loads((out/'manifest.json').read_text())['status'] if (out/'manifest.json').exists() else 'manifest_missing')
    try:
        for seed in ((2034,) if args.preflight else (2034,2035,2036)):
            wave=dict(seed=seed,started_at=datetime.now(timezone.utc).isoformat())
            manifest['waves'].append(wave);save()
            with ThreadPoolExecutor(max_workers=2) as executor:
                jobs=[executor.submit(launch,method,seed) for method in ('T','M')]
                wave['results']=[job.result() for job in jobs]
            wave['finished_at']=datetime.now(timezone.utc).isoformat();save()
            if any(r['status']!='completed' or r['exit_code']!=0 for r in wave['results']):
                raise RuntimeError('Paired wave incomplete; later seeds not started')
        manifest['status']='completed'
    except BaseException as error:
        manifest.update(status='failed',error=repr(error));raise
    finally:
        manifest.update(finished_at=datetime.now(timezone.utc).isoformat(),total_elapsed_seconds=time.perf_counter()-start);save()


if __name__=='__main__':
    main()
