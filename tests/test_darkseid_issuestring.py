from darkseid.issuestring import IssueString


def test_issue_string_pad():
    val = IssueString(int(1)).as_string(pad=3)
    assert val == "001"


def test_issue_float():
    val = IssueString("1½").as_float()
    assert val == 1.5


def test_issue_float_half():
    val = IssueString("½").as_float()
    assert val == 0.5


def test_issue_verify_float():
    val = IssueString("1.5").as_float()
    assert val == 1.5


def test_issue_string_no_value_as_int():
    val = IssueString("").as_int()
    assert val is None


def test_issue_int():
    val = IssueString("1").as_int()
    assert val == 1


def test_issue_float_as_int():
    val = IssueString("1.5").as_int()
    assert val == 1


def test_issue_string_monsters_unleashed():
    val = IssueString("1.MU").as_string(3)
    assert val == "001.MU"


def test_issue_string_minus_one():
    val = IssueString("-1").as_string(3)
    assert val == "-001"


def test_issue_string_none_value():
    val = IssueString("Test").as_string()
    assert val == "Test"
