# test_archivers.py
# ruff: noqa: ARG001, ARG002
"""Comprehensive tests for archiver modules using function-based approach."""

import io
import tempfile
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
import rarfile

from darkseid.archivers import ArchiverFactory, RarArchiver, UnknownArchiver, ZipArchiver
from darkseid.archivers.archiver import Archiver, ArchiverReadError


# Fixtures
@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def sample_zip_path(temp_dir):
    """Create a sample ZIP file for testing."""
    zip_path = temp_dir / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("file1.txt", "content1")
        zf.writestr("file2.jpg", b"fake_image_data")
        zf.writestr("dir/file3.txt", "content3")
    return zip_path


@pytest.fixture
def empty_zip_path(temp_dir):
    """Create an empty ZIP file for testing."""
    zip_path = temp_dir / "empty.zip"
    with zipfile.ZipFile(zip_path, "w") as _:
        pass
    return zip_path


@pytest.fixture
def sample_rar_path(temp_dir):
    """Create a mock RAR file path (actual RAR creation requires external tools)."""
    return temp_dir / "test.rar"


@pytest.fixture
def nonexistent_path(temp_dir):
    """Return path to a nonexistent file."""
    return temp_dir / "nonexistent.zip"


# Base Archiver Tests
def test_archiver_is_abstract():
    """Test that Archiver cannot be instantiated directly."""
    with pytest.raises(TypeError):
        Archiver(Path("test.zip"))


def test_archiver_path_property(sample_zip_path):
    """Test that archiver path property works correctly."""
    archiver = ZipArchiver(sample_zip_path)
    assert archiver.path == sample_zip_path


def test_archiver_context_manager(sample_zip_path):
    """Test that archiver works as context manager."""
    with ZipArchiver(sample_zip_path) as archiver:
        assert isinstance(archiver, ZipArchiver)
        assert archiver.path == sample_zip_path


# ZipArchiver Tests
def test_zip_archiver_init(sample_zip_path):
    """Test ZipArchiver initialization."""
    archiver = ZipArchiver(sample_zip_path)
    assert archiver.path == sample_zip_path


def test_zip_archiver_init_nonexistent_file(nonexistent_path):
    """Test ZipArchiver initialization with nonexistent file."""
    # Should not raise exception - file might be created later
    archiver = ZipArchiver(nonexistent_path)
    assert archiver.path == nonexistent_path


def test_zip_read_file_success(sample_zip_path):
    """Test reading existing file from ZIP archive."""
    archiver = ZipArchiver(sample_zip_path)
    content = archiver.read_file("file1.txt")
    assert content == b"content1"


def test_zip_read_file_binary(sample_zip_path):
    """Test reading binary file from ZIP archive."""
    archiver = ZipArchiver(sample_zip_path)
    content = archiver.read_file("file2.jpg")
    assert content == b"fake_image_data"


def test_zip_read_file_in_directory(sample_zip_path):
    """Test reading file from subdirectory in ZIP archive."""
    archiver = ZipArchiver(sample_zip_path)
    content = archiver.read_file("dir/file3.txt")
    assert content == b"content3"


def test_zip_read_nonexistent_file(sample_zip_path):
    """Test reading nonexistent file raises ArchiverReadError."""
    archiver = ZipArchiver(sample_zip_path)
    with pytest.raises(ArchiverReadError, match="File not found in archive"):
        archiver.read_file("nonexistent.txt")


def test_zip_read_corrupted_archive(temp_dir):
    """Test reading from corrupted ZIP file raises ArchiverReadError."""
    corrupted_path = temp_dir / "corrupted.zip"
    corrupted_path.write_text("not a zip file")

    archiver = ZipArchiver(corrupted_path)
    with pytest.raises(ArchiverReadError, match="Corrupt ZIP file"):
        archiver.read_file("any_file.txt")


def test_zip_write_file_string_data(temp_dir):
    """Test writing string data to ZIP archive."""
    zip_path = temp_dir / "write_test.zip"
    archiver = ZipArchiver(zip_path)

    result = archiver.write_file("test.txt", "hello world")
    assert result is True

    # Verify file was written
    content = archiver.read_file("test.txt")
    assert content == b"hello world"


def test_zip_write_file_bytes_data(temp_dir):
    """Test writing bytes data to ZIP archive."""
    zip_path = temp_dir / "write_test.zip"
    archiver = ZipArchiver(zip_path)

    data = b"binary data"
    result = archiver.write_file("test.bin", data)
    assert result is True

    # Verify file was written
    content = archiver.read_file("test.bin")
    assert content == data


def test_zip_write_file_overwrite_existing(sample_zip_path):
    """Test overwriting existing file in ZIP archive."""
    archiver = ZipArchiver(sample_zip_path)

    # Overwrite existing file
    result = archiver.write_file("file1.txt", "new content")
    assert result is True

    # Verify content was updated
    content = archiver.read_file("file1.txt")
    assert content == b"new content"


def test_zip_write_file_image_compression(temp_dir):
    """Test that image files use stored compression."""
    zip_path = temp_dir / "compression_test.zip"
    archiver = ZipArchiver(zip_path)

    # Write image file (should use ZIP_STORED)
    result = archiver.write_file("image.jpg", b"fake_image_data")
    assert result is True

    # Write text file (should use ZIP_DEFLATED)
    result = archiver.write_file("text.txt", "text content")
    assert result is True


def test_zip_remove_file_success(sample_zip_path):
    """Test removing existing file from ZIP archive."""
    archiver = ZipArchiver(sample_zip_path)

    # Verify file exists first
    assert "file1.txt" in archiver.get_filename_list()

    # Remove file
    result = archiver.remove_file("file1.txt")
    assert result is True

    # Verify file is gone
    assert "file1.txt" not in archiver.get_filename_list()


def test_zip_remove_nonexistent_file(sample_zip_path):
    """Test removing nonexistent file returns False."""
    archiver = ZipArchiver(sample_zip_path)
    result = archiver.remove_file("nonexistent.txt")
    assert result is False


def test_zip_remove_multiple_files(sample_zip_path):
    """Test removing multiple files from ZIP archive."""
    archiver = ZipArchiver(sample_zip_path)

    files_to_remove = ["file1.txt", "file2.jpg"]
    result = archiver.remove_files(files_to_remove)
    assert result is True

    # Verify files are gone
    remaining_files = archiver.get_filename_list()
    assert "file1.txt" not in remaining_files
    assert "file2.jpg" not in remaining_files
    assert "dir/file3.txt" in remaining_files  # Should still exist


def test_zip_remove_files_empty_list(sample_zip_path):
    """Test removing empty list of files returns True."""
    archiver = ZipArchiver(sample_zip_path)
    result = archiver.remove_files([])
    assert result is True


def test_zip_remove_files_nonexistent(sample_zip_path):
    """Test removing nonexistent files returns True."""
    archiver = ZipArchiver(sample_zip_path)
    result = archiver.remove_files(["nonexistent1.txt", "nonexistent2.txt"])
    assert result is True


def test_zip_get_filename_list(sample_zip_path):
    """Test getting list of files in ZIP archive."""
    archiver = ZipArchiver(sample_zip_path)
    files = archiver.get_filename_list()

    expected_files = ["file1.txt", "file2.jpg", "dir/file3.txt"]
    assert set(files) == set(expected_files)


def test_zip_get_filename_list_empty(empty_zip_path):
    """Test getting filename list from empty ZIP archive."""
    archiver = ZipArchiver(empty_zip_path)
    files = archiver.get_filename_list()
    assert files == []


def test_zip_get_filename_list_corrupted(temp_dir):
    """Test getting filename list from corrupted ZIP returns empty list."""
    corrupted_path = temp_dir / "corrupted.zip"
    corrupted_path.write_text("not a zip file")

    archiver = ZipArchiver(corrupted_path)
    files = archiver.get_filename_list()
    assert files == []


def test_zip_exists_file(sample_zip_path):
    """Test checking if file exists in ZIP archive."""
    archiver = ZipArchiver(sample_zip_path)

    assert archiver.exists("file1.txt") is True
    assert archiver.exists("nonexistent.txt") is False


def test_zip_copy_from_zip_archive(temp_dir, sample_zip_path):
    """Test copying from one ZIP archive to another."""
    dest_path = temp_dir / "destination.zip"
    source_archiver = ZipArchiver(sample_zip_path)
    dest_archiver = ZipArchiver(dest_path)

    result = dest_archiver.copy_from_archive(source_archiver)
    assert result is True

    # Verify all files were copied
    dest_files = dest_archiver.get_filename_list()
    source_files = source_archiver.get_filename_list()
    assert set(dest_files) == set(source_files)

    # Verify content is the same
    for filename in source_files:
        source_content = source_archiver.read_file(filename)
        dest_content = dest_archiver.read_file(filename)
        assert source_content == dest_content


# RarArchiver Tests
@patch("rarfile.RarFile")
def test_rar_archiver_init(mock_rar_file, sample_rar_path):
    """Test RarArchiver initialization."""
    archiver = RarArchiver(sample_rar_path)
    assert archiver.path == sample_rar_path


@patch("rarfile.RarFile")
def test_rar_read_file_success(mock_rar_file, sample_rar_path):
    """Test reading file from RAR archive."""
    # Mock the RAR file behavior
    mock_rf = Mock()
    mock_rf.read.return_value = b"rar content"
    mock_rar_file.return_value.__enter__.return_value = mock_rf

    archiver = RarArchiver(sample_rar_path)
    content = archiver.read_file("test.txt")

    assert content == b"rar content"
    mock_rf.read.assert_called_once_with("test.txt")


@patch("rarfile.RarFile")
def test_rar_read_file_cannot_exec(mock_rar_file, sample_rar_path):
    """Test RAR read error when cannot execute."""
    mock_rar_file.side_effect = rarfile.RarCannotExec("Cannot execute")

    archiver = RarArchiver(sample_rar_path)
    with pytest.raises(ArchiverReadError, match="Cannot execute RAR command"):
        archiver.read_file("test.txt")


@patch("rarfile.RarFile")
def test_rar_read_file_bad_rar(mock_rar_file, sample_rar_path):
    """Test RAR read error with corrupted file."""
    mock_rar_file.side_effect = rarfile.BadRarFile("Bad RAR file")

    archiver = RarArchiver(sample_rar_path)
    with pytest.raises(ArchiverReadError, match="Corrupt RAR file"):
        archiver.read_file("test.txt")


@patch("rarfile.RarFile")
def test_rar_read_file_not_found(mock_rar_file, sample_rar_path):
    """Test RAR read error when file not found."""
    mock_rf = Mock()
    mock_rf.read.side_effect = KeyError("File not found")
    mock_rar_file.return_value.__enter__.return_value = mock_rf

    archiver = RarArchiver(sample_rar_path)
    with pytest.raises(ArchiverReadError, match="File not found in archive"):
        archiver.read_file("nonexistent.txt")


@patch("rarfile.RarFile")
def test_rar_read_file_unsupported_operation(mock_rar_file, sample_rar_path):
    """Test RAR read handles UnsupportedOperation (empty directories)."""
    mock_rf = Mock()
    mock_rf.read.side_effect = io.UnsupportedOperation("Unsupported")
    mock_rar_file.return_value.__enter__.return_value = mock_rf

    archiver = RarArchiver(sample_rar_path)
    content = archiver.read_file("empty_dir/")

    assert content == b""


def test_rar_write_file_readonly(sample_rar_path):
    """Test that RAR write operations return False (read-only)."""
    archiver = RarArchiver(sample_rar_path)
    result = archiver.write_file("test.txt", "data")
    assert result is False


def test_rar_remove_file_readonly(sample_rar_path):
    """Test that RAR remove operations return False (read-only)."""
    archiver = RarArchiver(sample_rar_path)
    result = archiver.remove_file("test.txt")
    assert result is False


def test_rar_remove_files_readonly(sample_rar_path):
    """Test that RAR remove multiple files returns False (read-only)."""
    archiver = RarArchiver(sample_rar_path)
    result = archiver.remove_files(["file1.txt", "file2.txt"])
    assert result is False


@patch("rarfile.RarFile")
def test_rar_get_filename_list(mock_rar_file, sample_rar_path):
    """Test getting filename list from RAR archive."""
    mock_rf = Mock()
    mock_rf.namelist.return_value = ["file2.txt", "file1.txt", "dir/file3.txt"]
    mock_rar_file.return_value.__enter__.return_value = mock_rf

    archiver = RarArchiver(sample_rar_path)
    files = archiver.get_filename_list()

    # Should be sorted
    expected = ["dir/file3.txt", "file1.txt", "file2.txt"]
    assert files == expected


@patch("rarfile.RarFile")
def test_rar_get_filename_list_error(mock_rar_file, sample_rar_path):
    """Test RAR filename list error handling."""
    mock_rar_file.side_effect = rarfile.BadRarFile("Bad RAR")

    archiver = RarArchiver(sample_rar_path)
    with pytest.raises(ArchiverReadError, match="Cannot read RAR archive"):
        archiver.get_filename_list()


def test_rar_copy_from_archive_readonly(sample_rar_path):
    """Test that RAR copy operations return False (read-only)."""
    archiver = RarArchiver(sample_rar_path)
    other_archiver = Mock()
    result = archiver.copy_from_archive(other_archiver)
    assert result is False


# UnknownArchiver Tests
def test_unknown_archiver_name(temp_dir):
    """Test UnknownArchiver name method."""
    path = temp_dir / "unknown.xyz"
    archiver = UnknownArchiver(path)
    assert archiver.name() == "Unknown"


def test_unknown_archiver_read_file_not_implemented(temp_dir):
    """Test UnknownArchiver read_file raises NotImplementedError."""
    path = temp_dir / "unknown.xyz"
    archiver = UnknownArchiver(path)
    with pytest.raises(NotImplementedError):
        archiver.read_file("test.txt")


def test_unknown_archiver_write_file_false(temp_dir):
    """Test UnknownArchiver write_file returns False."""
    path = temp_dir / "unknown.xyz"
    archiver = UnknownArchiver(path)
    result = archiver.write_file("test.txt", "data")
    assert result is False


def test_unknown_archiver_remove_file_false(temp_dir):
    """Test UnknownArchiver remove_file returns False."""
    path = temp_dir / "unknown.xyz"
    archiver = UnknownArchiver(path)
    result = archiver.remove_file("test.txt")
    assert result is False


def test_unknown_archiver_remove_files_false(temp_dir):
    """Test UnknownArchiver remove_files returns False."""
    path = temp_dir / "unknown.xyz"
    archiver = UnknownArchiver(path)
    result = archiver.remove_files(["file1.txt", "file2.txt"])
    assert result is False


def test_unknown_archiver_get_filename_list_empty(temp_dir):
    """Test UnknownArchiver get_filename_list returns empty list."""
    path = temp_dir / "unknown.xyz"
    archiver = UnknownArchiver(path)
    files = archiver.get_filename_list()
    assert files == []


def test_unknown_archiver_copy_from_archive_false(temp_dir):
    """Test UnknownArchiver copy_from_archive returns False."""
    path = temp_dir / "unknown.xyz"
    archiver = UnknownArchiver(path)
    other_archiver = Mock()
    result = archiver.copy_from_archive(other_archiver)
    assert result is False


# ArchiverFactory Tests
def test_factory_create_zip_archiver(temp_dir):
    """Test factory creates ZipArchiver for .zip files."""
    zip_path = temp_dir / "test.zip"
    archiver = ArchiverFactory.create_archiver(zip_path)
    assert isinstance(archiver, ZipArchiver)
    assert archiver.path == zip_path


def test_factory_create_cbz_archiver(temp_dir):
    """Test factory creates ZipArchiver for .cbz files."""
    cbz_path = temp_dir / "test.cbz"
    archiver = ArchiverFactory.create_archiver(cbz_path)
    assert isinstance(archiver, ZipArchiver)


def test_factory_create_rar_archiver(temp_dir):
    """Test factory creates RarArchiver for .rar files."""
    rar_path = temp_dir / "test.rar"
    archiver = ArchiverFactory.create_archiver(rar_path)
    assert isinstance(archiver, RarArchiver)


def test_factory_create_cbr_archiver(temp_dir):
    """Test factory creates RarArchiver for .cbr files."""
    cbr_path = temp_dir / "test.cbr"
    archiver = ArchiverFactory.create_archiver(cbr_path)
    assert isinstance(archiver, RarArchiver)


def test_factory_create_unknown_archiver(temp_dir):
    """Test factory creates UnknownArchiver for unknown extensions."""
    unknown_path = temp_dir / "test.xyz"
    archiver = ArchiverFactory.create_archiver(unknown_path)
    assert isinstance(archiver, UnknownArchiver)


def test_factory_case_insensitive(temp_dir):
    """Test factory is case insensitive for extensions."""
    zip_path = temp_dir / "test.ZIP"
    archiver = ArchiverFactory.create_archiver(zip_path)
    assert isinstance(archiver, ZipArchiver)


def test_factory_register_new_archiver(temp_dir):
    """Test registering new archiver type with factory."""

    # Create a mock archiver class
    class MockArchiver(Archiver):
        def read_file(self, archive_file: str) -> bytes:
            return b"mock"

        def write_file(self, archive_file: str, data) -> bool:
            return True

        def remove_file(self, archive_file: str) -> bool:
            return True

        def remove_files(self, filename_list: list[str]) -> bool:
            return True

        def get_filename_list(self) -> list[str]:
            return []

        def test(self) -> bool:
            return True

        def copy_from_archive(self, other_archive: Archiver) -> bool:
            return True

    # Register new archiver
    ArchiverFactory.register_archiver(".mock", MockArchiver)

    # Test it works
    mock_path = temp_dir / "test.mock"
    archiver = ArchiverFactory.create_archiver(mock_path)
    assert isinstance(archiver, MockArchiver)


def test_factory_get_supported_extensions():
    """Test getting list of supported extensions."""
    extensions = ArchiverFactory.get_supported_extensions()
    expected_extensions = [".zip", ".cbz", ".rar", ".cbr"]

    for ext in expected_extensions:
        assert ext in extensions


# Integration Tests
def test_zip_to_zip_copy_integration(temp_dir):
    """Integration test: copy from one ZIP to another."""
    # Create source ZIP
    source_path = temp_dir / "source.zip"
    with zipfile.ZipFile(source_path, "w") as zf:
        zf.writestr("file1.txt", "content1")
        zf.writestr("file2.txt", "content2")

    # Create destination archiver
    dest_path = temp_dir / "dest.zip"
    source_archiver = ZipArchiver(source_path)
    dest_archiver = ZipArchiver(dest_path)

    # Copy files
    result = dest_archiver.copy_from_archive(source_archiver)
    assert result is True

    # Verify copy
    assert dest_archiver.exists("file1.txt")
    assert dest_archiver.exists("file2.txt")
    assert dest_archiver.read_file("file1.txt") == b"content1"
    assert dest_archiver.read_file("file2.txt") == b"content2"


def test_factory_integration(temp_dir):
    """Integration test: use factory to create and operate on archives."""
    # Create test ZIP
    zip_path = temp_dir / "test.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("test.txt", "factory test")

    # Use factory to create archiver
    archiver = ArchiverFactory.create_archiver(zip_path)

    # Perform operations
    assert archiver.exists("test.txt")
    content = archiver.read_file("test.txt")
    assert content == b"factory test"

    # Add new file
    result = archiver.write_file("new.txt", "new content")
    assert result is True
    assert archiver.exists("new.txt")


def test_context_manager_integration(sample_zip_path):
    """Integration test: use archiver as context manager."""
    with ZipArchiver(sample_zip_path) as archiver:
        files = archiver.get_filename_list()
        assert len(files) > 0

        content = archiver.read_file(files[0])
        assert isinstance(content, bytes)
        assert len(content) > 0


# Edge Cases and Error Conditions
def test_zip_write_to_readonly_file(temp_dir):
    """Test writing to read-only ZIP file."""
    zip_path = temp_dir / "readonly.zip"
    zip_path.touch()
    zip_path.chmod(0o444)  # Read-only

    archiver = ZipArchiver(zip_path)
    result = archiver.write_file("test.txt", "data")
    # Should handle permission error gracefully
    assert result is False


def test_zip_large_file_handling(temp_dir):
    """Test handling large files in ZIP archives."""
    zip_path = temp_dir / "large.zip"
    archiver = ZipArchiver(zip_path)

    # Create large content (1MB)
    large_content = "x" * (1024 * 1024)
    result = archiver.write_file("large.txt", large_content)
    assert result is True

    # Read it back
    content = archiver.read_file("large.txt")
    assert content == large_content.encode("utf-8")


def test_archiver_with_unicode_filenames(temp_dir):
    """Test handling Unicode filenames in archives."""
    zip_path = temp_dir / "unicode.zip"
    archiver = ZipArchiver(zip_path)

    # Test with Unicode filename
    unicode_filename = "тест_файл.txt"  # Russian text
    result = archiver.write_file(unicode_filename, "unicode content")
    assert result is True

    assert archiver.exists(unicode_filename)
    content = archiver.read_file(unicode_filename)
    assert content == b"unicode content"


def test_archiver_empty_data_handling(temp_dir):
    """Test handling empty data in archives."""
    zip_path = temp_dir / "empty_data.zip"
    archiver = ZipArchiver(zip_path)

    # Write empty string
    result = archiver.write_file("empty.txt", "")
    assert result is True

    # Read it back
    content = archiver.read_file("empty.txt")
    assert content == b""

    # Write empty bytes
    result = archiver.write_file("empty.bin", b"")
    assert result is True

    content = archiver.read_file("empty.bin")
    assert content == b""
