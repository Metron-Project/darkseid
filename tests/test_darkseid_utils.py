from pathlib import Path

from darkseid import utils


def test_remove_articles():
    txt = "The Champions & Inhumans"
    expected_result = "Champions Inhumans"
    result = utils.remove_articles(txt)
    assert result == expected_result


def test_removes_articles_that_contain_no_articles():
    txt = "Justice League"
    expected_result = "Justice League"
    result = utils.remove_articles(txt)
    assert result == expected_result


def test_list_to_string():
    thislist = ["apple", "banana", "cherry"]
    expected_result = "apple; banana; cherry"

    result = utils.list_to_string(thislist)
    assert result == expected_result


def test_unique_name(tmp_path):
    d = tmp_path / "test"
    d.mkdir()
    new_file = d / "Test.cbz"
    new_file.write_text("Blah")
    result = utils.unique_file(new_file)
    expected_result = Path(new_file.parent / f"{new_file.stem} (1){new_file.suffix}")

    assert result == expected_result


def test_recursive_list_with_file(tmp_path):
    temp_file = tmp_path / "test.cbz"
    expected_result = [temp_file]
    file_list = [temp_file]
    result = utils.get_recursive_filelist(file_list)

    assert result == expected_result


def test_recursive_list_with_directory(tmp_path):
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
