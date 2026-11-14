"""EXP-003 differential harness and temporary power-request checks."""
from dataclasses import replace
import unittest

from transit_rl.environment.passenger_assignment import PassengerAssignment
from transit_rl.experiment.assignment_equivalence import (
    compare_assignments, fixture_corpus, reference_class, verify_corpus,
)
from transit_rl.utils.awake import ES_CONTINUOUS, ES_SYSTEM_REQUIRED, keep_awake


class AssignmentFoundationTests(unittest.TestCase):
    def result(self):
        _,cfg,network,demand,plans=next(fixture_corpus())
        return PassengerAssignment(network,cfg,[demand]).assign(1,plans[1])

    def test_current_implementation_matches_frozen_reference(self):
        self.assertGreater(len(verify_corpus()),50)
        self.assertIsNot(reference_class(),PassengerAssignment)

    def test_scalar_difference_is_detected(self):
        original=self.result()
        with self.assertRaisesRegex(AssertionError,'served_passengers'):
            compare_assignments(replace(original,served_passengers=original.served_passengers+1),original)

    def test_allocation_difference_is_detected(self):
        original=self.result()
        changed=original.assigned_demand.copy()
        changed[0,1]+=1
        changed.setflags(write=False)
        with self.assertRaisesRegex(AssertionError,'assigned_demand'):
            compare_assignments(replace(original,assigned_demand=changed),original)

    def test_writable_array_is_detected(self):
        original=self.result()
        with self.assertRaisesRegex(AssertionError,'assigned_demand'):
            compare_assignments(replace(original,assigned_demand=original.assigned_demand.copy()),original)


class AwakeScopeTests(unittest.TestCase):
    def test_request_restores_previous_flags_on_error(self):
        calls=[]
        def setter(flags):
            calls.append(flags)
            return ES_CONTINUOUS
        with self.assertRaisesRegex(ValueError,'benchmark failed'):
            with keep_awake(setter=setter) as state:
                self.assertTrue(state['requested'])
                raise ValueError('benchmark failed')
        self.assertEqual(calls,[ES_CONTINUOUS|ES_SYSTEM_REQUIRED,ES_CONTINUOUS])

    def test_failed_request_does_not_start_work(self):
        with self.assertRaises(OSError):
            with keep_awake(setter=lambda flags:0):
                self.fail('Should not start benchmark without sleep request')

    def test_disabled_scope_does_not_call_windows(self):
        def setter(flags):
            self.fail('Disabled scope must not change execution state')
        with keep_awake(enabled=False,setter=setter) as state:
            self.assertFalse(state['requested'])


if __name__=='__main__':
    unittest.main()
