from __future__ import annotations

from typing import Any


def process_appointment_cancellation(result_state: Any) -> None:
    """
    Processes appointment cancellation state and executes the query result.
    """
    # Execute the query without assigning to an unused variable
    result_state.first()
