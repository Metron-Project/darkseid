"""Support for mixed digit/string type Issue field

Class for handling the odd permutations of an 'issue number' that the
comics industry throws at us.
e.g.: "12", "12.1", "0", "-1", "5AU", "100-2"
"""

# Copyright 2012-2014 Anthony Beville

from typing import Optional


class IssueString:
    """
    Class to handle various types of comic issue numbers.

    :param str text: The issue number.
    """

    def __init__(self, text: str) -> None:
        """Intialize a new IssueString."""
        # break up the issue number string into 2 parts: the numeric and suffix string.
        # (assumes that the numeric portion is always first)

        self.num: Optional[float] = None
        self.suffix: str = ""

        if text is None:
            return

        if isinstance(text, (int, float)):
            text = str(text)

        if not text:
            return

        # skip the minus sign if it's first
        start: int = 1 if text[0] == "-" else 0
        # if it's still not numeric at start skip it
        if text[start].isdigit() or text[start] == ".":
            idx = self._find_splitpoint(text, start)
            idx = self._move_trailing_numeric_decimal_to_suffix(idx, text)
            idx = self._determine_if_number_after_minus_sign(idx, start)

            part1 = text[:idx]
            part2 = text[idx : len(text)]

            if part1 != "":
                self.num = float(part1)
            self.suffix = part2
        else:
            self.suffix = text

    def _move_trailing_numeric_decimal_to_suffix(self, idx: int, text: str) -> int:
        # move trailing numeric decimal to suffix (only if there is other junk after )
        if text[idx - 1] == "." and len(text) != idx:
            idx -= 1
        return idx

    def _determine_if_number_after_minus_sign(self, idx: int, start: int) -> int:
        # if there is no numeric after the minus, make the minus part of
        # the suffix
        if idx == 1 and start == 1:
            return 0
        else:
            return idx

    def _find_splitpoint(self, text: str, start: int) -> int:
        # walk through the string, look for split point (the first non-numeric)
        decimal_count: int = 0
        for idx in range(start, len(text)):
            if text[idx] not in "0123456789.":
                break
            # special case: also split on second "."
            if text[idx] == ".":
                decimal_count += 1
                if decimal_count > 1:
                    break
        else:
            idx = len(text)

        return idx

    def as_string(self, pad: int = 0) -> str:
        """
        Returns a string with left-side zero padding

        :param int pad: The number of left-side zeroes to pad with.

        :returns: String with zero padding.
        :rtype: str
        """
        # return the float, left side zero-padded, with suffix attached
        if self.num is None:
            return self.suffix

        negative: bool = self.num < 0

        num_f: float = abs(self.num)

        num_int = int(num_f)
        num_s = str(num_f) if float(num_int) != num_f else str(num_int)
        num_s += self.suffix

        length = len(str(num_int))
        padding: str = "0" * (pad - length) if length < pad else ""
        num_s = padding + num_s
        if negative:
            num_s = "-" + num_s

        return num_s

    def as_float(self) -> Optional[float]:
        """
        Return a float with no suffix

        example: "1½" is returned as "1.5"

        :returns: String as a float.
        :rtype: float, optional
        """
        if self.suffix == "½":
            return self.num + 0.5 if self.num is not None else 0.5
        return self.num

    def as_int(self) -> Optional[int]:
        """
        Returns the integer version of the float

        :returns: String as an integer.
        :rtype: int, optional
        """
        return None if self.num is None else int(self.num)
