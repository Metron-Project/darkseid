"""Some generic utilities."""
# Copyright 2012-2014 Anthony Beville
# Copyright 2019 Brian Pepple

import itertools
from collections import defaultdict
from pathlib import Path


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
