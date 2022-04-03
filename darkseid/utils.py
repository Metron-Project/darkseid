"""Some generic utilities"""
# Copyright 2012-2014 Anthony Beville
# Copyright 2019 Brian Pepple

import itertools
from pathlib import Path
from typing import List


def get_recursive_filelist(pathlist: List[Path]) -> List[Path]:
    """
    Returns a path list of comic archives.

    :param pathlist: A list of path objects
    :type pathlist:  list of Path
    """
    filelist: List[Path] = []
    for path_str in pathlist:
        path = Path(path_str)
        if path.is_dir():
            filelist.extend(iter(path.rglob("*.[cC][bB][zZ]")))
        else:
            filelist.append(path)

    return sorted(filelist)


def list_to_string(list_of_strings: List[str]) -> str:
    """
    Function that takes a list of string and converts it to a string.
    For example: ["apple", "banana", "cherry"] is changed to "apple; banana; cherry"

    :param list_of_strings: A list of strings.
    :type list_of_strings: list of str
    """
    return "; ".join(map(str, list_of_strings))


def remove_articles(text: str) -> str:
    """
    Takes a string and removes any articles in it.

    :param str text: A string with articles (ex. 'and', 'a', 'the').
    """
    articles = [
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
        "the",
        "with",
    ]
    new_text = "".join(f"{word} " for word in text.split(" ") if word.lower() not in articles)

    new_text = new_text[:-1]

    return new_text


def unique_file(file_name: Path) -> Path:
    """
    Takes a filename and if one already exist with that name, returns a new filename.

    :param Path file_name: A path objects
    """
    original_stem = file_name.stem

    for i in itertools.count(1):
        if not file_name.exists():
            break
        file_name = file_name.parent / f"{original_stem} ({i}){file_name.suffix}"

    return file_name
