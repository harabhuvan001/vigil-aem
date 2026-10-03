"""Private finite Git fixture driver; invoked only inside owned temporary directories."""

import os
import shutil
import subprocess
from pathlib import Path

from vigil.benchmark.schema import GitState, safe_path


class _GitRepository:
    def __init__(self, root: Path, state: GitState) -> None:
        self.root = root
        self.base = dict(state.base)
        binary = shutil.which("git")
        if binary is None:
            raise RuntimeError("Git is required for SkillShiftBench fixtures")
        self.binary = binary
        # Do not inherit GIT_DIR, credentials, user config, templates, or executable hooks.
        self.env = {
            key: os.environ[key]
            for key in ("PATH", "SYSTEMROOT", "TEMP", "TMP")
            if key in os.environ
        }
        self.env.update(
            {
                "HOME": str(root.parent),
                "XDG_CONFIG_HOME": str(root.parent),
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "GIT_ATTR_NOSYSTEM": "1",
                "GIT_TERMINAL_PROMPT": "0",
                "GIT_AUTHOR_NAME": "SkillShift Fixture",
                "GIT_COMMITTER_NAME": "SkillShift Fixture",
                "GIT_AUTHOR_EMAIL": "fixture@example.invalid",
                "GIT_COMMITTER_EMAIL": "fixture@example.invalid",
                "GIT_AUTHOR_DATE": "2000-01-01T00:00:00+0000",
                "GIT_COMMITTER_DATE": "2000-01-01T00:00:00+0000",
                "LC_ALL": "C",
            }
        )
        root.mkdir()
        (root.parent / "empty-hooks").mkdir(exist_ok=True)
        self.run("init", "--initial-branch=main", f"--template={root.parent / 'empty-hooks'}")
        self._set_worktree(state.base)
        self.run("add", "--all")
        self.run("commit", "--allow-empty", "-m", "base")
        if state.commits == ["base", "skillshift"]:
            self._set_index(state.index)
            self.run("commit", "--allow-empty", "-m", "skillshift")
        if "topic" in state.branches:
            self.run("branch", "topic")
        if state.head == "topic":
            self.run("switch", "topic")
        if state.tags:
            self.run("tag", "v1")
        self._set_index(state.index)
        self._set_worktree(state.files)

    def run(self, *args: str) -> str:
        result = subprocess.run(
            [
                self.binary,
                "-c",
                f"core.hooksPath={self.root.parent / 'empty-hooks'}",
                "-c",
                "core.autocrlf=false",
                "-c",
                "core.safecrlf=false",
                "-c",
                "commit.gpgsign=false",
                "-c",
                "tag.gpgSign=false",
                "-c",
                "protocol.file.allow=never",
                *args,
            ],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=True,
            timeout=30,
        )
        return result.stdout

    def _path(self, name: str) -> Path:
        path = self.root / safe_path(name)
        if not path.resolve().is_relative_to(self.root.resolve()) or path.is_symlink():
            raise ValueError("Git fixture path escaped its temporary repository")
        return path

    def _files(self) -> dict[str, str]:
        files: dict[str, str] = {}
        # Prune .git instead of traversing its object store.
        for directory, subdirs, names in os.walk(self.root, followlinks=False):
            subdirs[:] = [name for name in subdirs if name != ".git"]
            for name in names:
                relative = (Path(directory) / name).relative_to(self.root).as_posix()
                files[relative] = self._path(relative).read_text(encoding="utf-8")
        return files

    def _set_worktree(self, files: dict[str, str]) -> None:
        for name in self._files():
            self._path(name).unlink()
        for name, content in files.items():
            path = self._path(name)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content.encode("utf-8"))

    def _set_index(self, index: dict[str, str]) -> None:
        self.run("read-tree", "--empty")
        self._set_worktree(index)
        for name in index:
            self.run("add", "--", safe_path(name))

    def snapshot(self) -> GitState:
        names = self.run("ls-files", "-z").split("\0")
        return GitState.model_validate(
            {
                "base": self.base,
                "files": self._files(),
                "index": {name: self.run("show", f":{safe_path(name)}") for name in names if name},
                "head": self.run("symbolic-ref", "--short", "HEAD").strip(),
                "branches": sorted(
                    self.run("for-each-ref", "--format=%(refname:short)", "refs/heads").splitlines()
                ),
                "tags": sorted(self.run("tag", "--list").splitlines()),
                "commits": self.run("log", "--reverse", "--format=%s").splitlines(),
            }
        )

    def apply(self, operation: str) -> None:
        commands: dict[str, tuple[str, ...]] = {
            "git_stage": ("add", "--", "note.txt"),
            "git_unstage": ("restore", "--staged", "--", "note.txt"),
            "git_commit": ("commit", "-m", "skillshift"),
            "git_branch": ("branch", "topic"),
            "git_delete_branch": ("branch", "-d", "topic"),
            "git_switch": ("switch", "topic"),
            "git_tag": ("tag", "v1"),
            "git_delete_tag": ("tag", "-d", "v1"),
            "git_restore": ("restore", "--worktree", "--", "note.txt"),
            "git_remove": ("rm", "--", "note.txt"),
        }
        self.run(*commands[operation])
