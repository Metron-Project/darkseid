"""Test for MetronInfoXML """

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from lxml import etree

from darkseid.metadata import GTIN, Arc, Basic, Credit, Metadata, Price, Role, Series
from darkseid.metroninfo import MetronInfo

from .conftest import MI_XSD


@pytest.fixture()
def test_meta_data() -> Metadata:
    series = Series("The Aquaman", 12345, "Aquaman", 3, "Limited", "en")
    md = Metadata(series=series)
    md.info_source = Basic("Metron", 12345)
    md.publisher = Basic("DC Comics", 1)
    md.collection_title = "The War of Atlantis"
    md.issue = "1"
    md.stories = [Basic("Foo", 12), Basic("Bar")]
    md.prices = [
        Price(Decimal("3.99"), country="US"),
        Price(Decimal("1.5"), country="GB"),
    ]
    md.page_count = 32
    md.cover_date = date(1993, 4, 1)
    md.store_date = date(1993, 2, 12)
    md.gtin = GTIN(76194137588500111)
    md.comments = "The First Issue!"
    md.notes = "Notes test text."
    md.characters = [Basic("Aquaman", 1), Basic("Mera"), Basic("Garth")]
    md.teams = [Basic("Atlanteans", 5), Basic("Justice League")]
    md.locations = [Basic("Atlantis", 9), Basic("Metropolis")]
    md.genres = [Basic("Super-Hero", 1)]
    md.story_arcs = [
        Arc("Crisis on Infinite Earths", 153, 4),
        Arc("Death of Aquagirl"),
    ]
    md.black_and_white = True
    md.age_rating = "Everyone"
    md.add_credit(Credit("Peter David", [Role("Writer", 1)], 908))
    md.add_credit(Credit("Martin Egeland", [Role("Penciller", 3), Role("Cover", 2)]))
    md.add_credit(Credit("Kevin Dooley", [Role("Editor", 4)]))
    md.add_credit(Credit("Howard Shum", [Role("Inker", 5), Role("Cover", 2)]))
    md.web_link = "https://metron.cloud/issue/son-of-vulcan-2005-6/"
    md.reprints = [
        Basic("Justice League #001 (1963)", 999),
        Basic("Justice League #002 (1963)", 1000),
    ]
    return md


def validate(xml_path: str, xsd_path: str) -> bool:

    xmlschema_doc = etree.parse(xsd_path)
    xmlschema = etree.XMLSchema(xmlschema_doc)

    xml_doc = etree.parse(xml_path)
    return xmlschema.validate(xml_doc)


def test_metroninfo_read_from_file(test_meta_data: Metadata, tmp_path: Path) -> None:
    """Test to read in the data from a file"""
    tmp_file = tmp_path / "test-read.xml"
    # Write metadata to file
    MetronInfo().write_to_external_file(tmp_file, test_meta_data)
    # Read the metadat from the file
    new_md = MetronInfo().read_from_external_file(tmp_file)
    assert new_md is not None
    assert new_md.info_source == test_meta_data.info_source
    assert new_md.publisher == test_meta_data.publisher
    assert new_md.series == test_meta_data.series
    assert new_md.issue == test_meta_data.issue
    assert new_md.stories == test_meta_data.stories
    assert new_md.comments == test_meta_data.comments
    assert new_md.notes == test_meta_data.notes
    assert new_md.cover_date == test_meta_data.cover_date
    assert new_md.store_date == test_meta_data.store_date
    assert new_md.characters == test_meta_data.characters
    assert new_md.genres == test_meta_data.genres
    assert new_md.locations == test_meta_data.locations
    assert new_md.story_arcs == test_meta_data.story_arcs
    assert new_md.teams == test_meta_data.teams
    assert new_md.prices == test_meta_data.prices
    assert new_md.gtin == test_meta_data.gtin
    assert new_md.black_and_white == test_meta_data.black_and_white
    assert new_md.series == test_meta_data.series
    assert new_md.credits == test_meta_data.credits
    assert new_md.web_link == test_meta_data.web_link
    assert new_md.page_count == test_meta_data.page_count
    assert new_md.collection_title == test_meta_data.collection_title
    assert new_md.reprints == test_meta_data.reprints


def test_metroninfo_write_to_file(test_meta_data: Metadata, tmp_path: Path) -> None:
    """Test of writing the metadata to a file"""
    tmp_file = tmp_path / "test-write.xml"
    MetronInfo().write_to_external_file(tmp_file, test_meta_data)
    assert tmp_file.read_text() is not None
    assert validate(tmp_file, MI_XSD) is True
