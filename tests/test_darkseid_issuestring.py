from unittest import TestCase, main

from darkseid.issuestring import IssueString


class TestIssueString(TestCase):
    def test_issue_string_pad(self):
        val = IssueString(int(1)).as_string(pad=3)
        self.assertEqual(val, "001")

    def test_issue_float(self):
        val = IssueString("1½").as_float()
        self.assertEqual(val, 1.5)

    def test_issue_float_half(self):
        val = IssueString("½").as_float()
        self.assertEqual(val, 0.5)

    def test_issue_verify_float(self):
        val = IssueString("1.5").as_float()
        self.assertEqual(val, 1.5)

    def test_issue_string_no_value_as_int(self):
        val = IssueString("").as_int()
        self.assertIsNone(val)

    def test_issue_int(self):
        val = IssueString("1").as_int()
        self.assertEqual(val, 1)

    def test_issue_float_as_int(self):
        val = IssueString("1.5").as_int()
        self.assertEqual(val, 1)

    def test_issue_string_monsters_unleashed(self):
        val = IssueString("1.MU").as_string(3)
        self.assertEqual(val, "001.MU")

    def test_issue_string_minus_one(self):
        val = IssueString("-1").as_string(3)
        self.assertEqual(val, "-001")

    def test_issue_string_none_value(self):
        val = IssueString("Test").as_string()
        self.assertEqual(val, "Test")


if __name__ == "__main__":
    main()
