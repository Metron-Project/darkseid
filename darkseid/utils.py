"""Some generic utilities."""
# Copyright 2012-2014 Anthony Beville
# Copyright 2019 Brian Pepple

import itertools
from collections import defaultdict
from pathlib import Path
from typing import Optional, Union  # Union type can be removed when Python3.9 support ends


def get_recursive_filelist(pathlist: list[Path]) -> list[Path]:
    """Returns a path list of comic archives.

    :param pathlist: A list of path objects
    :type pathlist:  list of Path
    """
    filelist: list[Path] = []
    for path_str in pathlist:
        path = Path(path_str)
        if path.is_dir():
            for comic_format in ["*.cbz", "*.cb7", "*.cbr"]:
                filelist.extend(iter(path.rglob(comic_format)))
        else:
            filelist.append(path)

    return sorted(filelist)


def list_to_string(list_of_strings: list[str]) -> str:
    """Function that takes a list of string and converts it to a string.
    For example: ["apple", "banana", "cherry"] is changed to "apple; banana; cherry".

    :param list_of_strings: A list of strings.
    :type list_of_strings: list of str
    """
    return "; ".join(map(str, list_of_strings))


def remove_articles(text: str) -> str:
    """Takes a string and removes any articles in it.

    :param str text: A string with articles (ex. 'and', 'a', 'the').
    """
    articles = {
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
    new_text = "".join(
        f"{word} " for word in text.split(" ") if word.casefold() not in articles
    )

    return new_text[:-1]


def unique_file(file_name: Path) -> Path:
    """Takes a filename and if one already exist with that name, returns a new filename.

    :param Path file_name: A path objects
    """
    original_stem = file_name.stem

    for i in itertools.count(1):
        if not file_name.exists():
            break
        file_name = file_name.parent / f"{original_stem} ({i}){file_name.suffix}"

    return file_name


def xlate(data: Optional[Union[int, str]], is_int: bool = False) -> Optional[Union[int, str]]:
    if data is None or data == "":
        return None
    if is_int:
        i = str(data).translate(
            defaultdict(lambda: None, zip((ord(c) for c in "1234567890"), "1234567890")),
        )
        if i == "0":
            return "0"
        return int(i) if i else None
    return str(data)
