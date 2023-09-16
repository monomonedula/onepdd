from unittest.mock import Mock

import freezegun
import pytest

from onepdd.puzzles import Puzzles
from onepdd.repo import GopddPuzzle
from onepdd.storage import StoredPuzzle, StoredIssue, SimpleFsStorage
from onepdd.tickets import Tickets
from onepdd.vcs import Issue, IssueAuthor


def test_puzzles_join_ok():
    assert Puzzles.join(
        [
            StoredPuzzle(
                id="209-c992021",
                ticket="209",
                estimate=30,
                role="DEV",
                lines="3-5",
                body="whatever 1234. Please fix soon 1.",
                file="resources/foobar.py",
                author="monomonedula",
                email="email@xxx.xyz",
                time="2023-03-26T23:27:31+03:00",
                alive=True,
                issue=StoredIssue(
                    href="https://foo.com/1234123/whatever", number="12345"
                ),
            )
        ],
        [
            GopddPuzzle(
                id="209-c992021",
                ticket="209",
                estimate=30,
                role="DEV",
                lines="3-5",
                body="whatever 1234. Please fix soon 1.",
                file="resources/foobar.py",
                author="monomonedula",
                email="email@xxx.xyz",
                time="2023-03-26T23:27:31+03:00",
            ),
            GopddPuzzle(
                id="209-c992022",
                ticket="208",
                estimate=15,
                role="DEV",
                lines="12-15",
                body="whatever 1234. Please fix soon 1234.",
                file="resources/foobar.py",
                author="monomonedula",
                email="email@xxx.xyz",
                time="2023-03-27T23:27:31+03:00",
            ),
        ],
    ) == [
        StoredPuzzle(
            id="209-c992021",
            ticket="209",
            estimate=30,
            role="DEV",
            lines="3-5",
            body="whatever 1234. Please fix soon 1.",
            file="resources/foobar.py",
            author="monomonedula",
            email="email@xxx.xyz",
            time="2023-03-26T23:27:31+03:00",
            alive=True,
            issue=StoredIssue(href="https://foo.com/1234123/whatever", number="12345"),
        ),
        StoredPuzzle(
            id="209-c992022",
            ticket="208",
            estimate=15,
            role="DEV",
            lines="12-15",
            body="whatever 1234. Please fix soon 1234.",
            file="resources/foobar.py",
            author="monomonedula",
            email="email@xxx.xyz",
            time="2023-03-27T23:27:31+03:00",
            alive=True,
            issue=None,
        ),
    ]


class FakeTickets(Tickets):
    def __init__(self, submissions: dict[str, Issue | None], closing: dict[str, bool]):
        self._submissions = submissions
        self._closing = closing

    async def submit(self, puzzle: StoredPuzzle) -> Issue | None:
        return self._submissions[puzzle.id]

    async def close(self, puzzle: StoredPuzzle) -> bool:
        return self._closing[puzzle.id]

    async def notify(self, issue: Issue, message: str):
        raise NotImplementedError


@pytest.mark.asyncio
@freezegun.freeze_time("2023-09-04T15:02:47.859211+00:00")
async def test_expose_ok(temporary_file):
    await Puzzles(Mock(), SimpleFsStorage(temporary_file)).expose(
        [
            StoredPuzzle(
                id="209-c992021",
                ticket="209",
                estimate=30,
                role="DEV",
                lines="3-5",
                body="whatever 1234. Please fix soon 1.",
                file="resources/foobar.py",
                author="monomonedula",
                email="email@xxx.xyz",
                time="2023-03-26T23:27:31+03:00",
                alive=True,
                issue=StoredIssue(
                    href="https://foo.com/1234123/whatever", number="12345"
                ),
            ),
            StoredPuzzle(
                id="210-c992022",
                ticket="210",
                estimate=15,
                role="DEV",
                lines="12-15",
                body="whatever 1234. Please fix soon 1234.",
                file="resources/foobar.py",
                author="monomonedula",
                email="email@xxx.xyz",
                time="2023-03-27T23:27:31+03:00",
                alive=True,
                issue=None,
            ),
            StoredPuzzle(
                id="212-c992022",
                ticket="212",
                estimate=15,
                role="DEV",
                lines="12-15",
                body="whatever 1234. Please fix soon 32444.",
                file="resources/foobar.py",
                author="monomonedula",
                email="email@xxx.xyz",
                time="2023-03-27T23:27:31+03:00",
                alive=True,
                issue=StoredIssue(
                    href="https://foo.com/45555/whatever",
                    number="5555",
                    closed="2023-09-04T15:02:47.859211+00:00",
                ),
            ),
            StoredPuzzle(
                id="213-c992022",
                ticket="212",
                estimate=15,
                role="DEV",
                lines="12-15",
                body="whatever 1234. Please fix soon 32444.",
                file="resources/foobar.py",
                author="monomonedula",
                email="email@xxx.xyz",
                time="2023-03-27T23:27:31+03:00",
                alive=False,
                issue=StoredIssue(
                    href="https://foo.com/32422/whatever",
                    number="32311",
                    closed=None,
                ),
            ),
        ],
        tickets=FakeTickets(
            {
                "210-c992022": Issue(
                    author=IssueAuthor(id="1234", username="whatever"),
                    href="https://foo.com/xxx210",
                    number="1234",
                    closed=False,
                ),
                "212-c992022": Issue(
                    author=IssueAuthor(id="1234", username="whatever"),
                    href="https://foo.com/xxx212",
                    number="1234",
                    closed=False,
                ),
            },
            {"213-c992022": True},
        ),
    )
    assert await SimpleFsStorage(temporary_file).load() == [
        {
            "id": "209-c992021",
            "ticket": "209",
            "estimate": 30,
            "role": "DEV",
            "lines": "3-5",
            "body": "whatever 1234. Please fix soon 1.",
            "file": "resources/foobar.py",
            "author": "monomonedula",
            "email": "email@xxx.xyz",
            "time": "2023-03-26T23:27:31+03:00",
            "alive": True,
            "issue": {
                "href": "https://foo.com/1234123/whatever",
                "number": "12345",
                "closed": None,
            },
        },
        {
            "id": "210-c992022",
            "ticket": "210",
            "estimate": 15,
            "role": "DEV",
            "lines": "12-15",
            "body": "whatever 1234. Please fix soon 1234.",
            "file": "resources/foobar.py",
            "author": "monomonedula",
            "email": "email@xxx.xyz",
            "time": "2023-03-27T23:27:31+03:00",
            "alive": True,
            "issue": {
                "href": "https://foo.com/xxx210",
                "number": "1234",
                "closed": None,
            },
        },
        {
            "id": "212-c992022",
            "ticket": "212",
            "estimate": 15,
            "role": "DEV",
            "lines": "12-15",
            "body": "whatever 1234. Please fix soon 32444.",
            "file": "resources/foobar.py",
            "author": "monomonedula",
            "email": "email@xxx.xyz",
            "time": "2023-03-27T23:27:31+03:00",
            "alive": True,
            "issue": {
                "href": "https://foo.com/xxx212",
                "number": "1234",
                "closed": None,
            },
        },
        {
            "id": "213-c992022",
            "ticket": "212",
            "estimate": 15,
            "role": "DEV",
            "lines": "12-15",
            "body": "whatever 1234. Please fix soon 32444.",
            "file": "resources/foobar.py",
            "author": "monomonedula",
            "email": "email@xxx.xyz",
            "time": "2023-03-27T23:27:31+03:00",
            "alive": False,
            "issue": {
                "href": "https://foo.com/32422/whatever",
                "number": "32311",
                "closed": "2023-09-04T15:02:47.859211+00:00",
            },
        },
    ]
