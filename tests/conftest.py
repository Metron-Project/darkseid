from pathlib import Path

import pytest

from darkseid.comicarchive import ComicArchive
from darkseid.genericmetadata import GenericMetadata

TEST_FILES_PATH = Path("tests/test_files")
IMG_DIR = TEST_FILES_PATH / "Captain_Science_001"
ARCHIVE_PATH = TEST_FILES_PATH / "Captain Science #001.cbz"
CB7_PATH = TEST_FILES_PATH / "Captain Science #001.cb7"
CI_XSD = TEST_FILES_PATH / "ComicInfo.xsd"
RAR_PATH = TEST_FILES_PATH / "Captain Science #001-cix-cbi.cbr"


@pytest.fixture(scope="session")
def fake_metadata():
    meta_data = GenericMetadata()
    meta_data.series = "Aquaman"
    meta_data.issue = "0"
    meta_data.title = "A Crash of Symbols"
    meta_data.publisher = "DC Comics"
    meta_data.year = 1994
    meta_data.month = 12
    meta_data.day = 1
    meta_data.volume = 1
    meta_data.story_arc = "Final Crisis"
    meta_data.characters = "Aquaman; Mera; Garth"
    meta_data.teams = "Justice League; Teen Titans"
    meta_data.comments = "Just some sample metadata."
    meta_data.black_and_white = True
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
    return ComicArchive(CB7_PATH)


@pytest.fixture(scope="session")
def fake_cbz() -> ComicArchive:
    return ComicArchive(ARCHIVE_PATH)


@pytest.fixture(scope="session")
def fake_rar() -> ComicArchive:
    return ComicArchive(RAR_PATH)
