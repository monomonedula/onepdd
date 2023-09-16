from typing import Any

from aiohttp import ClientSession
from pydantic import BaseModel
from starlette.templating import Jinja2Templates

from onepdd.config import Config
from onepdd.exc import OnePddError
from onepdd.puzzles import Puzzles

from onepdd.repo import GitRepo
from onepdd.storage import SimpleFsStorage
from onepdd.tickets import TicketsSimple, Issue
from onepdd.vcs import Vcs, IssueAuthor


class GithubRepoInfo(BaseModel):
    id: str
    name: str
    full_name: str
    html_url: str
    ssh_url: str
    clone_url: str
    default_branch: str


class GithubHookBody(BaseModel):
    repository: GithubRepoInfo


class HookGithub:
    def __init__(self, config: Config, templates: Jinja2Templates):
        self.config: Config = config
        self.templates: Jinja2Templates = templates

    async def handle(self, body: GithubHookBody):
        # todo: add hook verification
        async with GitRepo(
            uri=body.repository.ssh_url,
            name=body.repository.full_name,
            master=body.repository.default_branch,
            head_commit_hash="",
            id_rsa=self.config.id_rsa,
        ) as repo, ClientSession() as cs:
            await Puzzles(
                repo,
                SimpleFsStorage.from_vcs(
                    self.config.storage, "github", body.repository.full_name
                ),
            ).deploy(TicketsSimple(GithubVcs(cs, repo, self.config), self.templates))


class GithubError(OnePddError):
    pass


class GithubVcs(Vcs):
    def __init__(self, cs: ClientSession, repo: GitRepo, config: dict[str, Any]):
        self._cs: ClientSession = cs
        self.repo = repo
        self.config = config
        self.auth = config

    async def issue(self, issue_id: str) -> Issue:
        async with self._cs.get(
            f"https://github.com/api/{self.repo.name}/issues/{issue_id}"
        ) as resp:
            body = await resp.json()
            return Issue(
                author=IssueAuthor(
                    id=str(body["user"]["id"]), username=body["user"]["login"]
                ),
                href="",
                closed=body["state"] == "closed",
                number=issue_id,
            )

    async def create_issue(self, title: str, body: str) -> Issue | None:
        async with self._cs.post(
            f"https://github.com/api/{self.repo.name}/issues",
            json={
                "title": title,
                "body": body,
            },
        ) as resp:
            if resp.status != 201:
                raise GithubError(
                    f"Failed to create issue. "
                    f"repo: {self.repo.name}. Code: {resp.status}. "
                    f"Response: {await resp.content.read()!r}"
                )
            body = await resp.json()
            return Issue(
                author=IssueAuthor(
                    id=str(body["user"]["id"]), username=body["user"]["login"]
                ),
                href="",
                closed=body["state"] == "closed",
                number=str(body["id"]),
            )

    async def close_issue(self, issue_id: str):
        async with self._cs.patch(
            f"https://github.com/api/{self.repo.name}/issues/{issue_id}",
            json={
                "state": "closed",
            },
        ) as resp:
            if resp.status != 201:
                raise GithubError(
                    f"Failed to close issue. Issue id: {issue_id}, "
                    f"repo: {self.repo.name}. Code: {resp.status} "
                    f"Response: {await resp.content.read()!r}"
                )

    def puzzle_link_for_commit(self, sha: str, file: str, start: str, stop: str) -> str:
        return f"https://github.com/{self.repo.name}/blob/{sha}/{file}L{start}-L{stop}"

    async def add_comment(self, issue_id: str, msg: str):
        async with self._cs.post(
            f"https://github.com/api/{self.repo.name}/issues/{issue_id}/comments",
            json={
                "body": msg,
            },
        ) as resp:
            if resp.status != 201:
                raise GithubError(
                    f"Failed to add comment. "
                    f"issue: {issue_id}. repo: {self.repo.name}. "
                    f"Code: {resp.status}. "
                    f"Response: {await resp.content.read()!r}"
                )
