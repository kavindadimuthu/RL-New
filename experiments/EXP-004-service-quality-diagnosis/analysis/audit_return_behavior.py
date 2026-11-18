"""Post-execution S9 behavior inspection, not a preregistered advancement metric."""
import json
from pathlib import Path
import statistics
import sys


def analyse(directory):
    rows=[]
    for seed in (2034,2035,2036):
        path=directory/f'EXP-004-S9-M-seed{seed}-run01/evaluation-300.json'
        value=json.loads(path.read_text())
        evaluations=[]
        for v in value['evaluations']:
            counts={}
            for hour in v['hours']:
                for action,count in hour['action_counts'].items():
                    counts[action]=counts.get(action,0)+count
            assert sum(counts.values())==v['steps']
            first=v['hours'][0]
            evaluations.append(dict(tie_seed=v['seed'],steps=v['steps'],action_counts=counts,
                discarded_routes=v['diagnostics']['discarded_routes'],
                mean_routes=v['diagnostics']['mean_route_count'],
                first_hour=dict(actions=first['actions'],action_counts=first['action_counts'],
                    committed_routes=first['route_count'],served=first['served_passengers'],
                    discarded_unfinished_route=first['discarded_unfinished_route'])))
        rows.append(dict(seed=seed,evaluations=evaluations))
    return dict(status='verified_posthoc',purpose='Inspect final construction behavior after observing checkpoint decline; not used to change run or advancement criteria.',models=rows)


if __name__=='__main__':
    result=analyse(Path(sys.argv[1]))
    with Path(sys.argv[2]).open('x') as file:
        json.dump(result,file,indent=2);file.write('\n')
