"""EXP-003 registered real-workload capture and baseline profiling only.

No candidate implementation is executed; profile overhead is not a speed result.
"""
import argparse
import cProfile
from dataclasses import asdict, replace
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path
import platform
import pstats
import statistics
import subprocess
import sys
import time

for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name]='1'

import numpy as np
import scipy

from ..agent.q_learning_agent import QLearningAgent
from ..config import ExperimentConfig
from ..data.network import load_network_from_csv
from ..data.od_loader import load_od_matrices
from ..environment.service_plan import make_plan, plan_to_records
from ..environment.transit_environment import TransitEnvironment
from ..utils.awake import keep_awake
from .assignment_equivalence import ROOT, output_digest, reference_class
from .evaluation_comparison import memory_mb
from .trainer import run_episode

SEEDS=[2030,2031]
REPEAT_ORDER=[['miss_stream','training_stream','warm_hits'],
              ['warm_hits','training_stream','miss_stream'],
              ['training_stream','miss_stream','warm_hits']]


def now():
    return datetime.now(timezone.utc).isoformat()


def write(path,value):
    path.write_text(json.dumps(value,indent=2,default=str)+'\n',encoding='utf-8')


def capture(cfg,network,od,reference):
    plans,plan_ids,queries,actions,episodes=[],{},[],[],[]
    expected={}
    for seed in SEEDS:
        env=TransitEnvironment(network,od,cfg)
        underlying=reference(network,cfg,od)
        episode_index=0

        class Recorder:
            def assign(self,hour,plan):
                hits=underlying.cache_hits
                result=underlying.assign(hour,plan)
                if plan not in plan_ids:
                    plan_ids[plan]=len(plans)
                    plans.append(plan_to_records(plan))
                key=(hour,tuple((r.route,r.frequency) for r in plan))
                if key not in expected:
                    expected[key]=output_digest(result)
                queries.append(dict(hour=hour,plan_id=plan_ids[plan],seed=seed,episode=episode_index,
                                    expected_sha256=expected[key],cache_hit=underlying.cache_hits>hits))
                return result

        env.assigner=Recorder()
        step=env.step
        def record_step(action):
            actions.append(dict(seed=seed,episode=episode_index,hour=env.hour,
                                type=action.type,arg=action.arg))
            return step(action)
        env.step=record_step
        agent=QLearningAgent(cfg,seed)
        for episode_index in (1,2):
            t=time.perf_counter()
            reward,records,count,_=run_episode(env,agent,train=True)
            agent.decay_epsilon()
            episodes.append(dict(seed=seed,episode=episode_index,reward=reward,steps=count,
                                 capture_elapsed_seconds=time.perf_counter()-t,
                                 note='Instrumented trace capture, not an ordinary training-speed measurement'))
    return dict(plans=plans,queries=queries,actions=actions,episodes=episodes)


def select_misses(queries,plans,limit=512):
    """Select without timing/outcome inspection; cover every observed hour/route-count bucket."""
    unique,seen=[],set()
    for q in queries:
        key=(q['hour'],tuple((tuple(r['route']),r['frequency']) for r in plans[q['plan_id']]))
        if key not in seen:
            seen.add(key)
            unique.append(q)
    buckets={}
    for index,q in enumerate(unique):
        buckets.setdefault((q['hour'],len(plans[q['plan_id']])),index)
    selected=set(buckets.values())
    target=min(limit,len(unique))
    if len(selected)>target:
        raise ValueError('Prespecified sample cannot cover all buckets')
    available=[index for index in range(len(unique)) if index not in selected]
    needed=target-len(selected)
    if needed:
        for offset in np.linspace(0,len(available)-1,needed,dtype=int):
            selected.add(available[int(offset)])
    return [unique[index] for index in sorted(selected)]


def replay(assigner,queries,plans,verify=False):
    for q in queries:
        result=assigner.assign(q['hour'],plans[q['plan_id']])
        if verify and output_digest(result)!=q['expected_sha256']:
            raise AssertionError('Replay differs from captured assignment output')


def prepare_assigner(scenario,cfg,network,od,reference,trace,sampled):
    mode_cfg=replace(cfg,assignment_cache_size=0) if scenario=='miss_stream' else cfg
    assigner=reference(network,mode_cfg,od)
    queries=sampled if scenario!='training_stream' else trace['queries']
    plans=[make_plan(records) for records in trace['plans']]
    if scenario=='warm_hits':
        replay(assigner,sampled,plans)
        queries=sampled*4
    return assigner,queries,plans


def summarize(out):
    data=json.loads((out/'baseline_measurements.json').read_text())
    lines=['# EXP-003 stage 1: real workload and baseline profile','',
           'Baseline only. No candidate optimization or speedup claim. Fixed traces from two 24-hour episodes for each training seed 2030 and 2031, using A and the original exploration schedule. Instrumented capture durations are not ordinary training timings.','',
           '| Scenario | Calls/repetition | Median seconds | Range seconds | Median ms/call |',
           '|---|---:|---:|---:|---:|']
    for scenario in ('miss_stream','training_stream','warm_hits'):
        rows=[r for r in data if r['scenario']==scenario]
        values=[r['elapsed_seconds'] for r in rows]
        lines.append(f"| {scenario} | {rows[0]['calls']} | {statistics.median(values):.6f} | {min(values):.6f}–{max(values):.6f} | {1000*statistics.median(values)/rows[0]['calls']:.6f} |")
    lines+=['','## Profile interpretation','',
            'Separate cProfile runs exist for miss_stream and training_stream. Their cumulative times overlap; do not sum them or treat profiled durations as unprofiled execution speed. The retained profile text/function tables identify candidates, not a demonstrated improvement.','',
            'Samples cover observed hour/route-count buckets and retain sequence order. They are early-training traces, not a proof of mature-policy representativeness. Miss_stream disables result caching but allows route-table caching within each fresh replay. Warm_hits prepopulates the sampled plans outside timing. Training_stream preserves the captured mixed-hit/miss sequence with a fresh assigner each repetition.','',
            'Output hashes were verified outside timed loops. Setup, prefill, serialization, digest checks and profiler runs are excluded from baseline timings. Results are serial, one numerical thread, no GPU. Run metadata records sleep request, power/hardware, input/workload hashes and clock checks. No final Q-table export is retained.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    if not args.run:
        print('No run started. Review the stage-1 protocol and pass --run explicitly.')
        return 0
    status=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)
    if status.strip():
        raise RuntimeError('Commit the protocol, implementation and analysis before capture/profiling')
    args.output.mkdir(parents=True,exist_ok=False)
    out=args.output
    started,t0=now(),time.perf_counter()
    cfg=ExperimentConfig()
    cfg.validate()
    baseline=reference_class()
    network=load_network_from_csv(cfg.links_path,cfg.num_stops,cfg.links_are_bidirectional,cfg.input_stop_id_base)
    od=load_od_matrices(cfg.od_dir,cfg.od_filename_pattern,cfg.num_hours,cfg.num_stops,cfg.od_file_numbers())
    sources=[ROOT/'transit_rl/environment/passenger_assignment.py',*sorted(cfg.od_dir.glob('*.csv')),cfg.links_path]
    manifest=dict(study_id='EXP-003',run_id='EXP-003-S1-baseline-profile-run01',stage='capture_and_baseline_profile',
                  started_at=started,status='running',code_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  git_status=status,command=subprocess.list2cmdline([sys.executable,'-m','transit_rl.experiment.assignment_profile',*sys.argv[1:]]),
                  python=sys.version,numpy=np.__version__,scipy=scipy.__version__,platform=platform.platform(),
                  seeds=SEEDS,episodes_per_seed=2,repetition_order=REPEAT_ORDER,config=asdict(cfg),
                  input_and_source_sha256={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sources})
    write(out/'manifest.json',manifest)
    environment=subprocess.check_output([sys.executable,'-m','pip','freeze','--all'],text=True)
    (out/'requirements-lock.txt').write_text(environment,encoding='utf-8')
    machine_script="[ordered]@{cpu=@(Get-CimInstance Win32_Processor|Select-Object Name,NumberOfCores,NumberOfLogicalProcessors);memory=(Get-CimInstance Win32_OperatingSystem|Select-Object FreePhysicalMemory,TotalVisibleMemorySize);battery=@(Get-CimInstance Win32_Battery|Select-Object BatteryStatus,EstimatedChargeRemaining);power_scheme=(powercfg /getactivescheme)}|ConvertTo-Json -Depth 5"
    write(out/'machine.json',json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',machine_script],text=True)))
    try:
        with keep_awake() as power:
            if os.name=='nt' and not power['requested']:
                raise RuntimeError('Sleep request not active')
            manifest['sleep_request']=power
            write(out/'manifest.json',manifest)
            trace=capture(cfg,network,od,baseline)
            assert len(trace['queries'])<=5952
            sampled=select_misses(trace['queries'],trace['plans'])
            trace['miss_sample']=sampled
            write(out/'workload.json',trace)
            manifest['workload_sha256']=hashlib.sha256((out/'workload.json').read_bytes()).hexdigest()
            manifest['assignment_requests']=len(trace['queries'])
            manifest['miss_sample_size']=len(sampled)
            # Verify every scenario before timing; no digest overhead in measured loops.
            for scenario in REPEAT_ORDER[0]:
                assigner,queries,plans=prepare_assigner(scenario,cfg,network,od,baseline,trace,sampled)
                replay(assigner,queries,plans,verify=True)
            warm=baseline(network,cfg,od)
            replay(warm,trace['queries'][:16],[make_plan(p) for p in trace['plans']])
            measurements=[]
            for repeat,order in enumerate(REPEAT_ORDER,1):
                for scenario in order:
                    mem,free=memory_mb()
                    if mem>1536 or free<4096:
                        raise RuntimeError('Memory guard stopped baseline profiling')
                    setup=time.perf_counter()
                    assigner,queries,plans=prepare_assigner(scenario,cfg,network,od,baseline,trace,sampled)
                    setup_seconds=time.perf_counter()-setup
                    hits,misses=assigner.cache_hits,assigner.cache_misses
                    utc_start,wall,cpu=now(),time.perf_counter(),time.process_time()
                    replay(assigner,queries,plans)
                    elapsed,cpu_seconds=time.perf_counter()-wall,time.process_time()-cpu
                    row=dict(repeat=repeat,scenario=scenario,calls=len(queries),started_at=utc_start,finished_at=now(),
                             elapsed_seconds=elapsed,cpu_seconds=cpu_seconds,setup_seconds=setup_seconds,
                             cache_hits=assigner.cache_hits-hits,cache_misses=assigner.cache_misses-misses,
                             memory_mib=memory_mb()[0])
                    if scenario=='miss_stream':
                        assert row['cache_hits']==0 and row['cache_misses']==row['calls']
                    if scenario=='warm_hits':
                        assert row['cache_hits']==row['calls'] and row['cache_misses']==0
                    measurements.append(row)
                    write(out/'baseline_measurements.json',measurements)
                    print(json.dumps(row),flush=True)
                    if time.perf_counter()-t0>240:
                        raise RuntimeError('Overall 240-second guard exceeded')
            for scenario in ('miss_stream','training_stream'):
                assigner,queries,plans=prepare_assigner(scenario,cfg,network,od,baseline,trace,sampled)
                profile=cProfile.Profile()
                profile.runcall(replay,assigner,queries,plans)
                stream=io.StringIO()
                stats=pstats.Stats(profile,stream=stream)
                stats.sort_stats('cumulative').print_stats(40)
                stats.sort_stats('tottime').print_stats(30)
                (out/f'{scenario}_profile.txt').write_text(stream.getvalue(),encoding='utf-8')
                rows=[]
                for (filename,line,name),values in stats.stats.items():
                    rows.append(dict(file=filename,line=line,function=name,primitive_calls=values[0],
                                     calls=values[1],self_seconds=values[2],cumulative_seconds=values[3]))
                write(out/f'{scenario}_profile.json',dict(total_profiled_seconds=stats.total_tt,
                     functions=sorted(rows,key=lambda r:r['cumulative_seconds'],reverse=True)))
                if time.perf_counter()-t0>240:
                    raise RuntimeError('Overall 240-second guard exceeded during profiling')
            manifest['status']='completed'
        manifest['sleep_request_restored']=True
    except BaseException as error:
        manifest.update(status='failed',error=repr(error),finished_at=now())
        write(out/'manifest.json',manifest)
        raise
    manifest.update(finished_at=now(),process_elapsed_seconds=time.perf_counter()-t0)
    utc_span=(datetime.fromisoformat(manifest['finished_at'])-datetime.fromisoformat(started)).total_seconds()
    manifest['utc_span_seconds']=utc_span
    manifest['clock_discrepancy_seconds']=utc_span-manifest['process_elapsed_seconds']
    manifest['timing_qualified']=abs(manifest['clock_discrepancy_seconds'])>5
    event_script=f"$start=([datetimeoffset]::Parse('{started}')).LocalDateTime; $end=([datetimeoffset]::Parse('{manifest['finished_at']}')).LocalDateTime; $events=@(Get-WinEvent -FilterHashtable @{{LogName='System';ProviderName='Microsoft-Windows-Kernel-Power';Id=42,107,506,507;StartTime=$start;EndTime=$end}} -ErrorAction SilentlyContinue | ForEach-Object {{ $x=[xml]$_.ToXml(); [ordered]@{{id=$_.Id;record_id=$_.RecordId;timestamp_utc=$x.Event.System.TimeCreated.SystemTime;message=$_.Message}} }}); ConvertTo-Json -InputObject $events -Depth 5"
    try:
        events=json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',event_script],text=True))
        write(out/'power_events.json',dict(query_status='completed',events=events))
        if events:
            manifest['timing_qualified']=True
    except (subprocess.CalledProcessError,json.JSONDecodeError) as error:
        write(out/'power_events.json',dict(query_status='unavailable',error=repr(error)))
        manifest['timing_qualified']=True
    write(out/'manifest.json',manifest)
    summarize(out)
    print(f'Baseline capture/profile completed: {out}',flush=True)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
