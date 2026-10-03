import json
from pathlib import Path

import pytest

from vigil.agent.base import Task
from vigil.agent.executor import execute_action
from vigil.sandbox.base import SandboxState
from vigil.sandbox.filesystem import FilesystemSandbox
from vigil.sandbox.mock_api import MockAPISandbox
from vigil.sandbox.sql import SQLSandbox

CASES = json.loads(
    (Path(__file__).resolve().parents[2] / "benchmark/fixtures/toy_cases.json").read_text(
        encoding="utf-8"
    )
)
SANDBOXES = {"http": MockAPISandbox, "filesystem": FilesystemSandbox, "sql": SQLSandbox}


@pytest.mark.integration
@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_versioned_fixture_matches_deterministic_execution(case):
    sandbox = SANDBOXES[case["domain"]](SandboxState.model_validate(case["state"]))
    task = Task(
        task_id=case["id"],
        domain=case["domain"],
        goal="infrastructure smoke only",
        allowed_actions=[case["action"]],
        expected_action=case["action"],
    )
    first = execute_action(task, sandbox, case["action"], seed=42)
    assert first.success is case["success"]
    assert first.reward == case["reward"]
    assert first.metadata["severity"] == case["severity"]
    sandbox.reset()
    assert execute_action(task, sandbox, case["action"], seed=42) == first
