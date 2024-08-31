import tempfile
from pathlib import Path

import pytest

from darkseid.archivers.zip import ZipArchiver


@pytest.fixture()
def temp_zip_file():
    with tempfile.NamedTemporaryFile(suffix=".cbz", delete=False) as tmp:
        yield Path(tmp.name)
    tmp.close()
    Path(tmp.name).unlink(missing_ok=True)


@pytest.fixture()
def zip_archiver(temp_zip_file):
    return ZipArchiver(temp_zip_file)


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


@pytest.mark.parametrize(
    ("other_archive_files", "data"), [(["test.txt"], ["Hello, World!"])], ids=["simple_copy"]
)
def test_copy_from_archive(zip_archiver, other_archive_files, data):
    # Arrange
    other_archive = ZipArchiver(Path(tempfile.NamedTemporaryFile(suffix=".cbz", delete=False).name))
    for file, content in zip(other_archive_files, data, strict=False):
        other_archive.write_file(file, content)

    # Act
    result = zip_archiver.copy_from_archive(other_archive)

    # Assert
    assert result is True
    for file in other_archive_files:
        assert file in zip_archiver.get_filename_list()
        assert zip_archiver.read_file(file).decode() == content
