"""Tests for ComicInfo Tags."""

from datetime import date
from pathlib import Path

import pytest
from lxml import etree

from darkseid.comicinfo import ComicInfo
from darkseid.metadata import (
    AgeRatings,
    Arc,
    Basic,
    Credit,
    Links,
    Metadata,
    Notes,
    Publisher,
    Role,
    Series,
)

CI_XSD = Path("tests/test_files/ComicInfo.xsd")


@pytest.mark.parametrize(
    ("tmp_year", "tmp_month", "tmp_day", "expected"),
    [
        # Happy path tests
        (2023, 5, 15, date(2023, 5, 15)),  # Valid full date
        (2023, 5, None, date(2023, 5, 1)),  # Valid year and month, no day
        # Edge cases
        (2023, 2, 28, date(2023, 2, 28)),  # End of February non-leap year
        (2024, 2, 29, date(2024, 2, 29)),  # Leap year
        (2023, 1, 1, date(2023, 1, 1)),  # Start of the year
        (2023, 12, 31, date(2023, 12, 31)),  # End of the year
        # Error cases
        (2023, 2, 30, None),  # Invalid day in February
        (2023, 13, 1, None),  # Invalid month
        (2023, 0, 1, None),  # Invalid month
        (2023, 1, 0, None),  # Invalid day
        (None, 5, 15, None),  # Missing year
        (2023, None, 15, None),  # Missing month
    ],
    ids=[
        "valid_full_date",
        "valid_year_month_no_day",
        "end_of_february_non_leap",
        "leap_year",
        "start_of_year",
        "end_of_year",
        "invalid_day_february",
        "invalid_month_13",
        "invalid_month_0",
        "invalid_day_0",
        "missing_year",
        "missing_month",
    ],
)
def test_set_cover_date(tmp_year, tmp_month, tmp_day, expected):
    # Act
    result = ComicInfo()._set_cover_date(tmp_year, tmp_month, tmp_day)  # NOQA: SLF001

    # Assert
    assert result == expected


@pytest.fixture
def test_credits() -> list[Credit]:
    return [
        Credit("Peter David", [Role("Writer")]),
        Credit("Martin Egeland", [Role("Penciller")]),
        Credit("Martin Egeland", [Role("Cover")]),
        Credit("Kevin Dooley", [Role("Editor")]),
        Credit("Howard Shum", [Role("Inker")]),
        Credit("Howard Shum", [Role("Cover")]),
        Credit("Tom McCraw", [Role("Colorist")]),
        Credit("Dan Nakrosis", [Role("Letterer")]),
    ]


@pytest.fixture
def test_meta_data(test_credits: list[Credit]) -> Metadata:
    md = Metadata()
    md.publisher = Publisher("DC Comics", 1, Basic("DC Black Label", 2))
    md.series = Series(
        "Aquaman",
        sort_name="Aquaman",
        volume=3,
        format="Annual",
        language="en",
    )
    md.issue = "1"
    md.stories = [Basic("Foo"), Basic("Bar")]
    md.cover_date = date(1993, 4, 15)
    md.characters = [
        Basic("Aquaman"),
        Basic("Mera"),
        Basic("Garth"),
    ]
    md.teams = [Basic("Atlanteans"), Basic("Justice League")]
    md.locations = [Basic("Atlantis"), Basic("Metropolis")]
    md.genres = [Basic("Super-Hero")]
    md.story_arcs = [
        Arc("Crisis on Infinite Earths"),
        Arc("Death of Aquagirl"),
    ]
    md.black_and_white = True
    md.age_rating = AgeRatings(comic_rack="MA15+")
    md.manga = "YesAndRightToLeft"
    md.web_link = [
        Links("https://metron.cloud/issue/ultramega-2021-5/", True),
        Links("https://metron.cloud/issue/the-body-trade-2024-1/"),
        Links("https://metron.cloud/issue/the-body-trade-2024-2/"),
    ]
    md.notes = Notes(comic_rack="This is a test")
    for c in test_credits:
        md.add_credit(c)
    return md


def validate(xml_path: Path, xsd_path: Path) -> bool:
    xmlschema_doc = etree.parse(xsd_path)
    xmlschema = etree.XMLSchema(xmlschema_doc)

    xml_doc = etree.parse(xml_path)
    return xmlschema.validate(xml_doc)


def test_metadata_from_xml(test_meta_data: Metadata) -> None:
    """Simple test of creating the ComicInfo."""
    res = ComicInfo().string_from_metadata(test_meta_data)
    # TODO: add more asserts to verify data.
    assert res is not None


def test_meta_with_missing_stories(test_meta_data: Metadata, tmp_path: Path) -> None:
    """Test of writing the metadata to a file."""
    tmp_file = tmp_path / "test-write.xml"
    old_md = test_meta_data
    old_md.stories = None  # type: ignore
    ComicInfo().write_xml(tmp_file, test_meta_data)
    assert tmp_file.read_text() is not None
    assert validate(tmp_file, CI_XSD) is True
    new_md = ComicInfo().read_xml(tmp_file)
    assert old_md.stories == new_md.stories
    assert old_md.characters == new_md.characters


def test_meta_with_no_imprint(test_meta_data: Metadata, tmp_path: Path) -> None:
    """Test of writing the metadata with no imprint to a file."""
    tmp_file = tmp_path / "test-write.xml"
    old_md = test_meta_data
    old_md.publisher.imprint = None
    ComicInfo().write_xml(tmp_file, test_meta_data)
    assert tmp_file.read_text() is not None
    assert validate(tmp_file, CI_XSD) is True
    new_md = ComicInfo().read_xml(tmp_file)
    assert new_md.publisher.imprint is None
    assert old_md.characters == new_md.characters


def test_meta_write_to_file(test_meta_data: Metadata, tmp_path: Path) -> None:
    """Test of writing the metadata to a file."""
    tmp_file = tmp_path / "test-write.xml"
    ComicInfo().write_xml(tmp_file, test_meta_data)
    assert tmp_file.read_text() is not None
    assert validate(tmp_file, CI_XSD) is True


def test_meta_write_to_existing_file(test_meta_data: Metadata, tmp_path: Path) -> None:
    # sourcery skip: extract-duplicate-method
    """Test of writing the metadata to a file and then modifying comicinfo.xml"""
    # Write test metadata to file
    tmp_file = tmp_path / "test-write.xml"
    ci = ComicInfo()
    ci.write_xml(tmp_file, test_meta_data)
    assert tmp_file.read_text() is not None
    assert validate(tmp_file, CI_XSD) is True
    # Read the comicinfo.xml file and verify content
    md = ci.read_xml(tmp_file)
    assert md.genres == test_meta_data.genres
    # Modify the metadata and overwrite the existing comicinfo.xml
    md.genres = []
    ci.write_xml(tmp_file, md)
    assert tmp_file.read_text() is not None
    assert validate(tmp_file, CI_XSD) is True
    # Now reback the modified comicinfo.xml and verify
    new_md = ci.read_xml(tmp_file)
    assert new_md.genres is None


def test_invalid_age_write_to_file(tmp_path: Path) -> None:
    """Test writing of invalid age rating value to a file."""
    aquaman = Series("Aquaman")
    bad_metadata = Metadata(series=aquaman, age_rating=AgeRatings(comic_rack="MA 15+"))
    tmp_file = tmp_path / "test-age-write.xml"
    ci = ComicInfo()
    ci.write_xml(tmp_file, bad_metadata)
    result_md = ci.read_xml(tmp_file)
    assert tmp_file.read_text() is not None
    assert validate(tmp_file, CI_XSD) is True
    assert result_md.age_rating.comic_rack == "Unknown"


def test_invalid_manga_write_to_file(tmp_path: Path) -> None:
    """Test writing of invalid manga value to a file."""
    aquaman = Series("Aquaman")
    bad_metadata = Metadata(series=aquaman, manga="Foo Bar")
    tmp_file = tmp_path / "test-manga-write.xml"
    ci = ComicInfo()
    ci.write_xml(tmp_file, bad_metadata)
    result_md = ci.read_xml(tmp_file)
    assert tmp_file.read_text() is not None
    assert validate(tmp_file, CI_XSD) is True
    assert result_md.manga == "Unknown"


def test_read_from_file(test_meta_data: Metadata, tmp_path: Path) -> None:
    """Test to read in the data from a file."""
    tmp_file = tmp_path / "test-read.xml"
    # Write metadata to file
    ComicInfo().write_xml(tmp_file, test_meta_data)
    # Read the metadat from the file
    new_md = ComicInfo().read_xml(tmp_file)

    assert new_md is not None
    assert new_md.series.name == test_meta_data.series.name
    assert new_md.series.language == new_md.series.language
    assert new_md.issue == test_meta_data.issue
    assert new_md.stories == test_meta_data.stories
    assert new_md.cover_date == test_meta_data.cover_date
    assert new_md.credits[0] == test_meta_data.credits[0]
    assert new_md.characters == test_meta_data.characters
    assert new_md.teams == test_meta_data.teams
    assert new_md.story_arcs == test_meta_data.story_arcs
    assert new_md.locations == test_meta_data.locations
    assert new_md.black_and_white == test_meta_data.black_and_white
    assert new_md.publisher.name == test_meta_data.publisher.name
    assert new_md.publisher.imprint.name == test_meta_data.publisher.imprint.name
    assert new_md.notes.comic_rack == "This is a test"
