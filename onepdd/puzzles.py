from copy import deepcopy
from datetime import datetime, timezone

from onepdd.repo import GopddPuzzle, GitRepo
from onepdd.storage import Storage, StoredIssue, StoredPuzzle
from onepdd.tickets import Tickets


class Puzzles:
    def __init__(self, repo: GitRepo, storage: Storage):
        self.repo: GitRepo = repo
        self.storage: Storage = storage

    async def deploy(self, tickets: Tickets):
        """
        Find out which puzzles deservers to become new tickets and submit
        them to the repository (GitHub, for example). Also, find out which
        puzzles are no longer active and remove them from GitHub
        """
        await self.save(
            self.join(
                before=await self.storage.load(),
                snapshot=await self.repo.parsed(),
            )
        )
        await self.expose(await self.storage.load(), tickets)

    @staticmethod
    def join(
        before: list[StoredPuzzle], snapshot: list[GopddPuzzle]
    ) -> list[StoredPuzzle]:
        """
        Join existing JSON with the snapshot just arrived from PDD
        toolkit output after the analysis of the code base. New <puzzle>
        elements are added as <extra> elements. They later inside the
        method join() will be placed to the right positions and will
        either replace existing ones of will become new puzzles.
        """
        after: list[StoredPuzzle] = deepcopy(before)
        existing: set[str] = set(p.id for p in after)
        for puzzle in snapshot:
            if puzzle.id not in existing:
                after.append(
                    StoredPuzzle(
                        **puzzle.model_dump(),
                        alive=True,
                        issue=None,
                    )
                )
        return after

    async def expose(self, puzzles: list[StoredPuzzle], tickets: Tickets):
        puzzles = deepcopy(puzzles)
        for puzzle in puzzles:
            if ticket_to_be_closed(puzzle) and await tickets.close(puzzle):
                puzzle.issue.closed = datetime.now(tz=timezone.utc).isoformat()
                await self.save(puzzles)
            elif ticket_to_be_opened(puzzle) and (
                issue := await tickets.submit(puzzle)
            ):
                puzzle.issue = StoredIssue(
                    **{
                        "href": issue.href,
                        "number": issue.number,
                        "closed": None,
                    }
                )
                await self.save(puzzles)

    async def save(self, puzzles: list[StoredPuzzle]):
        await self.storage.save([p.model_dump() for p in puzzles])


def ticket_to_be_closed(puzzle: StoredPuzzle) -> bool:
    return not puzzle.alive and puzzle.issue and not puzzle.issue.closed


def ticket_to_be_opened(puzzle: StoredPuzzle) -> bool:
    return puzzle.alive and (not puzzle.issue or puzzle.issue.closed)
