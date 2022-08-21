from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from darkseid.comicarchive import ComicArchive
from darkseid.genericmetadata import Arc, Basic, ComicMetadata, Price, Series

TEST_FILES_PATH = Path("tests/test_files")
IMG_DIR = TEST_FILES_PATH / "Captain_Science_001"
ARCHIVE_PATH = TEST_FILES_PATH / "Captain Science #001.cbz"
CB7_PATH = TEST_FILES_PATH / "Captain Science #001.cb7"
CI_XSD = TEST_FILES_PATH / "ComicInfo.xsd"
RAR_PATH = TEST_FILES_PATH / "Captain Science #001-cix-cbi.cbr"


@pytest.fixture(scope="module")
def fake_metadata():
    meta_data = ComicMetadata()
    meta_data.series = Series(
        name="Aquaman",
        sort_name="Aquaman",
        volume=1,
        format="Annual",
    )
    meta_data.issue = "0"
    meta_data.stories = [Basic("A Crash of Symbols")]
    meta_data.publisher = Basic("DC Comics")
    meta_data.cover_date = date(1994, 12, 1)
    meta_data.story_arcs = [Arc("Final Crisis")]
    meta_data.characters = [
        Basic("Aquaman"),
        Basic("Mera"),
        Basic("Garth"),
    ]
    meta_data.teams = [Basic("Justice League"), Basic("Teen Titans")]
    meta_data.comments = "Just some sample metadata."
    meta_data.black_and_white = True
    meta_data.is_empty = False

    return meta_data


@pytest.fixture(scope="session")
def fake_overlay_metadata():
    overlay_md = ComicMetadata()
    overlay_md.series = Series(name="Aquaman", sort_name="Aquaman", volume=1, format="Annual")
    overlay_md.cover_date = date(1994, 10, 1)
    overlay_md.reprints = [Basic("Aquaman (1964) #64", 12345)]
    overlay_md.prices = [Price(Decimal("3.99")), Price(Decimal("1.5"), "CA")]
    overlay_md.collection_title = "Just another TPB"
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
