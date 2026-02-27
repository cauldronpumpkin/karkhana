"""Edge routing logic for the state machine."""

from src.types.state import WorkingState


def should_retry_coder(state: WorkingState) -> str:
    """Determine if coder should retry or move to review."""
    # Check error logs for current file
    if state.current_file and not state.completed_files:
        return "retry_coder"
    return "review"


def route_to_sandbox(state: WorkingState) -> str:
    """Route to sandbox or end based on pending files."""
    if state.pending_files:
        return "execute_sandbox"
    return "final_review"
