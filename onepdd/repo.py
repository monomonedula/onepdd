import base64
import re
import shlex
import tempfile
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, TypeAdapter

from onepdd.util import exec_cmd_shell


class GopddPuzzle(BaseModel):
    id: str
    ticket: str
    estimate: int
    role: str
    lines: str
    body: str
    file: str
    author: str
    email: str
    time: str


class GitRepo:
    def __init__(
        self,
        uri: str,
        name: str,
        master: str = "master",
        head_commit_hash: str = "",
        **options,
    ):
        self.id: str = self.repo_id(uri)
        self.name: str = name
        self.uri: str = uri
        self.id_rsa: str = options.get("id_rsa") or ""
        self.master: str = master
        self.head_commit_hash: str = head_commit_hash
        self._dir: Path | None = None
        self._tempdir: tempfile.TemporaryDirectory | None = None

    async def __aenter__(self) -> "GitRepo":
        self._tempdir = tempfile.TemporaryDirectory()
        self._tempdir.__enter__()
        self._dir = Path(self._tempdir.name)
        if self.path.exists():
            await self.pull()
        else:
            await self.clone()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self._tempdir.__exit__(exc_type, exc_val, exc_tb)

    @property
    def dir(self) -> Path:
        assert self._dir is not None, "must be initialized via context manager"
        return self._dir

    @property
    def path(self) -> Path:
        return self.dir / self.id

    @property
    def config(self) -> dict[str, Any]:
        f = self.path / ".0nepdd.yml"
        return yaml.safe_load(f.open()) if f.exists() else {}

    @property
    def gopdd_cmd(self) -> str:
        return f"cd {self.path} && gopdd -v"

    @staticmethod
    def repo_id(uri: str) -> str:
        return re.sub(r"[\s=/+]", "", base64.b64encode(uri.encode()).decode())

    async def parsed(self) -> list[GopddPuzzle]:
        json = await exec_cmd_shell(self.gopdd_cmd)
        return TypeAdapter(list[GopddPuzzle]).validate_json(json)

    async def clone(self):
        await self.prepare_key()
        await self.prepare_git()
        await exec_cmd_shell(
            f"git clone --depth=1 --quiet {shlex.quote(self.uri)} {shlex.quote(str(self.path))}"
        )

    async def pull(self):
        await self.prepare_key()
        await self.prepare_git()
        await exec_cmd_shell(
            " && ".join(
                [
                    f"cd {self.path}",
                    f"master={shlex.quote(self.master)}",
                    "git config --local core.autocrlf false",
                    "git reset origin/${master} --hard --quiet",
                    "git clean --force -d",
                    "git fetch --quiet",
                    "git checkout origin/${master}",
                    "git rebase --abort || true",
                    "git rebase --autostash --strategy-option=theirs origin/${master}",
                ]
            )
        )

    async def prepare_key(self):
        directory = Path.home() / ".ssh"
        if directory.exists():
            return
        directory.mkdir()
        if self.id_rsa:
            (directory / "id_rsa").write_text(self.id_rsa)
        await exec_cmd_shell(
            ";".join(
                [
                    'echo "Host *" > ~/.ssh/config',
                    'echo "  StrictHostKeyChecking no" >> ~/.ssh/config',
                    'echo "  UserKnownHostsFile=~/.ssh/known_hosts" >> ~/.ssh/config',
                    "chmod -R 600 ~/.ssh/*",
                ]
            )
        )

    @staticmethod
    async def prepare_git():
        await exec_cmd_shell(
            ";".join(
                [
                    "GIT=$(git --version)",
                    'if [[ "${GIT}" != "git version 2."* ]]',
                    'then echo "Git is too old: ${GIT}"',
                    "exit -1",
                    "fi",
                ]
            )
        )
        await exec_cmd_shell(
            ";".join(
                [
                    "if ! git config --get --global user.email",
                    'then git config --global user.email "server@0pdd.com"',
                    "fi",
                    "if ! git config --get --global user.name",
                    'then git config --global user.name "0pdd.com"',
                    "fi",
                ]
            )
        )
