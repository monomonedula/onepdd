import re
from abc import ABC, abstractmethod
from pathlib import Path

from starlette.templating import Jinja2Templates

from onepdd.vcs import Vcs, Issue
from onepdd.storage import StoredPuzzle


class Tickets(ABC):
    @abstractmethod
    async def submit(self, puzzle: StoredPuzzle) -> Issue | None:
        pass

    @abstractmethod
    async def close(self, puzzle: StoredPuzzle) -> bool:
        pass

    @abstractmethod
    async def notify(self, issue: Issue, message: str):
        pass


class TicketsSimple(Tickets):
    def __init__(self, vcs: Vcs, templates: Jinja2Templates):
        self.vcs: Vcs = vcs
        self.templates: Jinja2Templates = templates

    async def notify(self, issue: Issue, message: str):
        await self.vcs.add_comment(issue.number, f"@{issue.author.username} {message}")

    async def submit(self, puzzle: StoredPuzzle) -> Issue | None:
        issue = await self.vcs.create_issue(self.title(puzzle), self.body(puzzle))
        if self.users:
            await self.vcs.add_comment(
                issue.number,
                " ".join([*self.users, "please pay attention to this new issue."]),
            )
        return issue

    def title(self, puzzle: StoredPuzzle) -> str:
        yaml = self.vcs.config
        fmt = []
        if yaml.get("format") and isinstance(yaml["format"], list):
            fmt = [i.lower().strip() for i in yaml["format"]]
        length = 60
        for i in fmt:
            if re.match(r"^title-length=\d+$", i):
                length = int(re.sub("title-length=", "", i))
        length = min(max(length, 30), 255)
        if "short-title" in fmt:
            return truncated(puzzle.body, length)
        subject = Path(puzzle.file).name
        start, stop = puzzle.lines[0].split("-")
        return truncated(
            " ".join(
                [
                    subject,
                    ":",
                    (start if start == stop else f"{start}-{stop}"),
                    f": {puzzle.body}",
                ]
            )
        )

    def body(self, puzzle: StoredPuzzle) -> str:
        file = Path(puzzle.file)
        start, stop = puzzle.lines.split("-")
        sha = self.vcs.repo.head_commit_hash or self.vcs.repo.master
        url = self.vcs.puzzle_link_for_commit(sha, file, start, stop)
        return self.templates.get_template(
            f"{self.vcs.name.lower()}_tickets_body.html"
        ).render(url=url, puzzle=puzzle)

    @property
    def users(self) -> list[str]:
        config = self.vcs.repo.config
        if (
            not config
            or not config.get("alerts")
            or not config["alerts"].get(self.vcs.name.lower())
        ):
            return []
        return [
            "@" + re.sub(r"[^0-9a-zA-Z-]+", "", name.strip().lower())[:64]
            for name in config["alerts"][self.vcs.name.lower()]
        ]

    async def close(self, puzzle: StoredPuzzle) -> bool:
        if (await self.vcs.issue(puzzle.issue.number)).closed:
            return True
        await self.vcs.close_issue(puzzle.issue.number)
        await self.vcs.add_comment(
            puzzle.issue.number,
            f"The puzzle `{puzzle.number}` has disappeared"
            " from the source code, that's why I closed this issue."
            + (f" //cc {' '.join(self.users)}" if self.users else ""),
        )


def truncated(s: str, length: int = 40, tail: str = "...") -> str:
    clean = re.sub(r"\s+", " ", s).strip()
    if len(clean) <= length:
        return clean
    limit = length - len(tail)
    stop = clean.rindex(" ", limit) or 0
    return f"{clean[:stop]}{tail}"
