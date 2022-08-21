from pathlib import Path

import pytest

from darkseid.filename_parser import FileNameParser

from .test_params import test_file_names


@pytest.mark.parametrize("filename,reason,expected", test_file_names)
def test_file_name_parser(filename, reason, expected):
    p = FileNameParser()
    p.parse_filename(Path(filename))
    fp = p.__dict__
    for s in ["title"]:
        if s in expected:
            del expected[s]

    assert fp == expected
