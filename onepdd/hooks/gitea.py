import hmac
from typing import Annotated

from aiohttp import ClientSession
from fastapi import Header, HTTPException, Request
from pydantic import BaseModel
from starlette import status
from starlette.templating import Jinja2Templates

from onepdd.config import Config
from onepdd.exc import OnePddError
from onepdd.puzzles import Puzzles

from onepdd.repo import GitRepo
from onepdd.storage import SimpleFsStorage
from onepdd.tickets import TicketsSimple, Issue
from onepdd.vcs import Vcs, IssueAuthor


class GiteaRepoInfo(BaseModel):
    id: str
    name: str
    full_name: str
    html_url: str
    ssh_url: str
    clone_url: str
    default_branch: str


class GiteaHookBody(BaseModel):
    repository: GiteaRepoInfo


class HookGitea:
    def __init__(self, config: Config, templates: Jinja2Templates):
        self.config: Config = config
        self.templates: Jinja2Templates = templates

    async def handle(
        self,
        body: GiteaHookBody,
        request: Request,
        http_x_gitea_signature: Annotated[str | None, Header()] = None,
    ):
        await self.check_signature(request, http_x_gitea_signature)
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
                    self.config.storage, "gitea", body.repository.full_name
                ),
            ).deploy(TicketsSimple(GiteaVcs(cs, repo, self.config), self.templates))

    async def check_signature(
        self, request: Request, http_x_gitea_signature: str | None
    ):
        if not http_x_gitea_signature:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
        if not hmac.compare_digest(
            hmac.new(
                self.config.gitea_secret_key, await request.body(), "sha256"
            ).hexdigest(),
            http_x_gitea_signature,
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)


class GiteaError(OnePddError):
    pass


class GiteaVcs(Vcs):
    def __init__(self, cs: ClientSession, repo: GitRepo, config: Config):
        self._cs: ClientSession = cs
        self.repo = repo
        self.gitea_host: str = config.gitea_host
        self.token: str = config.gitea_token

    async def issue(self, issue_id: str) -> Issue:
        async with self._cs.get(
            f"{self.gitea_host}/api/{self.repo.name}/issues/{issue_id}?token={self.token}"
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
            f"{self.gitea_host}/api/{self.repo.name}/issues?token={self.token}?token={self.token}",
            json={
                "title": title,
                "body": body,
            },
        ) as resp:
            if resp.status != 201:
                raise GiteaError(
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
            f"{self.gitea_host}/api/{self.repo.name}/issues/{issue_id}?token={self.token}",
            json={
                "state": "closed",
            },
        ) as resp:
            if resp.status != 201:
                raise GiteaError(
                    f"Failed to close issue. Issue id: {issue_id}, "
                    f"repo: {self.repo.name}. Code: {resp.status} "
                    f"Response: {await resp.content.read()!r}"
                )

    def puzzle_link_for_commit(self, sha: str, file: str, start: str, stop: str) -> str:
        return f"{self.gitea_host}/{self.repo.name}/blob/{sha}/{file}L{start}-L{stop}"

    async def add_comment(self, issue_id: str, msg: str):
        async with self._cs.post(
            f"{self.gitea_host}/api/{self.repo.name}/issues/{issue_id}/comments?token={self.token}",
            json={
                "body": msg,
            },
        ) as resp:
            if resp.status != 201:
                raise GiteaError(
                    f"Failed to add comment. "
                    f"issue: {issue_id}. repo: {self.repo.name}. "
                    f"Code: {resp.status}. "
                    f"Response: {await resp.content.read()!r}"
                )
