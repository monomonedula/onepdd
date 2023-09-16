import dataclasses
from abc import ABC, abstractmethod
from typing import Any

from onepdd.repo import GitRepo


@dataclasses.dataclass
class IssueAuthor:
    id: str
    username: str


@dataclasses.dataclass
class Issue:
    author: IssueAuthor
    href: str
    number: str
    closed: bool


class Vcs(ABC):
    config: dict[str, Any]
    repo: GitRepo
    name: str

    @abstractmethod
    async def issue(self, issue_id: str) -> Issue:
        pass

    @abstractmethod
    def puzzle_link_for_commit(self, sha: str, file: str, start: str, stop: str) -> str:
        pass

    @abstractmethod
    async def add_comment(self, issue_id: str, msg: str):
        pass

    @abstractmethod
    async def create_issue(self, title: str, body: str) -> Issue | None:
        pass

    @abstractmethod
    async def close_issue(self, issue_id: str):
        pass
