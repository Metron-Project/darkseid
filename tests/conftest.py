from datetime import date
from pathlib import Path

import pytest

from darkseid.comicarchive import ComicArchive
from darkseid.genericmetadata import GeneralResource, GenericMetadata, SeriesMetadata

TEST_FILES_PATH = Path("tests/test_files")
IMG_DIR = TEST_FILES_PATH / "Captain_Science_001"
ARCHIVE_PATH = TEST_FILES_PATH / "Captain Science #001.cbz"
CB7_PATH = TEST_FILES_PATH / "Captain Science #001.cb7"
CI_XSD = TEST_FILES_PATH / "ComicInfo.xsd"
RAR_PATH = TEST_FILES_PATH / "Captain Science #001-cix-cbi.cbr"


@pytest.fixture(scope="session")
def fake_metadata():
    meta_data = GenericMetadata()
    meta_data.series = SeriesMetadata("Aquaman", "Aquaman", 1, "Annual")
    meta_data.issue = "0"
    meta_data.stories = ["A Crash of Symbols"]
    meta_data.publisher = "DC Comics"
    meta_data.cover_date = date(1994, 12, 1)
    meta_data.story_arcs = [GeneralResource("Final Crisis")]
    meta_data.characters = [
        GeneralResource("Aquaman"),
        GeneralResource("Mera"),
        GeneralResource("Garth"),
    ]
    meta_data.teams = [GeneralResource("Justice League"), GeneralResource("Teen Titans")]
    meta_data.comments = "Just some sample metadata."
    meta_data.black_and_white = True
    meta_data.is_empty = False

    return meta_data


@pytest.fixture(scope="session")
def fake_overlay_metadata():
    overlay_md = GenericMetadata()
    overlay_md.series = SeriesMetadata("Aquaman", "Aquaman", 1, "Annual")
    overlay_md.cover_date = date(1994, 10, 1)
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
