"""Tests for MetronInfo Tags."""

from datetime import date
from pathlib import Path

import pytest
from lxml import etree

from darkseid.metadata import Arc, Basic, Credit, Metadata, Role, Series, Universe
from darkseid.metroninfo import MetronInfo
from tests.conftest import MI_XSD


@pytest.fixture()
def test_credits() -> list[Credit]:
    return [
        Credit("Peter David", [Role("Writer", 1)], 666),
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
    md.info_source = Basic("Metron", 12344)
    md.alt_sources = [Basic("Comic Vine", 999)]
    md.publisher = Basic("DC Comics", 1)
    md.series = Series(
        "Aquaman",
        id_=10,
        sort_name="Aquaman",
        volume=3,
        format="Annual",
        language="en",
    )
    md.issue = "1"
    md.stories = [Basic("Foo"), Basic("Bar")]
    md.cover_date = date(1993, 4, 15)
    md.characters = [
        Basic("Aquaman", 541),
        Basic("Mera", 1234),
        Basic("Garth"),
    ]
    md.teams = [Basic("Atlanteans", 5432), Basic("Justice League")]
    md.locations = [Basic("Atlantis", 9876), Basic("Metropolis")]
    md.genres = [Basic("Super-Hero", 987)]
    md.story_arcs = [
        Arc("Crisis on Infinite Earths"),
        Arc("Death of Aquagirl"),
    ]
    md.universes = [Universe("ABC", 24, "Earth 25")]
    md.age_rating = "Teen"
    for c in test_credits:
        md.add_credit(c)
    return md


def validate(xml_path: Path, xsd_path: Path) -> bool:
    xmlschema_doc = etree.parse(xsd_path)
    xmlschema = etree.XMLSchema(xmlschema_doc)

    xml_doc = etree.parse(xml_path)
    return xmlschema.validate(xml_doc)


def test_meta_write_to_file(test_meta_data: Metadata, tmp_path: Path) -> None:
    """Test writing metadata to MetronInfo.xml"""
    tmp_file = tmp_path / "test-write.xml"
    MetronInfo().write_xml(tmp_file, test_meta_data)
    assert tmp_file.read_text() is not None
    assert validate(tmp_file, MI_XSD) is True


def test_read_from_file(test_meta_data: Metadata, tmp_path: Path) -> None:
    """Test to read in the data from a file."""
    tmp_file = tmp_path / "test-read.xml"
    # Write metadata to file
    MetronInfo().write_xml(tmp_file, test_meta_data)
    # Read the metadat from the file
    new_md = MetronInfo().read_xml(tmp_file)

    assert new_md is not None
    assert new_md.info_source == test_meta_data.info_source
    assert new_md.alt_sources == test_meta_data.alt_sources
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
