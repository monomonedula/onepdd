from pathlib import Path
from unittest.mock import Mock, seal

from starlette.templating import Jinja2Templates

from onepdd.storage import StoredPuzzle
from onepdd.tickets import TicketsSimple


async def test_tickets_body():
    puzzle_link = "https://foo.bar.com/blob/1234"
    vcs = Mock(puzzle_link_for_commit=Mock(return_value=puzzle_link))
    vcs.name = "gitea"
    vcs.repo = Mock()
    vcs.repo.head_commit_hash = ""
    vcs.repo.master = "master"
    seal(vcs)

    templates = Jinja2Templates((Path(__file__).parent.parent / "templates").resolve())
    assert TicketsSimple(vcs, templates).body(
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
            issue=None,
        )
    ) == (
        "The puzzle `209-c992021` |\n"
        "from #209 has to be resolved: |\n"
        "\\\n"
        "https://foo.bar.com/blob/1234\n"
        "\\\n"
        "The puzzle was created by monomonedula on |\n"
        "26-Mar-23. |\n"
        "\\\n"
        "\n"
        "Estimate: 30 minutes |\n"
        "\n"
        "\n"
        "role: DEV. |\n"
        "\n"
        "\\\n"
        "If you have any technical questions, don't ask me, |\n"
        'submit new tickets instead. The task will be \\"done\\" when |\n'
        "the problem is fixed and the text of the puzzle is |\n"
        "_removed_ from the source code. Here is more about |\n"
        "[PDD](http://www.yegor256.com/2009/03/04/pdd.html) and |\n"
        "[about me](http://www.yegor256.com/2017/04/05/pdd-in-action.html). |"
    )
