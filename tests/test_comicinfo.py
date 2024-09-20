"""Tests for ComicInfo Tags."""

from datetime import date
from pathlib import Path

import pytest
from lxml import etree

from darkseid.comicinfo import ComicInfo
from darkseid.metadata import URLS, Arc, Basic, Credit, Metadata, Publisher, Role, Series

CI_XSD = Path("tests/test_files/ComicInfo.xsd")


@pytest.fixture()
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


@pytest.fixture()
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
    md.age_rating = "MA15+"
    md.manga = "YesAndRightToLeft"
    md.web_link = URLS(
        "https://metron.cloud/issue/ultramega-2021-5/",
        [
            "https://metron.cloud/issue/the-body-trade-2024-1/",
            "https://metron.cloud/issue/the-body-trade-2024-2/",
        ],
    )
    for c in test_credits:
        md.add_credit(c)
    return md


def validate(xml_path: str, xsd_path: str) -> bool:
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
    old_md.stories = None
    ComicInfo().write_to_external_file(tmp_file, test_meta_data)
    assert tmp_file.read_text() is not None
    assert validate(tmp_file, CI_XSD) is True
    new_md = ComicInfo().read_from_external_file(tmp_file)
    assert old_md.stories == new_md.stories
    assert old_md.characters == new_md.characters


def test_meta_with_no_imprint(test_meta_data: Metadata, tmp_path: Path) -> None:
    """Test of writing the metadata with no imprint to a file."""
    tmp_file = tmp_path / "test-write.xml"
    old_md = test_meta_data
    old_md.publisher.imprint = None
    ComicInfo().write_to_external_file(tmp_file, test_meta_data)
    assert tmp_file.read_text() is not None
    assert validate(tmp_file, CI_XSD) is True
    new_md = ComicInfo().read_from_external_file(tmp_file)
    assert new_md.publisher.imprint is None
    assert old_md.characters == new_md.characters


def test_meta_write_to_file(test_meta_data: Metadata, tmp_path: Path) -> None:
    """Test of writing the metadata to a file."""
    tmp_file = tmp_path / "test-write.xml"
    ComicInfo().write_to_external_file(tmp_file, test_meta_data)
    assert tmp_file.read_text() is not None
    assert validate(tmp_file, CI_XSD) is True


def test_meta_write_to_existing_file(test_meta_data: Metadata, tmp_path: Path) -> None:
    # sourcery skip: extract-duplicate-method
    """Test of writing the metadata to a file and then modifying comicinfo.xml"""
    # Write test metadata to file
    tmp_file = tmp_path / "test-write.xml"
    ci = ComicInfo()
    ci.write_to_external_file(tmp_file, test_meta_data)
    assert tmp_file.read_text() is not None
    assert validate(tmp_file, CI_XSD) is True
    # Read the comicinfo.xml file and verify content
    md = ci.read_from_external_file(tmp_file)
    assert md.genres == test_meta_data.genres
    # Modify the metadata and overwrite the existing comicinfo.xml
    md.genres = []
    ci.write_to_external_file(tmp_file, md)
    assert tmp_file.read_text() is not None
    assert validate(tmp_file, CI_XSD) is True
    # Now reback the modified comicinfo.xml and verify
    new_md = ci.read_from_external_file(tmp_file)
    assert new_md.genres is None


def test_invalid_age_write_to_file(tmp_path: Path) -> None:
    """Test writing of invalid age rating value to a file."""
    aquaman = Series("Aquaman")
    bad_metadata = Metadata(series=aquaman, age_rating="MA 15+")
    tmp_file = tmp_path / "test-age-write.xml"
    ci = ComicInfo()
    ci.write_to_external_file(tmp_file, bad_metadata)
    result_md = ci.read_from_external_file(tmp_file)
    assert tmp_file.read_text() is not None
    assert validate(tmp_file, CI_XSD) is True
    assert result_md.age_rating == "Unknown"


def test_invalid_manga_write_to_file(tmp_path: Path) -> None:
    """Test writing of invalid manga value to a file."""
    aquaman = Series("Aquaman")
    bad_metadata = Metadata(series=aquaman, manga="Foo Bar")
    tmp_file = tmp_path / "test-manga-write.xml"
    ci = ComicInfo()
    ci.write_to_external_file(tmp_file, bad_metadata)
    result_md = ci.read_from_external_file(tmp_file)
    assert tmp_file.read_text() is not None
    assert validate(tmp_file, CI_XSD) is True
    assert result_md.manga == "Unknown"


def test_read_from_file(test_meta_data: Metadata, tmp_path: Path) -> None:
    """Test to read in the data from a file."""
    tmp_file = tmp_path / "test-read.xml"
    # Write metadata to file
    ComicInfo().write_to_external_file(tmp_file, test_meta_data)
    # Read the metadat from the file
    new_md = ComicInfo().read_from_external_file(tmp_file)

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
