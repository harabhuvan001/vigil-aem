"""Transfer arithmetic only; thresholds require experiment preregistration."""

import math
from enum import StrEnum


class TransferLabel(StrEnum):
    HELP = "HELP"
    NEUTRAL = "NEUTRAL"
    HARM = "HARM"


def transfer_delta(reward_with_skill: float, reward_without_skill: float) -> float:
    if not all(math.isfinite(value) for value in (reward_with_skill, reward_without_skill)):
        raise ValueError("Rewards must be finite")
    delta = reward_with_skill - reward_without_skill
    if not math.isfinite(delta):
        raise ValueError("Delta must be finite")
    return delta


def classify_transfer(delta: float, *, epsilon: float) -> TransferLabel:
    if not math.isfinite(delta) or not math.isfinite(epsilon) or epsilon < 0:
        raise ValueError("Delta must be finite and epsilon must be finite and nonnegative")
    if delta > epsilon:
        return TransferLabel.HELP
    if delta < -epsilon:
        return TransferLabel.HARM
    return TransferLabel.NEUTRAL
