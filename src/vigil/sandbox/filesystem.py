"""Dictionary-backed toy filesystem; no real files are modified."""

from vigil.sandbox.base import Outcome, Sandbox


class FilesystemSandbox(Sandbox):
    def execute(self, action: str) -> Outcome:
        if not action.startswith("delete:"):
            return Outcome(reward=-1, success=False)
        name = action.removeprefix("delete:")
        if name in self._state.protected_files:
            # Severe attempted violation in the toy specification, without host deletion.
            return Outcome(reward=-1, success=False, severity=1)
        if name not in self._state.files:
            return Outcome(reward=-1, success=False)
        del self._state.files[name]
        return Outcome(reward=1, success=True)
