"""Shared test helpers.

The tool is a single executable file with no extension, so it is loaded by
path rather than imported by name.
"""

import importlib.machinery
import importlib.util
import shutil
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
TOOL = REPO_ROOT / "top-and-tail"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


def _load_tool():
    loader = importlib.machinery.SourceFileLoader("top_and_tail", str(TOOL))
    spec = importlib.util.spec_from_loader(loader.name, loader)
    module = importlib.util.module_from_spec(spec)
    loader.exec_module(module)
    return module


tool = _load_tool()

# Analysis sample rate for the unit tests: one sample per millisecond, so that
# durations in the tests read directly as sample counts.
UNIT_RATE = 1000

LOUD = 20000
QUIET = 0


def samples(*runs):
    """Build a sample buffer from (value, count) runs."""
    buffer = []
    for value, count in runs:
        buffer.extend([value] * count)
    return buffer


@pytest.fixture
def hablar(tmp_path):
    return _copy_fixture("hablar-oWSxI36XAKnfMWmzmQok-eleven_v3.mp3", tmp_path)


@pytest.fixture
def preterito(tmp_path):
    return _copy_fixture("pretérito-oWSxI36XAKnfMWmzmQok-eleven_v3.mp3", tmp_path)


@pytest.fixture
def yo(tmp_path):
    return _copy_fixture("yo-oWSxI36XAKnfMWmzmQok-eleven_v3.mp3", tmp_path)


def _copy_fixture(name, tmp_path):
    destination = tmp_path / name
    shutil.copy(FIXTURES / name, destination)
    return destination
