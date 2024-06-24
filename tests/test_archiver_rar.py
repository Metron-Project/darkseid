import pytest

from darkseid.archivers.rar import RarArchiver


@pytest.fixture()
def rar_archiver(tmp_path):
    # Arrange
    rar_path = tmp_path / "test.rar"
    rar_path.touch()
    return RarArchiver(rar_path)


def test_remove_file(rar_archiver):
    # Act
    result = rar_archiver.remove_file("file.txt")

    # Assert
    assert result is False


def test_remove_files(rar_archiver):
    # Act
    result = rar_archiver.remove_files(["file1.txt", "file2.txt"])

    # Assert
    assert result is False


def test_write_file(rar_archiver):
    # Act
    result = rar_archiver.write_file("file.txt", "data")

    # Assert
    assert result is False


def test_copy_from_archive(rar_archiver):
    # Act
    result = rar_archiver.copy_from_archive(None)  # type: ignore

    # Assert
    assert result is False
