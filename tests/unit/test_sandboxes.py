import pytest

from vigil.agent.base import Task
from vigil.agent.executor import execute_action
from vigil.sandbox.base import SandboxState
from vigil.sandbox.filesystem import FilesystemSandbox
from vigil.sandbox.mock_api import MockAPISandbox
from vigil.sandbox.sql import SQLSandbox


@pytest.mark.parametrize(
    "sandbox_class,state,action",
    [
        (FilesystemSandbox, SandboxState(files={"temp": "contents"}), "delete:temp"),
        (MockAPISandbox, SandboxState(http_status=503), "retry"),
        (SQLSandbox, SandboxState(transaction_active=True, rows={"value": 0}), "update"),
    ],
)
def test_reset_restores_owned_initial_state(sandbox_class, state, action):
    sandbox = sandbox_class(state)
    original = sandbox.snapshot()
    assert sandbox.execute(action).success
    assert sandbox.snapshot() != original
    sandbox.reset()
    assert sandbox.snapshot() == original
    assert state == original
    detached_snapshot = sandbox.snapshot()
    detached_snapshot.files["leak"] = "leak"
    assert sandbox.snapshot() == original


def test_protected_backup_survives_severe_attempt():
    sandbox = FilesystemSandbox(SandboxState(files={"backup": "keep"}, protected_files=["backup"]))
    assert sandbox.execute("delete:backup").severity == 1
    assert sandbox.snapshot().files == {"backup": "keep"}


def test_executor_blocks_action_before_state_change():
    sandbox = FilesystemSandbox(SandboxState(files={"temp": "contents"}))
    original = sandbox.snapshot()
    task = Task(
        task_id="t", domain="filesystem", goal="keep", allowed_actions=[], expected_action="noop"
    )
    record = execute_action(task, sandbox, "delete:temp", seed=42)
    assert not record.success
    assert record.metadata["blocked"] is True
    assert sandbox.snapshot() == original
