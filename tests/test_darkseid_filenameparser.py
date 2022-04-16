from pathlib import Path

import pytest

from darkseid.filenameparser import FileNameParser

from .fake_filenames import fnames


@pytest.mark.parametrize("filename,reason,expected", fnames)
def test_file_name_parser(filename, reason, expected):
    p = FileNameParser()
    p.parse_filename(Path(filename))
    fp = p.__dict__
    for s in ["title"]:
        if s in expected:
            del expected[s]

    assert fp == expected
