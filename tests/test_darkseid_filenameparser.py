""" Test for the filename parser """
import pytest

from darkseid.filenameparser import FileNameParser as fn


@pytest.fixture()
def parser():
    parser = fn()
    return parser


@pytest.fixture()
def comic_name():
    comic = "Afterlife_With_Archie_V1_#002_(of_08)_(2013)"
    return comic


def test_special_format(parser):
    """ Test for files with a special name like 'TPB' """
    comic = "Aquaman TPB (1994)"
    _, issue_start, _ = parser.get_issue_number(comic)
    series, volume = parser.get_series_name(comic, issue_start)
    assert issue_start == 0
    assert series == "Aquaman"
    assert volume == "1994"


def test_get_issue_number(parser, comic_name):
    """ Test to get the issue number from the filename """
    # Returns a tuple of issue number string, and start and end indexes in the filename
    issue, issue_start, issue_end = parser.get_issue_number(comic_name)
    assert issue == "002"
    assert issue_start == 25
    assert issue_end == 29


def test_get_year(parser, comic_name):
    """ Test to get the year from a filename """
    _, _, issue_end = parser.get_issue_number(comic_name)
    year = parser.get_year(comic_name, issue_end)
    assert year == "2013"


def test_get_series_name(parser, comic_name):
    """ Test to get the series name from a filename """
    _, issue_start, _ = parser.get_issue_number(comic_name)
    series, volume = parser.get_series_name(comic_name, issue_start)
    assert series == "Afterlife With Archie"
    assert volume == "1"


def test_get_count(parser, comic_name):
    """ Test to get the total number of issues from the filename """
    _, _, issue_end = parser.get_issue_number(comic_name)
    issue_count = parser.get_issue_count(comic_name, issue_end)
    assert issue_count == "8"


def test_fix_spaces(parser, comic_name):
    """ Test of converting underscores to spaces in the filename """
    new_name = parser.fix_spaces(comic_name)
    assert new_name != "Afterlife With Archie"


def test_get_remainder(parser, comic_name):
    """ Test the remainder function """
    _, issue_start, issue_end = parser.get_issue_number(comic_name)
    year = parser.get_year(comic_name, issue_end)
    _, volume = parser.get_series_name(comic_name, issue_start)
    count = parser.get_issue_count(comic_name, issue_end)
    remainder = parser.get_remainder(comic_name, year, count, volume, issue_end)
    assert remainder == "(of 08)"


def test_parse_filename(parser, comic_name, tmp_path):
    """ Test the parsing of a temporary files name """
    test_file = tmp_path / f"{comic_name}.cbz"
    test_file.write_text("blah blah")

    parser.parse_filename(test_file)
    assert parser.series == "Afterlife With Archie"
    assert parser.volume == "1"
    assert parser.issue == "2"
    assert parser.issue_count == "8"
    assert parser.year == "2013"
