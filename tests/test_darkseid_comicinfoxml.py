""" Tests for ComicInfo Tags """
import pytest

from darkseid.comicinfoxml import ComicInfoXml
from darkseid.genericmetadata import GenericMetadata


@pytest.fixture()
def test_meta_data():
    meta_data = GenericMetadata()
    meta_data.series = "Aquaman"
    meta_data.issue = "1"
    meta_data.year = 1993
    meta_data.day = 15
    meta_data.add_credit("Peter David", "Writer")
    meta_data.add_credit("Martin Egeland", "Penciller")
    meta_data.add_credit("Martin Egeland", "Cover")
    meta_data.add_credit("Kevin Dooley", "Editor")
    meta_data.add_credit("Howard Shum", "Inker")
    meta_data.add_credit("Tom McCraw", "Colorist")
    meta_data.add_credit("Dan Nakrosis", "Letterer")
    return meta_data


def test_metadata_from_xml(test_meta_data):
    """Simple test of creating the ComicInfo"""
    res = ComicInfoXml().string_from_metadata(test_meta_data)
    # TODO: add more asserts to verify data.
    assert res is not None


def test_meta_write_to_file(test_meta_data, tmp_path):
    """Test of writing the metadata to a file"""
    tmp_file = tmp_path / "test-write.xml"
    ComicInfoXml().write_to_external_file(tmp_file, test_meta_data)
    # Read the contents of the file just written.
    # TODO: Verify the data.
    assert tmp_file.read_text() is not None


def test_read_from_file(test_meta_data, tmp_path):
    """Test to read in the data from a file"""
    tmp_file = tmp_path / "test-read.xml"
    # Write metadata to file
    ComicInfoXml().write_to_external_file(tmp_file, test_meta_data)
    # Read the metadat from the file
    new_md = ComicInfoXml().read_from_external_file(tmp_file)

    assert new_md is not None
    assert new_md.series == test_meta_data.series
    assert new_md.issue == test_meta_data.issue
    assert new_md.year == test_meta_data.year
    assert new_md.month == test_meta_data.month
    assert new_md.day == test_meta_data.day
