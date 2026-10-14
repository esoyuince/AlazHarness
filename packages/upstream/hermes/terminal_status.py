"""Unchanged upstream function; see packages/upstream/README.md and config/components.lock.json."""
from __future__ import annotations
from typing import Any

def terminal_run_status(result: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Map a ``run_conversation`` result to its terminal run status and the wire fields every
    terminal event/status carries. An interrupted turn is ``cancelled``; a turn that ended
    without finishing (``failed``, ``partial``, or ``completed=False`` such as the iteration
    budget) is ``failed``, so ``completed: true`` never rides next to ``partial: true``."""
    interrupted = bool(result.get("interrupted"))
    finished = (
        not interrupted and not result.get("failed") and not result.get("partial")
        and result.get("completed") is not False
    )
    status = "cancelled" if interrupted else "completed" if finished else "failed"
    fields: dict[str, Any] = {
        "completed": finished, "partial": bool(result.get("partial")), "interrupted": interrupted,
    }
    if not finished and result.get("turn_exit_reason"):
        fields["turn_exit_reason"] = str(result["turn_exit_reason"])
    if result.get("pending_steer"):
        # Undelivered steer text rides on every terminal event/status for client replay.
        fields["pending_steer"] = result["pending_steer"]
    return status, fields
