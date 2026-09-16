"""
Finite State Machine (FSM) for multi-cloud storage orchestration.

Defines the states and transitions for coordinating asynchronous operations
across AWS S3, Azure Blob, and GCP Storage with transactional rollback.
"""

from enum import Enum
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone


class StorageFSMState(str, Enum):
    """FSM States for multi-cloud storage lifecycle."""

    # Initial states
    INITIALIZED = "INITIALIZED"
    PARSING_INTENT = "PARSING_INTENT"
    INTENT_PARSED = "INTENT_PARSED"

    # Optimization states
    OPTIMIZING_POLICY = "OPTIMIZING_POLICY"
    POLICY_DETERMINED = "POLICY_DETERMINED"

    # Preparation states
    PREPARING_CLOUDS = "PREPARING_CLOUDS"
    ALLOCATING_PRESIGNED = "ALLOCATING_PRESIGNED"
    PRESIGNED_READY = "PRESIGNED_READY"

    # Transfer states
    UPLOADING_PARTS = "UPLOADING_PARTS"
    PARTS_UPLOADED = "PARTS_UPLOADED"
    COMPLETING_SESSIONS = "COMPLETING_SESSIONS"

    # Verification states
    VERIFYING_INTEGRITY = "VERIFYING_INTEGRITY"
    INTEGRITY_CONFIRMED = "INTEGRITY_CONFIRMED"

    # Terminal states
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLING_BACK = "ROLLING_BACK"
    ROLLED_BACK = "ROLLED_BACK"


# Allowed transitions matrix
ALLOWED_TRANSITIONS = {
    StorageFSMState.INITIALIZED: [
        StorageFSMState.PARSING_INTENT,
        StorageFSMState.FAILED
    ],
    StorageFSMState.PARSING_INTENT: [
        StorageFSMState.INTENT_PARSED,
        StorageFSMState.FAILED
    ],
    StorageFSMState.INTENT_PARSED: [
        StorageFSMState.OPTIMIZING_POLICY,
        StorageFSMState.FAILED
    ],
    StorageFSMState.OPTIMIZING_POLICY: [
        StorageFSMState.POLICY_DETERMINED,
        StorageFSMState.FAILED
    ],
    StorageFSMState.POLICY_DETERMINED: [
        StorageFSMState.PREPARING_CLOUDS,
        StorageFSMState.FAILED
    ],
    StorageFSMState.PREPARING_CLOUDS: [
        StorageFSMState.ALLOCATING_PRESIGNED,
        StorageFSMState.ROLLING_BACK,
        StorageFSMState.FAILED
    ],
    StorageFSMState.ALLOCATING_PRESIGNED: [
        StorageFSMState.PRESIGNED_READY,
        StorageFSMState.ROLLING_BACK,
        StorageFSMState.FAILED
    ],
    StorageFSMState.PRESIGNED_READY: [
        StorageFSMState.UPLOADING_PARTS,
        StorageFSMState.ROLLING_BACK,
        StorageFSMState.FAILED
    ],
    StorageFSMState.UPLOADING_PARTS: [
        StorageFSMState.PARTS_UPLOADED,
        StorageFSMState.ROLLING_BACK,
        StorageFSMState.FAILED
    ],
    StorageFSMState.PARTS_UPLOADED: [
        StorageFSMState.COMPLETING_SESSIONS,
        StorageFSMState.ROLLING_BACK,
        StorageFSMState.FAILED
    ],
    StorageFSMState.COMPLETING_SESSIONS: [
        StorageFSMState.VERIFYING_INTEGRITY,
        StorageFSMState.ROLLING_BACK,
        StorageFSMState.FAILED
    ],
    StorageFSMState.VERIFYING_INTEGRITY: [
        StorageFSMState.INTEGRITY_CONFIRMED,
        StorageFSMState.ROLLING_BACK,
        StorageFSMState.FAILED
    ],
    StorageFSMState.INTEGRITY_CONFIRMED: [
        StorageFSMState.COMPLETED
    ],
    StorageFSMState.ROLLING_BACK: [
        StorageFSMState.ROLLED_BACK,
        StorageFSMState.FAILED
    ],
    StorageFSMState.FAILED: [
        StorageFSMState.ROLLING_BACK
    ],
    # Terminal states
    StorageFSMState.COMPLETED: [],
    StorageFSMState.ROLLED_BACK: [],
}


@dataclass
class StateTransitionLog:
    """Record of a single state transition."""
    from_state: StorageFSMState
    to_state: StorageFSMState
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    message: str = ""
    error: Optional[str] = None


class StorageFSM:
    """
    State machine instance tracking the execution of a multi-cloud placement operation.
    """

    def __init__(self, operation_id: str):
        self.operation_id = operation_id
        self.current_state = StorageFSMState.INITIALIZED
        self.history: List[StateTransitionLog] = []
        self.context: Dict = {}
        self.created_at = datetime.now(timezone.utc)

    def transition_to(
        self,
        new_state: StorageFSMState,
        message: str = "",
        error: Optional[str] = None
    ) -> bool:
        """
        Attempt a state transition.

        Returns True if transition is valid, False otherwise.
        """
        allowed = ALLOWED_TRANSITIONS.get(self.current_state, [])

        if new_state not in allowed:
            # Invalid transition
            err_msg = f"Invalid transition from {self.current_state} to {new_state}"
            self.history.append(
                StateTransitionLog(
                    from_state=self.current_state,
                    to_state=self.current_state,
                    message=err_msg,
                    error=err_msg
                )
            )
            return False

        # Record valid transition
        log_entry = StateTransitionLog(
            from_state=self.current_state,
            to_state=new_state,
            message=message,
            error=error
        )
        self.history.append(log_entry)
        self.current_state = new_state

        return True

    def can_transition_to(self, new_state: StorageFSMState) -> bool:
        """Check if transition to new_state is allowed."""
        return new_state in ALLOWED_TRANSITIONS.get(self.current_state, [])

    def is_terminal(self) -> bool:
        """Check if state machine has reached a terminal state."""
        return self.current_state in [
            StorageFSMState.COMPLETED,
            StorageFSMState.ROLLED_BACK,
            StorageFSMState.FAILED
        ]

    def to_dict(self) -> Dict:
        """Serialize FSM state for API responses."""
        return {
            "operation_id": self.operation_id,
            "current_state": self.current_state.value,
            "is_terminal": self.is_terminal(),
            "history": [
                {
                    "from_state": log.from_state.value,
                    "to_state": log.to_state.value,
                    "timestamp": log.timestamp.isoformat(),
                    "message": log.message,
                    "error": log.error
                }
                for log in self.history
            ],
            "context": self.context,
            "created_at": self.created_at.isoformat()
        }
