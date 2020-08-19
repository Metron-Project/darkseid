"""A class for internal metadata storage

The goal of this class is to handle ALL the data that might come from various
tagging schemes and databases, such as ComicVine or GCD.  This makes conversion
possible, however lossy it might be

"""

# Copyright 2012-2014 Anthony Beville

from typing import Dict, List, Optional

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
        self.black_and_white: Optional[str] = None
        self.page_count: Optional[str] = None
        self.maturity_rating: Optional[str] = None

        self.story_arc: Optional[str] = None
        self.series_group: Optional[str] = None
        self.scan_info: Optional[str] = None

        self.characters: Optional[str] = None
        self.teams: Optional[str] = None
        self.locations: Optional[str] = None

        # TODO: Need to type hint the credits.
        self.credits = []
        self.tags: List[str] = []
        self.pages: List[Dict[str, str]] = []

        # Some CoMet-only items
        self.price: Optional[str] = None
        self.is_version_of: Optional[str] = None
        self.rights: Optional[str] = None
        self.identifier: Optional[str] = None
        self.last_mark: Optional[str] = None
        self.cover_image: Optional[str] = None

    def overlay(self, new_md):
        """Overlay a metadata object on this one

        That is, when the new object has non-None values, over-write them
        to this one.
        """

        def assign(cur, new):
            if new is not None:
                if isinstance(new, str) and len(new) == 0:
                    setattr(self, cur, None)
                else:
                    setattr(self, cur, new)

        if not new_md.is_empty:
            self.is_empty = False

        assign("series", new_md.series)
        assign("issue", new_md.issue)
        assign("issue_count", new_md.issue_count)
        assign("title", new_md.title)
        assign("publisher", new_md.publisher)
        assign("day", new_md.day)
        assign("month", new_md.month)
        assign("year", new_md.year)
        assign("volume", new_md.volume)
        assign("volume_count", new_md.volume_count)
        assign("genre", new_md.genre)
        assign("language", new_md.language)
        assign("country", new_md.country)
        assign("critical_rating", new_md.critical_rating)
        assign("alternate_series", new_md.alternate_series)
        assign("alternate_number", new_md.alternate_number)
        assign("alternate_count", new_md.alternate_count)
        assign("imprint", new_md.imprint)
        assign("web_link", new_md.web_link)
        assign("format", new_md.format)
        assign("manga", new_md.manga)
        assign("black_and_white", new_md.black_and_white)
        assign("maturity_rating", new_md.maturity_rating)
        assign("story_arc", new_md.story_arc)
        assign("series_group", new_md.series_group)
        assign("scan_info", new_md.scan_info)
        assign("characters", new_md.characters)
        assign("teams", new_md.teams)
        assign("locations", new_md.locations)
        assign("comments", new_md.comments)
        assign("notes", new_md.notes)

        assign("price", new_md.price)
        assign("is_version_of", new_md.is_version_of)
        assign("rights", new_md.rights)
        assign("identifier", new_md.identifier)
        assign("last_mark", new_md.last_mark)

        self.overlay_credits(new_md.credits)
        # TODO

        # not sure if the tags and pages should broken down, or treated
        # as whole lists....

        # For now, go the easy route, where any overlay
        # value wipes out the whole list
        if len(new_md.tags) > 0:
            assign("tags", new_md.tags)

        if len(new_md.pages) > 0:
            assign("pages", new_md.pages)

    def overlay_credits(self, new_credits):
        for credit in new_credits:
            primary = True if "primary" in credit and credit["primary"] else False
            # Remove credit role if person is blank
            if credit["person"] == "":
                for r in reversed(self.credits):
                    if r["role"].lower() == credit["role"].lower():
                        self.credits.remove(r)
            # otherwise, add it!
            else:
                self.add_credit(credit["person"], credit["role"], primary)

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

    def get_cover_page_index_list(self):
        # return a list of archive page indices of cover pages
        coverlist = [
            int(page["Image"])
            for page in self.pages
            if "Type" in page and page["Type"] == PageType.FrontCover
        ]

        if not coverlist:
            coverlist.append(0)

        return coverlist

    def add_credit(self, person, role, primary=False):

        credit = {"person": person, "role": role}
        if primary:
            credit["primary"] = primary

        # look to see if it's not already there...
        found = False
        for c in self.credits:
            if (
                c["person"].lower() == person.lower()
                and c["role"].lower() == role.lower()
            ):
                # no need to add it. just adjust the "primary" flag as needed
                c["primary"] = primary
                found = True
                break

        if not found:
            self.credits.append(credit)

    def __str__(self):
        vals = []
        if self.is_empty:
            return "No metadata"

        def add_string(tag, val):
            if val is not None and "{0}".format(val) != "":
                vals.append((tag, val))

        def add_attr_string(tag):
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

        add_attr_string("price")
        add_attr_string("is_version_of")
        add_attr_string("rights")
        add_attr_string("identifier")
        add_attr_string("last_mark")

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

        for c in self.credits:
            primary = ""
            if "primary" in c and c["primary"]:
                primary = " [P]"
            add_string("credit", c["role"] + ": " + c["person"] + primary)

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
