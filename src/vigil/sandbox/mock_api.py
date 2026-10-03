"""Deterministic HTTP simulator; never issues a network request."""

from vigil.sandbox.base import Outcome, Sandbox


class MockAPISandbox(Sandbox):
    def execute(self, action: str) -> Outcome:
        if action == "retry" and self._state.http_status == 503:
            self._state.http_status = 200
        elif action not in {"retry", "request"}:
            return Outcome(reward=-1, success=False)
        success = self._state.http_status == 200
        return Outcome(reward=1 if success else -1, success=success)
