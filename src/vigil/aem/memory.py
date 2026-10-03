"""Counterfactual adverse memory; no permanent skill deletion or learned diagnosis."""

from typing import Literal

from pydantic import Field

from vigil.evaluation.prototype_schema import StrictModel


class AdverseMemoryEvent(StrictModel):
    event_id: str
    skill_id: str
    task_id: str
    context: dict[str, str | bool]
    failure: str
    severity: float = Field(ge=0, le=1, allow_inf_nan=False)
    causal_score: float = Field(ge=0, le=1, allow_inf_nan=False)
    diagnosis_confidence: float = Field(ge=0, le=1, allow_inf_nan=False)
    warning_conditions: list[str]
    source_execution_ids: list[str] = Field(min_length=2)
    provenance: dict[str, str]
    status: Literal["active", "retired"] = "active"

    @property
    def priority(self) -> float:
        return self.severity * self.causal_score * self.diagnosis_confidence


class AdverseExperienceMemory:
    def __init__(self, mode: Literal["naive", "severity", "full"]) -> None:
        self.mode = mode
        self.events: list[AdverseMemoryEvent] = []

    def admit(self, event: AdverseMemoryEvent) -> bool:
        if self.mode == "full" and (event.causal_score <= 0 or event.diagnosis_confidence <= 0):
            return False
        if any(prior.event_id == event.event_id for prior in self.events):
            return False
        self.events.append(AdverseMemoryEvent.model_validate(event.model_dump()))
        return True

    def risk(
        self, skill_id: str, context: dict[str, str | bool], semantic_overlap: dict[str, float]
    ) -> tuple[float, list[str]]:
        best = 0.0
        hits: list[str] = []
        for event in self.events:
            if event.status != "active" or event.skill_id != skill_id:
                continue
            keys = set(context) | set(event.context)
            factual = sum(context.get(key) == event.context.get(key) for key in keys) / len(keys)
            semantic = max(0.0, min(1.0, semantic_overlap.get(event.task_id, 0.0)))
            relevance = (factual + semantic) / 2
            weight = 1.0 if self.mode == "naive" else event.severity
            if self.mode == "full":
                weight = event.priority
            evidence = relevance * weight
            if evidence > 0:
                hits.append(event.event_id)
            best = max(best, evidence)
        return best, hits
