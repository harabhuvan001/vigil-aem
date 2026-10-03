"""Adverse experience data only; diagnosis and learning are not implemented."""

from pydantic import BaseModel, ConfigDict, Field, JsonValue


class AdverseExperience(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)

    event_id: str = Field(min_length=1)
    skill_id: str | None = None
    context: dict[str, JsonValue] = Field(default_factory=dict)
    severity: float = Field(ge=0, le=1, allow_inf_nan=False)
    causal_score: float = Field(ge=0, le=1, allow_inf_nan=False)
    diagnosis_confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    warning_conditions: list[str] = Field(default_factory=list)
