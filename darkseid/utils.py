"""Some generic utilities"""

# Copyright 2012-2014 Anthony Beville
# Copyright 2019 Brian Pepple

import os
import pathlib


def get_recursive_filelist(pathlist):
    """ Create a recursive list of comic files """
    filelist = []
    for path in pathlist:
        for filename in pathlib.Path(path).rglob("*.[cC][bB][zZ]"):
            filelist.append(filename)

    filelist = sorted(filelist)

    return filelist


def listToString(l):
    string = ""
    if l is not None:
        for item in l:
            if len(string) > 0:
                string += "; "
            string += item
    return string


def removearticles(text):
    text = text.lower()
    articles = ["and", "a", "&", "issue", "the"]
    newText = ""
    for word in text.split(" "):
        if word not in articles:
            newText += word + " "

    newText = newText[:-1]

    # now get rid of some other junk
    newText = newText.replace(":", "")
    newText = newText.replace(",", "")
    newText = newText.replace("-", " ")

    # since the CV API changed, searches for series names with periods
    # now explicitly require the period to be in the search key,
    # so the line below is removed (for now)
    # newText = newText.replace(".", "")

    return newText


def unique_file(file_name):
    counter = 1
    # returns ('/path/file', '.ext')
    file_name_parts = os.path.splitext(file_name)
    while True:
        if not os.path.lexists(file_name):
            return file_name
        file_name = file_name_parts[0] + " (" + str(counter) + ")" + file_name_parts[1]
        counter += 1
