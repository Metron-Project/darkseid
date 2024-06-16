"""Support for mixed digit/string type Issue field.

Class for handling the odd permutations of an 'issue number' that the
comics industry throws at us.
e.g.: "12", "12.1", "0", "-1", "5AU", "100-2"
"""

# Copyright 2012-2014 Anthony Beville

from __future__ import annotations


class IssueString:
    """
    Handles issue number strings by breaking them into numeric and suffix parts, and provides methods to convert to
    different formats.
    """

    def __init__(self: IssueString, text: str) -> None:
        # sourcery skip: remove-unnecessary-cast
        """
        Initializes an IssueString object by parsing the input text into numeric and suffix parts.

        Args:
            text (str): The issue number string to parse.

        Returns:
            None
        """

        # break up the issue number string into 2 parts: the numeric and suffix string.
        # (assumes that the numeric portion is always first)

        self.num: float | None = None
        self.suffix: str = ""

        if text is None:
            return

        if isinstance(text, int | float):
            text = str(text)

        if not text:
            return

        # skip the minus sign if it's first
        start: int = 1 if text[0] == "-" else 0
        # if it's still not numeric at start skip it
        if text[start].isdigit() or text[start] == ".":
            idx = self._find_split_point(text, start)
            idx = self._move_trailing_numeric_decimal_to_suffix(idx, text)
            idx = self._determine_if_number_after_minus_sign(idx, start)

            part1 = text[:idx]
            part2 = text[idx:]

            if part1 != "":
                self.num = float(part1)
            self.suffix = part2
        else:
            self.suffix = text

    @staticmethod
    def _move_trailing_numeric_decimal_to_suffix(
        idx: int,
        text: str,
    ) -> int:
        """
        Moves a trailing numeric decimal to the suffix if there is other content after it.

        Args:
            idx (int): The index of the decimal point.
            text (str): The text to process.

        Returns:
            int: The updated index after moving the decimal if necessary.
        """

        # move trailing numeric decimal to suffix (only if there is other junk after )
        if text[idx - 1] == "." and len(text) != idx:
            idx -= 1
        return idx

    @staticmethod
    def _determine_if_number_after_minus_sign(
        idx: int,
        start: int,
    ) -> int:
        """
        Determines if there is a numeric value after a minus sign, adjusting the index accordingly.

        Args:
            idx (int): The current index position.
            start (int): The starting index position.

        Returns:
            int: The adjusted index based on the presence of a numeric value after the minus sign.
        """

        # if there is no numeric after the minus, make the minus part of
        # the suffix
        return 0 if idx == 1 and start == 1 else idx

    @staticmethod
    def _find_split_point(text: str, start: int) -> int:
        """
        Finds the split point in a string where the numeric part ends.

        Args:
            text (str): The input string to search for the split point.
            start (int): The starting index for the search.

        Returns:
            int: The index where the numeric part ends.
        """

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

    def as_string(self: IssueString, pad: int = 0) -> str:
        """
        Returns a string representation of the IssueString with left-side zero padding.

        Args:
            pad (int): The number of left-side zeroes to pad with.

        Returns:
            str: The IssueString as a string with zero padding.
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
            num_s = f"-{num_s}"

        return num_s

    def as_float(self: IssueString) -> float | None:
        """
        Returns the IssueString as a float value with no suffix.

        Returns:
            float | None: The IssueString as a float value, or None if the numeric part is not present.
        """

        if self.suffix == "½":
            return self.num + 0.5 if self.num is not None else 0.5
        return self.num

    def as_int(self: IssueString) -> int | None:
        """
        Returns the integer version of the float value in the IssueString.

        Returns:
            int | None: The integer value of the IssueString, or None if the numeric part is not present.
        """

        return None if self.num is None else int(self.num)
