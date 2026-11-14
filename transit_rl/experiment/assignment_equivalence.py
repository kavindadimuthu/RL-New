"""EXP-003 foundation: frozen reference and strict differential checks.

This is a correctness preflight, not a speed benchmark or training run.
python -m transit_rl.experiment.assignment_equivalence --output <scratch-dir>
"""
import argparse
from dataclasses import fields, replace
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import sys

import numpy as np

from ..config import ExperimentConfig
from ..data.network import build_network
from ..environment.passenger_assignment import PassengerAssignment
from ..environment.service_plan import RouteService
from ..utils.awake import keep_awake

ROOT = Path(__file__).resolve().parents[2]
STUDY = ROOT/'experiments/EXP-003-passenger-assignment-optimization'


def reference_class():
    manifest=json.loads((STUDY/'baseline.json').read_text())
    source=STUDY/manifest['reference_file']
    if hashlib.sha256(source.read_bytes()).hexdigest()!=manifest['raw_sha256']:
        raise ValueError('Frozen assignment baseline hash changed')
    name='transit_rl.environment._exp003_frozen_assignment'
    if name not in sys.modules:
        spec=importlib.util.spec_from_file_location(name,source)
        module=importlib.util.module_from_spec(spec)
        sys.modules[name]=module
        try:
            spec.loader.exec_module(module)
        except BaseException:
            sys.modules.pop(name,None)
            raise
    return sys.modules[name].PassengerAssignment


def compare_assignments(actual, expected):
    """No floating-point tolerance: check every stored output and array flag."""
    names=[f.name for f in fields(expected)]
    assert [f.name for f in fields(actual)]==names, 'Assignment fields differ'
    for name in names:
        a,b=getattr(actual,name),getattr(expected,name)
        if isinstance(b,np.ndarray):
            assert isinstance(a,np.ndarray) and a.shape==b.shape and a.dtype==b.dtype, name
            assert np.array_equal(a,b) and np.isfinite(a).all(), name
            assert a.flags.writeable==b.flags.writeable==False, name
        else:
            assert a==b, name
            if isinstance(a,(int,float)):
                assert np.isfinite(a), name
    assert actual.metrics()==expected.metrics(), 'Derived metrics differ'


def output_digest(result):
    values={}
    for field in fields(result):
        value=getattr(result,field.name)
        if isinstance(value,np.ndarray):
            value=dict(dtype=str(value.dtype),shape=value.shape,values=value.tolist(),readonly=not value.flags.writeable)
        values[field.name]=value
    data=json.dumps(values,sort_keys=True,allow_nan=False,separators=(',',':')).encode()
    return hashlib.sha256(data).hexdigest()


def fixture_corpus():
    """Ordered plans exercise capacity, transfers, caches, frequencies and ties."""
    cfg=replace(ExperimentConfig(),num_stops=4,num_hours=1,od_start_file_hour=0,max_route_length=4)
    cfg.validate()
    network=build_network([(1,2,4),(2,3,4),(3,4,4),(1,4,12)],4,True)
    demand=np.array([[0,50,180,300],[70,0,110,210],[220,90,0,60],[260,170,80,0]],dtype=float)
    route=lambda stops,f=1,kept=False:RouteService(tuple(stops),float(f),kept)
    plans=[(),(route([1,2,3,4]),),(route([1,2]),route([2,3]),route([3,4])),
           (route([1,2,3,4],1),route([1,4],2)),
           (route([1,2,3,4],2),route([1,4],2)),
           (route([1,4],2),route([1,2,3,4],2)),
           (route([1,2,3,4],2,True),route([1,4],2)),
           (route([1,2,3,4],2),route([1,4],2))]
    for rule in ['min_transfers_first','min_generalised_time']:
        for transfers in [False,True]:
            yield f'{rule}_two_transfers_{transfers}',replace(cfg,path_choice_rule=rule,enable_two_transfer_paths=transfers),network,demand,plans
    yield 'zero_demand',cfg,network,np.zeros_like(demand),plans[:3]
    yield 'directional_routes',replace(cfg,routes_are_bidirectional=False),network,demand,plans
    yield 'trip_time_limit',replace(cfg,max_acceptable_trip_minutes=15),network,demand,plans
    yield 'cache_disabled',replace(cfg,assignment_cache_size=0),network,demand,plans
    yield 'cache_eviction',replace(cfg,assignment_cache_size=1),network,demand,plans


def verify_corpus(candidate_class=PassengerAssignment):
    reference=reference_class()
    rows=[]
    for name,cfg,network,demand,plans in fixture_corpus():
        original=demand.copy()
        baseline=reference(network,cfg,[demand])
        candidate=candidate_class(network,cfg,[demand])
        for index,plan in enumerate(plans):
            expected=baseline.assign(1,plan)
            actual=candidate.assign(1,plan)
            compare_assignments(actual,expected)
            assert candidate.cache_hits==baseline.cache_hits
            assert candidate.cache_misses==baseline.cache_misses
            assert np.array_equal(demand,original), 'Input OD changed'
            rows.append(dict(fixture=name,plan_index=index,output_sha256=output_digest(actual)))
    return rows


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=ROOT/'transit_rl/results/EXP-003-preflight')
    args=parser.parse_args(argv)
    args.output.mkdir(parents=True,exist_ok=False)
    with keep_awake() as sleep_request:
        records=verify_corpus()
    result=dict(study_id='EXP-003',stage='foundation_correctness_only',
                verified_at_utc=datetime.now(timezone.utc).isoformat(),
                baseline=json.loads((STUDY/'baseline.json').read_text()),
                candidate='current unchanged production implementation',
                sleep_request=sleep_request,sleep_request_scope_finished=True,
                comparisons=len(records),records=records,performance_claim=False)
    (args.output/'fixture-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(f'Passed {len(records)} strict assignment comparisons. No speed benchmark or training performed.')


if __name__=='__main__':
    main()
