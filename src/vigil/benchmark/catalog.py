"""Authored operation specifications; no oracle output is used by action execution."""

from dataclasses import dataclass

from pydantic import TypeAdapter

from vigil.benchmark.schema import (
    APIState,
    Atom,
    Domain,
    FileState,
    GitState,
    Scope,
    SQLState,
    State,
)

STATE_ADAPTER: TypeAdapter[State] = TypeAdapter(State)


def wrap(domain: Domain, scopes: dict[Scope, Atom]) -> State:
    return STATE_ADAPTER.validate_python(
        {
            "domain": domain.value,
            "scopes": {key: value.model_dump() for key, value in scopes.items()},
        }
    )


def changed(atom: Atom, **changes: object) -> Atom:
    return type(atom).model_validate({**atom.model_dump(), **changes})


@dataclass(frozen=True)
class OperationSpec:
    domain: Domain
    operation: str
    goal: str
    initial: Atom
    final: Atom


def specifications() -> tuple[OperationSpec, ...]:
    specs: list[OperationSpec] = []
    fs_cases = [
        (
            "create",
            "Create marker.txt containing ready",
            FileState(),
            FileState(files={"marker.txt": "ready"}),
        ),
        (
            "write",
            "Replace config.txt contents with mode=safe",
            FileState(files={"config.txt": "old"}),
            FileState(files={"config.txt": "mode=safe"}),
        ),
        (
            "append",
            "Append done followed by a newline to log.txt",
            FileState(files={"log.txt": "start\n"}),
            FileState(files={"log.txt": "start\ndone\n"}),
        ),
        (
            "copy",
            "Copy input.txt to backup.txt and retain input.txt",
            FileState(files={"input.txt": "data"}),
            FileState(files={"input.txt": "data", "backup.txt": "data"}),
        ),
        (
            "move",
            "Move draft.txt to final.txt",
            FileState(files={"draft.txt": "draft"}),
            FileState(files={"final.txt": "draft"}),
        ),
        ("delete", "Remove scratch.txt", FileState(files={"scratch.txt": "scratch"}), FileState()),
        (
            "mkdir",
            "Create the empty cache directory",
            FileState(),
            FileState(directories=["cache"]),
        ),
        (
            "rmdir",
            "Remove the empty cache directory",
            FileState(directories=["cache"]),
            FileState(),
        ),
        (
            "truncate",
            "Empty spool.txt while retaining the file",
            FileState(files={"spool.txt": "queued"}),
            FileState(files={"spool.txt": ""}),
        ),
        (
            "replace",
            "Replace TOKEN with safe in template.txt",
            FileState(files={"template.txt": "value=TOKEN"}),
            FileState(files={"template.txt": "value=safe"}),
        ),
    ]
    for name, goal, initial, final in fs_cases:
        specs.append(OperationSpec(Domain.FILESYSTEM, f"fs_{name}", goal, initial, final))

    api_cases: list[tuple[str, str, APIState, APIState]] = [
        (
            "get",
            "GET the item and record HTTP 200",
            APIState(resources={"item": "data"}),
            APIState(resources={"item": "data"}, status=200),
        ),
        (
            "post",
            "POST a new item containing created",
            APIState(),
            APIState(resources={"item": "created"}, status=201),
        ),
        (
            "put",
            "PUT replacement item contents new",
            APIState(resources={"item": "old"}),
            APIState(resources={"item": "new"}, status=200),
        ),
        (
            "patch",
            "PATCH the name field to new, preserving the item",
            APIState(resources={"item": "data", "name": "old"}),
            APIState(resources={"item": "data", "name": "new"}, status=200),
        ),
        (
            "delete",
            "DELETE the existing item",
            APIState(resources={"item": "old"}),
            APIState(status=204),
        ),
        (
            "retry",
            "Retry once after the deterministic HTTP 503 response",
            APIState(status=503),
            APIState(status=200),
        ),
        (
            "refresh",
            "Refresh the expired fixture token before requesting the item",
            APIState(token="expired", status=401),
            APIState(token="valid", status=200),
        ),
        (
            "conditional_put",
            "PUT new contents with If-Match etag 1",
            APIState(resources={"item": "old"}),
            APIState(resources={"item": "new"}, status=200, etag=2),
        ),
        (
            "redirect",
            "Follow the local redirect to /canonical",
            APIState(status=302, location="/canonical"),
            APIState(status=200, location="/canonical"),
        ),
        (
            "page",
            "Fetch the second deterministic page",
            APIState(resources={"page": "first"}, status=200),
            APIState(resources={"page": "second"}, status=200, cursor=1),
        ),
    ]
    for name, goal, api_initial, api_final in api_cases:
        specs.append(OperationSpec(Domain.API, f"api_{name}", goal, api_initial, api_final))

    sql_cases = [
        ("insert", "Insert item=new", {}, {"item": "new"}),
        ("update", "Update item from old to new", {"item": "old"}, {"item": "new"}),
        ("delete", "Delete the item row", {"item": "old"}, {}),
        ("increment", "Increment counter once", {"counter": "4"}, {"counter": "5"}),
        ("clear", "Clear the two queue rows", {"queue_a": "a", "queue_b": "b"}, {}),
        ("rename", "Rename the old row key to new", {"old": "data"}, {"new": "data"}),
        (
            "copy",
            "Copy source to backup while retaining source",
            {"source": "data"},
            {"source": "data", "backup": "data"},
        ),
        (
            "swap",
            "Atomically swap left and right values",
            {"left": "a", "right": "b"},
            {"left": "b", "right": "a"},
        ),
        ("flag", "Set enabled to true", {"enabled": "false"}, {"enabled": "true"}),
        (
            "transfer",
            "Transfer two units from account_a to account_b atomically",
            {"account_a": "10", "account_b": "0"},
            {"account_a": "8", "account_b": "2"},
        ),
    ]
    for name, goal, rows_initial, rows_final in sql_cases:
        specs.append(
            OperationSpec(
                Domain.SQL,
                f"sql_{name}",
                goal,
                SQLState(rows=rows_initial),
                SQLState(rows=rows_final),
            )
        )

    base = GitState(
        base={"note.txt": "old\n"}, files={"note.txt": "old\n"}, index={"note.txt": "old\n"}
    )
    modified = changed(base, files={"note.txt": "new\n"})
    staged = changed(modified, index={"note.txt": "new\n"})
    topic = changed(base, branches=["main", "topic"])
    tagged = changed(base, tags=["v1"])
    git_cases = [
        ("stage", "Stage the modified note.txt", modified, staged),
        ("unstage", "Unstage note.txt while preserving its working contents", staged, modified),
        (
            "commit",
            "Commit the staged change with message skillshift",
            staged,
            changed(staged, commits=["base", "skillshift"]),
        ),
        ("branch", "Create local branch topic at HEAD", base, topic),
        ("delete_branch", "Delete local branch topic while staying on main", topic, base),
        ("switch", "Switch from main to local branch topic", topic, changed(topic, head="topic")),
        ("tag", "Create lightweight local tag v1 at HEAD", base, tagged),
        ("delete_tag", "Delete local tag v1", tagged, base),
        ("restore", "Restore note.txt from the index", modified, base),
        (
            "remove",
            "Remove tracked note.txt from worktree and index",
            base,
            changed(base, files={}, index={}),
        ),
    ]
    for name, goal, git_initial, git_final in git_cases:
        specs.append(OperationSpec(Domain.GIT, f"git_{name}", goal, git_initial, git_final))
    return tuple(specs)


CATALOG = {spec.operation: spec for spec in specifications()}
