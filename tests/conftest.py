import tempfile
from pathlib import Path

import pytest


@pytest.fixture()
def temporary_file():
    with tempfile.TemporaryDirectory() as path:
        yield Path(path) / "foo.json"
