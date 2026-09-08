from __future__ import annotations

from datetime import datetime, timedelta


def find_shared_slots(
    all_slots: list[datetime], availability: dict[int, dict], duration_min: int
) -> list[datetime]:
    """
    Finds available time slots across multiple doctors/schedules.
    """
    shared_slots = []
    for slot in all_slots:
        slot_end = slot + timedelta(minutes=duration_min)
        all_free = True
        for _doctor_id, info in availability.items():
            for occupation in info["occupied"]:
                if (
                    slot < occupation["end_datetime"]
                    and slot_end > occupation["start_datetime"]
                ):
                    all_free = False
                    break
            if not all_free:
                break
        if all_free:
            shared_slots.append(slot)
    return shared_slots
