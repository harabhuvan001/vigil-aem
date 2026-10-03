"""In-memory SQL action fixture; never parses or runs SQL on a real database."""

from vigil.sandbox.base import Outcome, Sandbox


class SQLSandbox(Sandbox):
    def execute(self, action: str) -> Outcome:
        if action != "update" or not self._state.transaction_active:
            return Outcome(reward=-1, success=False, severity=1)
        self._state.rows["value"] = self._state.rows.get("value", 0) + 1
        return Outcome(reward=1, success=True)
