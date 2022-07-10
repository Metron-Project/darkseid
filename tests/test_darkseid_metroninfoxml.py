"""Test for MetronInfoXML """

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from darkseid.genericmetadata import (
    GenericMetadata,
    InfoSourceMetadata,
    PriceMetadata,
    SeriesMetadata,
)
from darkseid.metroninfo import MetronInfoXML


@pytest.fixture()
def test_meta_data() -> GenericMetadata:
    series = SeriesMetadata("The Aquaman", "Aquaman", "Limited")
    meta_data = GenericMetadata(series=series)
    meta_data.info_source = InfoSourceMetadata("Metron", 12345)
    meta_data.publisher = "DC Comics"
    meta_data.collection_title = "The War of Atlantis"
    meta_data.issue = "1"
    meta_data.stories = ["Foo", "Bar"]
    meta_data.price = PriceMetadata("dollar", Decimal("3.99"))
    meta_data.cover_date = date(1993, 4, 14)
    meta_data.store_date = date(1993, 2, 12)
    meta_data.volume = 3
    meta_data.comments = "The First Issue!"
    meta_data.characters = ["Aquaman", "Mera", "Garth"]
    meta_data.teams = ["Atlanteans", "Justice League"]
    meta_data.locations = ["Atlantis", "Metropolis"]
    meta_data.genres = ["Super-Hero"]
    meta_data.story_arcs = ["Crisis on Infinite Earths", "Death of Aquagirl"]
    meta_data.black_and_white = True
    meta_data.age_rating = "Everyone"
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


def test_metadata_write_to_file(test_meta_data: GenericMetadata, tmp_path: Path) -> None:
    """Test of writing the metadata to a file"""
    tmp_file = tmp_path / "test-write.xml"
    MetronInfoXML().write_to_external_file(tmp_file, test_meta_data)
    assert tmp_file.read_text() is not None
