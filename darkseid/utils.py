"""Some generic utilities."""
# Copyright 2012-2014 Anthony Beville
# Copyright 2019 Brian Pepple

import itertools
import re
from collections import defaultdict
from enum import StrEnum
from pathlib import Path


class DataSources(StrEnum):
    COMIC_VINE = "Comic Vine"
    METRON = "Metron"
    GCD = "Grand Comics Database"


def get_issue_id_from_note(note_txt: str) -> dict[str, str] | None:
    """
    Extracts the issue ID from a given note text based on specific keywords and formats.
    This function identifies the source of the issue ID and returns it along with the ID itself.

    Args:
        note_txt (str): The text from which to extract the issue ID.

    Returns:
        dict[str, str] | None: A dictionary containing the source and the issue ID if found,
        otherwise None.
    """

    if not note_txt:
        return None

    note_lower = note_txt.lower()
    source_map = {
        "comic vine": DataSources.COMIC_VINE,
        "metron": DataSources.METRON,
        "grand comics database": DataSources.GCD,
    }

    if "comictagger" in note_lower:
        if match := re.search(r"(issue id (\d+))|(cvdb(\d+))", note_lower):
            for website, src_enum in source_map.items():
                if website in note_lower:
                    return {"source": src_enum, "id": match[2] or match[4]}
    elif "metrontagger" in note_lower:
        if match := re.search(r"issue_id:(\d+)", note_lower):
            return {"source": DataSources.METRON, "id": match[1]}

    return None


def cast_id_as_str(id_: str | int) -> str:
    """Convert an ID to a string.

    This function takes an ID that can be either a string or an integer and returns it as a string. If the input is
    an integer, it will be converted to a string; if it is already a string, it will be returned unchanged.

    Args:
        id_ (str | int): The ID to be converted.

    Returns:
        str: The ID represented as a string.
    """
    return str(id_) if isinstance(id_, int) else id_


def get_recursive_filelist(path_list: list[Path]) -> list[Path]:
    """
    Retrieves a list of files recursively from the provided paths.

    Args:
        path_list (list[Path]): List of paths to search for files.

    Returns:
        list[Path]: A sorted list of files found in the provided paths.
    """

    filelist: list[Path] = []
    for path_str in path_list:
        path = Path(path_str)
        if path.is_dir():
            for comic_format in ["*.cbz", "*.cbr"]:
                filelist.extend(iter(path.rglob(comic_format)))
        else:
            filelist.append(path)

    return sorted(filelist)


def list_to_string(list_of_strings: list[str]) -> str:
    """
    Converts a list of strings into a single comma-separated string.

    Args:
        list_of_strings (list[str]): The list of strings to convert.

    Returns:
        str: The comma-separated string.
    """

    return ", ".join((f'"{item}"' if "," in item else item) for item in list_of_strings)


def remove_articles(text: str) -> str:
    """
    Removes common articles from the input text.

    Args:
        text (str): The text from which articles are to be removed.

    Returns:
        str: The text with articles removed.
    """

    articles = frozenset(
        {
            "&",
            "a",
            "am",
            "an",
            "and",
            "as",
            "at",
            "be",
            "but",
            "by",
            "for",
            "if",
            "is",
            "issue",
            "it",
            "it's",
            "its",
            "itself",
            "of",
            "or",
            "so",
            "the",
            "with",
        }
    )
    new_text = "".join(f"{word} " for word in text.split(" ") if word.casefold() not in articles)

    return new_text[:-1]


def unique_file(file_name: Path) -> Path:
    """
    Generates a unique file name by appending a number in parentheses if the original file name already exists.

    Args:
        file_name (Path): The original file name to make unique.

    Returns:
        Path: The unique file name.
    """

    original_stem = file_name.stem
    for i in itertools.count(1):  # noqa: RET503
        if not file_name.exists():
            return file_name
        file_name = file_name.parent / f"{original_stem} ({i}){file_name.suffix}"


def xlate(data: int | str | None, is_int: bool = False) -> int | str | None:
    """
    Translates data to an integer or string based on the provided flag.

    Args:
        data (int | str | None): The data to translate.
        is_int (bool): A flag indicating whether to translate to an integer.

    Returns:
        int | str | None: The translated data.
    """

    if data is None or data == "":
        return None
    if is_int:
        i = str(data).translate(
            defaultdict(
                lambda: None,
                zip((ord(c) for c in "1234567890"), "1234567890", strict=False),
            ),
        )
        if i == "0":
            return "0"
        return int(i) if i else None
    return str(data)
