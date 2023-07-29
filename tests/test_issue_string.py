import pytest

from darkseid.issue_string import IssueString

float_test_values = {
    ("1½", 1.5),
    ("½", 0.5),
    ("0.5", 0.5),
    ("0", 0.0),
    ("1", 1.0),
    ("22.BEY", 22.0),
    ("22A", 22.0),
    ("22-A", 22.0),
}


@pytest.mark.parametrize("issue, expected", float_test_values)
def test_float_strings(issue: str, expected: float) -> None:
    assert IssueString(issue).as_float() == expected


int_test_values = {("1", 1), ("1.5", 1), ("", None)}


@pytest.mark.parametrize("issue, expected", int_test_values)
def test_issue_int(issue: str, expected: int) -> None:
    assert IssueString(issue).as_int() == expected


string_test_values = {
    ("1", "001", 3),
    ("1.MU", "001.MU", 3),
    ("-1", "-001", 3),
    ("Test", "Test", 0),
}


@pytest.mark.parametrize("issue, expected, pad", string_test_values)
def test_issue_string_monsters_unleashed(issue: str, expected: str, pad: int) -> None:
    assert IssueString(issue).as_string(pad) == expected
