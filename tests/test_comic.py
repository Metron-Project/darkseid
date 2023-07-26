""" Tests for comic archive files """
import sys
import zipfile
from pathlib import Path

import py7zr
import pytest

from darkseid.comic import Comic, UnknownArchiver
from darkseid.metadata import Metadata
from tests.conftest import IMG_DIR

# Uses to test image bytes
PAGE_TMPL = str(IMG_DIR / "CaptainScience#1_{page_num}.jpg")
PAGE_FIVE = PAGE_TMPL.format(page_num="05")

#######
# CB7 #
#######


def test_cb7_file_exists(fake_cb7: Comic) -> None:
    """Test function to determine archive is a 7zip file"""
    assert fake_cb7.is_sevenzip() is True


def test_cb7_number_of_pages(fake_cb7: Comic) -> None:
    """Test to determine number of pages in a cb7"""
    assert fake_cb7.get_number_of_pages() == 5


def test_cb7_file_is_writable(fake_cb7: Comic) -> None:
    """Test to determine if a cb7 is writable"""
    assert fake_cb7.is_writable() is True


def test_cb7_writing_with_no_metadata(fake_cb7: Comic) -> None:
    """Make sure writing no metadata to cb7 returns False"""
    assert fake_cb7.write_metadata(None) is False


# Skip test for windows, until some with a windows box can help debug this.
@pytest.mark.skipif(sys.platform in ["win32", "darwin"], reason="Skip MacOS & Windows.")
def test_cb7_test_metadata(tmp_path: Path, fake_metadata: Metadata) -> None:
    """Test to determine if a cb7 has metadata"""

    # Create cb7 archive/
    z_file: Path = tmp_path / "Captain Science v1 #001 (2000).cb7"
    with py7zr.SevenZipFile(z_file, "w") as cb7:
        cb7.writeall(IMG_DIR)

    ca = Comic(z_file)

    # verify archive has no metadata
    res = ca.has_metadata()
    assert res is False

    # now let's test that we can write some
    write_result = ca.write_metadata(fake_metadata)
    assert write_result is True
    assert ca.has_metadata() is True

    # Verify what was written
    new_md = ca.read_metadata()
    assert new_md.series.name == fake_metadata.series.name
    assert new_md.publisher.name == fake_metadata.publisher.name
    assert new_md.series.volume == fake_metadata.series.volume
    assert new_md.series.format == fake_metadata.series.format
    assert new_md.issue == fake_metadata.issue
    assert new_md.stories == fake_metadata.stories

    # now remove what was just written
    ca.remove_metadata()
    assert ca.has_metadata() is False


def test_removing_metadata_on_cb7_wo_metadata(fake_cb7: Comic) -> None:
    """
    Make sure trying to remove metadata from
    comic w/o any returns True
    """
    assert fake_cb7.write_metadata(None) is False
    assert fake_cb7.remove_metadata() is True


def test_cb7_get_random_page(fake_cb7: Comic) -> None:
    """Test to set if a page from a comic archive can be retrieved"""
    page = fake_cb7.get_page(4)
    with open(PAGE_FIVE, "rb") as cif:
        image = cif.read()
    assert image == page


def test_cb7_metadata_from_filename(fake_cb7: Comic) -> None:
    """Test to get metadata from comic archives filename"""
    test_md = fake_cb7.metadata_from_filename()
    assert test_md.series.name == "Captain Science"
    assert test_md.issue == "1"


def test_cb7_apply_file_info_to_metadata(fake_cb7: Comic) -> None:
    """Test to apply archive info to the generic metadata"""
    test_md = Metadata()
    fake_cb7.apply_archive_info_to_metadata(test_md)
    # TODO: Need to test calculate page sizes
    assert test_md.page_count == "5"


#######
# CBZ #
#######
def test_archive_from_img_dir(tmp_path: Path, fake_metadata: Metadata) -> None:
    z_file: Path = tmp_path / "Aquaman v1 #001 (of 08) (1994).cbz"
    with zipfile.ZipFile(z_file, "w") as zf:
        for p in IMG_DIR.iterdir():
            zf.write(p)

    ca = Comic(z_file)
    test_md = Metadata()
    test_md.set_default_page_list(ca.get_number_of_pages())
    test_md.overlay(fake_metadata)
    ca.write_metadata(test_md)
    res = ca.read_metadata()
    assert res.page_count == 5
    assert res.series.name == fake_metadata.series.name
    assert res.series.format == fake_metadata.series.format
    assert res.series.volume == fake_metadata.series.volume
    assert res.issue == fake_metadata.issue
    assert res.stories == fake_metadata.stories
    assert res.cover_date == fake_metadata.cover_date
    assert res.story_arcs == fake_metadata.story_arcs
    assert res.characters == fake_metadata.characters
    assert res.teams == fake_metadata.teams
    assert res.black_and_white == fake_metadata.black_and_white
    assert res.comments == fake_metadata.comments


def test_zip_file_exists(fake_cbz: Comic) -> None:
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

    ca = Comic(test_file)
    assert ca.seems_to_be_a_comic_archive() is False


def test_archive_number_of_pages(fake_cbz: Comic) -> None:
    """Test to determine number of pages in a comic archive"""
    assert fake_cbz.get_number_of_pages() == 5


def test_archive_is_writable(fake_cbz: Comic) -> None:
    """Test to determine if a comic archive is writable"""
    assert fake_cbz.is_writable() is True


def test_archive_writing_with_no_metadata(fake_cbz: Comic) -> None:
    """Make sure writing no metadata to comic returns False"""
    assert fake_cbz.write_metadata(None) is False


def test_archive_test_metadata(fake_cbz: Comic, fake_metadata: Metadata) -> None:
    """Test to determine if a comic archive has metadata"""
    # verify archive has no metadata
    assert fake_cbz.has_metadata() is False

    # now let's test that we can write some
    write_result = fake_cbz.write_metadata(fake_metadata)
    assert write_result is True
    assert fake_cbz.has_metadata() is True

    # Verify what was written
    new_md = fake_cbz.read_metadata()
    assert new_md.series.name == fake_metadata.series.name
    assert new_md.series.volume == fake_metadata.series.volume
    assert new_md.series.format == fake_metadata.series.format
    assert new_md.issue == fake_metadata.issue
    assert new_md.stories == fake_metadata.stories

    # now remove what was just written
    fake_cbz.remove_metadata()
    assert fake_cbz.has_metadata() is False


def test_removing_metadata_on_comic_wo_metadata(fake_cbz: Comic) -> None:
    """
    Make sure trying to remove metadata from
    comic w/o any returns True
    """
    assert fake_cbz.write_metadata(None) is False
    assert fake_cbz.remove_metadata() is True


@pytest.mark.skipif(sys.platform in ["win32"], reason="Skip Windows.")
def test_cbz_get_random_page(fake_cbz: Comic) -> None:
    """Test to set if a page from a comic archive can be retrieved"""
    page = fake_cbz.get_page(4)
    with open(PAGE_FIVE, "rb") as cif:
        image = cif.read()
    assert image == page


def test_archive_metadata_from_filename(fake_cbz: Comic) -> None:
    """Test to get metadata from comic archives filename"""
    test_md = fake_cbz.metadata_from_filename()
    assert test_md.series.name == "Captain Science"
    assert test_md.issue == "1"


@pytest.mark.skipif(sys.platform in ["win32"], reason="Skip Windows.")
def test_archive_apply_file_info_to_metadata(fake_cbz: Comic) -> None:
    """Test to apply archive info to the generic metadata"""
    test_md = Metadata()
    fake_cbz.apply_archive_info_to_metadata(test_md)
    # TODO: Need to test calculate page sizes
    assert test_md.page_count == "5"


# Skip test for windows, until some with a windows box can help debug this.
@pytest.mark.skipif(sys.platform in ["win32", "darwin"], reason="Skip MacOS & Windows.")
def test_archive_export_to_cb7(tmp_path, fake_cbz: Comic) -> None:
    fn = tmp_path / "fake_export.cb7"
    assert fake_cbz.export_as_cb7(fn) is True
    ca = Comic(fn)
    assert ca.is_sevenzip() is True
    assert ca.get_number_of_pages() == 5


#######
# CBR #
#######
@pytest.mark.skipif(sys.platform in ["win32", "darwin"], reason="Skip MacOS & Windows.")
def test_rar_write(fake_rar: Comic, fake_metadata: Metadata) -> None:
    assert fake_rar.write_metadata(fake_metadata) is False


# Skip test for Windows and MacOS.
@pytest.mark.skipif(sys.platform in ["win32", "darwin"], reason="Skip MacOS & Windows.")
def test_rar_file_exists(fake_rar: Comic) -> None:
    """Test function that determines if a file is a rar file"""
    assert fake_rar.is_zip() is False
    assert fake_rar.is_sevenzip() is False
    assert fake_rar.is_rar() is True


# Skip test for Windows and MacOS.
@pytest.mark.skipif(sys.platform in ["win32", "darwin"], reason="Skip MacOS & Windows.")
def test_rar_is_writable(fake_rar: Comic) -> None:
    """Test to determine if rar archive is writable"""
    assert fake_rar.is_writable() is False


# Skip test for Windows and MacOS.
@pytest.mark.skipif(sys.platform in ["win32", "darwin"], reason="Skip MacOS & Windows.")
def test_rar_read_metadata(fake_rar: Comic) -> None:
    """Test to read a rar files metadata"""
    md = fake_rar.read_metadata()
    assert md.series.name == "Captain Science"
    assert md.issue == "1"
    assert md.series.volume == 1950
    assert md.page_count == 36


# Skip test for Windows and MacOS.
@pytest.mark.skipif(sys.platform in ["win32", "darwin"], reason="Skip MacOS & Windows.")
def test_rar_metadata_from_filename(fake_rar: Comic) -> None:
    """Test to get metadata from comic archives filename"""
    test_md = fake_rar.metadata_from_filename()
    assert test_md.series.name == "Captain Science"
    assert test_md.issue == "1"


# Skip test for Windows and MacOS.
@pytest.mark.skipif(sys.platform in ["win32", "darwin"], reason="Skip MacOS & Windows.")
def test_rar_number_of_pages(fake_rar: Comic) -> None:
    """Test to determine number of pages in a comic archive"""
    assert fake_rar.get_number_of_pages() == 36


# Skip test for Windows and MacOS.
@pytest.mark.skipif(sys.platform in ["win32", "darwin"], reason="Skip MacOS & Windows.")
def test_rar_get_random_page(fake_rar: Comic) -> None:
    """Test to set if a page from a comic archive can be retrieved"""
    page = fake_rar.get_page(4)
    with open(PAGE_FIVE, "rb") as cif:
        image = cif.read()
    assert image == page


# Skip test for Windows and MacOS.
@pytest.mark.skipif(sys.platform in ["win32", "darwin"], reason="Skip MacOS & Windows.")
def test_rar_export_to_zip(tmp_path, fake_rar: Comic) -> None:
    fn = tmp_path / "fake_export.cbz"
    assert fake_rar.export_as_zip(fn) is True
    ca = Comic(fn)
    assert ca.is_zip() is True
    assert ca.get_number_of_pages() == 36


###########
# Unknown #
###########


def test_unknown_archive(tmp_path: Path) -> None:
    fn = tmp_path / "unknown"
    fn2 = tmp_path / "other"
    ca = UnknownArchiver(fn)
    oa = UnknownArchiver(fn2)
    txt_fn = "test.txt"
    assert ca.get_filename_list() == []
    assert ca.remove_file(txt_fn) is False
    assert ca.copy_from_archive(oa) is False
