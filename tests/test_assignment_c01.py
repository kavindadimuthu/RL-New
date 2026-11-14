"""C01 exact arithmetic/assignment checks, including negative edge cases."""
import ast
import copy
import unittest
import json
from pathlib import Path
import tempfile

import numpy as np

from transit_rl.experiment.assignment_candidate_c01 import C01PassengerAssignment, _segment_peak
from transit_rl.experiment.assignment_equivalence import STUDY, verify_corpus


class C01Tests(unittest.TestCase):
    def test_strict_fixture_equivalence(self):
        self.assertEqual(len(verify_corpus(C01PassengerAssignment)),67)

    def test_segment_maximum_edge_cases(self):
        cases=[[0.0],[4.0],[float('nan')],[float('inf')],[-float('inf')],
               [0.0,0.0],[-0.0,0.0],[0.0,-0.0],[7.0,7.0],[3.0,9.0],[9.0,3.0],
               [float('nan'),1.0],[1.0,float('nan')],[float('inf'),-float('inf')],
               [2.0,4.0,3.0],[0.0]*8]
        for dtype in [np.float16,np.float32,np.float64]:
            for case in cases:
                values=np.array(case,dtype=dtype)
                expected=float(values.max())
                actual=_segment_peak(values)
                if np.isnan(expected):
                    self.assertTrue(np.isnan(actual))
                else:
                    self.assertEqual(actual,expected)
                    self.assertEqual(np.signbit(actual),np.signbit(expected))
        for values in [np.array([1,3]),np.array([[1.0,2.0]]),np.array(4.0)]:
            self.assertEqual(_segment_peak(values),float(values.max()))
        with self.assertRaises(ValueError):
            _segment_peak(np.array([],dtype=float))

    def test_only_capacity_peak_expression_differs(self):
        reference=ast.parse((STUDY/'reference/passenger_assignment.py').read_text())
        from pathlib import Path
        import transit_rl.experiment.assignment_candidate_c01 as module
        candidate=ast.parse(Path(module.__file__).read_text())
        def method(tree):
            node=copy.deepcopy(next(n for n in ast.walk(tree) if isinstance(n,ast.FunctionDef) and n.name=='_assign_uncached'))
            available=next(n for n in ast.walk(node) if isinstance(n,ast.FunctionDef) and n.name=='available')
            available.body=[ast.Return(value=ast.Constant(value='capacity-query-hook'))]
            return ast.dump(node,include_attributes=False)
        self.assertEqual(method(reference),method(candidate))

    def test_random_segments_match_original_reduction(self):
        rng=np.random.default_rng(1234)
        for size in range(1,11):
            for _ in range(100):
                values=rng.normal(size=size)
                self.assertEqual(_segment_peak(values),float(values.max()))


class C01AdvancementTests(unittest.TestCase):
    def decision(self,candidate_seconds):
        from transit_rl.experiment.assignment_c01_trial import summarize
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)
            rows=[]
            for scenario in ['miss_stream','training_stream','warm_hits']:
                for repeat in range(1,6):
                    for backend in ['baseline','candidate']:
                        seconds=1 if backend=='baseline' else candidate_seconds
                        rows.append(dict(scenario=scenario,repeat=repeat,backend=backend,
                                         elapsed_seconds=seconds,calls=100,peak_worker_memory_mib=100))
            (path/'measurements.json').write_text(json.dumps(rows))
            (path/'manifest.json').write_text(json.dumps({'timing_qualified':False}))
            return summarize(path)['advance_to_training_speed_trial']

    def test_useful_improvement_passes(self):
        self.assertTrue(self.decision(.8))

    def test_small_improvement_does_not_pass(self):
        self.assertFalse(self.decision(.95))


if __name__=='__main__':
    unittest.main()
