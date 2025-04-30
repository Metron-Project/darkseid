import tempfile
from pathlib import Path
from unittest.mock import Mock
from zipfile import ZIP_DEFLATED, ZIP_STORED, BadZipfile, ZipFile

import pytest
from rarfile import BadRarFile

from darkseid.archivers.archiver import Archiver
from darkseid.archivers.zip import ZipArchiver


@pytest.fixture
def temp_zip_file():
    with tempfile.NamedTemporaryFile(suffix=".cbz", delete=False) as tmp:
        yield Path(tmp.name)
    tmp.close()
    Path(tmp.name).unlink(missing_ok=True)


@pytest.fixture
def zip_archiver(temp_zip_file):
    return ZipArchiver(temp_zip_file)


@pytest.mark.parametrize(
    ("filenames", "contents", "expected_compression_types"),
    [
        (
            ["text_file.txt"],
            [b"This is a text file."],
            [ZIP_DEFLATED],
        ),
        (
            ["image.jpg", "text_file.txt", "data.bin"],
            [b"image data", b"This is a text file.", b"binary data"],
            [ZIP_STORED, ZIP_DEFLATED, ZIP_DEFLATED],
        ),
        (
            ["empty.txt"],
            [b""],
            [ZIP_DEFLATED],
        ),
        (
            ["image1.png", "image2.jpeg"],
            [b"image1 data", b"image2 data"],
            [ZIP_STORED, ZIP_STORED],
        ),
    ],
    ids=["single", "multiple", "empty", "files_with_image_extensions"],
)
def test_copy_from_archive_happy_path(
    tmp_path: Path,
    filenames: list[str],
    contents: list[bytes],
    expected_compression_types: list[int],
):
    # Arrange
    other_archive_mock = Mock(spec=Archiver)
    other_archive_mock.get_filename_list.return_value = filenames
    other_archive_mock.read_file.side_effect = contents

    zip_archiver = ZipArchiver(tmp_path / "output.zip")

    # Act
    result = zip_archiver.copy_from_archive(other_archive_mock)

    # Assert
    assert result is True
    assert zip_archiver.path.exists()

    with ZipFile(zip_archiver.path, "r") as zout:
        assert zout.namelist() == filenames
        for i, filename in enumerate(filenames):
            with zout.open(filename) as f:
                assert f.read() == contents[i]
            info = zout.getinfo(filename)
            assert info.compress_type == expected_compression_types[i]


# Various edge cases.
@pytest.mark.parametrize(
    ("filenames", "contents"),
    [
        ([], []),
        (["file1.txt"], [None]),
    ],
    ids=["no_files", "None_data"],
)
def test_copy_from_archive_edge_cases(tmp_path: Path, filenames: list[str], contents: list[bytes]):
    # Arrange
    other_archive_mock = Mock(spec=Archiver)
    other_archive_mock.get_filename_list.return_value = filenames
    other_archive_mock.read_file.side_effect = contents
    zip_archiver = ZipArchiver(tmp_path / "output.zip")

    # Act
    result = zip_archiver.copy_from_archive(other_archive_mock)

    # Assert
    assert result is True
    assert zip_archiver.path.exists()

    with ZipFile(zip_archiver.path, "r") as zout:
        assert zout.namelist() == [
            f for f, c in zip(filenames, contents, strict=False) if c is not None
        ]


# Various error cases.
@pytest.mark.parametrize(
    ("filenames", "side_effect", "expected_log_message"),
    [
        (
            ["file1.txt"],
            BadZipfile("Bad ZIP file"),
            "Error while copying to",
        ),
        (
            ["file1.txt"],
            OSError("OS Error"),
            "Error while copying to",
        ),
        (
            ["file1.rar"],
            BadRarFile("Bad RAR file"),
            "",  # No log message expected for BadRarFile
        ),
    ],
    ids=["bad_zip_file", "os_error", "bad_rar_file"],
)
def test_copy_from_archive_error_cases(
    tmp_path: Path,
    filenames: list[str],
    side_effect: Exception,
    expected_log_message: str,
    caplog: pytest.LogCaptureFixture,
):
    # Arrange
    other_archive_mock = Mock(spec=Archiver)
    other_archive_mock.get_filename_list.return_value = filenames
    other_archive_mock.read_file.side_effect = side_effect
    zip_archiver = ZipArchiver(tmp_path / "output.zip")

    # Act
    result = zip_archiver.copy_from_archive(other_archive_mock)

    assert result is False
    assert zip_archiver.path.exists() is False  # File should not exist
    # Assert
    if id != "bad_rar_file":
        assert expected_log_message in caplog.text


@pytest.mark.parametrize(
    ("archive_file", "data"),
    [
        ("test.txt", "Hello, World!"),
        ("folder/test.txt", "Nested Hello!"),
        ("empty.txt", ""),
    ],
    ids=["simple_file", "nested_file", "empty_file"],
)
def test_write_file(zip_archiver, archive_file, data):
    # Act
    result = zip_archiver.write_file(archive_file, data)

    # Assert
    assert result is True
    assert archive_file in zip_archiver.get_filename_list()
    assert zip_archiver.read_file(archive_file).decode() == data


# TODO: Add a test for BadZipFile
@pytest.mark.parametrize(
    ("archive_file", "expected_exception"), [("nonexistent.zip", OSError)], ids=["nonexistent_file"]
)
def test_read_file_error(zip_archiver, archive_file, expected_exception):
    # Act & Assert
    with pytest.raises(expected_exception):
        zip_archiver.read_file(archive_file)


@pytest.mark.parametrize(
    ("archive_file", "data"), [("test.txt", "Hello, World!")], ids=["simple_file"]
)
def test_remove_file(zip_archiver, archive_file, data):
    # Arrange
    zip_archiver.write_file(archive_file, data)

    # Act
    result = zip_archiver.remove_file(archive_file)

    # Assert
    assert result is True
    assert archive_file not in zip_archiver.get_filename_list()


@pytest.mark.parametrize(
    ("filename_lst", "data"),
    [(["test1.txt", "test2.txt"], ["Hello, World!", "Another Hello!"])],
    ids=["multiple_files"],
)
def test_remove_files(zip_archiver, filename_lst, data):
    # Arrange
    for file, content in zip(filename_lst, data, strict=False):
        zip_archiver.write_file(file, content)

    # Act
    result = zip_archiver.remove_files(filename_lst)

    # Assert
    assert result is True
    for file in filename_lst:
        assert file not in zip_archiver.get_filename_list()


@pytest.mark.parametrize(
    ("archive_file", "data"), [("test.txt", "Hello, World!")], ids=["simple_file"]
)
def test_get_filename_list(zip_archiver, archive_file, data):
    # Arrange
    zip_archiver.write_file(archive_file, data)

    # Act
    filenames = zip_archiver.get_filename_list()

    # Assert
    assert archive_file in filenames


def test_read_file_key_error(tmp_path):
    # Arrange
    zip_path = tmp_path / "test.zip"
    with ZipFile(zip_path, "w") as zf:
        zf.writestr("existing_file.txt", b"test content")

    archiver = ZipArchiver(zip_path)

    # Act & Assert
    with pytest.raises(KeyError):
        archiver.read_file("non_existing_file.txt")
