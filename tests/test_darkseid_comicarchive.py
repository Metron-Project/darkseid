""" Tests for comic archive files """
import zipfile

import pytest

from darkseid.comicarchive import ComicArchive
from darkseid.genericmetadata import GenericMetadata

CONTENT = "content"


@pytest.fixture()
def test_metadata():
    meta_data = GenericMetadata()
    meta_data.series = "Aquaman"
    meta_data.issue = "0"
    meta_data.title = "A Crash of Symbols"
    meta_data.notes = "Test comment"
    meta_data.volume = "1"
    return meta_data


@pytest.fixture()
def fake_comic(tmp_path):
    img_1 = tmp_path / "image-1.jpg"
    img_1.write_text(CONTENT)
    img_2 = tmp_path / "image-2.jpg"
    img_2.write_text(CONTENT)
    img_3 = tmp_path / "image-3.jpg"
    img_3.write_text(CONTENT)

    z_file = tmp_path / "Aquaman v1 #001 (of 08) (1994).cbz"
    zf = zipfile.ZipFile(z_file, "w")
    try:
        zf.write(img_1)
        zf.write(img_2)
        zf.write(img_3)
    finally:
        zf.close()

    comic = ComicArchive(z_file)

    return comic


def test_zip_file_exists(fake_comic):
    """ Test function that determines if a file is a zip file """
    res = fake_comic.is_zip()
    assert res is True


def test_whether_text_file_is_comic_archive(tmp_path):
    """
    Test that a text file produces a false result
    when determining whether it's a comic archive
    """
    test_file = tmp_path / "text-file-test.txt"
    test_file.write_text("Blah Blah Blah")

    comic_archive = ComicArchive(test_file)
    res = comic_archive.seems_to_be_a_comic_archive()
    assert res is not True


def test_archive_number_of_pages(fake_comic):
    """ Test to determine number of pages in a comic archive """
    res = fake_comic.get_number_of_pages()
    assert res == 3


def test_archive_is_writable(fake_comic):
    """ Test to determine if a comic archive is writable """
    res = fake_comic.is_writable()
    assert res is True


def test_archive_writing_with_no_metadata(fake_comic):
    """Make sure writing no metadata to comic returns False"""
    res = fake_comic.write_metadata(None)
    assert res is False


def test_archive_test_metadata(fake_comic, test_metadata):
    """ Test to determine if a comic archive has metadata """
    # verify archive has no metadata
    res = fake_comic.has_metadata()
    assert res is False

    # now let's test that we can write some
    write_result = fake_comic.write_metadata(test_metadata)
    assert write_result is True
    has_md = fake_comic.has_metadata()

    assert has_md is True
    assert res is False

    # Verify what was written
    new_md = fake_comic.read_metadata()
    assert new_md.series == test_metadata.series
    assert new_md.issue == test_metadata.issue
    assert new_md.title == test_metadata.title
    assert new_md.notes == test_metadata.notes
    assert new_md.volume == test_metadata.volume

    # now remove what was just written
    fake_comic.remove_metadata()
    remove_md = fake_comic.has_metadata()
    assert remove_md is False


def test_removing_metadata_on_comic_wo_metadata(fake_comic):
    """
    Make sure trying to remove metadata from
    comic w/o any returns True
    """
    res = fake_comic.write_metadata(None)
    remove_result = fake_comic.remove_metadata()
    assert res is False
    assert remove_result is True


def test_archive_get_page(fake_comic):
    """ Test to set if a page from a comic archive can be retrieved """
    # Get page 2
    img = fake_comic.get_page(1)
    assert img is not None


def test_archive_metadata_from_filename(fake_comic):
    """ Test to get metadata from comic archives filename """
    test_md = fake_comic.metadata_from_filename()
    assert test_md.series == "Aquaman"
    assert test_md.issue == "1"
    assert test_md.volume == "1"
    assert test_md.year == "1994"


def test_archive_apply_file_info_to_metadata(fake_comic):
    """ Test to apply archive info to the generic metadata """
    test_md = GenericMetadata()
    fake_comic.apply_archive_info_to_metadata(test_md)
    # TODO: Need to test calculate page sizes
    assert test_md.page_count == 3
