from pathlib import Path

import pytest

from darkseid.comicarchive import ComicArchive
from darkseid.genericmetadata import GenericMetadata

TEST_FILES_PATH = Path("tests/test_files")
IMG_DIR = TEST_FILES_PATH / "Captain_Science_001"
ARCHIVE_PATH = TEST_FILES_PATH / "Captain Science #001.cbz"
CB7_PATH = TEST_FILES_PATH / "Captain Science #001.cb7"


@pytest.fixture(scope="session")
def fake_metadata():
    meta_data = GenericMetadata()
    meta_data.series = "Aquaman"
    meta_data.issue = "0"
    meta_data.title = "A Crash of Symbols"
    meta_data.is_empty = False

    return meta_data


@pytest.fixture(scope="session")
def fake_overlay_metadata():
    overlay_md = GenericMetadata()
    overlay_md.year = "1994"
    overlay_md.month = "10"
    overlay_md.day = "1"

    return overlay_md


@pytest.fixture(scope="session")
def fake_cb7() -> ComicArchive:
    return ComicArchive(ARCHIVE_PATH)


@pytest.fixture(scope="session")
def fake_cbz() -> ComicArchive:
    return ComicArchive(ARCHIVE_PATH)
