from pathlib import Path

import pytest

from darkseid.archivers.archiver import Archiver


@pytest.fixture()
def archiver():
    return Archiver(Path("/fake/path"))


def test_init():
    # Arrange
    path = Path("/fake/path")

    # Act
    archiver = Archiver(path)

    # Assert
    assert archiver.path == path


@pytest.mark.parametrize(
    ("archive_file", "expected_exception"),
    [
        ("file1.txt", NotImplementedError),
        ("file2.txt", NotImplementedError),
    ],
    ids=["file1.txt", "file2.txt"],
)
def test_read_file(archiver, archive_file, expected_exception):
    # Act & Assert
    with pytest.raises(expected_exception):
        archiver.read_file(archive_file)


@pytest.mark.parametrize(
    ("archive_file", "data", "expected_result"),
    [
        ("file1.txt", "data1", False),
        ("file2.txt", "data2", False),
    ],
    ids=["file1.txt_data1", "file2.txt_data2"],
)
def test_write_file(archiver, archive_file, data, expected_result):
    # Act
    result = archiver.write_file(archive_file, data)

    # Assert
    assert result == expected_result


@pytest.mark.parametrize(
    ("archive_file", "expected_result"),
    [("file1.txt", False), ("file2.txt", False)],
    ids=["file1.txt", "file2.txt"],
)
def test_remove_file(archiver, archive_file, expected_result):
    # Act
    result = archiver.remove_file(archive_file)

    # Assert
    assert result == expected_result


@pytest.mark.parametrize(
    ("filename_lst", "expected_result"),
    [(["file1.txt", "file2.txt"], False), (["file3.txt"], False)],
    ids=["multiple_files", "single_file"],
)
def test_remove_files(archiver, filename_lst, expected_result):
    # Act
    result = archiver.remove_files(filename_lst)

    # Assert
    assert result == expected_result


def test_get_filename_list(archiver):
    # Act
    result = archiver.get_filename_list()

    # Assert
    assert result == []


@pytest.mark.parametrize(
    ("other_archive", "expected_result"),
    [(Archiver(Path("/other/path")), False)],
    ids=["other_archive"],
)
def test_copy_from_archive(archiver, other_archive, expected_result):
    # Act
    result = archiver.copy_from_archive(other_archive)

    # Assert
    assert result == expected_result


@pytest.mark.parametrize(
    ("input_path", "expected_path"),
    [
        (Path("/home/bpepple/test1"), Path("/home/bpepple/test1")),
        (Path("/home/bpepple/test2"), Path("/home/bpepple/test2")),
        (Path("/home/bpepple/test3"), Path("/home/bpepple/test3")),
        (Path(), Path()),  # edge case: empty path
        (Path("/"), Path("/")),  # edge case: root path
    ],
    ids=[
        "happy_path_test1",
        "happy_path_test2",
        "happy_path_test3",
        "edge_case_empty_path",
        "edge_case_root_path",
    ],
)
def test_archiver_path(input_path, expected_path):
    # Arrange
    archiver = Archiver(input_path)

    # Act
    result = archiver.path

    # Assert
    assert result == expected_path
