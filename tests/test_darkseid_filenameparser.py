""" Test for the filename parser """
import pytest

from darkseid.filenameparser import FileNameParser as fnp

SERIES_NAME = "Afterlife With Archie"


@pytest.fixture()
def comic_name():
    return "Afterlife_With_Archie_V1_#002_(of_08)_(2013)"


def test_series_name_with_plus_sign():
    comic = "A+X #001 (2012)"
    issue_number, issue_start, _ = fnp().get_issue_number(comic)
    series, volume = fnp().get_series_name(comic, issue_start)
    assert issue_number == "001"
    assert issue_start == 4
    assert series == "A+X"
    assert volume == ""


def test_special_format():
    """Test for files with a special name like 'TPB'"""
    comic = "Aquaman TPB (1994)"
    _, issue_start, _ = fnp().get_issue_number(comic)
    series, volume = fnp().get_series_name(comic, issue_start)
    assert issue_start == 0
    assert series == "Aquaman"
    assert volume == "1994"


def test_get_issue_number(comic_name):
    """Test to get the issue number from the filename"""
    # Returns a tuple of issue number string, and start and end indexes in the filename
    issue, issue_start, issue_end = fnp().get_issue_number(comic_name)
    assert issue == "002"
    assert issue_start == 25
    assert issue_end == 29


def test_get_year(comic_name):
    """Test to get the year from a filename"""
    _, _, issue_end = fnp().get_issue_number(comic_name)
    year = fnp().get_year(comic_name, issue_end)
    assert year == "2013"


def test_get_series_name(comic_name):
    """Test to get the series name from a filename"""
    _, issue_start, _ = fnp().get_issue_number(comic_name)
    series, volume = fnp().get_series_name(comic_name, issue_start)
    assert series == SERIES_NAME
    assert volume == "1"


def test_get_count(comic_name):
    """Test to get the total number of issues from the filename"""
    _, _, issue_end = fnp().get_issue_number(comic_name)
    issue_count = fnp().get_issue_count(comic_name, issue_end)
    assert issue_count == "8"


def test_fix_spaces(comic_name):
    """Test of converting underscores to spaces in the filename"""
    new_name = fnp().fix_spaces(comic_name)
    assert new_name != SERIES_NAME


def test_get_remainder(comic_name):
    """Test the remainder function"""
    _, issue_start, issue_end = fnp().get_issue_number(comic_name)
    year = fnp().get_year(comic_name, issue_end)
    _, volume = fnp().get_series_name(comic_name, issue_start)
    count = fnp().get_issue_count(comic_name, issue_end)
    remainder = fnp().get_remainder(comic_name, year, count, volume, issue_end)
    assert remainder == "(of 08)"


def test_parse_filename(comic_name, tmp_path):
    """Test the parsing of a temporary files name"""
    test_file = tmp_path / f"{comic_name}.cbz"
    test_file.write_text("blah blah")

    f = fnp()
    f.parse_filename(test_file)
    assert f.series == SERIES_NAME
    assert f.volume == "1"
    assert f.issue == "2"
    assert f.issue_count == "8"
    assert f.year == "2013"
