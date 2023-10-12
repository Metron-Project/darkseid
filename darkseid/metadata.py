"""A class for internal metadata storage.

The goal of this class is to handle ALL the data that might come from various
tagging schemes and databases, such as Metron, ComicVine or GCD.  This makes conversion
possible, however lossy it might be

"""

# Copyright 2012-2014 Anthony Beville
# Copyright 2020 Brian Pepple

from dataclasses import dataclass, field, fields
from datetime import date
from decimal import Decimal
from typing import Optional, TypedDict

import pycountry

MAX_UPC = 17
MAX_ISBN = 13


class Validations:
    def __post_init__(self: "Validations") -> None:
        """
        Run validation methods if declared.

        The validation method can be a simple check that raises ValueError or a transformation
        to the field value. The validation is performed by calling a function named:
        `validate_<field_name>(self, value, field) -> field.type`.

        Args:
            self: The instance of the Validations class.

        Returns:
            None

        Example:
            ```python
            validations = Validations()
            validations.__post_init__()
            ```
        """
        for name, field_ in self.__dataclass_fields__.items():
            if method := getattr(self, f"validate_{name}", None):
                setattr(self, name, method(getattr(self, name), field=field_))


class PageType:
    """These page info classes are exactly the same as the CIX scheme, since
    it's unique.
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

    @staticmethod
    def validate_country(value: str, **_: any) -> str:
        """
        Validates a country value.

        If the value is None, it returns the default country code "US". Otherwise, it strips
        any leading or trailing whitespace from the value. If the value is empty after
        stripping, it raises a ValueError.

        If the length of the value is 2, it tries to find the country object using the alpha-2
        code. Otherwise, it tries to look up the country object using the value. If the country
        object is not found, it raises a ValueError.

        Args:
            value (str): The country value to validate.
            **_ (any): Additional keyword arguments (ignored).

        Returns:
            str: The validated country code.

        Raises:
            ValueError: Raised when the value is empty, or when the country object cannot be
            found.

        Example:
            ```python
            country = "US"
            validated_country = Validations.validate_country(country)
            print(validated_country)  # Output: "US"
            ```
        """
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
class Basic:
    name: str
    id_: Optional[int] = None


@dataclass
class Role(Basic):
    primary: bool = False


@dataclass
class Series(Basic, Validations):
    sort_name: Optional[str] = None
    volume: Optional[int] = None
    format: Optional[str] = None
    language: Optional[str] = None  # 2-letter iso code

    @staticmethod
    def validate_language(value: str, **_: any) -> Optional[str]:
        """
        Validates a language value.

        If the value is empty, it returns None. Otherwise, it strips any leading or trailing
        whitespace from the value. If the length of the value is 2, it tries to find the
        language object using the alpha-2 code. Otherwise, it tries to look up the language
        object using the value. If the language object is not found, it raises a ValueError.

        Args:
            value (str): The language value to validate.
            **_ (any): Additional keyword arguments (ignored).

        Returns:
            Optional[str]: The validated language code, or None if the value is empty.

        Raises:
            ValueError: Raised when the language object cannot be found.

        Example:
            ```python
            language = "en"
            validated_language = Validations.validate_language(language)
            print(validated_language)  # Output: "en"
            ```
        """
        if not value:
            return None
        value = value.strip()
        if len(value) == 2:
            obj = pycountry.languages.get(alpha_2=value)
        else:
            try:
                obj = pycountry.languages.lookup(value)
            except LookupError as e:
                raise ValueError(f"Couldn't find language for {value}") from e
        if obj is None:
            raise ValueError(f"Couldn't get language code for {value}")
        return obj.alpha_2


@dataclass
class Arc(Basic):
    number: Optional[int] = None


@dataclass
class Credit:
    person: str
    role: list[Role]
    id_: Optional[int] = None


@dataclass
class GTIN(Validations):
    upc: Optional[int] = None
    isbn: Optional[int] = None

    @staticmethod
    def validate_upc(value: int, **_: any) -> Optional[int]:
        """
        Validates a UPC (Universal Product Code) value.

        If the value is None or not an instance of int, it returns None. Otherwise, it checks
        if the length of the UPC value is greater than the maximum allowed length. If it is, it
        raises a ValueError.

        Args:
            value (int): The UPC value to validate.
            **_ (any): Additional keyword arguments (ignored).

        Returns:
            Optional[int]: The validated UPC value, or None if the value is None or not an
            instance of int.

        Raises:
            ValueError: Raised when the length of the UPC value is greater than the maximum
            allowed length.

        Example:
            ```python
            upc = 1234567890
            validated_upc = Validations.validate_upc(upc)
            print(validated_upc)  # Output: 1234567890
            ```
        """
        # sourcery skip: class-extract-method
        if value is None or not isinstance(value, int):
            return None

        int_str = str(value)
        if len(int_str) > MAX_UPC:
            raise ValueError(f"UPC has a length greater than {MAX_UPC}")

        return value

    @staticmethod
    def validate_isbn(value: int, **_: any) -> Optional[int]:
        """
        Validates an ISBN (International Standard Book Number) value.

        If the value is None or not an instance of int, it returns None. Otherwise, it checks
        if the length of the ISBN value is greater than the maximum allowed length. If it is,
        it raises a ValueError.

        Args:
            value (int): The ISBN value to validate.
            **_ (any): Additional keyword arguments (ignored).

        Returns:
            Optional[int]: The validated ISBN value, or None if the value is None or not an
            instance of int.

        Raises:
            ValueError: Raised when the length of the ISBN value is greater than the maximum
            allowed length.

        Example:
            ```python
            isbn = 1234567890
            validated_isbn = Validations.validate_isbn(isbn)
            print(validated_isbn)  # Output: 1234567890
            ```
        """
        if value is None or not isinstance(value, int):
            return None

        int_str = str(value)
        if len(int_str) > MAX_ISBN:
            raise ValueError(f"ISBN has a length greater than {MAX_ISBN}")

        return value


@dataclass
class Metadata:
    """
    Represents metadata for a comic.

    Attributes:
        is_empty (bool): Indicates if the metadata is empty.
        tag_origin (Optional[str]): The origin of the tag.
        info_source (Optional[Basic]): The information source.
        series (Optional[Series]): The series information.
        issue (Optional[str]): The issue information.
        collection_title (Optional[str]): The title of the collection.
        stories (list[Basic]): The list of stories.
        publisher (Optional[Basic]): The publisher information.
        cover_date (Optional[date]): The cover date.
        store_date (Optional[date]): The store date.
        prices (list[Price]): The list of prices.
        gtin (Optional[GTIN]): The GTIN (Global Trade Item Number).
        issue_count (Optional[int]): The count of issues.
        genres (list[Basic]): The list of genres.
        comments (Optional[str]): The comments.
        volume_count (Optional[str]): The count of volumes.
        critical_rating (Optional[str]): The critical rating.
        country (Optional[str]): The country.
        alternate_series (Optional[str]): The alternate series.
        alternate_number (Optional[str]): The alternate number.
        alternate_count (Optional[int]): The count of alternates.
        imprint (Optional[str]): The imprint.
        notes (Optional[str]): The notes.
        web_link (Optional[str]): The web link.
        manga (Optional[str]): The manga information.
        black_and_white (Optional[bool]): Indicates if the comic is black and white.
        page_count (Optional[int]): The count of pages.
        age_rating (Optional[str]): The age rating.
        story_arcs (list[Arc]): The list of story arcs.
        series_group (Optional[str]): The series group.
        scan_info (Optional[str]): The scan information.
        characters (list[Basic]): The list of characters.
        teams (list[Basic]): The list of teams.
        locations (list[Basic]): The list of locations.
        credits (list[Credit]): The list of credits.
        reprints (list[Basic]): The list of reprints.
        tags (list[Basic]): The list of tags.
        pages (list[ImageMetadata]): The list of pages.

    Methods:
        __post_init__: Initializes the metadata object.
        overlay: Overlays a metadata object on this one.
        overlay_credits: Overlays the credits from a new metadata object.
        set_default_page_list: Sets a default page list.
        get_archive_page_index: Gets the archive page index for a given displayed page number.
        get_cover_page_index_list: Gets a list of archive page indices of cover pages.
        _existing_credit: Checks if a credit with the given creator already exists.
        _role_exists: Checks if a role already exists in the old roles list.
        add_credit: Adds a new credit to the metadata.
        __str__: Returns a string representation of the metadata.

    Example:
        ```python
        metadata = Metadata(is_empty=True)
        metadata.overlay(new_md)
        print(metadata)
        ```
    """

    is_empty: bool = True
    tag_origin: Optional[str] = None

    info_source: Optional[Basic] = None
    series: Optional[Series] = None
    issue: Optional[str] = None
    collection_title: Optional[str] = None
    stories: list[Basic] = field(default_factory=list)
    publisher: Optional[Basic] = None
    cover_date: Optional[date] = None
    store_date: Optional[date] = None
    prices: list[Price] = field(default_factory=list)
    gtin: Optional[GTIN] = None
    issue_count: Optional[int] = None
    genres: list[Basic] = field(default_factory=list)
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

    story_arcs: list[Arc] = field(default_factory=list)
    series_group: Optional[str] = None
    scan_info: Optional[str] = None

    characters: list[Basic] = field(default_factory=list)
    teams: list[Basic] = field(default_factory=list)
    locations: list[Basic] = field(default_factory=list)

    credits: list[Credit] = field(default_factory=list)
    reprints: list[Basic] = field(default_factory=list)
    tags: list[Basic] = field(default_factory=list)
    pages: list[ImageMetadata] = field(default_factory=list)

    def __post_init__(self: "Metadata") -> None:
        """
        Executes the post-initialization process for a Metadata instance.

        The method iterates over the attributes of the Metadata object and checks if any
        attribute has a non-empty value, excluding the "is_empty" attribute. If a non-empty
        value is found, the "is_empty" attribute is set to False and the iteration is stopped.

        Args:
            self (Metadata): The Metadata instance.

        Returns:
            None

        Example:
            ```python
            metadata = Metadata()
            metadata.__post_init__()
            print(metadata.is_empty)  # Output: False
            ```
        """
        for key, value in self.__dict__.items():
            if value and key != "is_empty":
                self.is_empty = False
                break

    def overlay(self: "Metadata", new_md: "Metadata") -> None:
        """
        Overlays a metadata object on this one.

        The method assigns non-None values from the new metadata object to the corresponding
        attributes of the current metadata object. If a value is an empty string, it is
        assigned as None. The "is_empty" attribute of the current metadata object is set to
        False if the new metadata object is not empty.

        Args:
            self (Metadata): The current metadata object.
            new_md (Metadata): The new metadata object to overlay.

        Returns:
            None

        Example:
            ```python
            metadata = Metadata()
            new_metadata = Metadata(series="Series 1", issue="Issue 1")
            metadata.overlay(new_metadata)
            print(metadata.series)  # Output: "Series 1"
            print(metadata.issue)  # Output: "Issue 1"
            ```
        """

        def assign(cur: str, new: any) -> None:
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

    def overlay_credits(self: "Metadata", new_credits: list[Credit]) -> None:
        """
        Overlays the credits from a new metadata object on the current metadata object.

        The method iterates over the new credits and removes any credit role if the person is
        blank. If the person is not blank, the "primary" attribute of the credit is set based
        on the presence of the "primary" key in the credit dictionary. The credit is then
        added to the current metadata object using the "add_credit" method.

        Args:
            self (Metadata): The current metadata object.
            new_credits (list[Credit]): The list of new credits to overlay.

        Returns:
            None

        Example:
            ```python
            metadata = Metadata()
            new_credits = [Credit(person="John Doe", role="Writer")]
            metadata.overlay_credits(new_credits)
            print(metadata.credits)  # Output: [Credit(person="John Doe", role="Writer")]
            ```
        """
        for c in new_credits:
            # Remove credit role if person is blank
            if c.person == "":
                for r in reversed(self.credits):
                    if r.role.casefold() == c.role.casefold():
                        self.credits.remove(r)
            else:
                c.primary = bool("primary" in c and c.primary)
                self.add_credit(c)

    def set_default_page_list(self: "Metadata", count: int) -> None:
        """
        Generates a default page list for the Metadata object.

        The method creates a default page list with the specified count. Each page is
        represented by an ImageMetadata object with the "Image" attribute set to the
        corresponding index. The first page is marked as the front cover by setting the "Type"
        attribute to PageType.FrontCover. The generated page list is appended to the "pages"
        attribute of the Metadata object.

        Args:
            self (Metadata): The Metadata object.
            count (int): The count of pages to generate.

        Returns:
            None

        Example:
            ```python
            metadata = Metadata()
            metadata.set_default_page_list(5)
            print(metadata.pages)
            # Output: [ImageMetadata(Image=0, Type=PageType.FrontCover),
            # ImageMetadata(Image=1), ImageMetadata(Image=2), ImageMetadata(Image=3),
            # ImageMetadata(Image=4)]
            ```
        """
        # generate a default page list, with the first page marked as the cover
        for i in range(count):
            page_dict = ImageMetadata(Image=i)
            if i == 0:
                page_dict["Type"] = PageType.FrontCover
            self.pages.append(page_dict)

    def get_archive_page_index(self: "Metadata", pagenum: int) -> int:
        """
        Converts the displayed page number to the page index of the file in the archive.

        The method takes a displayed page number and returns the corresponding page index in
        the archive. If the displayed page number is within the range of the available pages,
        the "Image" attribute of the corresponding page in the "pages" attribute of the
        Metadata object is returned as an integer. If the displayed page number is out of
        range, 0 is returned.

        Args:
            self (Metadata): The Metadata object.
            pagenum (int): The displayed page number.

        Returns:
            int: The page index in the archive.

        Example:
            ```python
            metadata = Metadata()
            metadata.pages = [ImageMetadata(Image=0), ImageMetadata(Image=1), ImageMetadata(Image=2)]
            index = metadata.get_archive_page_index(1)
            print(index)  # Output: 1
            ```
        """  # noqa: E501

        # convert the displayed page number to the page index of the file in the archive
        return int(self.pages[pagenum]["Image"]) if pagenum < len(self.pages) else 0

    def get_cover_page_index_list(self: "Metadata") -> list[int]:
        """
        Returns a list of archive page indices of cover pages.

        The method iterates over the pages in the Metadata object and checks if a page is
        marked as a front cover by having a "Type" attribute equal to PageType.FrontCover. If a
        front cover page is found, its "Image" attribute is added to the coverlist. If no front
        cover pages are found, the coverlist is initialized with a single element of 0.

        Returns:
            list[int]: The list of archive page indices of cover pages.

        Example:
            ```python
            metadata = Metadata()
            metadata.pages = [ImageMetadata(Image=0, Type=PageType.FrontCover),ImageMetadata(Image=1), ImageMetadata(Image=2)]
            cover_indices = metadata.get_cover_page_index_list()
            print(cover_indices)  # Output: [0]
            ```
        """  # noqa: E501
        coverlist = [
            int(p["Image"])
            for p in self.pages
            if "Type" in p and p["Type"] == PageType.FrontCover
        ]

        if not coverlist:
            coverlist.append(0)

        return coverlist

    def _existing_credit(self: "Metadata", creator: str) -> tuple[bool, Optional[int]]:
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

    @staticmethod
    def _role_exists(new_role: Role, old_roles: list[Role]) -> bool:
        return any(role.name.casefold() == new_role.name.casefold() for role in old_roles)

    def add_credit(self: "Metadata", new_credit: Credit) -> None:
        exist, idx = self._existing_credit(new_credit.person)
        if exist:
            existing_credit: Credit = self.credits[idx]
            for new_role in new_credit.role:
                if not self._role_exists(new_role, existing_credit.role):
                    existing_credit.role.append(new_role)
        else:
            self.credits.append(new_credit)

    def __str__(self: "Metadata") -> str:
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
