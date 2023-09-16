import datetime
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from pydantic import BaseModel


class Storage(ABC):
    @abstractmethod
    async def load(self) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    async def save(self, data: dict[str, Any]):
        pass


class SimpleFsStorage(Storage):
    def __init__(
        self,
        path: Path,
    ):
        self.path: Path = path

    async def save(self, data: dict[str, Any]):
        self.path.write_text(json.dumps(data))

    async def load(self) -> list[dict[str, Any]]:
        return json.loads(self.path.read_text())

    @classmethod
    def from_vcs(cls, base_dir: Path, vcs: str, repo: str) -> "SimpleFsStorage":
        return SimpleFsStorage(base_dir / f"{vcs}-{repo}")


class StoredIssue(BaseModel):
    href: str
    number: str
    closed: str | None = None


class StoredPuzzle(BaseModel):
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
    alive: bool
    issue: StoredIssue | None
