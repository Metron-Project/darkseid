""" Tests for comic archive files """
import os
import zipfile
from pathlib import Path
from typing import List

import py7zr
import pytest

from darkseid.comicarchive import ComicArchive
from darkseid.genericmetadata import GenericMetadata

CONTENT = "content"


@pytest.fixture()
def test_metadata() -> GenericMetadata:
    meta_data = GenericMetadata()
    meta_data.series = "Aquaman"
    meta_data.issue = "0"
    meta_data.title = "A Crash of Symbols"
    meta_data.notes = "Test comment"
    meta_data.volume = "1"
    return meta_data


@pytest.fixture()
def fake_cbz(tmp_path: Path) -> ComicArchive:
    image_list: List[Path] = []
    fake_images: List[str] = [
        "MarvelTeam-Up058-00fc.jpg",
        "MarvelTeam-Up058-01.jpg",
        "MarvelTeam-Up058-02.jpg",
        "MarvelTeam-Up058-LP.jpg",
    ]
    for fake in fake_images:
        img: Path = tmp_path / fake
        img.write_text(CONTENT)
        image_list.append(img)

    z_file: Path = tmp_path / "Aquaman v1 #001 (of 08) (1994).cbz"
    with zipfile.ZipFile(z_file, "w") as zf:
        for i in image_list:
            zf.write(i)

    return ComicArchive(z_file)


@pytest.fixture()
def fake_cb7(tmp_path: Path) -> ComicArchive:
    image_list: List[Path] = []
    fake_images: List[str] = [
        "MarvelTeam-Up058-00fc.jpg",
        "MarvelTeam-Up058-01.jpg",
        "MarvelTeam-Up058-02.jpg",
        "MarvelTeam-Up058-03.jpg",
        "MarvelTeam-Up058-LP.jpg",
    ]
    for fake in fake_images:
        img: Path = tmp_path / fake
        img.write_text(CONTENT)
        image_list.append(img)

    z_file: Path = tmp_path / "Foo Bar v1 #001 (2000).cb7"
    with py7zr.SevenZipFile(z_file, "w") as archive:
        for i in image_list:
            archive.write(i)

    return ComicArchive(z_file)


def test_cb7_file_exists(fake_cb7: ComicArchive) -> None:
    """Test function to determine archive is a 7zip file"""
    assert fake_cb7.is_sevenzip() is True


def test_cb7_number_of_pages(fake_cb7: ComicArchive) -> None:
    """Test to determine number of pages in a cb7"""
    assert fake_cb7.get_number_of_pages() == 5


def test_cb7_file_is_writable(fake_cb7: ComicArchive) -> None:
    """Test to determine if a cb7 is writable"""
    assert fake_cb7.is_writable() is True


def test_cb7_writing_with_no_metadata(fake_cb7: ComicArchive) -> None:
    """Make sure writing no metadata to cb7 returns False"""
    assert fake_cb7.write_metadata(None) is False


# Skip test for windows, until some with a windows box can help debug this.
@pytest.mark.skipif(
    os.name == "nt", reason="Broken on windows, need window user help with debugging."
)
def test_cb7_test_metadata(fake_cb7: ComicArchive, test_metadata: GenericMetadata) -> None:
    """Test to determine if a cb7 has metadata"""
    # verify archive has no metadata
    res = fake_cb7.has_metadata()
    assert res is False

    # now let's test that we can write some
    write_result = fake_cb7.write_metadata(test_metadata)
    assert write_result is True
    assert fake_cb7.has_metadata() is True

    # Verify what was written
    new_md = fake_cb7.read_metadata()
    assert new_md.series == test_metadata.series
    assert new_md.issue == test_metadata.issue
    assert new_md.title == test_metadata.title
    assert new_md.notes == test_metadata.notes
    assert new_md.volume == test_metadata.volume

    # now remove what was just written
    fake_cb7.remove_metadata()
    assert fake_cb7.has_metadata() is False


def test_removing_metadata_on_cb7_wo_metadata(fake_cb7: ComicArchive) -> None:
    """
    Make sure trying to remove metadata from
    comic w/o any returns True
    """
    assert fake_cb7.write_metadata(None) is False
    assert fake_cb7.remove_metadata() is True


# def test_cb7_get_page(fake_cb7: ComicArchive) -> None:
#     """Test to set if a page from a comic archive can be retrieved"""
#     # Get page 2
#     assert fake_cb7.get_page(0) is not None


def test_cb7_metadata_from_filename(fake_cb7: ComicArchive) -> None:
    """Test to get metadata from comic archives filename"""
    test_md = fake_cb7.metadata_from_filename()
    assert test_md.series == "Foo Bar"
    assert test_md.issue == "1"
    assert test_md.volume == "1"
    assert test_md.year == "2000"


def test_cb7_apply_file_info_to_metadata(fake_cb7: ComicArchive) -> None:
    """Test to apply archive info to the generic metadata"""
    test_md = GenericMetadata()
    fake_cb7.apply_archive_info_to_metadata(test_md)
    # TODO: Need to test calculate page sizes
    assert test_md.page_count == "5"


# ------------------------------------------------------------------
def test_zip_file_exists(fake_cbz: ComicArchive) -> None:
    """Test function that determines if a file is a zip file"""
    assert fake_cbz.is_zip() is True
    assert fake_cbz.is_sevenzip() is False


def test_whether_text_file_is_comic_archive(tmp_path: Path) -> None:
    """
    Test that a text file produces a false result
    when determining whether it's a comic archive
    """
    test_file = tmp_path / "text-file-test.txt"
    test_file.write_text("Blah Blah Blah")

    ca = ComicArchive(test_file)
    assert ca.seems_to_be_a_comic_archive() is False


def test_archive_number_of_pages(fake_cbz: ComicArchive) -> None:
    """Test to determine number of pages in a comic archive"""
    assert fake_cbz.get_number_of_pages() == 4


def test_archive_is_writable(fake_cbz: ComicArchive) -> None:
    """Test to determine if a comic archive is writable"""
    assert fake_cbz.is_writable() is True


def test_archive_writing_with_no_metadata(fake_cbz: ComicArchive) -> None:
    """Make sure writing no metadata to comic returns False"""
    assert fake_cbz.write_metadata(None) is False


def test_archive_test_metadata(fake_cbz: ComicArchive, test_metadata: GenericMetadata) -> None:
    """Test to determine if a comic archive has metadata"""
    # verify archive has no metadata
    assert fake_cbz.has_metadata() is False

    # now let's test that we can write some
    write_result = fake_cbz.write_metadata(test_metadata)
    assert write_result is True
    assert fake_cbz.has_metadata() is True

    # Verify what was written
    new_md = fake_cbz.read_metadata()
    assert new_md.series == test_metadata.series
    assert new_md.issue == test_metadata.issue
    assert new_md.title == test_metadata.title
    assert new_md.notes == test_metadata.notes
    assert new_md.volume == test_metadata.volume

    # now remove what was just written
    fake_cbz.remove_metadata()
    assert fake_cbz.has_metadata() is False


def test_removing_metadata_on_comic_wo_metadata(fake_cbz: ComicArchive) -> None:
    """
    Make sure trying to remove metadata from
    comic w/o any returns True
    """
    assert fake_cbz.write_metadata(None) is False
    assert fake_cbz.remove_metadata() is True


def test_archive_get_page(fake_cbz: ComicArchive) -> None:
    """Test to set if a page from a comic archive can be retrieved"""
    # Get page 2
    assert fake_cbz.get_page(1) is not None


def test_archive_metadata_from_filename(fake_cbz: ComicArchive) -> None:
    """Test to get metadata from comic archives filename"""
    test_md = fake_cbz.metadata_from_filename()
    assert test_md.series == "Aquaman"
    assert test_md.issue == "1"
    assert test_md.volume == "1"
    assert test_md.year == "1994"


def test_archive_apply_file_info_to_metadata(fake_cbz: ComicArchive) -> None:
    """Test to apply archive info to the generic metadata"""
    test_md = GenericMetadata()
    fake_cbz.apply_archive_info_to_metadata(test_md)
    # TODO: Need to test calculate page sizes
    assert test_md.page_count == "4"
