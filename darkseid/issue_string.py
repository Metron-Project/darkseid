"""Support for mixed digit/string type Issue field.

Class for handling the odd permutations of an 'issue number' that the
comics industry throws at us.
e.g.: "12", "12.1", "0", "-1", "5AU", "100-2"
"""
# Copyright 2012-2014 Anthony Beville
# Copyright 2025 Brian Pepple

from __future__ import annotations

__all__ = ["IssueString"]


class IssueString:
    """
    Handles issue number strings by breaking them into numeric and suffix parts,
    and provides methods to convert to different formats.\n
    This class parses comic book issue numbers that can contain various formats
    including decimals, negative numbers, and alphanumeric suffixes.\n
    Examples:
        >>> issue = IssueString("12.5AU")
        >>> issue.num
        12.5
        >>> issue.suffix
        'AU'
        >>> issue.as_string(pad=3)
        '012.5AU'
    """

    # Constants for better maintainability
    NUMERIC_CHARS = frozenset("0123456789.")
    HALF_SYMBOL = "½"
    HALF_VALUE = 0.5

    def __init__(self, text: str | float | None) -> None:
        """
        Initialize an IssueString object by parsing the input text.

        Args:
            text: The issue number to parse. Can be string, int, float, or None.

        Raises:
            TypeError: If text is not a supported type.
        """
        self.num: float | None = None
        self.suffix: str = ""

        if text is None:
            return

        # Normalize input to string
        if text_str := self._normalize_input(text):
            self._parse_issue_string(text_str)
        else:
            return

    @staticmethod
    def _normalize_input(text: str | float) -> str:
        """Convert input to string format for parsing."""
        if isinstance(text, (int | float)):
            return str(text)
        if isinstance(text, str):
            return text
        msg = f"Unsupported type for issue string: {type(text)}"
        raise TypeError(msg)

    def _parse_issue_string(self, text: str) -> None:
        """Parse the issue string into numeric and suffix components."""
        if not text:
            return

        # Handle negative numbers
        start_idx = 1 if text.startswith("-") else 0

        # Check if we have a numeric start
        if not self._has_numeric_start(text, start_idx):
            self.suffix = text
            return

        # Find where numeric part ends
        split_idx = self._find_numeric_end(text, start_idx)
        split_idx = self._adjust_for_trailing_decimal(text, split_idx)
        split_idx = self._handle_lone_minus_sign(split_idx, start_idx)

        suffix_part = text[split_idx:]

        if numeric_part := text[:split_idx]:
            try:
                self.num = float(numeric_part)
            except ValueError:
                # If conversion fails, treat entire string as suffix
                self.suffix = text
                return

        self.suffix = suffix_part

    @staticmethod
    def _has_numeric_start(text: str, start_idx: int) -> bool:
        """Check if the text starts with a numeric character at the given index."""
        return start_idx < len(text) and (text[start_idx].isdigit() or text[start_idx] == ".")

    def _find_numeric_end(self, text: str, start_idx: int) -> int:
        """Find where the numeric portion of the string ends."""
        decimal_count = 0

        for idx in range(start_idx, len(text)):
            char = text[idx]

            if char not in self.NUMERIC_CHARS:
                return idx

            # Handle multiple decimal points - split on the second one
            if char == ".":
                decimal_count += 1
                if decimal_count > 1:
                    return idx

        return len(text)

    @staticmethod
    def _adjust_for_trailing_decimal(text: str, idx: int) -> int:
        """Move trailing decimal point to suffix if there's content after it."""
        return idx - 1 if (0 < idx < len(text) and text[idx - 1] == ".") else idx

    @staticmethod
    def _handle_lone_minus_sign(idx: int, start_idx: int) -> int:
        """Handle case where minus sign has no numeric content after it."""
        # If we only found a minus sign with no numbers, include it in suffix
        return 0 if idx == 1 and start_idx == 1 else idx

    def as_string(self, pad: int = 0) -> str:
        """
        Return a string representation with optional zero padding.\n
        Examples:
            >>> IssueString("5.2").as_string(pad=3)
            '005.2'
            >>> IssueString("-12AU").as_string(pad=4)
            '-0012AU'

        Args:
            pad: Number of digits to pad the integer part with leading zeros.

        Returns:
            String representation of the issue number with padding and suffix.
        """
        if self.num is None:
            return self.suffix

        is_negative = self.num < 0
        abs_num = abs(self.num)

        # Format the number preserving decimals when necessary
        num_str = str(int(abs_num)) if abs_num == int(abs_num) else str(abs_num)
        # Apply padding to integer part only
        if pad > 0:
            integer_part = str(int(abs_num))
            if len(integer_part) < pad:
                padding = "0" * (pad - len(integer_part))
                num_str = padding + num_str

        # Add suffix and handle negative sign
        result = num_str + self.suffix
        return f"-{result}" if is_negative else result

    def as_float(self) -> float | None:
        """
        Return the numeric value as a float.\n
        Special handling for the half symbol (½) which adds 0.5 to the base number.

        Examples:
            >>> IssueString("12½").as_float()
            12.5
            >>> IssueString("5").as_float()
            5.0

        Returns:
            Float value of the issue number, or None if no numeric part exists.
        """
        if self.suffix == self.HALF_SYMBOL:
            base_value = self.num if self.num is not None else 0
            return base_value + self.HALF_VALUE
        return self.num

    def as_int(self) -> int | None:
        """
        Return the integer portion of the numeric value.

        Examples:
            >>> IssueString("12.7").as_int()
            12
            >>> IssueString("AU").as_int()
            None

        Returns:
            Integer value (truncated, not rounded) or None if no numeric part.
        """
        return None if self.num is None else int(self.num)

    def __str__(self) -> str:
        """Return string representation without padding."""
        return self.as_string()

    def __repr__(self) -> str:
        """Return detailed string representation for debugging."""
        return f"IssueString(num={self.num}, suffix='{self.suffix}')"

    def __eq__(self, other: object) -> bool:
        """Check equality with another IssueString or comparable object."""
        if isinstance(other, IssueString):
            return self.num == other.num and self.suffix == other.suffix
        if isinstance(other, (str | int | float)):
            other_issue = IssueString(other)
            return self == other_issue
        return False

    def __lt__(self, other: IssueString) -> bool:
        """
        Compare IssueString objects for sorting.\n
        Comparison priority:
        1. Numeric value (None is treated as 0)
        2. Suffix (alphabetical)
        """
        if not isinstance(other, IssueString):
            return NotImplemented

        self_num = self.num if self.num is not None else 0
        other_num = other.num if other.num is not None else 0

        if self_num != other_num:
            return self_num < other_num
        return self.suffix < other.suffix

    def is_numeric_only(self) -> bool:
        """Check if the issue string contains only numeric content."""
        return self.num is not None and not self.suffix

    def has_suffix(self) -> bool:
        """Check if the issue string has a non-empty suffix."""
        return bool(self.suffix)
