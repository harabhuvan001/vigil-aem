"""Executable paired deterministic experiments, governance ablations and prospective AEM."""

import json
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from vigil.aem.memory import AdverseExperienceMemory, AdverseMemoryEvent
from vigil.agent.policy import choose_action, goal_action
from vigil.benchmark.schema import Category, Fixture, SourceSkill, TransferTask
from vigil.evaluation.prototype_schema import (
    PrototypeConfig,
    PublicTask,
    StrictModel,
    digest,
    expose,
    public_view,
)
from vigil.governor.applicability import inspect_preconditions
from vigil.governor.policy import risk_decision
from vigil.governor.risk import Predictor
from vigil.governor.shift import inspect_shift
from vigil.sandbox.skillshift import SkillShiftFixture


class Trial(StrictModel):
    execution_id: str
    task_id: str
    source_skill_id: str
    domain: str
    category: str
    system: str
    stage: str
    action: str
    skill_exposed: bool
    reward: float
    success: bool
    severity: float
    initial_state_hash: str
    public_view_hash: str
    final_state_hash: str
    final_state_json: str
    duration_seconds: float
    timestamp: str
    seed: int
    prompt_version: str
    benchmark_hash: str
    git_commit: str


class Recorder:
    def __init__(
        self,
        output: Path,
        fixtures: list[Fixture],
        config: PrototypeConfig,
        benchmark_hash: str,
        git_commit: str,
        resume: bool,
    ) -> None:
        self.path = output / "execution_ledger.jsonl"
        self.fixtures = {f.fixture_id: f for f in fixtures}
        self.config = config
        self.benchmark_hash = benchmark_hash
        self.commit = git_commit
        self.trials: dict[str, Trial] = {}
        if self.path.exists():
            if not resume:
                raise ValueError(
                    "Measured ledger exists; use a new output directory or explicit --resume"
                )
            for line in self.path.read_text(encoding="utf-8").splitlines():
                record = Trial.model_validate_json(line)
                if (
                    record.benchmark_hash != benchmark_hash
                    or record.prompt_version != config.prompt_version
                ):
                    raise ValueError("Cannot resume changed benchmark/policy provenance")
                self.trials[record.execution_id] = record

    def run(
        self, task: TransferTask, action: str, system: str, stage: str, skill_exposed: bool = False
    ) -> Trial:
        key = f"{stage}:{system}:{task.task_id}"
        if key in self.trials:
            cached = self.trials[key]
            if cached.action != action or cached.initial_state_hash != digest(task.initial_state):
                raise ValueError("Resume action/state changed; use a new experiment output")
            return cached
        started = time.perf_counter()
        with SkillShiftFixture(self.fixtures[task.fixture_id]) as environment:
            before = environment.observe()
            view = public_view(task, before)
            initial_hash = digest(before)
            if initial_hash != digest(task.initial_state):
                raise ValueError("Trial did not start at frozen initial state")
            outcome = environment.run(task, action)
            final = environment.observe()
        trial = Trial(
            execution_id=key,
            task_id=task.task_id,
            source_skill_id=task.source_skill_id,
            domain=task.domain.value,
            category=task.transfer_category.value,
            system=system,
            stage=stage,
            action=action,
            skill_exposed=skill_exposed,
            reward=outcome.reward,
            success=outcome.success,
            severity=outcome.severity,
            initial_state_hash=initial_hash,
            public_view_hash=digest(view),
            final_state_hash=digest(final),
            final_state_json=final.model_dump_json(),
            duration_seconds=time.perf_counter() - started,
            timestamp=datetime.now(UTC).isoformat(),
            seed=self.config.seed,
            prompt_version=self.config.prompt_version,
            benchmark_hash=self.benchmark_hash,
            git_commit=self.commit,
        )
        self.trials[key] = trial
        with self.path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(trial.model_dump_json() + "\n")
        return trial


def context_facts(view: PublicTask) -> dict[str, str | bool]:
    return {
        "domain": view.domain.value,
        "primary_exists": "primary" in view.state.scopes,
        "primary_protected": "primary" in view.protected_scopes,
        "requested_secondary": goal_action(view) == "apply_secondary",
        "completed_request": goal_action(view) == "noop",
    }


def transfer_label(gain: float, epsilon: float) -> str:
    return "HELP" if gain > epsilon else "HARM" if gain < -epsilon else "NEUTRAL"


def measure_pairs(
    tasks: list[TransferTask], skills: list[SourceSkill], similarities: Any, recorder: Recorder
) -> tuple[pd.DataFrame, pd.DataFrame]:
    skill_map = {s.skill_id: s for s in skills}
    skill_index = {s.skill_id: i for i, s in enumerate(skills)}
    pairs = []
    features = []
    # Historical statistics are measured source demonstrations, never target outcomes.
    histories = {}
    for source_skill in skills:
        source = next(
            t
            for t in tasks
            if t.source_skill_id == source_skill.skill_id and t.transfer_category == Category.EXACT
        )
        histories[source_skill.skill_id] = recorder.run(
            source, source_skill.source_context.expected_action, "SOURCE", "source", True
        )
    for index, task in enumerate(tasks):
        skill = expose(skill_map[task.source_skill_id])
        similarity = float(similarities[index, skill_index[task.source_skill_id]])
        view = public_view(task, task.initial_state)
        without_action = choose_action(
            view,
            None,
            similarity=similarity,
            similarity_threshold=recorder.config.similarity_threshold,
        )
        with_action = choose_action(
            view,
            skill,
            similarity=similarity,
            similarity_threshold=recorder.config.similarity_threshold,
        )
        without = recorder.run(task, without_action, "S0", "core", False)
        with_skill = recorder.run(task, with_action, "S1", "core", True)
        if (
            without.initial_state_hash != with_skill.initial_state_hash
            or without.public_view_hash != with_skill.public_view_hash
        ):
            raise ValueError("Paired conditions differ before skill exposure")
        gain = with_skill.reward - without.reward
        label = transfer_label(gain, recorder.config.epsilon)
        pairs.append(
            {
                "task_id": task.task_id,
                "source_skill_id": task.source_skill_id,
                "domain": task.domain.value,
                "category": task.transfer_category.value,
                "semantic_similarity": similarity,
                "reward_without": without.reward,
                "reward_with": with_skill.reward,
                "success_without": without.success,
                "success_with": with_skill.success,
                "severity_with": with_skill.severity,
                "transfer_gain": gain,
                "label": label,
                "initial_without": without.initial_state_hash,
                "initial_with": with_skill.initial_state_hash,
                "execution_without": without.execution_id,
                "execution_with": with_skill.execution_id,
                "action_without": without.action,
                "action_with": with_skill.action,
            }
        )
        applicability = inspect_preconditions(view, skill)
        shift = inspect_shift(view, skill)
        prior = histories[task.source_skill_id]
        features.append(
            {
                "task_id": task.task_id,
                "source_skill_id": task.source_skill_id,
                "semantic_similarity": similarity,
                "applicability_score": applicability.score,
                "failed_precondition_count": len(applicability.violated),
                "shift_score": shift.score,
                "domain_match": int(task.domain == skill.domain),
                "historical_skill_success_rate": float(prior.success),
                "historical_skill_failure_rate": float(not prior.success),
                "previous_usage_count": 1,
                "satisfied_conditions": json.dumps(applicability.satisfied),
                "violated_conditions": json.dumps(applicability.violated),
                "unknown_conditions": json.dumps(applicability.unknown),
                "shift_signals": json.dumps(shift.signals),
                "shift_unknown": json.dumps(shift.unknown),
                "label": label,
            }
        )
        if (index + 1) % 20 == 0:
            print(f"Measured core pairs {index + 1}/{len(tasks)}", flush=True)
    return pd.DataFrame(pairs), pd.DataFrame(features)


def select_thresholds(
    validation: pd.DataFrame, risks: Any, config: PrototypeConfig
) -> dict[str, Any]:
    choices = []
    for low in (0.1, 0.25, 0.4):
        for high in (0.6, 0.75, 0.9):
            decisions = np.asarray([risk_decision(float(r), low, high) for r in risks])
            # Sandbox postconditions in validation are represented by measured candidate success.
            eligible = validation.semantic_similarity.to_numpy() >= config.similarity_threshold
            use = eligible & (
                (decisions == "USE")
                | ((decisions == "VERIFY") & validation.success_with.to_numpy())
            )
            rewards = np.where(use, validation.reward_with, validation.reward_without)
            safe_avoided = eligible & (~use) & validation.success_with.to_numpy()
            utility = float(
                rewards.mean()
                - config.verification_cost * ((decisions == "VERIFY") & eligible).mean()
                - config.safe_rejection_cost * safe_avoided.mean()
            )
            choices.append({"low": low, "high": high, "validation_utility": utility})
    best = max(choices, key=lambda row: (row["validation_utility"], row["high"], row["low"]))
    return {**best, "selection_partition": "validation", "grid": choices}


def event_from_pair(row: Any, task: TransferTask, recorder: Recorder) -> AdverseMemoryEvent | None:
    if row.success_with:
        return None
    same_state = row.initial_with == row.initial_without
    causal = max(0.0, min(1.0, -float(row.transfer_gain) / 2))
    replay = recorder.run(task, row.action_with, "ATTRIBUTION", "aem-replay", True)
    original = recorder.trials[row.execution_with]
    reliable = (
        same_state
        and replay.final_state_hash == original.final_state_hash
        and replay.reward == original.reward
        and replay.action == original.action
    )
    return AdverseMemoryEvent(
        event_id=f"adverse:{task.task_id}",
        skill_id=task.source_skill_id,
        task_id=task.task_id,
        context=context_facts(public_view(task, task.initial_state)),
        failure="Measured source-exposed policy failed deterministic postconditions",
        severity=float(row.severity_with),
        causal_score=causal,
        diagnosis_confidence=1.0 if reliable else 0.0,
        warning_conditions=[
            key
            for key, value in context_facts(public_view(task, task.initial_state)).items()
            if value is True
        ],
        source_execution_ids=[row.execution_without, row.execution_with, replay.execution_id],
        provenance={
            "git_commit": recorder.commit,
            "benchmark_hash": recorder.benchmark_hash,
            "attribution": "paired-deterministic-v1",
        },
    )


def execute_governed(
    task: TransferTask,
    skill: SourceSkill,
    similarity: float,
    native_risk: float,
    calibrated_risk: float,
    system: str,
    stage: str,
    thresholds: dict[str, Any],
    recorder: Recorder,
    memory: AdverseExperienceMemory | None = None,
    semantic_overlap: dict[str, float] | None = None,
) -> dict[str, Any]:
    view = public_view(task, task.initial_state)
    candidate = choose_action(
        view,
        expose(skill),
        similarity=similarity,
        similarity_threshold=recorder.config.similarity_threshold,
    )
    fallback = goal_action(view)
    eligibility = similarity >= recorder.config.similarity_threshold
    decision = "USE"
    evidence = 0.0
    hits: list[str] = []
    verify_seconds = 0.0
    verified = False
    risk = native_risk if system == "S3" else calibrated_risk
    if system == "S2":
        check = inspect_preconditions(view, expose(skill))
        decision = "REJECT" if check.violated or check.unknown else "USE"
    elif system == "S3":
        decision = "REJECT" if risk >= 0.5 else "USE"
    else:
        if memory is not None:
            evidence, hits = memory.risk(
                skill.skill_id, context_facts(view), semantic_overlap or {}
            )
            risk = 1 - (1 - risk) * (1 - evidence)
        decision = risk_decision(float(risk), thresholds["low"], thresholds["high"])
    use = eligibility and decision == "USE"
    if eligibility and decision == "VERIFY" and system != "S4":
        verified = True
        verification = recorder.run(task, candidate, system, f"verify-{stage}", True)
        verify_seconds = verification.duration_seconds
        use = verification.success
    result = recorder.run(task, candidate if use else fallback, system, stage, True)
    return {
        **result.model_dump(),
        "candidate_used": use,
        "decision": decision,
        "risk": float(risk),
        "aem_relevance_weight": evidence,
        "aem_hits": json.dumps(hits),
        "verified": verified,
        "verification_seconds": verify_seconds,
        "semantic_similarity": similarity,
    }


def compare_systems(
    tasks: list[TransferTask],
    skills: list[SourceSkill],
    pairs: pd.DataFrame,
    features: pd.DataFrame,
    native: Predictor,
    calibrated: Predictor,
    thresholds: dict[str, Any],
    recorder: Recorder,
    goal_cosines: Any,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    task_map = {task.task_id: task for task in tasks}
    skill_map = {skill.skill_id: skill for skill in skills}
    task_index = {task.task_id: i for i, task in enumerate(tasks)}
    memories: dict[str, AdverseExperienceMemory] = {
        "S6": AdverseExperienceMemory("naive"),
        "S7": AdverseExperienceMemory("severity"),
        "S8": AdverseExperienceMemory("full"),
    }
    for row in pairs.itertuples():
        task = task_map[row.task_id]
        if features.loc[features.task_id == task.task_id, "partition"].iloc[0] not in {
            "fit",
            "calibration",
        }:
            continue
        event = event_from_pair(row, task, recorder)
        if event is not None:
            for memory in memories.values():
                memory.admit(event)
    outcomes = []
    native_values = native.probabilities(features)[:, 2]
    calibrated_values = calibrated.probabilities(features)[:, 2]
    for index, task in enumerate(tasks):
        pair = pairs.iloc[index]
        for system in ("S0", "S1"):
            trial = recorder.trials[
                pair.execution_without if system == "S0" else pair.execution_with
            ]
            outcomes.append(
                {
                    **trial.model_dump(),
                    "candidate_used": system == "S1"
                    and pair.semantic_similarity >= recorder.config.similarity_threshold,
                    "decision": "BASELINE",
                    "risk": None,
                    "aem_relevance_weight": 0.0,
                    "aem_hits": "[]",
                    "verified": False,
                    "verification_seconds": 0.0,
                    "semantic_similarity": pair.semantic_similarity,
                }
            )
        overlap = {
            other.task_id: float(goal_cosines[index, task_index[other.task_id]]) for other in tasks
        }
        for system in ("S2", "S3", "S4", "S5", "S6", "S7", "S8"):
            outcomes.append(
                execute_governed(
                    task,
                    skill_map[task.source_skill_id],
                    float(pair.semantic_similarity),
                    float(native_values[index]),
                    float(calibrated_values[index]),
                    system,
                    "systems",
                    thresholds,
                    recorder,
                    memories.get(system),
                    overlap,
                )
            )
        if (index + 1) % 20 == 0:
            print(f"Executed S0-S8 tasks {index + 1}/{len(tasks)}", flush=True)
    # Prospective controls: first encounters seed memory; later trials never train predictor.
    controls = []
    forced_records = []
    control_events = []
    test_skills = features.loc[features.partition == "test", "source_skill_id"].unique()
    for skill_id in test_skills:
        family = pairs[pairs.source_skill_id == skill_id]
        seed = family[family.category == "NEGATIVE"].iloc[0].copy()
        seed_task = task_map[seed.task_id]
        control_reference = {}
        # Separate forced-source interventions, measured rather than presumed harmful.
        for category in ("NEGATIVE", "DECEPTIVE"):
            forced_pair = family[family.category == category].iloc[0].copy()
            forced_task = task_map[forced_pair.task_id]
            without = recorder.run(
                forced_task,
                goal_action(public_view(forced_task, forced_task.initial_state)),
                "WITHOUT_SKILL",
                "forced-control-pair",
                False,
            )
            with_skill = recorder.run(
                forced_task,
                skill_map[skill_id].source_context.expected_action,
                "WITH_SKILL",
                "forced-control-pair",
                True,
            )
            if (
                without.initial_state_hash != with_skill.initial_state_hash
                or without.public_view_hash != with_skill.public_view_hash
            ):
                raise ValueError("Forced intervention pair differs before exposure")
            forced_pair["reward_without"] = without.reward
            forced_pair["reward_with"] = with_skill.reward
            forced_pair["success_with"] = with_skill.success
            forced_pair["success_without"] = without.success
            forced_pair["initial_hash_without"] = without.initial_state_hash
            forced_pair["initial_hash_with"] = with_skill.initial_state_hash
            forced_pair["severity_with"] = with_skill.severity
            forced_pair["transfer_gain"] = with_skill.reward - without.reward
            forced_pair["label"] = transfer_label(
                float(forced_pair.transfer_gain), recorder.config.epsilon
            )
            forced_pair["action_with"] = with_skill.action
            forced_pair["execution_without"] = without.execution_id
            forced_pair["execution_with"] = with_skill.execution_id
            control_reference[forced_task.task_id] = forced_pair
            forced_records.append(forced_pair.to_dict())
        seed = control_reference[seed_task.task_id]
        if seed.label != "HARM":
            continue
        memories_local = {
            "S6": AdverseExperienceMemory("naive"),
            "S7": AdverseExperienceMemory("severity"),
            "S8": AdverseExperienceMemory("full"),
        }
        event = event_from_pair(seed, seed_task, recorder)
        assert event is not None
        control_events.append(event.model_dump())
        for memory in memories_local.values():
            memory.admit(event)
        related = family[family.category == "DECEPTIVE"].iloc[0]
        safe = family[family.category == "EXACT"].iloc[0]
        unrelated = next(
            t
            for t in tasks
            if t.domain != seed_task.domain
            and t.transfer_category == Category.EXACT
            and t.source_skill_id in set(test_skills)
        )
        conditions = [
            ("exact_recurrence", seed_task),
            ("related_recurrence", task_map[related.task_id]),
            ("similar_safe", task_map[safe.task_id]),
            ("unrelated", unrelated),
        ]
        for condition, task in conditions:
            index = task_index[task.task_id]
            pair = control_reference.get(task.task_id, pairs.iloc[index])
            overlap = {seed_task.task_id: float(goal_cosines[index, task_index[seed_task.task_id]])}
            for system in ("S5", "S6", "S7", "S8"):
                row = execute_governed(
                    task,
                    skill_map[task.source_skill_id],
                    float(pair.semantic_similarity),
                    float(native_values[index]),
                    float(calibrated_values[index]),
                    system,
                    f"controls-{skill_id}-{condition}",
                    thresholds,
                    recorder,
                    memories_local.get(system),
                    overlap,
                )
                row.update(
                    {
                        "control": condition,
                        "seed_task_id": seed_task.task_id,
                        "reference_reward": pair.reward_without,
                        "measured_gain": pair.transfer_gain,
                        "source_candidate_safe": bool(pair.success_with),
                        "seed_severity": event.severity,
                    }
                )
                controls.append(row)
        print(f"Executed recurrence controls for {skill_id}", flush=True)
    all_events = [event.model_dump() for memory in memories.values() for event in memory.events]
    (recorder.path.parent / "adverse_memory.json").write_text(
        json.dumps(all_events, indent=2), encoding="utf-8"
    )
    (recorder.path.parent / "control_adverse_memory.json").write_text(
        json.dumps(control_events, indent=2), encoding="utf-8"
    )
    forced = pd.DataFrame(forced_records)
    forced.to_parquet(recorder.path.parent / "forced_control_pairs.parquet", index=False)
    forced_features = features[features.task_id.isin(forced.task_id)].drop(columns="label")
    forced_features = forced_features.merge(forced[["task_id", "label"]], on="task_id")
    forced_features.to_parquet(
        recorder.path.parent / "forced_control_features.parquet", index=False
    )
    return pd.DataFrame(outcomes), pd.DataFrame(controls)


def summarize_systems(
    outcomes: pd.DataFrame, pairs: pd.DataFrame, features: pd.DataFrame, epsilon: float
) -> pd.DataFrame:
    joined = outcomes.merge(pairs[["task_id", "reward_without", "transfer_gain"]], on="task_id")
    joined = joined.merge(features[["task_id", "partition"]], on="task_id")
    rows = []
    for population, data in [
        ("all_descriptive", joined),
        ("held_out_test", joined[joined.partition == "test"]),
    ]:
        for system, group in data.groupby("system", sort=True):
            gain = group.reward - group.reward_without
            beneficial = group.transfer_gain > epsilon
            rows.append(
                {
                    "population": population,
                    "system": system,
                    "tasks": len(group),
                    "success": float(group.success.mean()),
                    "mean_transfer_gain": float(gain.mean()),
                    "NTR": float((gain < -epsilon).mean()),
                    "PTR": float((gain[beneficial] > epsilon).mean()) if beneficial.any() else None,
                    "candidate_use_rate": float(group.candidate_used.mean()),
                    "verification_frequency": float(group.verified.mean()),
                    "mean_runtime_seconds": float(
                        (group.duration_seconds + group.verification_seconds).mean()
                    ),
                    "mean_verification_seconds": float(group.verification_seconds.mean()),
                }
            )
    return pd.DataFrame(rows)


def summarize_aem(controls: pd.DataFrame, epsilon: float) -> pd.DataFrame:
    rows = []
    if controls.empty:
        return pd.DataFrame(
            columns=[
                "system",
                "trials",
                "FRR",
                "CFA",
                "OAR",
                "PTR",
                "NTR",
                "success",
                "mean_transfer_gain",
            ]
        )
    for system, group in controls.groupby("system", sort=True):
        recurrence = group.control.isin(["exact_recurrence", "related_recurrence"]) & (
            group.measured_gain < -epsilon
        )
        severe = recurrence & (group.seed_severity >= 1)
        safe = group.control.isin(["similar_safe", "unrelated"]) & group.source_candidate_safe
        beneficial = group.measured_gain > epsilon
        gains = group.reward - group.reference_reward
        rows.append(
            {
                "system": system,
                "trials": len(group),
                "recurrence_trials": int(recurrence.sum()),
                "safe_trials": int(safe.sum()),
                "FRR": float((~group.success[recurrence]).mean()) if recurrence.any() else None,
                "CFA": float(group.success[severe].mean()) if severe.any() else None,
                "OAR": float((~group.candidate_used[safe]).mean()) if safe.any() else None,
                "PTR": float((gains[beneficial] > epsilon).mean()) if beneficial.any() else None,
                "NTR": float((gains < -epsilon).mean()),
                "success": float(group.success.mean()),
                "mean_transfer_gain": float(gains.mean()),
                "verification_frequency": float(group.verified.mean()),
            }
        )
    return pd.DataFrame(rows)
