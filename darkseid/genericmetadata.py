"""A class for internal metadata storage

The goal of this class is to handle ALL the data that might come from various
tagging schemes and databases, such as Metron, ComicVine or GCD.  This makes conversion
possible, however lossy it might be

"""

# Copyright 2012-2014 Anthony Beville
# Copyright 2020 Brian Pepple

from dataclasses import dataclass, field, fields
from datetime import date
from decimal import Decimal
from typing import List, Optional, Tuple, TypedDict

import pycountry

MAX_UPC = 17
MAX_ISBN = 13


class Validations:
    def __post_init__(self):
        """Run validation methods if declared.
        The validation method can be a simple check
        that raises ValueError or a transformation to
        the field value.
        The validation is performed by calling a function named:
            `validate_<field_name>(self, value, field) -> field.type`
        """
        for name, field_ in self.__dataclass_fields__.items():
            if method := getattr(self, f"validate_{name}", None):
                setattr(self, name, method(getattr(self, name), field=field_))


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
class Price(Validations):
    amount: Decimal
    country: str = field(default="US")

    def validate_country(self, value: str, **_) -> str:
        if value is None:
            return "US"
        value = value.strip()
        if not value:
            raise ValueError("No value given for country")

        if len(value) == 2:
            obj = pycountry.countries.get(alpha_2=value)
        else:
            try:
                obj = pycountry.countries.lookup(value)
            except LookupError as e:
                raise ValueError(f"Couldn't find country for {value}") from e

        if obj is None:
            raise ValueError(f"Couldn't get country code for {value}")
        return obj.alpha_2


@dataclass
class GeneralResource:
    name: str
    id_: Optional[int] = None


@dataclass
class RoleMetadata(GeneralResource):
    primary: bool = False


@dataclass
class SeriesMetadata(GeneralResource):
    sort_name: Optional[str] = None
    volume: Optional[int] = None
    format: Optional[str] = None


@dataclass
class Arc(GeneralResource):
    number: Optional[int] = None


@dataclass
class CreditMetadata:
    person: str
    role: List[RoleMetadata]
    id_: Optional[int] = None


@dataclass
class GTIN(Validations):
    upc: Optional[int] = None
    isbn: Optional[int] = None

    def validate_upc(self, value: int, **_) -> Optional[int]:
        # sourcery skip: class-extract-method
        if value is None or not isinstance(value, int):
            return None

        int_str = str(value)
        if len(int_str) > MAX_UPC:
            raise ValueError(f"UPC has a length greater than {MAX_UPC}")

        return value

    def validate_isbn(self, value: int, **_) -> Optional[int]:
        if value is None or not isinstance(value, int):
            return None

        int_str = str(value)
        if len(int_str) > MAX_ISBN:
            raise ValueError(f"ISBN has a length greater than {MAX_ISBN}")

        return value


@dataclass
class GenericMetadata:
    is_empty: bool = True
    tag_origin: Optional[str] = None

    info_source: Optional[GeneralResource] = None
    series: Optional[SeriesMetadata] = None
    issue: Optional[str] = None
    collection_title: Optional[str] = None
    stories: List[GeneralResource] = field(default_factory=list)
    publisher: Optional[GeneralResource] = None
    cover_date: Optional[date] = None
    store_date: Optional[date] = None
    prices: List[Price] = field(default_factory=list)
    gtin: Optional[GTIN] = None
    issue_count: Optional[int] = None
    genres: List[GeneralResource] = field(default_factory=list)
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

    story_arcs: List[Arc] = field(default_factory=list)
    series_group: Optional[str] = None
    scan_info: Optional[str] = None

    characters: List[GeneralResource] = field(default_factory=list)
    teams: List[GeneralResource] = field(default_factory=list)
    locations: List[GeneralResource] = field(default_factory=list)

    credits: List[CreditMetadata] = field(default_factory=list)
    reprints: List[GeneralResource] = field(default_factory=list)
    tags: List[GeneralResource] = field(default_factory=list)
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
        assign("collection_title", new_md.collection_title)
        assign("issue_count", new_md.issue_count)
        if len(new_md.stories) > 0:
            assign("stories", new_md.stories)
        assign("publisher", new_md.publisher)
        assign("cover_date", new_md.cover_date)
        assign("store_date", new_md.store_date)
        if len(new_md.prices) > 0:
            assign("price", new_md.prices)
        assign("gtin", new_md.gtin)
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
        if len(new_md.reprints) > 0:
            assign("reprints", new_md.reprints)
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
                    if r.role.casefold() == c.role.casefold():
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
                    if creator.casefold() == existing.person.casefold()
                ),
                (False, None),
            )
            if self.credits
            else (False, None)
        )

    def _role_exists(self, new_role: RoleMetadata, old_roles: List[RoleMetadata]) -> bool:
        return any(role.name.casefold() == new_role.name.casefold() for role in old_roles)

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
        cls = self.__class__
        cls_name = cls.__name__
        indent = " " * 4
        res = [f"{cls_name}("]
        for f in fields(cls):
            value = getattr(self, f.name)
            if value is not None:
                res.append(f"{indent}{f.name} = {value!r},")
        res.append(")")
        return "\n".join(res)
