""" Tests for ComicInfo Tags """
from datetime import date
from pathlib import Path

import pytest
from lxml import etree

from darkseid.comicinfoxml import ComicInfoXml
from darkseid.genericmetadata import GenericMetadata, SeriesMetadata

from .conftest import CI_XSD


@pytest.fixture()
def test_meta_data():
    meta_data = GenericMetadata()
    meta_data.series = SeriesMetadata("Aquaman", "Aquaman", 3, "Annual")
    meta_data.issue = "1"
    meta_data.stories = ["Foo", "Bar"]
    meta_data.cover_date = date(1993, 4, 15)
    meta_data.characters = ["Aquaman", "Mera", "Garth"]
    meta_data.teams = ["Atlanteans", "Justice League"]
    meta_data.locations = ["Atlantis", "Metropolis"]
    meta_data.genres = ["Super-Hero"]
    meta_data.story_arcs = ["Crisis on Infinite Earths", "Death of Aquagirl"]
    meta_data.black_and_white = True
    meta_data.age_rating = "MA15+"
    meta_data.manga = "YesAndRightToLeft"
    meta_data.add_credit("Peter David", "Writer")
    meta_data.add_credit("Martin Egeland", "Penciller")
    meta_data.add_credit("Martin Egeland", "Cover")
    meta_data.add_credit("Kevin Dooley", "Editor")
    meta_data.add_credit("Howard Shum", "Inker")
    meta_data.add_credit("Howard Shum", "Cover")
    meta_data.add_credit("Tom McCraw", "Colorist")
    meta_data.add_credit("Dan Nakrosis", "Letterer")
    return meta_data


def validate(xml_path: str, xsd_path: str) -> bool:

    xmlschema_doc = etree.parse(xsd_path)
    xmlschema = etree.XMLSchema(xmlschema_doc)

    xml_doc = etree.parse(xml_path)
    return xmlschema.validate(xml_doc)


def test_metadata_from_xml(test_meta_data: GenericMetadata) -> None:
    """Simple test of creating the ComicInfo"""
    res = ComicInfoXml().string_from_metadata(test_meta_data)
    # TODO: add more asserts to verify data.
    assert res is not None


def test_meta_write_to_file(test_meta_data: GenericMetadata, tmp_path: Path) -> None:
    """Test of writing the metadata to a file"""
    tmp_file = tmp_path / "test-write.xml"
    ComicInfoXml().write_to_external_file(tmp_file, test_meta_data)
    assert tmp_file.read_text() is not None
    assert validate(tmp_file, CI_XSD) is True


def test_invalid_age_write_to_file(tmp_path: Path) -> None:
    """Test writing of invalid age rating value to a file."""
    aquaman = SeriesMetadata("Aquaman")
    bad_metadata = GenericMetadata(series=aquaman, age_rating="MA 15+")
    tmp_file = tmp_path / "test-age-write.xml"
    ci = ComicInfoXml()
    ci.write_to_external_file(tmp_file, bad_metadata)
    result_md = ci.read_from_external_file(tmp_file)
    assert tmp_file.read_text() is not None
    assert validate(tmp_file, CI_XSD) is True
    assert result_md.age_rating == "Unknown"


def test_invalid_manga_write_to_file(tmp_path: Path) -> None:
    """Test writing of invalid manga value to a file."""
    aquaman = SeriesMetadata("Aquaman")
    bad_metadata = GenericMetadata(series=aquaman, manga="Foo Bar")
    tmp_file = tmp_path / "test-manga-write.xml"
    ci = ComicInfoXml()
    ci.write_to_external_file(tmp_file, bad_metadata)
    result_md = ci.read_from_external_file(tmp_file)
    assert tmp_file.read_text() is not None
    assert validate(tmp_file, CI_XSD) is True
    assert result_md.manga == "Unknown"


def test_read_from_file(test_meta_data: GenericMetadata, tmp_path: Path) -> None:
    """Test to read in the data from a file"""
    tmp_file = tmp_path / "test-read.xml"
    # Write metadata to file
    ComicInfoXml().write_to_external_file(tmp_file, test_meta_data)
    # Read the metadat from the file
    new_md = ComicInfoXml().read_from_external_file(tmp_file)

    assert new_md is not None
    assert new_md.series.name == test_meta_data.series.name
    assert new_md.issue == test_meta_data.issue
    assert new_md.stories == test_meta_data.stories
    assert new_md.cover_date == test_meta_data.cover_date
    assert new_md.credits[0] == test_meta_data.credits[0]
    assert new_md.characters == test_meta_data.characters
    assert new_md.teams == test_meta_data.teams
    assert new_md.story_arcs == test_meta_data.story_arcs
    assert new_md.locations == test_meta_data.locations
    assert new_md.black_and_white == test_meta_data.black_and_white
