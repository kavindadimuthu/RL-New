"""EXP-003 C01 verification and registered serial paired timing.

--verify is a correctness check; --run requires committed code/clean worktree.
"""
import argparse
from concurrent.futures import ProcessPoolExecutor
import ctypes
from dataclasses import asdict
from datetime import datetime, timezone
import gc
import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import platform
import statistics as stats
import subprocess
import sys
import time

for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS'):
    os.environ[name]='1'

from ..agent.q_learning_agent import QLearningAgent
from ..config import ExperimentConfig
from ..environment.transit_environment import TransitEnvironment
from ..utils.awake import keep_awake
from .assignment_candidate_c01 import C01PassengerAssignment
from .assignment_equivalence import ROOT, STUDY, reference_class, verify_corpus
from .assignment_profile import load_network_from_csv, load_od_matrices, prepare_assigner, replay
from .evaluation_comparison import memory_mb
from .trainer import run_episode

BACKENDS={'baseline':reference_class,'candidate':lambda:C01PassengerAssignment}
SCENARIOS=['miss_stream','training_stream','warm_hits']


def now():
    return datetime.now(timezone.utc).isoformat()


def write(path,value):
    path.write_text(json.dumps(value,indent=2,default=str)+'\n',encoding='utf-8')


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inputs():
    cfg=ExperimentConfig()
    cfg.validate()
    source=STUDY/'evidence/stage1'
    meta=json.loads((source/'manifest.json').read_text())
    path=source/'workload.json'
    if sha(path)!=meta['workload_sha256']:
        raise ValueError('Registered workload hash changed')
    if json.loads(json.dumps(asdict(cfg),default=str))!=meta['config']:
        raise ValueError('Configuration differs from registered workload')
    for name,expected in meta['input_and_source_sha256'].items():
        if sha(ROOT/name)!=expected:
            raise ValueError(f'Production/input reference changed: {name}')
    network=load_network_from_csv(cfg.links_path,cfg.num_stops,cfg.links_are_bidirectional,cfg.input_stop_id_base)
    od=load_od_matrices(cfg.od_dir,cfg.od_filename_pattern,cfg.num_hours,cfg.num_stops,cfg.od_file_numbers())
    return cfg,network,od,json.loads(path.read_text()),meta['workload_sha256']


def stamp_actions(env):
    digest=hashlib.sha256()
    count=0
    original=env.step
    def wrapped(action):
        nonlocal count
        hour=env.hour
        result=original(action)
        digest.update(json.dumps([hour,action.type,action.arg,result.reward,result.done],separators=(',',':')).encode())
        count+=1
        return result
    env.step=wrapped
    return lambda:(count,digest.hexdigest())


def verify_candidate():
    started=now()
    fixture_count=len(verify_corpus(C01PassengerAssignment))
    cfg,network,od,trace,workload_hash=inputs()
    replay_count=0
    for scenario in SCENARIOS:
        assigner,queries,plans=prepare_assigner(scenario,cfg,network,od,C01PassengerAssignment,trace,trace['miss_sample'])
        replay(assigner,queries,plans,verify=True)
        replay_count+=len(queries)
    trajectories=[]
    for seed in [2032,2033]:
        left=TransitEnvironment(network,od,cfg)
        right=TransitEnvironment(network,od,cfg)
        left.assigner=reference_class()(network,cfg,od)
        right.assigner=C01PassengerAssignment(network,cfg,od)
        baseline=QLearningAgent(cfg,seed)
        candidate=QLearningAgent(cfg,seed)
        left_trace,right_trace=stamp_actions(left),stamp_actions(right)
        for episode in [1,2,3]:
            a=run_episode(left,baseline,train=True)
            b=run_episode(right,candidate,train=True)
            baseline.decay_epsilon()
            candidate.decay_epsilon()
            assert a==b,'Rewards, hourly records, steps or unseen counts differ'
            assert baseline.q==candidate.q,'Q-table differs'
            assert baseline.visits==candidate.visits,'Visits differ'
            assert baseline.epsilon==candidate.epsilon
            assert baseline.rng.getstate()==candidate.rng.getstate(),'Learner RNG differs'
            assert left_trace()==right_trace(),'Action/reward trajectory differs'
            assert left.hourly_plans==right.hourly_plans
            trajectories.append(dict(seed=seed,episode=episode,reward=a[0],steps=a[2],
                                      cumulative_actions=left_trace()[0],action_reward_sha256=left_trace()[1],
                                      states=baseline.num_states,pairs=baseline.num_state_action_pairs,
                                      q_visits_rng_equal=True))
        del left,right,baseline,candidate
        gc.collect()
    return dict(status='passed',started_at=started,finished_at=now(),fixture_comparisons=fixture_count,
                real_output_hashes_verified=replay_count,training_seed_episodes=trajectories,
                workload_sha256=workload_hash,tolerance='none',large_q_tables='not_saved')


def peak_memory_mib():
    class Counters(ctypes.Structure):
        _fields_=[('cb',ctypes.c_ulong),('faults',ctypes.c_ulong)]+[(key,ctypes.c_size_t) for key in
                   ('peak','working','peak_paged','paged','peak_nonpaged','nonpaged','pagefile','peak_pagefile')]
    counters=Counters()
    counters.cb=ctypes.sizeof(counters)
    kernel=ctypes.WinDLL('kernel32')
    kernel.GetCurrentProcess.restype=ctypes.c_void_p
    function=ctypes.WinDLL('psapi').GetProcessMemoryInfo
    function.argtypes=[ctypes.c_void_p,ctypes.POINTER(Counters),ctypes.c_ulong]
    if not function(kernel.GetCurrentProcess(),ctypes.byref(counters),counters.cb):
        raise ctypes.WinError()
    return counters.peak/2**20


def timed_job(job):
    cfg,network,od,trace,workload_hash=inputs()
    if workload_hash!=job['workload_sha256']:
        raise ValueError('Worker workload differs')
    backend=BACKENDS[job['backend']]()
    warm=backend(network,cfg,od)
    from ..environment.service_plan import make_plan
    replay(warm,trace['queries'][:16],[make_plan(p) for p in trace['plans']])
    del warm
    setup=time.perf_counter()
    assigner,queries,plans=prepare_assigner(job['scenario'],cfg,network,od,backend,trace,trace['miss_sample'])
    setup_seconds=time.perf_counter()-setup
    hits,misses=assigner.cache_hits,assigner.cache_misses
    started,wall,cpu=now(),time.perf_counter(),time.process_time()
    replay(assigner,queries,plans)
    elapsed,cpu_seconds=time.perf_counter()-wall,time.process_time()-cpu
    result=dict(**job,pid=os.getpid(),started_at=started,finished_at=now(),elapsed_seconds=elapsed,
                cpu_seconds=cpu_seconds,setup_seconds=setup_seconds,calls=len(queries),
                cache_hits=assigner.cache_hits-hits,cache_misses=assigner.cache_misses-misses,
                peak_worker_memory_mib=peak_memory_mib())
    assert result['calls']==result['cache_hits']+result['cache_misses']
    if job['scenario']=='miss_stream':
        assert result['cache_hits']==0
    if job['scenario']=='warm_hits':
        assert result['cache_misses']==0
    return result


def summarize(out):
    rows=json.loads((out/'measurements.json').read_text())
    assert len(rows)==30
    summary=[]
    for scenario in SCENARIOS:
        group={name:[r for r in rows if r['scenario']==scenario and r['backend']==name] for name in BACKENDS}
        assert all(len(g)==5 for g in group.values())
        baseline=stats.median(r['elapsed_seconds'] for r in group['baseline'])
        candidate=stats.median(r['elapsed_seconds'] for r in group['candidate'])
        summary.append(dict(scenario=scenario,calls=group['baseline'][0]['calls'],
                            baseline_median_seconds=baseline,candidate_median_seconds=candidate,
                            reduction_fraction=1-candidate/baseline,speedup=baseline/candidate,
                            baseline_range=[min(r['elapsed_seconds'] for r in group['baseline']),max(r['elapsed_seconds'] for r in group['baseline'])],
                            candidate_range=[min(r['elapsed_seconds'] for r in group['candidate']),max(r['elapsed_seconds'] for r in group['candidate'])]))
    warm=next(r for r in summary if r['scenario']=='warm_hits')
    bpeak=max(r['peak_worker_memory_mib'] for r in rows if r['backend']=='baseline')
    cpeak=max(r['peak_worker_memory_mib'] for r in rows if r['backend']=='candidate')
    manifest=json.loads((out/'manifest.json').read_text())
    passed=all(r['reduction_fraction']>=.10 for r in summary if r['scenario']!='warm_hits')
    passed=passed and not (warm['reduction_fraction']<-.05 and warm['candidate_median_seconds']-warm['baseline_median_seconds']>.001)
    passed=passed and cpeak-bpeak<=64 and not manifest['timing_qualified']
    result=dict(scenarios=summary,baseline_peak_worker_mib=bpeak,candidate_peak_worker_mib=cpeak,
                peak_memory_increase_mib=cpeak-bpeak,advance_to_training_speed_trial=bool(passed),
                production_default_changed=False,timing_qualified=manifest['timing_qualified'])
    write(out/'comparison.json',result)
    lines=['# EXP-003 C01: verification and paired assignment timing','',
           'The production assignment remains unchanged. C01 is an independently selectable experimental backend. All correctness gates passed before timing. Five serial paired repetitions per cache scenario, fresh process per backend/repetition, one numerical thread, same captured inputs.','',
           '| Scenario | Baseline median seconds | C01 median seconds | Time reduction | Speedup |',
           '|---|---:|---:|---:|---:|']
    for r in summary:
        lines.append(f"| {r['scenario']} | {r['baseline_median_seconds']:.6f} | {r['candidate_median_seconds']:.6f} | {100*r['reduction_fraction']:.2f}% | {r['speedup']:.3f}x |")
    lines+=['',f'Peak worker working-set high-water mark, including imports/setup/prefill: baseline {bpeak:.2f} MiB; C01 {cpeak:.2f} MiB. This is not a pure algorithm-allocation measurement.', '',
            f'Registered assignment-level advancement criteria passed: **{bool(passed)}**. Timing qualification: {manifest["timing_qualified"]}.', '',
            'The criterion requires at least 10% median reduction in both miss/mixed streams, no warmed-hit regression exceeding both 5% and 1 ms, and no more than 64 MiB additional peak worker memory. Raw paired values and ranges are retained. Very short warmed-hit CPU times have coarse resolution; no significance claim is made.', '',
            'Correctness verification covers the 67 strict synthetic fixtures, all three real workload streams with exact output hashes, and three complete training episodes for each seed 2032/2033. Rewards, hourly records, action trace, Q-table, visits, epsilon, RNG and final plans agreed exactly. This is finite tested equivalence, not a proof for every possible input.', '',
            'No end-to-end training-speed experiment or production adoption occurs here. Only if the criteria pass may a separately registered training-speed trial proceed. On failure, preserve this result and register another candidate/run rather than alter the frozen baseline or selectively repeat timings. Large Q-tables/checkpoints were not exported.']
    (out/'REPORT.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return result


def power_metadata():
    script="[ordered]@{cpu=@(Get-CimInstance Win32_Processor|Select-Object Name,NumberOfCores,NumberOfLogicalProcessors);memory=(Get-CimInstance Win32_OperatingSystem|Select-Object FreePhysicalMemory,TotalVisibleMemorySize);battery=@(Get-CimInstance Win32_Battery|Select-Object BatteryStatus,EstimatedChargeRemaining);power_scheme=(powercfg /getactivescheme)}|ConvertTo-Json -Depth 5"
    return json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',script],text=True))


def events_between(start,end):
    script=f"$start=([datetimeoffset]::Parse('{start}')).LocalDateTime;$end=([datetimeoffset]::Parse('{end}')).LocalDateTime;$events=@(Get-WinEvent -FilterHashtable @{{LogName='System';ProviderName='Microsoft-Windows-Kernel-Power';Id=42,107,506,507;StartTime=$start;EndTime=$end}} -ErrorAction SilentlyContinue|ForEach-Object {{$x=[xml]$_.ToXml();[ordered]@{{id=$_.Id;record_id=$_.RecordId;timestamp_utc=$x.Event.System.TimeCreated.SystemTime;message=$_.Message}}}});ConvertTo-Json -InputObject $events -Depth 5"
    return json.loads(subprocess.check_output(['powershell.exe','-NoProfile','-Command',script],text=True))


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    group=parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--verify',action='store_true')
    group.add_argument('--run',action='store_true')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    status=subprocess.check_output(['git','status','--porcelain'],cwd=ROOT,text=True)
    if args.run and status.strip():
        raise RuntimeError('Commit candidate/protocol/analysis before timing')
    args.output.mkdir(parents=True,exist_ok=False)
    out=args.output
    started,t0=now(),time.perf_counter()
    candidate_source=Path(__file__).with_name('assignment_candidate_c01.py')
    manifest=dict(study_id='EXP-003',run_id='EXP-003-C01-'+('paired-run01' if args.run else 'precheck-run01'),
                  status='running',started_at=started,git_status=status,mode='paired_timing' if args.run else 'correctness_only',
                  execution_commit=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),
                  candidate_sha256=sha(candidate_source),python=sys.version,platform=platform.platform(),
                  command=subprocess.list2cmdline([sys.executable,'-m','transit_rl.experiment.assignment_c01_trial',*sys.argv[1:]]),
                  numerical_threads=1,production_default='frozen-equivalent unchanged assignment',large_artifacts='not_saved')
    write(out/'manifest.json',manifest)
    (out/'requirements-lock.txt').write_text(subprocess.check_output([sys.executable,'-m','pip','freeze','--all'],text=True),encoding='utf-8')
    write(out/'machine.json',power_metadata())
    try:
        with keep_awake() as power:
            manifest['sleep_request']=power
            if not power['requested']:
                raise RuntimeError('Sleep-prevention request missing')
            verification=verify_candidate()
            write(out/'verification.json',verification)
            manifest['workload_sha256']=verification['workload_sha256']
            if args.run:
                rows=[]
                context=multiprocessing.get_context('spawn')
                for scenario in SCENARIOS:
                    for repeat in range(1,6):
                        order=['baseline','candidate'] if repeat%2 else ['candidate','baseline']
                        for backend in order:
                            mem,free=memory_mb()
                            if mem>1536 or free<4096 or time.perf_counter()-t0>240:
                                raise RuntimeError('Registered memory/time guard stopped trial')
                            job=dict(scenario=scenario,repeat=repeat,backend=backend,workload_sha256=verification['workload_sha256'])
                            with ProcessPoolExecutor(max_workers=1,mp_context=context) as pool:
                                row=pool.submit(timed_job,job).result()
                            if row['peak_worker_memory_mib']>1536:
                                raise RuntimeError('Worker peak-memory guard exceeded')
                            rows.append(row)
                            write(out/'measurements.json',rows)
                            print(json.dumps(row),flush=True)
                if sha(candidate_source)!=manifest['candidate_sha256']:
                    raise RuntimeError('Candidate source changed during trial')
            manifest['status']='completed'
        manifest['sleep_request_restored']=True
    except BaseException as error:
        manifest.update(status='failed',error=repr(error),finished_at=now())
        write(out/'manifest.json',manifest)
        raise
    manifest.update(finished_at=now(),process_elapsed_seconds=time.perf_counter()-t0)
    span=(datetime.fromisoformat(manifest['finished_at'])-datetime.fromisoformat(started)).total_seconds()
    manifest['utc_span_seconds']=span
    manifest['timing_qualified']=abs(span-manifest['process_elapsed_seconds'])>5
    try:
        events=events_between(started,manifest['finished_at'])
        write(out/'power_events.json',dict(status='completed',events=events))
        manifest['timing_qualified']=manifest['timing_qualified'] or bool(events)
    except (subprocess.CalledProcessError,json.JSONDecodeError) as error:
        write(out/'power_events.json',dict(status='unavailable',error=repr(error)))
        manifest['timing_qualified']=True
    write(out/'manifest.json',manifest)
    if args.run:
        print(json.dumps(summarize(out),indent=2))
    else:
        print('C01 correctness checks passed; no timing comparison performed.')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
