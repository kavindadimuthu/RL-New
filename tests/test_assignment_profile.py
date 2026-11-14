"""Workload selection and scenario semantics before baseline measurements."""
from dataclasses import replace
import unittest

from transit_rl.experiment.assignment_equivalence import fixture_corpus, reference_class
from transit_rl.experiment.assignment_profile import prepare_assigner, replay, select_misses
from transit_rl.environment.service_plan import plan_to_records


class AssignmentProfileTests(unittest.TestCase):
    def test_sample_is_unique_ordered_and_covers_buckets(self):
        plans=[[],[{'route':[1,2],'frequency':1}],[{'route':[1,2],'frequency':2}]]
        queries=[{'hour':h,'plan_id':p} for h in [1,2] for p in [0,1,1,2,0]]
        selected=select_misses(queries,plans,limit=4)
        self.assertEqual(len(selected),4)
        self.assertEqual({(q['hour'],len(plans[q['plan_id']])) for q in selected},
                         {(1,0),(1,1),(2,0),(2,1)})
        indices=[queries.index(q) for q in selected]
        self.assertEqual(indices,sorted(indices))

    def test_cache_scenarios_have_expected_hits_and_misses(self):
        _,cfg,network,demand,plans=next(fixture_corpus())
        # Two different committed services; repeated calls in the mixed stream.
        trace=dict(plans=[plan_to_records(p) for p in plans[:2]],
                   queries=[{'hour':1,'plan_id':p} for p in [0,1,0,1]])
        sampled=select_misses(trace['queries'],trace['plans'])
        reference=reference_class()
        for scenario,expected in [('miss_stream',(0,2)),('training_stream',(2,2)),('warm_hits',(8,0))]:
            assigner,queries,restored=prepare_assigner(scenario,cfg,network,[demand],reference,trace,sampled)
            hits,misses=assigner.cache_hits,assigner.cache_misses
            replay(assigner,queries,restored)
            self.assertEqual((assigner.cache_hits-hits,assigner.cache_misses-misses),expected)


if __name__=='__main__':
    unittest.main()
