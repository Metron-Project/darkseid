"""Tests for IssueString class using function-based approach."""

import pytest

from darkseid.issue_string import IssueString


def test_init_with_none():
    """Test initialization with None value."""
    issue = IssueString(None)
    assert issue.num is None
    assert issue.suffix == ""


def test_init_with_empty_string():
    """Test initialization with empty string."""
    issue = IssueString("")
    assert issue.num is None
    assert issue.suffix == ""


def test_init_with_simple_integer():
    """Test initialization with simple integer string."""
    issue = IssueString("12")
    assert issue.num == 12.0
    assert issue.suffix == ""


def test_init_with_float_string():
    """Test initialization with decimal number string."""
    issue = IssueString("12.5")
    assert issue.num == 12.5
    assert issue.suffix == ""


def test_init_with_negative_integer():
    """Test initialization with negative integer."""
    issue = IssueString("-12")
    assert issue.num == -12.0
    assert issue.suffix == ""


def test_init_with_negative_float():
    """Test initialization with negative decimal."""
    issue = IssueString("-12.5")
    assert issue.num == -12.5
    assert issue.suffix == ""


def test_init_with_zero():
    """Test initialization with zero."""
    issue = IssueString("0")
    assert issue.num == 0.0
    assert issue.suffix == ""


def test_init_with_suffix():
    """Test initialization with numeric and suffix parts."""
    issue = IssueString("12AU")
    assert issue.num == 12.0
    assert issue.suffix == "AU"


def test_init_with_decimal_and_suffix():
    """Test initialization with decimal number and suffix."""
    issue = IssueString("12.5AU")
    assert issue.num == 12.5
    assert issue.suffix == "AU"


def test_init_with_only_suffix():
    """Test initialization with only alphabetic content."""
    issue = IssueString("AU")
    assert issue.num is None
    assert issue.suffix == "AU"


def test_init_with_hyphenated_suffix():
    """Test initialization with hyphenated issue number."""
    issue = IssueString("100-2")
    assert issue.num == 100.0
    assert issue.suffix == "-2"


def test_init_with_float_input():
    """Test initialization with float input."""
    issue = IssueString(12.5)
    assert issue.num == 12.5
    assert issue.suffix == ""


def test_init_with_int_input():
    """Test initialization with integer input."""
    issue = IssueString(12)
    assert issue.num == 12.0
    assert issue.suffix == ""


def test_init_with_unsupported_type():
    """Test initialization with unsupported type raises TypeError."""
    with pytest.raises(TypeError, match="Unsupported type for issue string"):
        IssueString([1, 2, 3])  # type: ignore


def test_init_with_lone_minus_sign():
    """Test initialization with just a minus sign."""
    issue = IssueString("-")
    assert issue.num is None
    assert issue.suffix == "-"


def test_init_with_trailing_decimal():
    """Test initialization with trailing decimal point."""
    issue = IssueString("12.")
    assert issue.num == 12.0
    assert issue.suffix == ""


def test_init_with_multiple_decimals():
    """Test initialization with multiple decimal points."""
    issue = IssueString("12.5.1")
    assert issue.num == 12.5
    assert issue.suffix == ".1"


def test_as_string_without_padding():
    """Test as_string method without padding."""
    issue = IssueString("12.5AU")
    assert issue.as_string() == "12.5AU"


def test_as_string_with_padding():
    """Test as_string method with padding."""
    issue = IssueString("5.2")
    assert issue.as_string(pad=3) == "005.2"


def test_as_string_negative_with_padding():
    """Test as_string method with negative number and padding."""
    issue = IssueString("-12AU")
    assert issue.as_string(pad=4) == "-0012AU"


def test_as_string_only_suffix():
    """Test as_string method with only suffix."""
    issue = IssueString("AU")
    assert issue.as_string(pad=3) == "AU"


def test_as_string_integer_formatting():
    """Test as_string preserves integer formatting when appropriate."""
    issue = IssueString("12")
    assert issue.as_string() == "12"


def test_as_float_basic():
    """Test as_float method with basic number."""
    issue = IssueString("12.5")
    assert issue.as_float() == 12.5


def test_as_float_with_half_symbol():
    """Test as_float method with half symbol."""
    issue = IssueString("12")
    issue.suffix = "½"
    assert issue.as_float() == 12.5


def test_as_float_half_symbol_no_base():
    """Test as_float method with half symbol and no base number."""
    issue = IssueString("½")
    assert issue.as_float() == 0.5


def test_as_float_none():
    """Test as_float method with no numeric content."""
    issue = IssueString("AU")
    assert issue.as_float() is None


def test_as_int_basic():
    """Test as_int method with basic number."""
    issue = IssueString("12.7")
    assert issue.as_int() == 12


def test_as_int_negative():
    """Test as_int method with negative number."""
    issue = IssueString("-12.7")
    assert issue.as_int() == -12


def test_as_int_none():
    """Test as_int method with no numeric content."""
    issue = IssueString("AU")
    assert issue.as_int() is None


def test_str_representation():
    """Test __str__ method."""
    issue = IssueString("12.5AU")
    assert str(issue) == "12.5AU"


def test_repr_representation():
    """Test __repr__ method."""
    issue = IssueString("12.5AU")
    assert repr(issue) == "IssueString(num=12.5, suffix='AU')"


def test_equality_with_same_issuestring():
    """Test equality with identical IssueString objects."""
    issue1 = IssueString("12AU")
    issue2 = IssueString("12AU")
    assert issue1 == issue2


def test_equality_with_different_issuestring():
    """Test inequality with different IssueString objects."""
    issue1 = IssueString("12AU")
    issue2 = IssueString("13AU")
    assert issue1 != issue2


def test_equality_with_string():
    """Test equality with string input."""
    issue = IssueString("12")
    assert issue == "12"
    assert issue != "13"


def test_equality_with_int():
    """Test equality with integer input."""
    issue = IssueString("12")
    assert issue == 12
    assert issue != 13


def test_equality_with_float():
    """Test equality with float input."""
    issue = IssueString("12.5")
    assert issue == 12.5
    assert issue != 12.0


def test_equality_with_unsupported_type():
    """Test equality with unsupported type."""
    issue = IssueString("12")
    assert issue != [1, 2, 3]


def test_less_than_numeric_comparison():
    """Test less than comparison based on numeric values."""
    issue1 = IssueString("5")
    issue2 = IssueString("10")
    assert issue1 < issue2
    assert not (issue2 < issue1)


def test_less_than_suffix_comparison():
    """Test less than comparison based on suffix when numbers are equal."""
    issue1 = IssueString("5A")
    issue2 = IssueString("5B")
    assert issue1 < issue2
    assert not (issue2 < issue1)


def test_less_than_none_numeric():
    """Test less than comparison when one has None numeric value."""
    issue1 = IssueString("AU")  # num is None
    issue2 = IssueString("5")
    assert issue1 < issue2  # None treated as 0


def test_less_than_unsupported_type():
    """Test less than comparison with unsupported type."""
    issue = IssueString("5")
    result = issue.__lt__("not an IssueString")  # type: ignore
    assert result is NotImplemented


def test_is_numeric_only_true():
    """Test is_numeric_only method returns True for numeric-only content."""
    issue = IssueString("12.5")
    assert issue.is_numeric_only() is True


def test_is_numeric_only_false_with_suffix():
    """Test is_numeric_only method returns False when suffix exists."""
    issue = IssueString("12AU")
    assert issue.is_numeric_only() is False


def test_is_numeric_only_false_no_numeric():
    """Test is_numeric_only method returns False when no numeric content."""
    issue = IssueString("AU")
    assert issue.is_numeric_only() is False


def test_has_suffix_true():
    """Test has_suffix method returns True when suffix exists."""
    issue = IssueString("12AU")
    assert issue.has_suffix() is True


def test_has_suffix_false():
    """Test has_suffix method returns False when no suffix."""
    issue = IssueString("12")
    assert issue.has_suffix() is False


def test_has_suffix_empty_string():
    """Test has_suffix method returns False for empty suffix."""
    issue = IssueString("12")
    issue.suffix = ""
    assert issue.has_suffix() is False


def test_edge_case_decimal_start():
    """Test parsing when string starts with decimal point."""
    issue = IssueString(".5")
    assert issue.num == 0.5
    assert issue.suffix == ""


def test_edge_case_negative_decimal_start():
    """Test parsing negative number starting with decimal."""
    issue = IssueString("-.5")
    assert issue.num == -0.5
    assert issue.suffix == ""


def test_edge_case_complex_suffix():
    """Test parsing with complex alphanumeric suffix."""
    issue = IssueString("12A1B2")
    assert issue.num == 12.0
    assert issue.suffix == "A1B2"


def test_sorting_mixed_issues():
    """Test sorting a list of IssueString objects."""
    issues = [
        IssueString("10"),
        IssueString("2"),
        IssueString("2A"),
        IssueString("2B"),
        IssueString("1.5"),
    ]

    sorted_issues = sorted(issues)
    expected_order = [
        IssueString("1.5"),
        IssueString("2"),
        IssueString("2A"),
        IssueString("2B"),
        IssueString("10"),
    ]

    for actual, expected in zip(sorted_issues, expected_order, strict=False):
        assert actual == expected


def test_invalid_float_conversion():
    """Test handling of strings that can't be converted to float."""
    # This tests internal behavior where float conversion might fail
    issue = IssueString("12.5.6.7")  # Multiple decimals might cause issues
    # The class should handle this gracefully
    assert isinstance(issue.num, float | type(None))
    assert isinstance(issue.suffix, str)
