# ruff: noqa: C901, PLR0915
"""A class for internal metadata storage.

The goal of this class is to handle ALL the data that might come from various
tagging schemes and databases, such as Metron, ComicVine or GCD.  This makes conversion
possible, however lossy it might be

"""

# Copyright 2012-2014 Anthony Beville
# Copyright 2020 Brian Pepple
from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING, TypedDict

if TYPE_CHECKING:
    from datetime import date, datetime
    from decimal import Decimal


import pycountry

MAX_UPC = 17
MAX_ISBN = 13
COUNTRY_LEN = 2
YEAR_LEN = 4


class Validations:
    def __init__(self):
        self.__dataclass_fields__ = None

    def __post_init__(self: Validations) -> None:
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
    """
    Defines constants for different types of pages.

    This class provides a set of predefined page types for categorizing pages in a publication.
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
    """
    Defines the structure of ImageMetadata using TypedDict.

    This class represents the metadata associated with an image.
    """

    Type: str
    Bookmark: str
    DoublePage: bool
    Image: int | str
    ImageSize: str
    ImageHeight: str
    ImageWidth: str


@dataclass
class Price(Validations):
    """
    A data class representing a price with validations.

    Attributes:
        amount (Decimal): The amount associated with the price.
        country (str): The country associated with the price, defaults to "US".
    """

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
            ValueError: Raised when the country code cannot be found or when no value is given for the country.
        """

        if value is None:
            return "US"
        value = value.strip()
        if not value:
            msg = "No value given for country"
            raise ValueError(msg)

        if len(value) == COUNTRY_LEN:
            obj = pycountry.countries.get(alpha_2=value)
        else:
            try:
                obj = pycountry.countries.lookup(value)
            except LookupError as e:
                msg = f"Couldn't find country for {value}"
                raise ValueError(msg) from e

        if obj is None:
            msg = f"Couldn't get country code for {value}"
            raise ValueError(msg)
        return obj.alpha_2


@dataclass
class Basic:
    """
    A data class representing basic information.

    Attributes:
        name (str): The name associated with the basic information.
        id_ (int | None): The ID associated with the basic information, defaults to None.
    """

    name: str
    id_: int | str | None = None


@dataclass
class InfoSources:
    """
    Dataclass representing information sources with associated metadata.

    This class is used to store the name, identifier, and primary status of an information source. It allows for
    structured representation of sources, facilitating easier management and access to their attributes.

    Attributes:
        name (str): The name of the information source.
        id_ (int): The unique identifier for the information source.
        primary (bool): A flag indicating if this source is the primary one. Defaults to False.
    """

    name: str
    id_: int | str
    primary: bool = False


@dataclass
class Universe(Basic):
    """
    A data class representing a universe.

    Attributes:
        name (str): The name associated with the basic information.
        id_ (int | None): The ID associated with the basic information, defaults to None.
        designation (str | None): The designation of the universe, defaults to None.
    """

    designation: str | None = None


@dataclass
class Role(Basic):
    """
    A data class representing a role.

    Attributes:
        name (str): The name associated with the basic information.
        id_ (int | None): The ID associated with the basic information, defaults to None.
        primary (bool): Indicates if the role is primary, defaults to False.
    """

    primary: bool = False


@dataclass
class AlternativeNames(Basic):
    """
    A data class representing an alternative name for a series with basic information and validations.

    Attributes:
        name (str): The alternative name for a series.
        id_ (int | None): The ID associated with the alternative name, defaults to None.
        language (str | None): The 2-letter ISO code of the language, defaults to None.

    Static Methods:
        validate_language(value: str, **_: any) -> str | None: Validates a language value.
    """

    language: str | None = None

    @staticmethod
    def validate_language(value: str, **_: any) -> str | None:
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
        """

        if not value:
            return None
        value = value.strip()

        if len(value) == COUNTRY_LEN:
            obj = pycountry.languages.get(alpha_2=value)
        else:
            try:
                obj = pycountry.languages.lookup(value)
            except LookupError as e:
                msg = f"Couldn't find language {value}"
                raise ValueError(msg) from e
        if obj is None:
            msg = f"Couldn't find language {value}"
            raise ValueError(msg)
        return obj.alpha_2


@dataclass
class Series(Basic, Validations):
    """
    A data class representing a series with basic information and validations.

    Attributes:
        name (str): The name associated with the basic information.
        id_ (int | None): The ID associated with the basic information, defaults to None.
        sort_name (str | None): The sort name of the series, defaults to None.
        volume (int | None): The volume of the series, defaults to None.
        format (str | None): The format of the series, defaults to None.
        start_year (int | None): The year that the series started in. A 4 digit value.
        issue_count (Optional[int]): The count of issues.
        volume_count (int | None): The count of volumes.
        alternative_names: list[AlternativeNames]: A list of alternative names for series.
        language (str | None): The 2-letter ISO code of the language, defaults to None.

    Static Methods:
        validate_language(value: str, **_: any) -> str | None: Validates a language value.
    """

    sort_name: str | None = None
    volume: int | None = None
    format: str | None = None
    start_year: int | None = None
    issue_count: int | None = None
    volume_count: int | None = None
    alternative_names: list[AlternativeNames] = field(default_factory=list)
    language: str | None = None  # 2-letter iso code

    @staticmethod
    def validate_start_year(value: int, **_: any) -> int | None:
        if not value:
            return None

        if len(str(value)) == YEAR_LEN:
            return value

        msg = f"Year: {value} length must be {YEAR_LEN}"
        raise ValueError(msg)

    @staticmethod
    def validate_language(value: str, **_: any) -> str | None:
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
        """

        if not value:
            return None
        value = value.strip()

        if len(value) == COUNTRY_LEN:
            obj = pycountry.languages.get(alpha_2=value)
        else:
            try:
                obj = pycountry.languages.lookup(value)
            except LookupError as e:
                msg = f"Couldn't find language {value}"
                raise ValueError(msg) from e
        if obj is None:
            msg = f"Couldn't find language {value}"
            raise ValueError(msg)
        return obj.alpha_2


@dataclass
class Publisher(Basic):
    """
    A data class representing a Publisher with basic information.

    Attributes:
        name (str): The name associated with the basic information.
        id_ (int | None): The ID associated with the basic information, defaults to None.
        imprint (Basic | None): The Imprint of a Publisher with basic information, defaults to None.
    """

    imprint: Basic | None = None


@dataclass
class Arc(Basic):
    """
    A data class representing an arc with basic information.

    Attributes:
        name (str): The name associated with the basic information.
        id_ (int | None): The ID associated with the basic information, defaults to None.
        number (int | None): The number of the arc, defaults to None.
    """

    number: int | None = None


@dataclass
class Credit:
    """
    A data class representing a creator credit.

    Attributes:
        person (str): The name of the person associated with the credit.
        role (list[Role]): The list of roles associated with the credit.
        id_ (int | None): The ID associated with the credit, defaults to None.
    """

    person: str
    role: list[Role]
    id_: int | None = None


@dataclass
class Links:
    """
    Dataclass representing a URL with an optional primary flag.

    This class is used to store a URL and indicate whether it is the primary URL. It can be extended to include validation for the URL format in the future.

    Attributes:
        url (str): The URL string.
        primary (bool): A flag indicating if this URL is the primary one. Defaults to False.
    """

    # TODO: Probably worthwhile to validate the strings are URLS.
    url: str
    primary: bool = False


@dataclass
class Notes:
    """
    Notes is a data class designed to hold notes for the different formats.

    Attributes:
        metron_info (str): A string containing information about the metronome.
        comic_rack (str): A string representing the comic book collection.
    """

    metron_info: str = ""
    comic_rack: str = ""


@dataclass
class AgeRatings:
    """
    Represents age ratings for comics, storing information from different sources.
    This class holds metadata related to age ratings, allowing for easy access and management.

    Attributes:
        metron_info (str): Information related to age ratings from Metron.
        comic_rack (str): Information related to age ratings from Comic Rack.
    """

    metron_info: str = ""
    comic_rack: str = ""


@dataclass
class GTIN(Validations):
    """
    A data class representing a GTIN (Global Trade Item Number) with validations.

    Attributes:
        upc (int | None): The UPC (Universal Product Code) associated with the GTIN, defaults to None.
        isbn (int | None): The ISBN (International Standard Book Number) associated with the GTIN, defaults to None.

    Static Methods:
        validate_upc(value: int, **_: any) -> int | None: Validates a UPC (Universal Product Code) value.
        validate_isbn(value: int, **_: any) -> int | None: Validates an ISBN (International Standard Book Number) value.
    """

    upc: int | None = None
    isbn: int | None = None

    @staticmethod
    def validate_upc(value: int, **_: any) -> int | None:
        """
        Validates a UPC (Universal Product Code) value.

        If the value is None or not an instance of int, it returns None. Otherwise, it checks
        if the length of the UPC value is greater than the maximum allowed length. If it is, it
        raises a ValueError.

        Args:
            value (int): The UPC value to validate.
            **_ (any): Additional keyword arguments (ignored).

        Returns:
            Optional[int]: The validated UPC value, or None if the value is None or not an instance of int.

        Raises:
            ValueError: Raised when the length of the UPC value is greater than the maximum allowed length.
        """

        # sourcery skip: class-extract-method
        if value is None or not isinstance(value, int):
            return None

        int_str = str(value)
        if len(int_str) > MAX_UPC:
            msg = f"UPC has a length greater than {MAX_UPC}"
            raise ValueError(msg)

        return value

    @staticmethod
    def validate_isbn(value: int, **_: any) -> int | None:
        """
        Validates an ISBN (International Standard Book Number) value.

        If the value is None or not an instance of int, it returns None. Otherwise, it checks
        if the length of the ISBN value is greater than the maximum allowed length. If it is,
        it raises a ValueError.

        Args:
            value (int): The ISBN value to validate.
            **_ (any): Additional keyword arguments (ignored).

        Returns:
            Optional[int]: The validated ISBN value, or None if the value is None or not an instance of int.

        Raises:
            ValueError: Raised when the length of the ISBN value is greater than the maximum allowed length.
        """

        if value is None or not isinstance(value, int):
            return None

        int_str = str(value)
        if len(int_str) > MAX_ISBN:
            msg = f"ISBN has a length greater than {MAX_ISBN}"
            raise ValueError(msg)

        return value


@dataclass
class Metadata:
    """
    Represents metadata for a comic.

    Attributes:
        is_empty (bool): Indicates if the metadata is empty.
        tag_origin (Optional[str]): The origin of the tag.
        info_source (Optional[list[InfoSources]]): The information source.
        series (Optional[Series]): The series information.
        issue (Optional[str]): The issue information.
        collection_title (Optional[str]): The title of the collection.
        stories (list[Basic]): The list of stories.
        publisher (Optional[Publisher]): The publisher information.
        cover_date (Optional[date]): The cover date.
        store_date (Optional[date]): The store date.
        prices (list[Price]): The list of prices.
        gtin (Optional[GTIN]): The GTIN (Global Trade Item Number).
        genres (list[Basic]): The list of genres.
        comments (Optional[str]): The comments.
        critical_rating (Optional[str]): The critical rating.
        country (Optional[str]): The country.
        alternate_series (Optional[str]): The alternate series.
        alternate_number (Optional[str]): The alternate number.
        alternate_count (Optional[int]): The count of alternates.
        notes (Optional[Notes]): The notes.
        web_link (Optional[list[Links]]): The web link.
        manga (Optional[str]): The manga information.
        black_and_white (Optional[bool]): Indicates if the comic is black and white.
        page_count (Optional[int]): The count of pages.
        age_rating (Optional[AgeRatings]): The age rating.
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
    tag_origin: str | None = None

    info_source: list[InfoSources] | None = None
    series: Series | None = None
    issue: str | None = None
    collection_title: str | None = None
    stories: list[Basic] = field(default_factory=list)
    publisher: Publisher | None = None
    cover_date: date | None = None
    store_date: date | None = None
    prices: list[Price] = field(default_factory=list)
    gtin: GTIN | None = None
    genres: list[Basic] = field(default_factory=list)
    comments: str | None = None  # use same way as Summary in CIX

    critical_rating: str | None = None
    country: str | None = None

    alternate_series: str | None = None
    alternate_number: str | None = None
    alternate_count: int | None = None
    notes: Notes | None = None
    web_link: list[Links] | None = None
    manga: str | None = None
    black_and_white: bool | None = None
    page_count: int | None = None
    age_rating: AgeRatings | None = None

    story_arcs: list[Arc] = field(default_factory=list)
    series_group: str | None = None
    scan_info: str | None = None

    characters: list[Basic] = field(default_factory=list)
    teams: list[Basic] = field(default_factory=list)
    locations: list[Basic] = field(default_factory=list)
    universes: list[Universe] = field(default_factory=list)

    credits: list[Credit] = field(default_factory=list)
    reprints: list[Basic] = field(default_factory=list)
    tags: list[Basic] = field(default_factory=list)
    pages: list[ImageMetadata] = field(default_factory=list)

    modified: datetime | None = None

    def __post_init__(self: Metadata) -> None:
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

    def overlay(self: Metadata, new_md: Metadata) -> None:  # noqa: PLR0912
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
        if len(new_md.stories) > 0:
            assign("stories", new_md.stories)
        assign("publisher", new_md.publisher)
        assign("cover_date", new_md.cover_date)
        assign("store_date", new_md.store_date)
        if len(new_md.prices) > 0:
            assign("price", new_md.prices)
        assign("gtin", new_md.gtin)
        if len(new_md.genres) > 0:
            assign("genre", new_md.genres)
        assign("country", new_md.country)
        assign("critical_rating", new_md.critical_rating)
        assign("alternate_series", new_md.alternate_series)
        assign("alternate_number", new_md.alternate_number)
        assign("alternate_count", new_md.alternate_count)
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
        if len(new_md.universes) > 0:
            assign("universes", new_md.universes)
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

    def overlay_credits(self: Metadata, new_credits: list[Credit]) -> None:
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
        for credit in new_credits:
            # Remove credit role if person is blank
            if credit.person == "":
                for r in reversed(self.credits):
                    if r.role.casefold() == credit.role.casefold():
                        self.credits.remove(r)
            else:
                credit.primary = bool("primary" in credit and credit.primary)
                self.add_credit(credit)

    def set_default_page_list(self: Metadata, count: int) -> None:
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

    def get_archive_page_index(self: Metadata, pagenum: int) -> int:
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
        """

        # convert the displayed page number to the page index of the file in the archive
        return int(self.pages[pagenum]["Image"]) if pagenum < len(self.pages) else 0

    def get_cover_page_index_list(self: Metadata) -> list[int]:
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
        """
        coverlist = [
            int(p["Image"]) for p in self.pages if "Type" in p and p["Type"] == PageType.FrontCover
        ]

        if not coverlist:
            coverlist.append(0)

        return coverlist

    def _existing_credit(self: Metadata, creator: str) -> tuple[bool, int | None]:
        """
        Checks if a credit with the specified creator already exists in the Metadata.

        Args:
            creator (str): The creator to check for in the existing credits.

        Returns:
            tuple[bool, int | None]: A tuple containing a boolean indicating if the credit exists and the index of the existing credit, or None if not found.
        """

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
        """
        Checks if a role already exists in the list of old roles.

        Args:
            new_role (Role): The new role to check for in the old roles list.
            old_roles (list[Role]): The list of old roles to check against.

        Returns:
            bool: True if the role already exists, False otherwise.
        """

        return any(role.name.casefold() == new_role.name.casefold() for role in old_roles)

    def add_credit(self: Metadata, new_credit: Credit) -> None:
        """
        Adds a new credit to the Metadata.

        If a credit with the same person already exists, the roles from the new credit are added to the existing credit.
        If the person is new, the new credit is appended to the list of credits.

        Args:
            new_credit (Credit): The new credit to add to the Metadata.

        Returns:
            None
        """

        exist, idx = self._existing_credit(new_credit.person)
        if exist:
            existing_credit: Credit = self.credits[idx]
            for new_role in new_credit.role:
                if not self._role_exists(new_role, existing_credit.role):
                    existing_credit.role.append(new_role)
        else:
            self.credits.append(new_credit)

    def __str__(self: Metadata) -> str:
        """
        Returns a string representation of the Metadata object with its attributes and values.
        """

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
