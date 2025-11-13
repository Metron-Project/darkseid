# ruff: noqa: SLF001
"""Tests for the Comic class using function-based pytest approach."""

import io
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from PIL import Image
from py7zr import py7zr

from darkseid.comic import (
    COMIC_RACK_FILENAME,
    METRON_INFO_FILENAME,
    SUPPORTED_IMAGE_EXTENSIONS,
    Comic,
    ComicArchiveError,
    ComicError,
    ComicMetadataError,
    MetadataFormat,
)
from darkseid.metadata.data_classes import ImageMetadata, Metadata


# Fixtures
@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_cbz_file(temp_dir):
    """Create a sample CBZ file for testing."""
    cbz_path = temp_dir / "test_comic.cbz"

    # Create a simple image in memory
    img = Image.new("RGB", (100, 150), color="red")
    img_bytes = io.BytesIO()
    img.save(img_bytes, format="JPEG")
    img_data = img_bytes.getvalue()

    # Create CBZ file
    with zipfile.ZipFile(cbz_path, "w") as zf:
        zf.writestr("page001.jpg", img_data)
        zf.writestr("page002.jpg", img_data)
        zf.writestr("ComicInfo.xml", "<ComicInfo><Title>Test Comic</Title></ComicInfo>")

    return cbz_path


@pytest.fixture
def sample_seven_zip_path(temp_dir):
    seven_zip_path = temp_dir / "test.cb7"
    with py7zr.SevenZipFile(seven_zip_path, "w") as zf:
        zf.writestr("content1", "file1.txt")
        zf.writestr(b"fake_image_data", "file2.jpg")
        zf.writestr("content3", "dir/file3.txt")
    return seven_zip_path


@pytest.fixture
def sample_metadata():
    """Create sample metadata for testing."""
    metadata = Metadata()
    metadata.title = "Test Comic"
    metadata.issue = "1"
    metadata.page_count = 2
    return metadata


@pytest.fixture
def mock_archiver():
    """Create a mock archiver for testing."""
    archiver = Mock()
    archiver.is_write_operation_expected.return_value = True
    archiver.get_filename_list.return_value = ["page001.jpg", "page002.jpg", "ComicInfo.xml"]
    archiver.read_file.return_value = b"test image data"
    archiver.write_file.return_value = True
    archiver.remove_files.return_value = True
    return archiver


# Test MetadataFormat enum
def test_metadata_format_string_representation():
    """Test MetadataFormat string representation."""
    assert str(MetadataFormat.COMIC_INFO) == "ComicInfo"
    assert str(MetadataFormat.METRON_INFO) == "MetronInfo"
    assert str(MetadataFormat.UNKNOWN) == "Unknown"


# Test Comic initialization
def test_comic_init_with_valid_path(sample_cbz_file):
    """Test Comic initialization with valid path."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)
        assert comic.path == sample_cbz_file
        assert comic.name == sample_cbz_file.name


def test_comic_init_with_string_path(sample_cbz_file):
    """Test Comic initialization with string path."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(str(sample_cbz_file))
        assert comic.path == sample_cbz_file


def test_comic_init_nonexistent_file():
    """Test Comic initialization with nonexistent file."""
    with pytest.raises(ComicArchiveError, match="Comic file does not exist"):
        Comic("/nonexistent/path.cbz")


def test_comic_init_archiver_creation_failure(sample_cbz_file):
    """Test Comic initialization when archiver creation fails."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.side_effect = Exception("Archiver creation failed")
        with pytest.raises(ComicArchiveError, match="Failed to create archiver"):
            Comic(sample_cbz_file)


# Test string representations
def test_comic_str(sample_cbz_file):
    """Test Comic string representation."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)
        assert str(comic) == sample_cbz_file.name


def test_comic_repr(sample_cbz_file):
    """Test Comic detailed string representation."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg", "page2.jpg"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)
        repr_str = repr(comic)
        assert "Comic(path=" in repr_str
        assert "pages=2" in repr_str


# Test properties
def test_comic_properties(sample_cbz_file):
    """Test Comic properties."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        assert comic.path == sample_cbz_file
        assert comic.name == sample_cbz_file.name
        assert comic.size > 0


# Test archive validation
def test_is_archive_valid_zip(sample_cbz_file):
    """Test archive validation for ZIP files."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        with patch.object(comic._archiver, "test", return_value=True):
            assert comic.is_archive_valid() is True


def test_is_archive_valid_rar(sample_cbz_file):
    """Test archive validation for RAR files."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        with patch.object(comic._archiver, "test", return_value=True):
            assert comic.is_archive_valid() is True


def test_is_archive_valid_neither(sample_cbz_file):
    """Test archive validation when neither ZIP nor RAR."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        with patch.object(comic._archiver, "test", return_value=False):
            assert comic.is_archive_valid() is False


def test_is_archive_valid_exception(sample_cbz_file):
    """Test archive validation when exception occurs."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        with patch.object(comic._archiver, "test", side_effect=Exception()):
            assert comic.is_archive_valid() is False


# Test archive type detection
# def test_zip_test(sample_cbz_file):
#     """Test ZIP file detection."""
#     with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
#         mock_factory.return_value = Mock()
#         comic = Comic(sample_cbz_file)
#         assert comic._archiver.test() is True
#
#
# def test_rar_test(sample_cbz_file):
#     """Test RAR file detection."""
#     with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
#         mock_factory.return_value = Mock()
#         comic = Comic(sample_cbz_file)
#
#         with patch("rarfile.is_rarfile", return_value=True):
#             assert comic._archiver.test() is True
#
#
# def test_rar_test_exception(sample_cbz_file):
#     """Test RAR file detection with exception."""
#     with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
#         mock_factory.return_value = Mock()
#         comic = Comic(sample_cbz_file)
#
#         with patch("rarfile.is_rarfile", side_effect=Exception()):
#             assert comic._archiver.test() is False


def test_is_zip_by_extension(temp_dir):
    """Test ZIP detection by file extension."""
    zip_path = temp_dir / "test.cbz"
    zip_path.touch()

    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(zip_path)
        assert (comic.path.suffix.lower() in {".cbz", ".zip"}) is True


def test_is_rar_by_extension(temp_dir):
    """Test RAR detection by file extension."""
    rar_path = temp_dir / "test.cbr"
    rar_path.touch()

    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(rar_path)
        assert (comic.path.suffix.lower() in {".cbr"}) is True


# Test writability
def test_is_writable_true(sample_cbz_file):
    """Test writability when conditions are met."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.is_write_operation_expected.return_value = True
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        with patch("os.access", return_value=True):
            assert comic.is_writable() is True


def test_is_writable_archiver_not_writable(sample_cbz_file):
    """Test writability when archiver doesn't support writing."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.is_write_operation_expected.return_value = False
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)
        assert comic.is_writable() is False


def test_is_writable_no_file_access(sample_cbz_file):
    """Test writability when file access is denied."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.is_write_operation_expected.return_value = True
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        with patch("os.access", return_value=False):
            assert comic.is_writable() is False


# Test comic archive detection
def test_seems_to_be_a_comic_archive(sample_cbz_file):
    """Test comic archive detection."""
    comic = Comic(sample_cbz_file)
    assert comic.seems_to_be_a_comic_archive() is True


def test_seems_to_be_a_comic_archive_no_pages(sample_cbz_file):
    """Test comic archive detection with no pages."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = []
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        assert comic.seems_to_be_a_comic_archive() is False


# Test page operations
def test_get_page_valid_index(sample_cbz_file):
    """Test getting a page with valid index."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg", "page2.jpg"]
        mock_archiver.read_file.return_value = b"image data"
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)
        page_data = comic.get_page(0)
        assert page_data == b"image data"


def test_get_page_invalid_index(sample_cbz_file):
    """Test getting a page with invalid index."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)
        assert comic.get_page(-1) is None
        assert comic.get_page(10) is None


def test_get_page_read_error(sample_cbz_file):
    """Test getting a page when read fails."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg"]
        mock_archiver.read_file.side_effect = OSError("Read failed")
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)
        assert comic.get_page(0) is None


def test_get_page_name_valid_index(sample_cbz_file):
    """Test getting page name with valid index."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg", "page2.jpg"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)
        assert comic.get_page_name(0) == "page1.jpg"
        assert comic.get_page_name(1) == "page2.jpg"


def test_get_page_name_invalid_index(sample_cbz_file):
    """Test getting page name with invalid index."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)
        assert comic.get_page_name(-1) is None
        assert comic.get_page_name(10) is None


# Test image detection
@pytest.mark.parametrize(
    ("filename", "expected"),
    [
        ("image.jpg", True),
        ("image.jpeg", True),
        ("image.png", True),
        ("image.gif", True),
        ("image.webp", True),
        ("image.JPG", True),  # Case insensitive
        ("image.txt", False),
        (".hidden.jpg", False),  # Hidden files
        ("normal.jpg", True),
    ],
)
def test_is_image(filename, expected):
    """Test image file detection."""
    path = Path(filename)
    assert Comic.is_image(path) == expected


# Test page list operations
def test_get_page_name_list(sample_cbz_file):
    """Test getting page name list."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = [
            "page2.jpg",
            "page1.jpg",
            "info.txt",
            ".hidden.jpg",
        ]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)
        page_list = comic.get_page_name_list()

        # Should be sorted and only include image files
        assert page_list == ["page1.jpg", "page2.jpg"]


def test_get_page_name_list_no_sort(sample_cbz_file):
    """Test getting page name list without sorting."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page2.jpg", "page1.jpg"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)
        page_list = comic.get_page_name_list(sort_list=False)

        # Should maintain original order but filter images
        assert page_list == ["page2.jpg", "page1.jpg"]


def test_get_page_name_list_cached(sample_cbz_file):
    """Test that page name list is cached."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        # First call
        page_list1 = comic.get_page_name_list()
        # Second call should use cache
        page_list2 = comic.get_page_name_list()

        assert page_list1 == page_list2
        # Archiver should only be called once
        mock_archiver.get_filename_list.assert_called_once()


def test_get_page_name_list_exception(sample_cbz_file):
    """Test page name list when exception occurs."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.side_effect = Exception("Error")
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)
        page_list = comic.get_page_name_list()
        assert page_list == []


def test_get_number_of_pages(sample_cbz_file):
    """Test getting number of pages."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg", "page2.jpg", "info.txt"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)
        assert comic.get_number_of_pages() == 2


def test_get_number_of_pages_cached(sample_cbz_file):
    """Test that page count is cached."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        # Multiple calls should use cache
        count1 = comic.get_number_of_pages()
        count2 = comic.get_number_of_pages()

        assert count1 == count2 == 1
        mock_archiver.get_filename_list.assert_called_once()


# Test metadata operations
def test_read_metadata_comic_rack(sample_cbz_file):
    """Test reading ComicInfo metadata."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg", "ComicInfo.xml"]
        mock_archiver.read_file.return_value = b"<ComicInfo><Number>1</Number></ComicInfo>"
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        with patch("darkseid.metadata.comicinfo.ComicInfo.metadata_from_string") as mock_parse:
            mock_metadata = Metadata()
            mock_metadata.issue = "1"
            mock_parse.return_value = mock_metadata

            metadata = comic.read_metadata(MetadataFormat.COMIC_INFO)
            assert metadata.issue == "1"


def test_read_metadata_metron_info(sample_cbz_file):
    """Test reading MetronInfo metadata."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg", "MetronInfo.xml"]
        mock_archiver.read_file.return_value = b"<MetronInfo><Number>2</Number></MetronInfo>"
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        with patch("darkseid.metadata.metroninfo.MetronInfo.metadata_from_string") as mock_parse:
            mock_metadata = Metadata()
            mock_metadata.issue = "2"
            mock_parse.return_value = mock_metadata

            metadata = comic.read_metadata(MetadataFormat.METRON_INFO)
            assert metadata.issue == "2"


def test_read_metadata_unknown_format(sample_cbz_file):
    """Test reading metadata with unknown format."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        metadata = comic.read_metadata(MetadataFormat.UNKNOWN)
        assert isinstance(metadata, Metadata)


def test_read_metadata_parse_error(sample_cbz_file):
    """Test reading metadata when parsing fails."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["ComicInfo.xml"]
        mock_archiver.read_file.return_value = b"invalid xml"
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        with patch(
            "darkseid.metadata.comicinfo.ComicInfo.metadata_from_string", side_effect=Exception()
        ):
            metadata = comic.read_metadata(MetadataFormat.COMIC_INFO)
            assert isinstance(metadata, Metadata)


def test_read_raw_metadata_not_found(sample_cbz_file):
    """Test reading raw metadata when file not found."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = []
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)
        assert comic.read_raw_ci_metadata() is None


def test_read_raw_metadata_decode_error(sample_cbz_file):
    """Test reading raw metadata with decode error."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["ComicInfo.xml"]
        mock_archiver.read_file.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "error")
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)
        assert comic.read_raw_ci_metadata() is None


# Test metadata writing
def test_write_metadata_comic_rack(sample_cbz_file, sample_metadata):
    """Test writing ComicInfo metadata."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.is_write_operation_expected.return_value = True
        mock_archiver.write_file.return_value = True
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        with (
            patch.object(comic, "is_writable", return_value=True),
            patch(
                "darkseid.metadata.comicinfo.ComicInfo.string_from_metadata", return_value="<xml/>"
            ),
        ):
            result = comic.write_metadata(sample_metadata, MetadataFormat.COMIC_INFO)
            assert result is True


def test_write_metadata_not_writable(sample_cbz_file, sample_metadata):
    """Test writing metadata when archive is not writable."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        with patch.object(comic, "is_writable", return_value=False):
            result = comic.write_metadata(sample_metadata, MetadataFormat.COMIC_INFO)
            assert result is False


def test_write_metadata_unsupported_format(sample_cbz_file, sample_metadata):
    """Test writing metadata with unsupported format."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        with pytest.raises(ComicMetadataError, match="Unsupported metadata format"):
            comic.write_metadata(sample_metadata, MetadataFormat.UNKNOWN)


def test_write_metadata_none_metadata(sample_cbz_file):
    """Test writing None metadata."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        result = comic.write_metadata(None, MetadataFormat.COMIC_INFO)  # type: ignore
        assert result is False


def test_write_metadata_exception(sample_cbz_file, sample_metadata):
    """Test writing metadata when exception occurs."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.is_write_operation_expected.return_value = True
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        with (
            patch.object(comic, "is_writable", return_value=True),
            patch.object(comic, "_apply_archive_info_to_metadata", side_effect=Exception()),
        ):
            result = comic.write_metadata(sample_metadata, MetadataFormat.COMIC_INFO)
            assert result is False


# Test metadata removal
def test_remove_metadata_comic_rack(sample_cbz_file):
    """Test removing ComicInfo metadata."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["ComicInfo.xml", "page1.jpg"]
        mock_archiver.remove_files.return_value = True
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        with patch.object(comic, "has_metadata", return_value=True):
            result = comic.remove_metadata([MetadataFormat.COMIC_INFO])
            assert result is True


def test_remove_metadata_not_found(sample_cbz_file):
    """Test removing metadata when not found."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        with patch.object(comic, "has_metadata", return_value=False):
            result = comic.remove_metadata([MetadataFormat.COMIC_INFO])
            assert result is True  # No metadata to remove is considered success


def test_remove_metadata_unsupported_format(sample_cbz_file):
    """Test removing metadata with unsupported format."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        result = comic.remove_metadata([MetadataFormat.UNKNOWN])
        assert result is False


def test_remove_metadata_case_insensitive(sample_cbz_file):
    """Test removing metadata with case-insensitive filename matching."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["COMICINFO.XML", "page1.jpg"]
        mock_archiver.remove_files.return_value = True
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        with patch.object(comic, "has_metadata", return_value=True):
            result = comic.remove_metadata([MetadataFormat.COMIC_INFO])
            assert result is True
            mock_archiver.remove_files.assert_called_once_with(["COMICINFO.XML"])


# def test_remove_metadata_exception(sample_cbz_file):
#     """Test removing metadata when exception occurs."""
#     with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
#         mock_archiver = Mock()
#         mock_archiver.get_filename_list.side_effect = Exception("Error")
#         mock_factory.return_value = mock_archiver
#
#         comic = Comic(sample_cbz_file)
#
#         with patch.object(comic, "has_metadata", return_value=True):
#             result = comic.remove_metadata([MetadataFormat.COMIC_INFO])
#             assert result is False


# Test page removal
def test_remove_pages_success(sample_cbz_file):
    """Test successful page removal."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg", "page2.jpg", "page3.jpg"]
        mock_archiver.remove_files.return_value = True
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        with patch.object(comic, "is_writable", return_value=True):
            result = comic.remove_pages([0, 2])  # Remove first and third pages
            assert result is True
            mock_archiver.remove_files.assert_called_once_with(["page1.jpg", "page3.jpg"])


def test_remove_pages_empty_list(sample_cbz_file):
    """Test removing pages with empty list."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        result = comic.remove_pages([])
        assert result is False


def test_remove_pages_not_writable(sample_cbz_file):
    """Test removing pages when archive is not writable."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        with patch.object(comic, "is_writable", return_value=False):
            result = comic.remove_pages([0])
            assert result is False


def test_remove_pages_invalid_index(sample_cbz_file):
    """Test removing pages with invalid index."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        with patch.object(comic, "is_writable", return_value=True):
            result = comic.remove_pages([10])  # Invalid index
            assert result is False


def test_remove_pages_exception(sample_cbz_file):
    """Test removing pages when exception occurs."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg"]
        mock_archiver.remove_files.side_effect = Exception("Error")
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        with patch.object(comic, "is_writable", return_value=True):
            result = comic.remove_pages([0])
            assert result is False


# Test metadata detection
def test_has_metadata_comic_rack(sample_cbz_file):
    """Test ComicInfo metadata detection."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg", "ComicInfo.xml"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        with patch.object(comic, "seems_to_be_a_comic_archive", return_value=True):
            assert comic.has_metadata(MetadataFormat.COMIC_INFO) is True


def test_has_metadata_metron_info(sample_cbz_file):
    """Test MetronInfo metadata detection."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg", "MetronInfo.xml"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        with patch.object(comic, "seems_to_be_a_comic_archive", return_value=True):
            assert comic.has_metadata(MetadataFormat.METRON_INFO) is True


def test_has_metadata_not_comic_archive(sample_cbz_file):
    """Test metadata detection when not a comic archive."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        with patch.object(comic, "seems_to_be_a_comic_archive", return_value=False):
            assert comic.has_metadata(MetadataFormat.COMIC_INFO) is False


def test_has_metadata_case_insensitive(sample_cbz_file):
    """Test metadata detection is case insensitive."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg", "COMICINFO.XML"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        with patch.object(comic, "seems_to_be_a_comic_archive", return_value=True):
            assert comic.has_metadata(MetadataFormat.COMIC_INFO) is True


def test_has_metadata_cached(sample_cbz_file):
    """Test that metadata detection is cached."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["ComicInfo.xml"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        with patch.object(comic, "seems_to_be_a_comic_archive", return_value=True):
            # Multiple calls should use cache
            result1 = comic.has_metadata(MetadataFormat.COMIC_INFO)
            result2 = comic.has_metadata(MetadataFormat.COMIC_INFO)

            assert result1 == result2 is True
            mock_archiver.get_filename_list.assert_called_once()


def test_has_metadata_exception(sample_cbz_file):
    """Test metadata detection when exception occurs."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.side_effect = Exception("Error")
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        with patch.object(comic, "seems_to_be_a_comic_archive", return_value=True):
            assert comic.has_metadata(MetadataFormat.COMIC_INFO) is False


def test_has_metadata_unknown_format(sample_cbz_file):
    """Test metadata detection with unknown format."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        assert comic.has_metadata(MetadataFormat.UNKNOWN) is False


# Test archive info application to metadata
def test_apply_archive_info_to_metadata_basic(sample_cbz_file, sample_metadata):
    """Test applying basic archive info to metadata."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg", "page2.jpg"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)
        comic._apply_archive_info_to_metadata(sample_metadata)

        assert sample_metadata.page_count == 2


def test_apply_archive_info_to_metadata_with_page_sizes(sample_cbz_file, sample_metadata):
    """Test applying archive info with page size calculation."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg"]
        mock_archiver.read_file.return_value = b"fake image data"
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        # Add a page that needs size calculation
        page = ImageMetadata()
        page["Image"] = "0"
        sample_metadata.pages = [page]

        # Mock PIL Image
        mock_image = Mock()
        mock_image.size = (100, 150)
        mock_image.__enter__ = Mock(return_value=mock_image)
        mock_image.__exit__ = Mock(return_value=None)

        with patch("PIL.Image.open", return_value=mock_image):
            comic._apply_archive_info_to_metadata(sample_metadata, calc_page_sizes=True)

        assert page["ImageSize"] == "15"  # len(b"fake image data")
        assert page["ImageWidth"] == "100"
        assert page["ImageHeight"] == "150"


def test_apply_archive_info_to_metadata_skip_complete_pages(sample_cbz_file, sample_metadata):
    """Test skipping pages that already have complete info."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        # Add a page with complete info
        page = ImageMetadata()
        page["Image"] = "0"
        page["ImageSize"] = "1000"
        page["ImageWidth"] = "100"
        page["ImageHeight"] = "150"
        sample_metadata.pages = [page]

        comic._apply_archive_info_to_metadata(sample_metadata, calc_page_sizes=True)

        # Page info should remain unchanged
        assert page["ImageSize"] == "1000"
        mock_archiver.read_file.assert_not_called()


def test_apply_archive_info_to_metadata_invalid_page_index(sample_cbz_file, sample_metadata):
    """Test handling invalid page index during info application."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        # Add a page with invalid index
        page = ImageMetadata()
        page["Image"] = "invalid"
        sample_metadata.pages = [page]

        # Should not raise exception
        comic._apply_archive_info_to_metadata(sample_metadata, calc_page_sizes=True)


def test_apply_archive_info_to_metadata_image_error(sample_cbz_file, sample_metadata):
    """Test handling image processing errors during info application."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg"]
        mock_archiver.read_file.return_value = b"fake image data"
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        page = ImageMetadata()
        page["Image"] = "0"
        sample_metadata.pages = [page]

        with patch("PIL.Image.open", side_effect=OSError("Cannot identify image")):
            # Should not raise exception
            comic._apply_archive_info_to_metadata(sample_metadata, calc_page_sizes=True)

            # Should still set image size
            assert page["ImageSize"] == "15"


# Test ZIP export
def test_export_as_zip_already_zip(sample_cbz_file, temp_dir):
    """Test exporting when already ZIP format."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        result = comic.export_as_zip(temp_dir / "output.cbz")
        assert result is True


# def test_export_as_zip_success(sample_cbz_file, temp_dir):
#     """Test successful ZIP export."""
#     with patch('darkseid.comic.ArchiverFactory.create_archiver') as mock_factory:
#         mock_archiver = Mock()
#         mock_factory.return_value = mock_archiver
#
#         comic = Comic(sample_cbz_file)
#
#         with patch.object(comic, 'is_zip', return_value=False):
#             with patch('darkseid.archivers.zip.ZipArchiver') as mock_zip_class:
#                 mock_zip_archiver = Mock()
#                 mock_zip_archiver.copy_from_archive.return_value = True
#                 mock_zip_class.return_value = mock_zip_archiver
#
#                 result = comic.export_as_zip(temp_dir / "output.cbz")
#                 assert result is True


def test_export_as_zip_failure(sample_seven_zip_path, temp_dir):
    """Test ZIP export failure."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_seven_zip_path)

        with (
            patch("darkseid.archivers.zip.ZipArchiver", side_effect=Exception("Error")),
        ):
            result = comic.export_as_zip(temp_dir / "output.cbz")
            assert result is False


# Test metadata formats detection
def test_get_metadata_formats(sample_cbz_file):
    """Test getting available metadata formats."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        with patch.object(comic, "has_metadata") as mock_has:

            def has_metadata_side_effect(fmt):
                return fmt in [MetadataFormat.COMIC_INFO, MetadataFormat.METRON_INFO]

            mock_has.side_effect = has_metadata_side_effect

            formats = comic.get_metadata_formats()
            expected = {MetadataFormat.COMIC_INFO, MetadataFormat.METRON_INFO}
            assert formats == expected


def test_get_metadata_formats_empty(sample_cbz_file):
    """Test getting metadata formats when none present."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        with patch.object(comic, "has_metadata", return_value=False):
            formats = comic.get_metadata_formats()
            assert formats == set()


# Test comic validation
def test_is_valid_comic_true(sample_cbz_file):
    """Test valid comic detection."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        with (
            patch.object(comic, "is_archive_valid", return_value=True),
            patch.object(comic, "seems_to_be_a_comic_archive", return_value=True),
        ):
            assert comic.is_valid_comic() is True


def test_is_valid_comic_file_not_exists():
    """Test comic validation when file doesn't exist."""
    # This will fail during initialization, so we test differently
    non_existent = Path("/nonexistent/file.cbz")

    with pytest.raises(ComicArchiveError):
        Comic(non_existent)


def test_is_valid_comic_invalid_archive(sample_cbz_file):
    """Test comic validation with invalid archive."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        with patch.object(comic, "is_archive_valid", return_value=False):
            assert comic.is_valid_comic() is False


def test_is_valid_comic_not_comic_archive(sample_cbz_file):
    """Test comic validation when not a comic archive."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        with (
            patch.object(comic, "is_archive_valid", return_value=True),
            patch.object(comic, "seems_to_be_a_comic_archive", return_value=False),
        ):
            assert comic.is_valid_comic() is False


def test_is_valid_comic_exception(sample_cbz_file):
    """Test comic validation when exception occurs."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        with patch.object(comic, "is_archive_valid", side_effect=Exception("Error")):
            assert comic.is_valid_comic() is False


# Test cache reset
def test_reset_cache(sample_cbz_file):
    """Test cache reset functionality."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        # Populate cache
        comic.get_number_of_pages()
        assert comic._cache.page_count is not None

        # Reset cache
        comic._reset_cache()

        # Verify cache is cleared
        assert comic._cache.page_count is None
        assert comic._cache.page_list is None
        assert comic._cache.has_ci is None
        assert comic._cache.has_mi is None
        assert comic._cache.metadata is None


# Test page validation
def test_validate_page_index_valid(sample_cbz_file):
    """Test page index validation with valid index."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg", "page2.jpg"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        # Should not raise exception
        comic._validate_page_index(0)
        comic._validate_page_index(1)


def test_validate_page_index_negative(sample_cbz_file):
    """Test page index validation with negative index."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        with pytest.raises(ValueError, match="Page index cannot be negative"):
            comic._validate_page_index(-1)


def test_validate_page_index_out_of_range(sample_cbz_file):
    """Test page index validation with out of range index."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        with pytest.raises(ValueError, match=r"Page index .* is out of range"):
            comic._validate_page_index(10)


# Test page list validation and fixing
def test_validate_and_fix_page_list_mismatch(sample_cbz_file):
    """Test page list validation when counts mismatch."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg", "page2.jpg"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        # Create metadata with wrong page count
        comic._cache.metadata = Metadata()
        comic._cache.metadata.pages = [ImageMetadata()]  # Only 1 page in metadata

        comic._validate_and_fix_page_list()

        # Pages should be reset and default list created
        assert len(comic._cache.metadata.pages) == 2  # Should match actual page count


def test_validate_and_fix_page_list_empty_pages(sample_cbz_file):
    """Test page list validation when pages list is empty."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg", "page2.jpg"]
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        # Create metadata with empty pages
        comic._cache.metadata = Metadata()
        comic._cache.metadata.pages = []

        with patch.object(comic._cache.metadata, "set_default_page_list") as mock_set_default:
            comic._validate_and_fix_page_list()
            mock_set_default.assert_called_once_with(2)


def test_validate_and_fix_page_list_none_metadata(sample_cbz_file):
    """Test page list validation when metadata is None."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_factory.return_value = Mock()
        comic = Comic(sample_cbz_file)

        comic._metadata = None

        # Should not raise exception
        comic._validate_and_fix_page_list()


# Test error handling in exception classes
def test_comic_error_inheritance():
    """Test that custom exceptions inherit correctly."""
    assert issubclass(ComicArchiveError, ComicError)
    assert issubclass(ComicMetadataError, ComicError)
    assert issubclass(ComicError, Exception)


def test_comic_exceptions_can_be_raised():
    """Test that custom exceptions can be raised and caught."""
    msg = "Test error"
    with pytest.raises(ComicError):
        raise ComicError(msg)

    msg = "Archive error"
    with pytest.raises(ComicArchiveError):
        raise ComicArchiveError(msg)

    msg = "Metadata error"
    with pytest.raises(ComicMetadataError):
        raise ComicMetadataError(msg)


# Test constants
def test_constants():
    """Test that constants are properly defined."""
    assert isinstance(SUPPORTED_IMAGE_EXTENSIONS, frozenset)
    assert ".jpg" in SUPPORTED_IMAGE_EXTENSIONS
    assert ".jpeg" in SUPPORTED_IMAGE_EXTENSIONS
    assert ".png" in SUPPORTED_IMAGE_EXTENSIONS
    assert ".gif" in SUPPORTED_IMAGE_EXTENSIONS
    assert ".webp" in SUPPORTED_IMAGE_EXTENSIONS

    assert COMIC_RACK_FILENAME == "ComicInfo.xml"
    assert METRON_INFO_FILENAME == "MetronInfo.xml"


# Integration-style tests
def test_full_workflow_read_metadata(sample_cbz_file):
    """Test a complete workflow of reading metadata."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.get_filename_list.return_value = ["page1.jpg", "ComicInfo.xml"]
        mock_archiver.read_file.return_value = b"<ComicInfo><Number>1.MU</Number></ComicInfo>"
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        # Check if has metadata
        with patch.object(comic, "seems_to_be_a_comic_archive", return_value=True):
            assert comic.has_metadata(MetadataFormat.COMIC_INFO) is True

        # Read raw metadata
        raw_data = comic.read_raw_ci_metadata()
        assert raw_data == "<ComicInfo><Number>1.MU</Number></ComicInfo>"

        # Read parsed metadata
        with patch("darkseid.metadata.comicinfo.ComicInfo.metadata_from_string") as mock_parse:
            mock_metadata = Metadata()
            mock_metadata.issue = "1.MU"
            mock_parse.return_value = mock_metadata

            metadata = comic.read_metadata(MetadataFormat.COMIC_INFO)
            assert metadata.issue == "1.MU"


def test_full_workflow_write_and_remove_metadata(sample_cbz_file, sample_metadata):
    """Test a complete workflow of writing and removing metadata."""
    with patch("darkseid.comic.ArchiverFactory.create_archiver") as mock_factory:
        mock_archiver = Mock()
        mock_archiver.is_write_operation_expected.return_value = True
        mock_archiver.get_filename_list.return_value = ["page1.jpg"]
        mock_archiver.write_file.return_value = True
        mock_archiver.remove_files.return_value = True
        mock_factory.return_value = mock_archiver

        comic = Comic(sample_cbz_file)

        with (
            patch.object(comic, "is_writable", return_value=True),
            patch(
                "darkseid.metadata.comicinfo.ComicInfo.string_from_metadata", return_value="<xml/>"
            ),
        ):
            # Write metadata
            result = comic.write_metadata(sample_metadata, MetadataFormat.COMIC_INFO)
            assert result is True

            # Now remove it
            with patch.object(comic, "has_metadata", return_value=True):
                result = comic.remove_metadata([MetadataFormat.COMIC_INFO])
                assert result is True
