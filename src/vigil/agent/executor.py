"""Execute one explicit toy action; autonomous action selection is planned."""

from vigil.agent.base import ExecutionRecord, Task
from vigil.sandbox.base import Sandbox


def execute_action(
    task: Task, sandbox: Sandbox, action: str, *, seed: int, skill_id: str | None = None
) -> ExecutionRecord:
    if action not in task.allowed_actions:
        return ExecutionRecord(
            task_id=task.task_id,
            skill_id=skill_id,
            reward=-1,
            success=False,
            seed=seed,
            metadata={"blocked": True, "reason": "action_not_allowed"},
        )
    outcome = sandbox.execute(action)
    return ExecutionRecord(
        task_id=task.task_id,
        skill_id=skill_id,
        reward=outcome.reward,
        success=outcome.success,
        seed=seed,
        metadata={"severity": outcome.severity, "fixture_only": True},
    )
