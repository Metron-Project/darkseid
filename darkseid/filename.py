"""Functions for parsing comic info from filename

This should probably be re-written, but, well, it mostly works!
"""

# Copyright 2012-2014 Anthony Beville

import contextlib
import re
from pathlib import Path
from typing import List, Tuple
from urllib.parse import unquote


class FileNameParser:
    """Class to get parse the filename to get information about the comic."""

    def __init__(self) -> None:
        self.issue: str = ""
        self.series: str = ""
        self.volume: str = ""
        self.issue_count: str = ""
        self.year: str = ""
        self.remainder: str = ""

    @staticmethod
    def repl(match):
        return " " * len(match.group())

    def fix_spaces(self, string: str, remove_dashes: bool = True) -> str:
        """Returns a string with the spaces fixed"""

        placeholders = ["[-_]", "  +"] if remove_dashes else ["[_]", "  +"]
        for place_holder in placeholders:
            string = re.sub(place_holder, self.repl, string)
        return string  # .strip()

    def get_issue_count(self, filename: str, issue_end: int) -> str:
        """Returns a string with the issue count"""

        count: str = ""
        filename = filename[issue_end:]

        # replace any name separators with spaces
        tmpstr: str = self.fix_spaces(filename)
        found: bool = False

        if match := re.search(r"(?<=\sof\s)\d+(?=\s)", tmpstr, re.IGNORECASE):
            count = match.group()
            found = True

        if match := re.search(r"(?<=\(of\s)\d+(?=\))", tmpstr, re.IGNORECASE):
            if not found:
                count = match.group()
                found = True

        count = count.lstrip("0")

        return count

    def get_issue_number(self, filename: str) -> Tuple[str, int, int]:
        """Returns a tuple of issue number string, and start and end indexes in the filename
        (The indexes will be used to split the string up for further parsing)
        """

        found: bool = False
        issue: str = ""
        start: int = 0
        end: int = 0

        # first, look for multiple "--", this means it's formatted differently
        # from most:
        if "--" in filename:
            # the pattern seems to be that anything to left of the first "--"
            # is the series name followed by issue
            filename = re.sub("--.*", self.repl, filename)

        elif "__" in filename:
            # the pattern seems to be that anything to left of the first "__"
            # is the series name followed by issue
            filename = re.sub("__.*", self.repl, filename)

        filename = filename.replace("+", " ")

        # replace parenthetical phrases with spaces
        filename = re.sub(r"\(.*?\)", self.repl, filename)
        filename = re.sub(r"\[.*?\]", self.repl, filename)

        # replace any name separators with spaces
        filename = self.fix_spaces(filename)

        # remove any "of NN" phrase with spaces (problem: this could break on
        # some titles)
        filename = re.sub(r"of [\d]+", self.repl, filename)

        # print u"[{0}]".format(filename)

        # we should now have a cleaned up filename version with all the words in
        # the same positions as original filename

        # make a list of each word and its position
        word_list: List[Tuple[str, int, int]] = [
            (match.group(0), match.start(), match.end())
            for match in re.finditer(r"\S+", filename)
        ]

        # remove the first word, since it can't be the issue number
        if len(word_list) > 1:
            word_list = word_list[1:]
        else:
            # only one word??  just bail.
            return issue, start, end

        # Now try to search for the likely issue number word in the list

        # Intialize the word variable so that it's not unbound.
        word: Tuple[str, int, int] = ("", 0, 0)
        # first look for a word with "#" followed by digits with optional suffix
        # this is almost certainly the issue number
        for word in reversed(word_list):
            if re.match(r"#[-]?(([0-9]*\.[0-9]+|[0-9]+)(\w*))", word[0]):
                found = True
                break

        # same as above but w/o a '#', and only look at the last word in the
        # list
        if not found:
            word = word_list[-1]
            if re.match(r"[-]?(([0-9]*\.[0-9]+|[0-9]+)(\w*))", word[0]):
                found = True

        # now try to look for a # followed by any characters
        if not found:
            for word in reversed(word_list):
                if re.match(r"#\S+", word[0]):
                    found = True
                    break

        if found:
            issue = word[0]
            start = word[1]
            end = word[2]
            if issue[0] == "#":
                issue = issue[1:]

        return issue, start, end

    def get_series_name(self, filename: str, issue_start: int) -> Tuple[str, str]:
        """Use the issue number string index to split the filename string"""

        if issue_start != 0:
            filename = filename[:issue_start]

        # in case there is no issue number, remove some obvious stuff
        if "--" in filename:
            # the pattern seems to be that anything to left of the first "--"
            # is the series name followed by issue
            filename = re.sub("--.*", self.repl, filename)

        elif "__" in filename:
            # the pattern seems to be that anything to left of the first "__"
            # is the series name followed by issue
            filename = re.sub("__.*", self.repl, filename)

        tmpstr = self.fix_spaces(filename, remove_dashes=False)

        series = tmpstr
        volume = ""

        # save the last word
        try:
            last_word = series.split()[-1]
        except ValueError:
            last_word = ""

        # remove any parenthetical phrases
        series = re.sub(r"\(.*?\)", "", series)

        # search for volume number
        if match := re.search(r"(.+)([vV]|[Vv][oO][Ll]\.?\s?)(\d+)\s*$", series):
            series = match[1]
            volume = match[3]

        # if a volume wasn't found, see if the last word is a year in parentheses
        # since that's a common way to designate the volume
        if volume == "":
            if match := re.search(r"(\()(\d{4})(-(\d{4}|)|)(\))", last_word):
                volume = match[2]

        series = series.strip()

        # if we don't have an issue number (issue_start==0), look
        # for hints i.e. "TPB", "one-shot", "OS", "OGN", etc that might
        # be removed to help search online
        if issue_start == 0:
            one_shot_words = ["tpb", "os", "one-shot", "ogn", "gn"]
            with contextlib.suppress(ValueError):
                last_word = series.split()[-1]
                if last_word.casefold() in one_shot_words:
                    series = series.rsplit(" ", 1)[0]
        return series, volume.strip()

    @staticmethod
    def get_year(filename: str, issue_end: int) -> str:
        """Return the year from the filename"""

        filename = filename[issue_end:]

        year: str = ""
        # look for four digit number with "(" ")" or "--" around it
        if match := re.search(r"(\(\d\d\d\d\))|(--\d\d\d\d--)", filename):
            year = match.group()
            # remove non-digits
            year = re.sub("[^0-9]", "", year)
        return year

    def get_remainder(
        self, filename: str, year: str, count: str, volume: str, issue_end: int
    ) -> str:
        """Make a guess at where the the non-interesting stuff begins"""

        remainder: str = ""

        if "--" in filename:
            remainder = filename.split("--", 1)[1]
        elif "__" in filename:
            remainder = filename.split("__", 1)[1]
        elif issue_end != 0:
            remainder = filename[issue_end:]

        remainder = self.fix_spaces(remainder, remove_dashes=False)
        if volume != "":
            remainder = remainder.replace(f"Vol.{volume}", "", 1)
        if year != "":
            remainder = remainder.replace(year, "", 1)
        if count != "":
            remainder = remainder.replace(f"of {count}", "", 1)

        remainder = remainder.replace("()", "")
        remainder = remainder.replace("  ", " ")  # cleans some whitespace mess

        return remainder.strip()

    def parse_filename(self, comic: Path) -> None:
        """Method to parse the filename."""

        # Get comic name without path or extension
        filename = comic.stem

        # url decode, just in case
        filename = unquote(filename)

        # sometimes archives get messed up names from too many decodes
        # often url encodings will break and leave "_28" and "_29" in place
        # of "(" and ")"  see if there are a number of these, and replace them
        if filename.count("_28") > 1 and filename.count("_29") > 1:
            filename = filename.replace("_28", "(")
            filename = filename.replace("_29", ")")

        self.issue, issue_start, issue_end = self.get_issue_number(filename)
        self.series, self.volume = self.get_series_name(filename, issue_start)

        # provides proper value when the filename doesn't have a issue number
        if issue_end == 0:
            issue_end = len(self.series)

        self.year = self.get_year(filename, issue_end)
        self.issue_count = self.get_issue_count(filename, issue_end)
        self.remainder = self.get_remainder(
            filename, self.year, self.issue_count, self.volume, issue_end
        )

        if self.issue != "":
            # strip off leading zeros
            self.issue = self.issue.lstrip("0")
            if self.issue == "":
                self.issue = "0"
            if self.issue[0] == ".":
                self.issue = f"0{self.issue}"
