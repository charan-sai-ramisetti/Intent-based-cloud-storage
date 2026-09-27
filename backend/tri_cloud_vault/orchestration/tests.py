import unittest
from orchestration.fsm import StorageFSM, StorageFSMState


class OrchestrationFSMTests(unittest.TestCase):
    """Test Storage FSM state transitions and error handling."""

    def test_fsm_initial_state(self):
        fsm = StorageFSM("op-test-123")
        self.assertEqual(fsm.current_state, StorageFSMState.INITIALIZED)
        self.assertEqual(fsm.operation_id, "op-test-123")
        self.assertFalse(fsm.is_terminal())

    def test_fsm_valid_transitions(self):
        fsm = StorageFSM("op-test-456")
        self.assertTrue(fsm.transition_to(StorageFSMState.PARSING_INTENT))
        self.assertTrue(fsm.transition_to(StorageFSMState.INTENT_PARSED))
        self.assertTrue(fsm.transition_to(StorageFSMState.OPTIMIZING_POLICY))
        self.assertTrue(fsm.transition_to(StorageFSMState.POLICY_DETERMINED))
        self.assertTrue(fsm.transition_to(StorageFSMState.PREPARING_CLOUDS))
        self.assertTrue(fsm.transition_to(StorageFSMState.ALLOCATING_PRESIGNED))
        self.assertTrue(fsm.transition_to(StorageFSMState.PRESIGNED_READY))
        self.assertFalse(fsm.is_terminal())

    def test_fsm_full_lifecycle(self):
        """Test full successful forward transition through all phases to COMPLETED."""
        fsm = StorageFSM("op-test-full")
        self.assertTrue(fsm.transition_to(StorageFSMState.PARSING_INTENT))
        self.assertTrue(fsm.transition_to(StorageFSMState.INTENT_PARSED))
        self.assertTrue(fsm.transition_to(StorageFSMState.OPTIMIZING_POLICY))
        self.assertTrue(fsm.transition_to(StorageFSMState.POLICY_DETERMINED))
        self.assertTrue(fsm.transition_to(StorageFSMState.PREPARING_CLOUDS))
        self.assertTrue(fsm.transition_to(StorageFSMState.ALLOCATING_PRESIGNED))
        self.assertTrue(fsm.transition_to(StorageFSMState.PRESIGNED_READY))
        self.assertTrue(fsm.transition_to(StorageFSMState.UPLOADING_PARTS))
        self.assertTrue(fsm.transition_to(StorageFSMState.PARTS_UPLOADED))
        self.assertTrue(fsm.transition_to(StorageFSMState.COMPLETING_SESSIONS))
        self.assertTrue(fsm.transition_to(StorageFSMState.VERIFYING_INTEGRITY))
        self.assertTrue(fsm.transition_to(StorageFSMState.INTEGRITY_CONFIRMED))
        self.assertTrue(fsm.transition_to(StorageFSMState.COMPLETED))
        self.assertTrue(fsm.is_terminal())
        self.assertEqual(fsm.current_state, StorageFSMState.COMPLETED)

    def test_fsm_invalid_transition(self):
        """FSM must reject transitions that violate the state graph."""
        fsm = StorageFSM("op-test-invalid")
        # Direct jump from INITIALIZED to COMPLETED is forbidden
        self.assertFalse(fsm.transition_to(StorageFSMState.COMPLETED))
        self.assertEqual(fsm.current_state, StorageFSMState.INITIALIZED)

    def test_fsm_rollback_transition(self):
        fsm = StorageFSM("op-test-789")
        fsm.transition_to(StorageFSMState.PARSING_INTENT)
        fsm.transition_to(StorageFSMState.INTENT_PARSED)
        fsm.transition_to(StorageFSMState.OPTIMIZING_POLICY)
        fsm.transition_to(StorageFSMState.POLICY_DETERMINED)
        fsm.transition_to(StorageFSMState.PREPARING_CLOUDS)
        fsm.transition_to(StorageFSMState.ROLLING_BACK)
        fsm.transition_to(StorageFSMState.ROLLED_BACK)
        self.assertTrue(fsm.is_terminal())
        self.assertEqual(fsm.current_state, StorageFSMState.ROLLED_BACK)
