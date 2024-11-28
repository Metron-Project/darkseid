from pathlib import Path

import pytest

from darkseid import utils
from darkseid.utils import get_issue_id_from_note, DataSources


@pytest.mark.parametrize(
    "note_txt, expected",
    [
        # Happy path tests
        (
            "Tagged with ComicTagger 1.6.0b3.dev0 using info from Comic Vine on 2024-11-26 10:44:04. [Issue ID 806681]",
            {"source": DataSources.COMIC_VINE, "id": "806681"},
        ),
        (
            "Tagged with the ninjas.walk.alone fork of ComicTagger 1.3.5 using info from Comic Vine on "
            "2023-05-09 22:26:42.  [CVDB806681]",
            {"source": DataSources.COMIC_VINE, "id": "806681"},
        ),
        (
            "Tagged with ComicTagger 1.6.0b3.dev0 using info from Grand Comics Database on "
            "2024-11-26 10:44:04. [Issue ID 806681]",
            {"source": DataSources.GCD, "id": "806681"},
        ),
        (
            "Tagged with MetronTagger-2.3.0 using info from Metron on 2024-06-22 20:32:47. [issue_id:48013]",
            {"source": DataSources.METRON, "id": "48013"},
        ),
        # Edge cases
        ("", None),
        ("ComicTagger issue id 0000 Comic Vine", {"source": DataSources.COMIC_VINE, "id": "0000"}),
        ("ComicTagger issue id 1234", None),
        ("MetronTagger issue_id:", None),
        # Error cases
        ("Random text with no issue id", None),
        ("ComicTagger issue id abc Comic Vine", None),
        ("MetronTagger issue_id:abc", None),
    ],
    ids=[
        "comic_vine_issue_id",
        "comic_vine_cvdb",
        "gcd_issue_id",
        "metrontagger_issue_id",
        "zero_issue_id",
        "empty_note",
        "missing_source",
        "missing_id_after_colon",
        "no_issue_id",
        "non_numeric_issue_id",
        "non_numeric_metron_id",
    ],
)
def test_get_issue_id_from_note(note_txt, expected):
    # Act
    result = get_issue_id_from_note(note_txt)

    # Assert
    assert result == expected


test_articles = [
    pytest.param("The Champions & Inhumans", "Test string with '&'", "Champions Inhumans"),
    pytest.param("Justice League", "Test string with no articles", "Justice League"),
    pytest.param("The X-Men", "Test string with leading 'The'", "X-Men"),
]


@pytest.mark.parametrize(("test_string", "reason", "expected"), test_articles)
def test_file_name_for_articles(
    test_string: str,
    reason: str,  # noqa: ARG001
    expected: str,
) -> None:
    result = utils.remove_articles(test_string)

    assert result == expected


test_string_lists = [
    pytest.param(["apple", "banana", "cherry"], "Normal string list", "apple, banana, cherry"),
    pytest.param(
        ["Outsiders", "Infinity, Inc.", "Teen Titans"],
        "String list with comma value",
        'Outsiders, "Infinity, Inc.", Teen Titans',
    ),
]


@pytest.mark.parametrize(("test_list", "reason", "expected"), test_string_lists)
def test_list_to_string(test_list: list[str], reason: str, expected: str) -> None:  # noqa: ARG001
    result = utils.list_to_string(test_list)
    assert result == expected


def test_unique_name(tmp_path: Path) -> None:
    d = tmp_path / "test"
    d.mkdir()
    new_file = d / "Test.cbz"
    new_file.write_text("Blah")
    result = utils.unique_file(new_file)
    expected_result = Path(new_file.parent / f"{new_file.stem} (1){new_file.suffix}")

    assert result == expected_result


def test_recursive_list_with_file(tmp_path: Path) -> None:
    temp_file = tmp_path / "test.cbz"
    temp_file.write_text("foo")
    temp_cbr = tmp_path / "fugazi.cbr"
    temp_cbr.write_text("You are not what you own")
    # The following file should be *excluded* from results
    temp_txt = tmp_path / "fail.txt"
    temp_txt.write_text("yikes")

    expected_result = [temp_cbr, temp_file]
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
