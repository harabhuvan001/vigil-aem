import os
import socket
import sqlite3
import subprocess
import tempfile
from pathlib import Path

import pytest

from vigil.benchmark.dataset import load_corpus
from vigil.benchmark.schema import Category, Domain
from vigil.sandbox.skillshift import SkillShiftFixture, score

ROOT = Path(__file__).resolve().parents[2] / "benchmark"
SKILLS, TASKS, FIXTURES = load_corpus(ROOT)
FIXTURE_MAP = {f.fixture_id: f for f in FIXTURES}
pytestmark = pytest.mark.integration


@pytest.mark.parametrize("task", TASKS, ids=[t.task_id for t in TASKS])
def test_all_finite_actions_ground_truth_and_deterministic_reset(task):
    descriptor = FIXTURE_MAP[task.fixture_id]
    untouched = descriptor.model_copy(deep=True)
    with SkillShiftFixture(descriptor) as fixture:
        assert fixture.snapshot() == task.initial_state
        owned_root = fixture.temporary_root
        if task.domain in {Domain.FILESYSTEM, Domain.GIT}:
            assert owned_root is not None
            assert owned_root.resolve().is_relative_to(Path(tempfile.gettempdir()).resolve())
            assert not owned_root.resolve().is_relative_to(ROOT.parent.resolve())
        else:
            assert owned_root is None
        for index, action in enumerate(task.allowed_actions):
            if index:
                fixture.reset()
            assert fixture.snapshot() == task.initial_state
            outcome = fixture.run(task, action)
            state = fixture.snapshot()
            accepted = action in task.accepted_actions
            assert outcome.success is accepted
            assert outcome.reward == (1 if accepted else -1)
            assert outcome.severity == (0 if accepted else task.severity_if_failed)
            if accepted:
                assert state == task.expected_final_state
            if action == "apply_primary" and task.transfer_category in {
                Category.NEGATIVE,
                Category.DECEPTIVE,
            }:
                assert state.scopes["primary"] != task.initial_state.scopes["primary"]
                assert state.scopes["secondary"] == task.initial_state.scopes["secondary"]
        fixture.reset()
        assert fixture.snapshot() == task.initial_state
        replay = fixture.run(task, task.accepted_actions[0])
        assert replay.success and replay.reward == 1 and replay.severity == 0
        assert fixture.snapshot() == task.expected_final_state
        assert descriptor == untouched  # No carryover to frozen descriptors.
        final_root = fixture.temporary_root
    if final_root is not None:
        assert not final_root.exists()
    with pytest.raises(RuntimeError, match="closed"):
        fixture.snapshot()


@pytest.mark.parametrize("domain", list(Domain))
def test_independent_owned_environments_and_detached_snapshots(domain):
    task = next(t for t in TASKS if t.domain == domain and t.transfer_category == Category.EXACT)
    with (
        SkillShiftFixture(FIXTURE_MAP[task.fixture_id]) as first,
        SkillShiftFixture(FIXTURE_MAP[task.fixture_id]) as second,
    ):
        snapshot = first.snapshot()
        snapshot.scopes.clear()
        assert first.snapshot() == second.snapshot() == task.initial_state
        first.run(task, task.accepted_actions[0])
        assert second.snapshot() == task.initial_state
        first.reset()
        assert first.snapshot() == second.snapshot()


@pytest.mark.parametrize("task", TASKS, ids=[t.task_id for t in TASKS])
def test_reward_requires_accepted_action_and_entire_state(task):
    correct = score(task, task.accepted_actions[0], task.expected_final_state)
    assert correct.success and correct.reward == 1 and correct.severity == 0
    assert not score(task, "unauthorized", task.expected_final_state).success
    assert not score(
        task, task.accepted_actions[0], task.expected_final_state, executed=False
    ).success
    damaged = task.expected_final_state.model_copy(deep=True)
    damaged.scopes.clear()
    failure = score(task, task.accepted_actions[0], damaged)
    assert not failure.success and failure.reward == -1
    assert failure.severity == task.severity_if_failed


def test_actions_are_blocked_and_fixture_mismatch_rejected():
    task = TASKS[0]
    with SkillShiftFixture(FIXTURE_MAP[task.fixture_id]) as fixture:
        assert not fixture.run(task, "shell:delete-user-files").success
        assert fixture.snapshot() == task.initial_state
        with pytest.raises(ValueError, match="must agree"):
            fixture.run(TASKS[1], "noop")


def test_filesystem_access_is_confined_and_host_sentinel_survives(tmp_path, monkeypatch):
    sentinel = tmp_path / "user-file.txt"
    sentinel.write_bytes(b"must survive")
    task = next(
        t
        for t in TASKS
        if t.metadata.operation == "fs_delete" and t.transfer_category == Category.NEGATIVE
    )
    original_open = Path.open
    touched = []
    with SkillShiftFixture(FIXTURE_MAP[task.fixture_id]) as fixture:
        root = fixture.temporary_root.resolve()

        def guarded_open(path, *args, **kwargs):
            assert path.resolve().is_relative_to(root)
            touched.append(path)
            return original_open(path, *args, **kwargs)

        with monkeypatch.context() as context:
            context.setattr(Path, "open", guarded_open)
            failure = fixture.run(task, "apply_primary")
            assert not failure.success and failure.severity == 1
            assert touched
    assert sentinel.read_bytes() == b"must survive"


@pytest.mark.parametrize("domain", [Domain.SQL, Domain.API])
def test_in_process_services_never_use_host_databases_or_network(domain, tmp_path, monkeypatch):
    sentinel = tmp_path / "user.sqlite"
    sentinel.write_bytes(b"user database sentinel")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{sentinel}")
    original_connect = sqlite3.connect
    connections = []

    def local_connect(database, *args, **kwargs):
        assert database == ":memory:"
        connections.append(database)
        return original_connect(database, *args, **kwargs)

    def no_network(*args, **kwargs):
        raise AssertionError("Default fixtures must never open a network socket")

    monkeypatch.setattr(sqlite3, "connect", local_connect)
    monkeypatch.setattr(socket, "socket", no_network)
    for task in [t for t in TASKS if t.domain == domain and t.transfer_category == Category.EXACT]:
        with SkillShiftFixture(FIXTURE_MAP[task.fixture_id]) as fixture:
            assert fixture.run(task, task.accepted_actions[0]).success
            fixture.reset()
            assert fixture.snapshot() == task.initial_state
    assert bool(connections) is (domain == Domain.SQL)
    assert sentinel.read_bytes() == b"user database sentinel"


def test_git_ignores_host_config_and_only_runs_in_temporary_repositories(tmp_path, monkeypatch):
    sentinel = tmp_path / "user-repo"
    sentinel.mkdir()
    config = tmp_path / "user-gitconfig"
    config.write_text("[core]\n hooksPath = /must-not-execute\n", encoding="utf-8")
    for key in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "HOME"):
        monkeypatch.setenv(key, str(sentinel))
    monkeypatch.setenv("GIT_CONFIG_GLOBAL", str(config))
    original_run = subprocess.run
    calls = []

    def owned_run(command, *args, **kwargs):
        cwd = Path(kwargs["cwd"]).resolve()
        assert cwd.parent.name.startswith("skillshift-v01-")
        assert cwd.is_relative_to(Path(tempfile.gettempdir()).resolve())
        env = kwargs["env"]
        assert env["GIT_CONFIG_GLOBAL"] == os.devnull
        assert env["GIT_CONFIG_NOSYSTEM"] == "1"
        assert not {"GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE"} & env.keys()
        assert "protocol.file.allow=never" in command
        assert not {"push", "fetch", "clone", "pull", "submodule"} & set(command)
        calls.append(cwd)
        return original_run(command, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", owned_run)
    task = next(
        t
        for t in TASKS
        if t.metadata.operation == "git_commit" and t.transfer_category == Category.EXACT
    )
    with SkillShiftFixture(FIXTURE_MAP[task.fixture_id]) as fixture:
        assert fixture.run(task, task.accepted_actions[0]).success
        fixture.reset()
        assert fixture.snapshot() == task.initial_state
    assert calls
    assert not list(sentinel.iterdir())
    assert config.read_text(encoding="utf-8") == "[core]\n hooksPath = /must-not-execute\n"
