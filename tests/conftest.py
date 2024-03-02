from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from darkseid.comic import Comic
from darkseid.metadata import Arc, Basic, Metadata, Price, Series

TEST_FILES_PATH = Path("tests/test_files")
IMG_DIR = TEST_FILES_PATH / "Captain_Science_001"
ARCHIVE_PATH = TEST_FILES_PATH / "Captain Science #001.cbz"
CI_XSD = TEST_FILES_PATH / "ComicInfo.xsd"
RAR_PATH = TEST_FILES_PATH / "Captain Science #001-cix-cbi.cbr"


@pytest.fixture(scope="module")
def fake_metadata() -> Metadata:
    md = Metadata()
    md.series = Series(
        name="Aquaman",
        sort_name="Aquaman",
        volume=1,
        format="Annual",
    )
    md.issue = "0"
    md.stories = [Basic("A Crash of Symbols")]
    md.publisher = Basic("DC Comics")
    md.cover_date = date(1994, 12, 1)
    md.story_arcs = [Arc("Final Crisis, Inc")]
    md.characters = [
        Basic("Aquaman"),
        Basic("Mera"),
        Basic("Garth"),
    ]
    md.teams = [Basic("Justice League"), Basic("Infinity, Inc")]
    md.comments = "Just some sample metadata."
    md.black_and_white = True
    md.is_empty = False

    return md


@pytest.fixture(scope="session")
def fake_overlay_metadata() -> Metadata:
    overlay_md = Metadata()
    overlay_md.series = Series(name="Aquaman", sort_name="Aquaman", volume=1, format="Annual")
    overlay_md.cover_date = date(1994, 10, 1)
    overlay_md.reprints = [Basic("Aquaman (1964) #64", 12345)]
    overlay_md.prices = [Price(Decimal("3.99")), Price(Decimal("1.5"), "CA")]
    overlay_md.collection_title = "Just another TPB"
    return overlay_md


@pytest.fixture(scope="session")
def fake_cbz() -> Comic:
    return Comic(ARCHIVE_PATH)


@pytest.fixture(scope="session")
def fake_rar() -> Comic:
    return Comic(RAR_PATH)
