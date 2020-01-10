"""Some generic utilities"""
# Copyright 2012-2014 Anthony Beville
# Copyright 2019 Brian Pepple

import pathlib


def get_recursive_filelist(pathlist):
    """Takes a list of paths and return a list of comic archives"""
    filelist = []
    for path in pathlist:
        path = pathlib.Path(path)
        if path.is_dir():
            for filename in path.rglob("*.[cC][bB][zZ]"):
                filelist.append(filename)
        else:
            filelist.append(path)

    filelist = sorted(filelist)

    return filelist


def list_to_string(list_of_strings):
    """
    Function that takes a list of string and converts it to a string.
    For example: ["apple", "banana", "cherry"] is changed to "apple; banana; cherry"
    """
    string = ""
    if list_of_strings is not None:
        for item in list_of_strings:
            if len(string) > 0:
                string += "; "
            string += item
    return string


def remove_articles(text):
    """Takes a string and removes any articles in it."""
    text = text.lower()
    articles = ["and", "a", "&", "issue", "the"]
    new_text = ""
    for word in text.split(" "):
        if word not in articles:
            new_text += word + " "

    new_text = new_text[:-1]

    # now get rid of some other junk
    new_text = new_text.replace(":", "")
    new_text = new_text.replace(",", "")
    new_text = new_text.replace("-", " ")

    return new_text


def unique_file(file_name):
    """Takes a filename and if one already exist with that name returns a new filename"""
    counter = 0
    path = pathlib.Path(file_name)

    while True:
        if not path.exists():
            return path
        counter += 1
        path = pathlib.Path(path.parent).joinpath(
            f"{path.stem} ({counter}){path.suffix}"
        )
