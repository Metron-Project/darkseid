"""A class for internal metadata storage

The goal of this class is to handle ALL the data that might come from various
tagging schemes and databases, such as Metron, ComicVine or GCD.  This makes conversion
possible, however lossy it might be

"""

# Copyright 2012-2014 Anthony Beville
# Copyright 2020 Brian Pepple

from typing import Dict, List, Optional, Tuple

from . import utils


class PageType:

    """
    These page info classes are exactly the same as the CIX scheme, since
    it's unique
    """

    FrontCover = "FrontCover"
    InnerCover = "InnerCover"
    Roundup = "Roundup"
    Story = "Story"
    Advertisement = "Advertisement"
    Editorial = "Editorial"
    Letters = "Letters"
    Preview = "Preview"
    BackCover = "BackCover"
    Other = "Other"
    Deleted = "Deleted"


class GenericMetadata:
    def __init__(self) -> None:

        self.is_empty: bool = True
        self.tag_origin: Optional[str] = None

        self.series: Optional[str] = None
        self.issue: Optional[str] = None
        self.title: Optional[str] = None
        self.publisher: Optional[str] = None
        self.month: Optional[str] = None
        self.year: Optional[str] = None
        self.day: Optional[str] = None
        self.issue_count: Optional[str] = None
        self.volume: Optional[str] = None
        self.genre: Optional[str] = None
        self.language: Optional[str] = None  # 2 letter iso code
        self.comments: Optional[str] = None  # use same way as Summary in CIX

        self.volume_count: Optional[str] = None
        self.critical_rating: Optional[str] = None
        self.country: Optional[str] = None

        self.alternate_series: Optional[str] = None
        self.alternate_number: Optional[str] = None
        self.alternate_count: Optional[str] = None
        self.imprint: Optional[str] = None
        self.notes: Optional[str] = None
        self.web_link: Optional[str] = None
        self.format: Optional[str] = None
        self.manga: Optional[str] = None
        self.black_and_white: Optional[bool] = None
        self.page_count: Optional[int] = None
        self.maturity_rating: Optional[str] = None

        self.story_arc: Optional[str] = None
        self.series_group: Optional[str] = None
        self.scan_info: Optional[str] = None

        self.characters: Optional[str] = None
        self.teams: Optional[str] = None
        self.locations: Optional[str] = None

        self.credits: List[Dict[str, str]] = []
        self.tags: List[str] = []
        self.pages: List[Dict[str, str]] = []

    def overlay(self, new_md: "GenericMetadata") -> None:
        """Overlay a metadata object on this one

        That is, when the new object has non-None values, over-write them
        to this one.
        """

        def assign_str(cur: str, new: Optional[str]) -> None:
            if new is not None:
                setattr(self, cur, new)

        def assign_bool(cur: str, new: Optional[bool]) -> None:
            if new is not None:
                setattr(self, cur, new)

        if not new_md.is_empty:
            self.is_empty = False

        assign_str("series", new_md.series)
        assign_str("issue", new_md.issue)
        assign_str("issue_count", new_md.issue_count)
        assign_str("title", new_md.title)
        assign_str("publisher", new_md.publisher)
        assign_str("day", new_md.day)
        assign_str("month", new_md.month)
        assign_str("year", new_md.year)
        assign_str("volume", new_md.volume)
        assign_str("volume_count", new_md.volume_count)
        assign_str("genre", new_md.genre)
        assign_str("language", new_md.language)
        assign_str("country", new_md.country)
        assign_str("critical_rating", new_md.critical_rating)
        assign_str("alternate_series", new_md.alternate_series)
        assign_str("alternate_number", new_md.alternate_number)
        assign_str("alternate_count", new_md.alternate_count)
        assign_str("imprint", new_md.imprint)
        assign_str("web_link", new_md.web_link)
        assign_str("format", new_md.format)
        assign_str("manga", new_md.manga)
        assign_bool("black_and_white", new_md.black_and_white)
        assign_str("maturity_rating", new_md.maturity_rating)
        assign_str("story_arc", new_md.story_arc)
        assign_str("series_group", new_md.series_group)
        assign_str("scan_info", new_md.scan_info)
        assign_str("characters", new_md.characters)
        assign_str("teams", new_md.teams)
        assign_str("locations", new_md.locations)
        assign_str("comments", new_md.comments)
        assign_str("notes", new_md.notes)

        # TODO

        # not sure if the tags and pages should broken down, or treated
        # as whole lists....

        # For now, go the easy route, where any overlay
        # value wipes out the whole list
        def assign_list(cur: str, new: List[str]) -> None:
            setattr(self, cur, new)

        def assign_list_pages(cur: str, new: List[Dict[str, str]]) -> None:
            setattr(self, cur, new)

        if len(new_md.tags) > 0:
            assign_list("tags", new_md.tags)

        if len(new_md.pages) > 0:
            assign_list_pages("pages", new_md.pages)

    def set_default_page_list(self, count: int) -> None:
        # generate a default page list, with the first page marked as the cover
        for i in range(count):
            page_dict = {"Image": str(i)}
            if i == 0:
                page_dict["Type"] = PageType.FrontCover
            self.pages.append(page_dict)

    def get_archive_page_index(self, pagenum: int) -> int:
        # convert the displayed page number to the page index of the file in
        # the archive
        if pagenum < len(self.pages):
            return int(self.pages[pagenum]["Image"])
        else:
            return 0

    def get_cover_page_index_list(self) -> List[int]:
        # return a list of archive page indices of cover pages
        coverlist = [
            int(page["Image"])
            for page in self.pages
            if "Type" in page and page["Type"] == PageType.FrontCover
        ]

        if not coverlist:
            coverlist.append(0)

        return coverlist

    def add_credit(self, person: str, role: str) -> None:

        credit: Dict[str, str] = {"person": person, "role": role}
        self.credits.append(credit)

    def __str__(self) -> str:
        vals: List[Tuple[str, str]] = []
        if self.is_empty:
            return "No metadata"

        def add_string(tag: str, val: str) -> None:
            if val is not None and f"{val}" != "":
                vals.append((tag, val))

        def add_attr_string(tag: str) -> None:
            add_string(tag, getattr(self, tag))

        add_attr_string("series")
        add_attr_string("issue")
        add_attr_string("issue_count")
        add_attr_string("title")
        add_attr_string("publisher")
        add_attr_string("year")
        add_attr_string("month")
        add_attr_string("day")
        add_attr_string("volume")
        add_attr_string("volume_count")
        add_attr_string("genre")
        add_attr_string("language")
        add_attr_string("country")
        add_attr_string("critical_rating")
        add_attr_string("alternate_series")
        add_attr_string("alternate_number")
        add_attr_string("alternate_count")
        add_attr_string("imprint")
        add_attr_string("web_link")
        add_attr_string("format")
        add_attr_string("manga")

        if self.black_and_white:
            add_attr_string("black_and_white")
        add_attr_string("maturity_rating")
        add_attr_string("story_arc")
        add_attr_string("series_group")
        add_attr_string("scan_info")
        add_attr_string("characters")
        add_attr_string("teams")
        add_attr_string("locations")
        add_attr_string("comments")
        add_attr_string("notes")

        add_string("tags", utils.list_to_string(self.tags))

        # find the longest field name
        flen = 0
        for i in vals:
            flen = max(flen, len(i[0]))
        flen += 1

        # format the data nicely
        outstr = ""
        fmt_str = "{0: <" + str(flen) + "} {1}\n"
        for i in vals:
            outstr += fmt_str.format(i[0] + ":", i[1])

        return outstr
