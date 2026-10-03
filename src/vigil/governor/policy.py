"""Three-way risk decision; thresholds are frozen using validation only."""

from typing import Literal


def risk_decision(risk: float, low: float, high: float) -> Literal["USE", "VERIFY", "REJECT"]:
    if not 0 <= low < high <= 1 or not 0 <= risk <= 1:
        raise ValueError("Invalid probability or decision thresholds")
    if risk <= low:
        return "USE"
    if risk >= high:
        return "REJECT"
    return "VERIFY"
