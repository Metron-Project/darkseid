"""Some generic utilities"""
# Copyright 2012-2014 Anthony Beville
# Copyright 2019 Brian Pepple

from pathlib import Path
from typing import List


def get_recursive_filelist(pathlist: List[str]) -> List[Path]:
    """Takes a list of paths and return a list of comic archives"""
    filelist: List[Path] = []
    for path_str in pathlist:
        path = Path(path_str)
        if path.is_dir():
            for filename in path.rglob("*.[cC][bB][zZ]"):
                filelist.append(filename)
        else:
            filelist.append(path)

    return sorted(filelist)


def list_to_string(list_of_strings: List[str]) -> str:
    """
    Function that takes a list of string and converts it to a string.
    For example: ["apple", "banana", "cherry"] is changed to "apple; banana; cherry"
    """
    return "; ".join(map(str, list_of_strings))


def remove_articles(text: str) -> str:
    """Takes a string and removes any articles in it."""
    text = text.lower()
    articles: List[str] = ["and", "a", "&", "issue", "the"]
    new_text: str = ""
    for word in text.split(" "):
        if word not in articles:
            new_text += word + " "

    new_text = new_text[:-1]

    # now get rid of some other junk
    new_text = new_text.replace(":", "")
    new_text = new_text.replace(",", "")
    new_text = new_text.replace("-", " ")

    return new_text


def unique_file(file_name: str) -> Path:
    """Takes a filename and if one already exist with that name returns a new filename"""
    counter: int = 0
    path = Path(file_name)
    # Use original stem so on multiple matches it doesn't keep appending counter variable
    original_stem = path.stem

    while True:
        if not path.exists():
            return path
        counter += 1
        path = path.parent / f"{original_stem} ({counter}){path.suffix}"
