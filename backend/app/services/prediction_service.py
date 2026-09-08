from __future__ import annotations

import json


def evaluate_patient_history(
    patient_data: dict, history: list[dict], symptom_description: str
) -> str:
    """
    Evaluates patient history, cancellation/attendance rates, and symptom rules
    to predict appointment priority and recommended specialty.
    """
    if not history:
        return json.dumps(
            {
                "patient": f"{patient_data['first_name']} {patient_data['last_name']}",
                "prediction": "no_data",
                "probability": "N/A",
                "message": "Insufficient history to predict.",
            },
            ensure_ascii=False,
            indent=2,
        )

    total = len(history)
    cancelled = sum(1 for h in history if h["status"] == "CANCELLED")
    completed = sum(1 for h in history if h["status"] == "COMPLETED")

    # Calculate base rates
    cancellation_rate = cancelled / total if total > 0 else 0
    attendance_rate = completed / total if total > 0 else 0

    # Risk factors
    risk_factors = []
    if cancellation_rate > 0.3:
        risk_factors.append("High rate of previous cancellations")
    if attendance_rate < 0.5:
        risk_factors.append("Low historical attendance rate")

    # Evaluate symptoms and match rules
    symptoms_lower = symptom_description.lower()
    matched_rule = None

    rules = {
        "emergency": {
            "keywords": ["chest pain", "severe bleeding", "unconscious", "stroke"],
            "level": "HIGH",
            "specialty": "Emergency",
            "time": "Immediate",
        },
        "urgent": {
            "keywords": ["high fever", "fracture", "severe pain"],
            "level": "MEDIUM-HIGH",
            "specialty": "Internal Medicine",
            "time": "24 hours",
        },
    }

    for _level, rule in rules.items():
        for keyword in rule["keywords"]:
            if keyword in symptoms_lower:
                matched_rule = rule
                break
        if matched_rule:
            break

    if not matched_rule:
        matched_rule = {
            "level": "MEDIUM",
            "specialty": "General Medicine",
            "time": "3-5 days",
        }

    return json.dumps(
        {
            "patient": f"{patient_data['first_name']} {patient_data['last_name']}",
            "prediction": matched_rule["level"],
            "recommended_specialty": matched_rule["specialty"],
            "estimated_time": matched_rule["time"],
            "risk_factors": risk_factors,
            "cancellation_rate": round(cancellation_rate, 2),
            "attendance_rate": round(attendance_rate, 2),
        },
        ensure_ascii=False,
        indent=2,
    )
