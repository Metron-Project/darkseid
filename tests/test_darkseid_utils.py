from pathlib import Path

import pytest

from darkseid import utils

from .test_params import test_articles


@pytest.mark.parametrize("test_string,reason,expected", test_articles)
def test_file_name_for_articles(test_string: str, reason: str, expected: str) -> None:
    result = utils.remove_articles(test_string)

    assert result == expected


def test_list_to_string() -> None:
    thislist = ["apple", "banana", "cherry"]
    expected_result = "apple; banana; cherry"

    result = utils.list_to_string(thislist)
    assert result == expected_result


def test_unique_name(tmp_path: Path) -> None:
    d = tmp_path / "test"
    d.mkdir()
    new_file = d / "Test.cbz"
    new_file.write_text("Blah")
    result = utils.unique_file(new_file)
    expected_result = Path(new_file.parent / f"{new_file.stem} (1){new_file.suffix}")

    assert result == expected_result


def test_recursive_list_with_file(tmp_path: Path) -> None:
    temp_cb7 = tmp_path / "foo.cb7"
    temp_cb7.write_text("blah")
    temp_file = tmp_path / "test.cbz"
    temp_file.write_text("foo")
    # The following file should be *excluded* from results
    temp_txt = tmp_path / "fail.txt"
    temp_txt.write_text("yikes")

    expected_result = [temp_cb7, temp_file]
    result = utils.get_recursive_filelist([tmp_path])

    assert result == expected_result


def test_recursive_list_with_directory(tmp_path: Path) -> None:
    temp_dir = tmp_path / "recursive"
    temp_dir.mkdir()

    # Not really zip files, but we really only care about the file extension
    temp_file_1 = temp_dir / "test-1.cbz"
    temp_file_1.write_text("content")

    temp_file_2 = temp_dir / "test-2.cbz"
    temp_file_2.write_text("content")

    expected_result = [temp_file_2, temp_file_1]
    expected_result = sorted(expected_result)

    file_list = [temp_dir]
    result = utils.get_recursive_filelist(file_list)

    assert result == expected_result
