"""A class for internal metadata storage

The goal of this class is to handle ALL the data that might come from various
tagging schemes and databases, such as Metron, ComicVine or GCD.  This makes conversion
possible, however lossy it might be

"""

# Copyright 2012-2014 Anthony Beville
# Copyright 2020 Brian Pepple

from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Tuple, TypedDict

from .utils import list_to_string


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


class ImageMetadata(TypedDict, total=False):
    Type: str
    Bookmark: str
    DoublePage: bool
    Image: int
    ImageSize: str
    ImageHeight: str
    ImageWidth: str


@dataclass
class RoleMetadata:
    name: str
    id: Optional[int] = None
    primary: bool = False


@dataclass
class CreditMetadata:
    person: str
    role: List[RoleMetadata]


@dataclass
class SeriesMetadata:
    name: str
    sort_name: Optional[str] = None
    volume: Optional[int] = None
    format: Optional[str] = None


@dataclass
class InfoSourceMetadata:
    source: str
    id: int


@dataclass
class GenericMetadata:
    is_empty: bool = True
    tag_origin: Optional[str] = None

    info_source: Optional[InfoSourceMetadata] = None
    series: Optional[SeriesMetadata] = None
    issue: Optional[str] = None
    stories: List[str] = field(default_factory=list)
    publisher: Optional[str] = None
    cover_date: Optional[date] = None
    store_date: Optional[date] = None
    issue_count: Optional[int] = None
    genres: List[str] = field(default_factory=list)
    language: Optional[str] = None  # 2 letter iso code
    comments: Optional[str] = None  # use same way as Summary in CIX

    volume_count: Optional[str] = None
    critical_rating: Optional[str] = None
    country: Optional[str] = None

    alternate_series: Optional[str] = None
    alternate_number: Optional[str] = None
    alternate_count: Optional[int] = None
    imprint: Optional[str] = None
    notes: Optional[str] = None
    web_link: Optional[str] = None
    manga: Optional[str] = None
    black_and_white: Optional[bool] = None
    page_count: Optional[int] = None
    age_rating: Optional[str] = None

    story_arcs: List[str] = field(default_factory=list)
    series_group: Optional[str] = None
    scan_info: Optional[str] = None

    characters: List[str] = field(default_factory=list)
    teams: List[str] = field(default_factory=list)
    locations: List[str] = field(default_factory=list)

    credits: List[CreditMetadata] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    pages: List[ImageMetadata] = field(default_factory=list)

    def __post_init__(self):
        for key, value in self.__dict__.items():
            if value and key != "is_empty":
                self.is_empty = False
                break

    def overlay(self, new_md: "GenericMetadata") -> None:
        """Overlay a metadata object on this one

        That is, when the new object has non-None values, over-write them
        to this one.
        """

        def assign(cur, new) -> None:
            if new is not None:
                if isinstance(new, str) and len(new) == 0:
                    setattr(self, cur, None)
                else:
                    setattr(self, cur, new)

        if not new_md.is_empty:
            self.is_empty = False

        assign("series", new_md.series)
        assign("info_source", new_md.info_source)
        assign("issue", new_md.issue)
        assign("issue_count", new_md.issue_count)
        if len(new_md.stories) > 0:
            assign("stories", new_md.stories)
        assign("publisher", new_md.publisher)
        assign("cover_date", new_md.cover_date)
        assign("store_date", new_md.store_date)
        assign("volume_count", new_md.volume_count)
        if len(new_md.genres) > 0:
            assign("genre", new_md.genres)
        assign("language", new_md.language)
        assign("country", new_md.country)
        assign("critical_rating", new_md.critical_rating)
        assign("alternate_series", new_md.alternate_series)
        assign("alternate_number", new_md.alternate_number)
        assign("alternate_count", new_md.alternate_count)
        assign("imprint", new_md.imprint)
        assign("web_link", new_md.web_link)
        assign("manga", new_md.manga)
        assign("black_and_white", new_md.black_and_white)
        assign("age_rating", new_md.age_rating)
        if len(new_md.story_arcs) > 0:
            assign("story_arcs", new_md.story_arcs)
        assign("series_group", new_md.series_group)
        assign("scan_info", new_md.scan_info)
        if len(new_md.characters) > 0:
            assign("characters", new_md.characters)
        if len(new_md.teams) > 0:
            assign("teams", new_md.teams)
        if len(new_md.locations) > 0:
            assign("locations", new_md.locations)
        assign("comments", new_md.comments)
        assign("notes", new_md.notes)

        if new_md.credits:
            self.overlay_credits(new_md.credits)

        # For now, go the easy route, where any overlay
        # value wipes out the whole list
        if len(new_md.tags) > 0:
            assign("tags", new_md.tags)

        if len(new_md.pages) > 0:
            assign("pages", new_md.pages)

    def overlay_credits(self, new_credits: List[CreditMetadata]) -> None:
        for c in new_credits:
            # Remove credit role if person is blank
            if c.person == "":
                for r in reversed(self.credits):
                    if r.role.lower() == c.role.lower():
                        self.credits.remove(r)
            else:
                c.primary = bool("primary" in c and c.primary)
                self.add_credit(c)

    def set_default_page_list(self, count: int) -> None:
        # generate a default page list, with the first page marked as the cover
        for i in range(count):
            page_dict = ImageMetadata(Image=i)
            if i == 0:
                page_dict["Type"] = PageType.FrontCover
            self.pages.append(page_dict)

    def get_archive_page_index(self, pagenum: int) -> int:
        # convert the displayed page number to the page index of the file in the archive
        return int(self.pages[pagenum]["Image"]) if pagenum < len(self.pages) else 0

    def get_cover_page_index_list(self) -> List[int]:
        # return a list of archive page indices of cover pages
        coverlist = [
            int(p["Image"])
            for p in self.pages
            if "Type" in p and p["Type"] == PageType.FrontCover
        ]

        if not coverlist:
            coverlist.append(0)

        return coverlist

    def _existing_credit(self, creator: str) -> Tuple[bool, Optional[int]]:
        return (
            next(
                (
                    (True, i)
                    for i, existing in enumerate(self.credits)
                    if creator.lower() == existing.person.lower()
                ),
                (False, None),
            )
            if self.credits
            else (False, None)
        )

    def _role_exists(self, new_role: RoleMetadata, old_roles: List[RoleMetadata]) -> bool:
        return any(role.name.lower() == new_role.name.lower() for role in old_roles)

    def add_credit(self, new_credit: CreditMetadata) -> None:
        exist, idx = self._existing_credit(new_credit.person)
        if exist:
            existing_credit: CreditMetadata = self.credits[idx]
            for new_role in new_credit.role:
                if not self._role_exists(new_role, existing_credit.role):
                    existing_credit.role.append(new_role)
        else:
            self.credits.append(new_credit)

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
        if self.stories:
            add_attr_string("stories")
        add_attr_string("publisher")
        add_attr_string("cover_date")
        add_attr_string("store_date")
        add_attr_string("volume_count")
        if self.genres:
            add_attr_string("genres")
        add_attr_string("language")
        add_attr_string("country")
        add_attr_string("critical_rating")
        add_attr_string("alternate_series")
        add_attr_string("alternate_number")
        add_attr_string("alternate_count")
        add_attr_string("imprint")
        add_attr_string("web_link")
        add_attr_string("manga")

        if self.black_and_white:
            add_attr_string("black_and_white")
        add_attr_string("age_rating")
        if self.story_arcs:
            add_attr_string("story_arcs")
        add_attr_string("series_group")
        add_attr_string("scan_info")
        if self.characters:
            add_attr_string("characters")
        if self.teams:
            add_attr_string("teams")
        if self.locations:
            add_attr_string("locations")
        add_attr_string("comments")
        add_attr_string("notes")

        add_string("tags", list_to_string(self.tags))

        for c in self.credits:
            primary = ""
            if "primary" in c and c.primary:
                primary = " [P]"
            add_string("credit", c.role + ": " + c.person + primary)

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
