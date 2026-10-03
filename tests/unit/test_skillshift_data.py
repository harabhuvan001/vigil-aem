import hashlib
import json
import math
from collections import Counter
from contextlib import nullcontext
from pathlib import Path

import pytest
from pydantic import ValidationError

from vigil.benchmark.catalog import CATALOG
from vigil.benchmark.dataset import (
    DATA_PATHS,
    FIXTURES_PATH,
    SKILLS_PATH,
    TASKS_PATH,
    build_corpus,
    checksum_bytes,
    jsonl_bytes,
    load_corpus,
    validate_integrity,
    verify_checksums,
    write_corpus,
)
from vigil.benchmark.schema import Category, Domain, FileState, Fixture, SourceSkill, TransferTask

ROOT = Path(__file__).resolve().parents[2] / "benchmark"
SKILLS, TASKS, FIXTURES = load_corpus(ROOT)


def test_counts_domains_ids_and_categories():
    assert len(SKILLS) == 40
    assert len(TASKS) == len(FIXTURES) == 200
    assert set(Domain) == {skill.domain for skill in SKILLS}
    assert Counter(s.domain for s in SKILLS) == {domain: 10 for domain in Domain}
    assert Counter(t.domain for t in TASKS) == {domain: 50 for domain in Domain}
    assert Counter(t.transfer_category for t in TASKS) == {category: 40 for category in Category}
    assert len(CATALOG) == 40
    for skill in SKILLS:
        group = [task for task in TASKS if task.source_skill_id == skill.skill_id]
        assert Counter(t.transfer_category for t in group) == Counter(Category)
        assert len({t.metadata.operation for t in group}) == 1
    validate_integrity(SKILLS, TASKS, FIXTURES)


@pytest.mark.parametrize(
    "model,path", [(SourceSkill, SKILLS_PATH), (TransferTask, TASKS_PATH), (Fixture, FIXTURES_PATH)]
)
def test_all_jsonl_records_roundtrip_and_schema_exports(model, path):
    for line in (ROOT / path).read_text(encoding="utf-8").splitlines():
        record = model.model_validate_json(line)
        assert model.model_validate_json(record.model_dump_json()) == record
    names = {
        SourceSkill: "skillshift_skill",
        TransferTask: "skillshift_transfer_task",
        Fixture: "skillshift_fixture",
    }
    schema = json.loads((ROOT / "schemas" / f"{names[model]}.json").read_text(encoding="utf-8"))
    assert schema == model.model_json_schema()


@pytest.mark.parametrize("value", [-0.01, 1.01, math.nan, math.inf, True, "0.5"])
def test_severity_values_are_finite_numeric_in_range(value):
    data = TASKS[0].model_dump()
    data["severity_if_failed"] = value
    with pytest.raises(ValidationError):
        TransferTask.model_validate(data)


@pytest.mark.parametrize(
    "field,value",
    [
        ("domain", "external"),
        ("transfer_category", "UNKNOWN"),
        ("task_id", ""),
        ("natural_language_goal", ""),
        ("allowed_actions", []),
        ("accepted_actions", []),
        ("allowed_actions", ["shell:rm"]),
        ("accepted_actions", ["apply_secondary"]),
        ("allowed_actions", ["noop", "noop"]),
        ("reward_rules", None),
        ("expected_final_state", None),
        ("fixture_id", "../escape"),
    ],
)
def test_invalid_task_contracts_are_rejected(field, value):
    data = TASKS[0].model_dump()
    data[field] = value
    with pytest.raises(ValidationError):
        TransferTask.model_validate(data)


@pytest.mark.parametrize("field", list(TransferTask.model_fields))
def test_each_task_field_is_required(field):
    data = TASKS[0].model_dump()
    del data[field]
    with pytest.raises(ValidationError):
        TransferTask.model_validate(data)


@pytest.mark.parametrize("field", list(SourceSkill.model_fields))
def test_each_skill_contract_is_required_except_fixed_version(field):
    data = SKILLS[0].model_dump()
    del data[field]
    if field == "version":
        assert SourceSkill.model_validate(data).version == "0.1"
    else:
        with pytest.raises(ValidationError):
            SourceSkill.model_validate(data)


def test_unknown_fields_and_invalid_nested_rules_fail_closed():
    data = TASKS[0].model_dump()
    data["invented"] = "unsupported"
    with pytest.raises(ValidationError):
        TransferTask.model_validate(data)
    data = TASKS[0].model_dump()
    data["reward_rules"]["rule_id"] = "llm_judge"
    with pytest.raises(ValidationError):
        TransferTask.model_validate(data)
    data = FIXTURES[0].model_dump()
    data["reset_id"] = "external_database"
    with pytest.raises(ValidationError):
        Fixture.model_validate(data)


@pytest.mark.parametrize(
    "path",
    [
        "../user.txt",
        "/etc/passwd",
        "C:/Users/file",
        r"..\file",
        ".git/config",
        "safe/../../escape",
        "nul",
        "a:stream",
    ],
)
def test_paths_cannot_reference_host_or_git_metadata(path):
    with pytest.raises(ValidationError):
        FileState(files={path: "data"})


@pytest.mark.parametrize(
    "mutation",
    [
        "skill_count",
        "task_count",
        "fixture_count",
        "duplicate_skill",
        "duplicate_task",
        "duplicate_fixture",
        "duplicate_source",
        "missing_skill",
        "missing_fixture",
        "missing_category",
        "bad_domain",
        "fixture_state",
        "unknown_operation",
        "source_context",
        "metadata_operation",
        "invalid_severity",
        "missing_reward",
        "missing_outcome",
    ],
)
def test_integrity_detects_corruption(mutation):
    skills = [s.model_copy(deep=True) for s in SKILLS]
    tasks = [t.model_copy(deep=True) for t in TASKS]
    fixtures = [f.model_copy(deep=True) for f in FIXTURES]
    if mutation == "skill_count":
        skills.pop()
    elif mutation == "task_count":
        tasks.pop()
    elif mutation == "fixture_count":
        fixtures.pop()
    elif mutation == "duplicate_skill":
        skills[1] = skills[0]
    elif mutation == "duplicate_task":
        tasks[1] = tasks[0]
    elif mutation == "duplicate_fixture":
        fixtures[1] = fixtures[0]
    elif mutation == "duplicate_source":
        skills[1].source_task_id = skills[0].source_task_id
    elif mutation == "missing_skill":
        tasks[0].source_skill_id = "missing"
    elif mutation == "missing_fixture":
        tasks[0].fixture_id = "missing"
    elif mutation == "missing_category":
        tasks[1].transfer_category = Category.EXACT
    elif mutation == "bad_domain":
        skills[0] = skills[0].model_copy(update={"domain": "external"})
    elif mutation == "fixture_state":
        fixtures[0] = fixtures[0].model_copy(update={"initial_state": fixtures[1].initial_state})
    elif mutation == "unknown_operation":
        fixtures[0].operation = "unknown"
    elif mutation == "source_context":
        skills[0].source_context.fixture_id = "missing"
    elif mutation == "metadata_operation":
        tasks[0].metadata.operation = "unknown"
    elif mutation == "invalid_severity":
        tasks[0] = tasks[0].model_copy(update={"severity_if_failed": math.nan})
    elif mutation == "missing_reward":
        tasks[0] = tasks[0].model_copy(update={"reward_rules": None})
    elif mutation == "missing_outcome":
        tasks[0] = tasks[0].model_copy(update={"expected_final_state": None})
    warning = (
        pytest.warns(UserWarning)
        if mutation in {"bad_domain", "missing_outcome"}
        else nullcontext()
    )
    with warning, pytest.raises((ValueError, ValidationError)):
        validate_integrity(skills, tasks, fixtures)


def test_checksums_and_regeneration_are_byte_reproducible(tmp_path):
    verify_checksums(ROOT)
    skills, tasks, fixtures = build_corpus()
    for path, records in [(SKILLS_PATH, skills), (TASKS_PATH, tasks), (FIXTURES_PATH, fixtures)]:
        assert jsonl_bytes(records) == (ROOT / path).read_bytes()
    write_corpus(tmp_path)
    write_corpus(tmp_path)  # Identical data is safe; no implicit reannotation.
    verify_checksums(tmp_path)
    assert checksum_bytes(tmp_path) == (ROOT / "skillshift_v0.1.sha256").read_bytes()
    for path in DATA_PATHS:
        assert (tmp_path / path).read_bytes() == (ROOT / path).read_bytes()
        assert b"\r\n" not in (ROOT / path).read_bytes()
    for line in (ROOT / "skillshift_v0.1.sha256").read_text().splitlines():
        digest, path = line.split("  ")
        assert digest == hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def test_tamper_is_detected_and_frozen_data_cannot_be_overwritten(tmp_path):
    write_corpus(tmp_path)
    target = tmp_path / TASKS_PATH
    original = target.read_bytes()
    target.write_bytes(original + b"\n")
    with pytest.raises(ValueError, match="SHA256"):
        verify_checksums(tmp_path)
    with pytest.raises(ValueError, match="Refusing to overwrite"):
        write_corpus(tmp_path)
    assert target.read_bytes() == original + b"\n"
