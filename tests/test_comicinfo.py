"""Tests for ComicInfo Tags."""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree

from darkseid.metadata.comicinfo import ComicInfo
from darkseid.metadata.data_classes import (
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
        Links("https://metron.cloud/issue/ultramega-2021-5/", primary=True),
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
    """Test of writing the metadata to a file and then modifying comicinfo.xml."""
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


def test_community_rating_write_and_read(tmp_path: Path) -> None:
    """Test that community_rating is written to and read back from ComicInfo XML."""
    tmp_file = tmp_path / "test-community-rating.xml"
    md = Metadata(series=Series("Aquaman"), community_rating=Decimal("4.50"))

    ci = ComicInfo()
    ci.write_xml(tmp_file, md)
    assert validate(tmp_file, CI_XSD) is True

    new_md = ci.read_xml(tmp_file)
    assert new_md.community_rating == Decimal("4.50")


def test_community_rating_none_not_written(tmp_path: Path) -> None:
    """Test that a None community_rating produces no CommunityRating element."""
    tmp_file = tmp_path / "test-no-community-rating.xml"
    md = Metadata(series=Series("Aquaman"))

    ComicInfo().write_xml(tmp_file, md)
    assert validate(tmp_file, CI_XSD) is True
    assert "CommunityRating" not in tmp_file.read_text()


def test_community_rating_boundary_values_roundtrip(tmp_path: Path) -> None:
    """Test that boundary values 0 and 5 survive a write/read roundtrip."""
    ci = ComicInfo()

    for rating in (Decimal("0.00"), Decimal("5.00")):
        tmp_file = tmp_path / f"test-rating-{rating}.xml"
        md = Metadata(series=Series("Aquaman"), community_rating=rating)
        ci.write_xml(tmp_file, md)
        assert validate(tmp_file, CI_XSD) is True
        new_md = ci.read_xml(tmp_file)
        assert new_md.community_rating == rating


def test_community_rating_in_xml_string() -> None:
    """Test that community_rating appears correctly in the XML string output."""
    md = Metadata(series=Series("Aquaman"), community_rating=Decimal("3.75"))
    xml_str = ComicInfo().string_from_metadata(md)
    assert "<CommunityRating>3.75</CommunityRating>" in xml_str


def test_community_rating_parsed_from_xml_string() -> None:
    """Test that community_rating is parsed correctly from an XML string."""
    xml = (
        '<?xml version="1.0" encoding="utf-8"?>'
        "<ComicInfo>"
        "<Series>Aquaman</Series>"
        "<CommunityRating>2.50</CommunityRating>"
        "</ComicInfo>"
    )
    md = ComicInfo().metadata_from_string(xml)
    assert md.community_rating == Decimal("2.50")


def test_invalid_community_rating_in_xml_string() -> None:
    """Test that a non-numeric CommunityRating in XML is silently ignored."""
    xml = (
        '<?xml version="1.0" encoding="utf-8"?>'
        "<ComicInfo>"
        "<Series>Aquaman</Series>"
        "<CommunityRating>not-a-number</CommunityRating>"
        "</ComicInfo>"
    )
    md = ComicInfo().metadata_from_string(xml)
    assert md.community_rating is None


def test_main_character_or_team_write_and_read(tmp_path: Path) -> None:
    """Test that main_character_or_team is written to and read back from ComicInfo XML."""
    tmp_file = tmp_path / "test-main-character.xml"
    md = Metadata(series=Series("Aquaman"), main_character_or_team="Aquaman")

    ci = ComicInfo()
    ci.write_xml(tmp_file, md)
    assert validate(tmp_file, CI_XSD) is True

    new_md = ci.read_xml(tmp_file)
    assert new_md.main_character_or_team == "Aquaman"


def test_main_character_or_team_none_not_written(tmp_path: Path) -> None:
    """Test that a None main_character_or_team produces no MainCharacterOrTeam element."""
    tmp_file = tmp_path / "test-no-main-character.xml"
    md = Metadata(series=Series("Aquaman"))

    ComicInfo().write_xml(tmp_file, md)
    assert validate(tmp_file, CI_XSD) is True
    assert "MainCharacterOrTeam" not in tmp_file.read_text()


def test_main_character_or_team_in_xml_string() -> None:
    """Test that main_character_or_team appears correctly in the XML string output."""
    md = Metadata(series=Series("Aquaman"), main_character_or_team="Aquaman")
    xml_str = ComicInfo().string_from_metadata(md)
    assert "<MainCharacterOrTeam>Aquaman</MainCharacterOrTeam>" in xml_str


def test_main_character_or_team_parsed_from_xml_string() -> None:
    """Test that MainCharacterOrTeam is parsed correctly from an XML string."""
    xml = (
        '<?xml version="1.0" encoding="utf-8"?>'
        "<ComicInfo>"
        "<Series>Aquaman</Series>"
        "<MainCharacterOrTeam>Aquaman</MainCharacterOrTeam>"
        "</ComicInfo>"
    )
    md = ComicInfo().metadata_from_string(xml)
    assert md.main_character_or_team == "Aquaman"


def test_review_write_and_read(tmp_path: Path) -> None:
    """Test that review is written to and read back from ComicInfo XML."""
    tmp_file = tmp_path / "test-review.xml"
    md = Metadata(series=Series("Aquaman"), review="A fantastic underwater adventure.")

    ci = ComicInfo()
    ci.write_xml(tmp_file, md)
    assert validate(tmp_file, CI_XSD) is True

    new_md = ci.read_xml(tmp_file)
    assert new_md.review == "A fantastic underwater adventure."


def test_review_none_not_written(tmp_path: Path) -> None:
    """Test that a None review produces no Review element."""
    tmp_file = tmp_path / "test-no-review.xml"
    md = Metadata(series=Series("Aquaman"))

    ComicInfo().write_xml(tmp_file, md)
    assert validate(tmp_file, CI_XSD) is True
    assert "Review" not in tmp_file.read_text()


def test_review_in_xml_string() -> None:
    """Test that review appears correctly in the XML string output."""
    md = Metadata(series=Series("Aquaman"), review="A fantastic underwater adventure.")
    xml_str = ComicInfo().string_from_metadata(md)
    assert "<Review>A fantastic underwater adventure.</Review>" in xml_str


def test_review_parsed_from_xml_string() -> None:
    """Test that Review is parsed correctly from an XML string."""
    xml = (
        '<?xml version="1.0" encoding="utf-8"?>'
        "<ComicInfo>"
        "<Series>Aquaman</Series>"
        "<Review>A fantastic underwater adventure.</Review>"
        "</ComicInfo>"
    )
    md = ComicInfo().metadata_from_string(xml)
    assert md.review == "A fantastic underwater adventure."
