"""A class to encapsulate MetronInfo.xml data."""

# Copyright 2024 Brian Pepple

from __future__ import annotations

__all__ = ["MetronInfo"]

import xml.etree.ElementTree as ET
from decimal import Decimal
from pathlib import Path
from typing import TYPE_CHECKING
from xml.etree.ElementTree import ParseError

from defusedxml.ElementTree import fromstring
from xmlschema import XMLSchema11, XMLSchemaValidationError

from darkseid.base_metadata_handler import BaseMetadataHandler, XmlError
from darkseid.issue_string import IssueString
from darkseid.metadata import (
    GTIN,
    AgeRatings,
    AlternativeNames,
    Arc,
    Basic,
    Credit,
    InfoSources,
    Links,
    Metadata,
    Notes,
    Price,
    Publisher,
    Role,
    Series,
    Universe,
)

if TYPE_CHECKING:
    from datetime import date

# Constants
EARLIEST_YEAR = 1900
VOLUME_THRESHOLD = 1000
DEFAULT_COUNTRY = "US"

# Validation sets
VALID_INFO_SOURCES = frozenset(
    {
        "anilist",
        "comic vine",
        "grand comics database",
        "kitsu",
        "mangadex",
        "mangaupdates",
        "marvel",
        "metron",
        "myanimelist",
        "league of comic geeks",
    }
)

VALID_AGE_RATINGS = frozenset(
    {"unknown", "everyone", "teen", "teen plus", "mature", "explicit", "adult"}
)

VALID_SERIES_FORMATS = frozenset(
    {
        "annual",
        "digital chapter",
        "graphic novel",
        "hardcover",
        "limited series",
        "omnibus",
        "one-shot",
        "single issue",
        "trade paperback",
    }
)

VALID_ROLES = frozenset(
    {
        "writer",
        "script",
        "story",
        "plot",
        "interviewer",
        "artist",
        "penciller",
        "layouts",
        "breakdowns",
        "illustrator",
        "inker",
        "embellisher",
        "finishes",
        "ink assists",
        "colorist",
        "color separations",
        "color assists",
        "color flats",
        "digital art technician",
        "gray tone",
        "letterer",
        "cover",
        "editor",
        "consulting editor",
        "assistant editor",
        "associate editor",
        "group editor",
        "senior editor",
        "managing editor",
        "collection editor",
        "production",
        "designer",
        "logo design",
        "translator",
        "supervising editor",
        "executive editor",
        "editor in chief",
        "president",
        "publisher",
        "chief creative officer",
        "executive producer",
        "other",
    }
)

# Rating mappings
RATING_MAPPINGS = {
    "Unknown": frozenset({"rating pending", "unknown"}),
    "Everyone": frozenset({"everyone", "everyone 10+", "g", "kids to adults", "early childhood"}),
    "Teen": frozenset({"pg", "teen"}),
    "Teen Plus": frozenset({"ma15+"}),
    "Mature": frozenset({"adults only 18+", "mature 17+", "r18+", "m"}),
    "Explicit": frozenset({"x18+"}),
}

# Series format mappings
FORMAT_MAPPINGS = {
    "Annual": frozenset({"annual"}),
    "Digital Chapter": frozenset({"digital chapter", "digital"}),
    "Graphic Novel": frozenset({"graphic novel"}),
    "Hardcover": frozenset({"hardcover", "hard-cover"}),
    "Limited Series": frozenset({"limited series"}),
    "Omnibus": frozenset({"omnibus"}),
    "One-Shot": frozenset({"1 shot", "1-shot", "fcbd", "one shot", "one-shot", "preview"}),
    "Single Issue": frozenset(
        {"single issue", "magazine", "series", "giant", "giant size", "giant-size"}
    ),
    "Trade Paperback": frozenset({"trade paperback", "tpb", "trade paper back"}),
}


class MetronInfo(BaseMetadataHandler):
    """A class to manage comic metadata and its MetronInfo XML representation.

    This class provides methods to convert metadata to and from XML format, validate information sources,
    and manage various attributes related to comic series, genres, and roles.
    """

    def __init__(self) -> None:
        """Initialize the MetronInfo instance."""
        self._schema_path = Path("darkseid") / "schemas" / "MetronInfo" / "v1" / "MetronInfo.xsd"

    def metadata_from_string(self, xml_string: str) -> Metadata:
        """Convert an XML string to a Metadata object.

        Args:
            xml_string: The XML string to be converted.

        Returns:
            The resulting Metadata object.
        """
        try:
            tree = ET.ElementTree(fromstring(xml_string))
        except ParseError:
            return Metadata()
        return self._convert_xml_to_metadata(tree)

    def string_from_metadata(self, metadata: Metadata, xml_bytes: bytes = b"") -> str:
        """Convert a Metadata object to an XML string.

        Args:
            metadata: The Metadata object to convert.
            xml_bytes: Optional XML bytes to include.

        Returns:
            The resulting XML string.
        """
        tree = self._convert_metadata_to_xml(metadata, xml_bytes)
        return ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True).decode()

    def write_xml(self, filename: Path, metadata: Metadata, xml_bytes: bytes | None = None) -> None:
        """Write a Metadata object to an XML file.

        Args:
            filename: The path to the file where the XML will be written.
            metadata: The Metadata object to write.
            xml_bytes: Optional XML bytes to include.

        Raises:
            XmlError: If XML validation fails.
        """
        tree = self._convert_metadata_to_xml(metadata, xml_bytes)
        self._validate_xml(tree)
        # Create parent directories if they don't exist
        Path(filename.parent).mkdir(parents=True, exist_ok=True)
        tree.write(filename, encoding="UTF-8", xml_declaration=True)

    def _validate_xml(self, tree: ET.ElementTree) -> None:
        """Validate XML against schema.

        Args:
            tree: The XML tree to validate.

        Raises:
            XmlError: If validation fails.
        """
        try:
            schema = XMLSchema11(self._schema_path)
            schema.validate(tree)
        except XMLSchemaValidationError as e:
            msg = f"Failed to validate XML: {e!r}"
            raise XmlError(msg) from e

    @staticmethod
    def _get_root(xml_bytes: bytes | None) -> ET.Element:
        """Get or create root XML element.

        Args:
            xml_bytes: Optional XML bytes to parse.

        Returns:
            Root XML element.
        """
        if not xml_bytes:
            return ET.Element("MetronInfo")
        try:
            return ET.ElementTree(fromstring(xml_bytes)).getroot()
        except ParseError:
            return ET.Element("MetronInfo")

    @staticmethod
    def _is_valid_info_source(source: str | None) -> bool:
        """Check if info source is valid.

        Args:
            source: Source name to validate.

        Returns:
            True if valid, False otherwise.
        """
        if not isinstance(source, str):
            return False
        return source.strip().lower() in VALID_INFO_SOURCES

    @staticmethod
    def _normalize_age_rating(age_rating: AgeRatings | None) -> str | None:
        """Normalize age rating to valid MetronInfo format.

        Args:
            age_rating: Age rating to normalize.

        Returns:
            Normalized age rating or None.
        """
        if not age_rating:
            return None

        if age_rating.metron_info:
            return (
                "Unknown"
                if age_rating.metron_info.lower() not in VALID_AGE_RATINGS
                else age_rating.metron_info
            )

        if age_rating.comic_rack:
            lower_val = age_rating.comic_rack.lower()
            for rating, synonyms in RATING_MAPPINGS.items():
                if lower_val in synonyms:
                    return rating

        return None

    @staticmethod
    def _normalize_series_format(format_str: str | None) -> str | None:
        """Normalize series format to valid MetronInfo format.

        Args:
            format_str: Format string to normalize.

        Returns:
            Normalized format or None.
        """
        if not format_str:
            return None

        lower_val = format_str.strip().lower()
        return next(
            (fmt for fmt, synonyms in FORMAT_MAPPINGS.items() if lower_val in synonyms),
            None,
        )

    @staticmethod
    def _set_date_element(root: ET.Element, tag: str, date_val: date | None = None) -> None:
        """Set date element in YYYY-MM-DD format.

        Args:
            root: Root element.
            tag: Element tag name.
            date_val: Date value.
        """
        element = root.find(tag)
        if date_val is None:
            if element is not None:
                root.remove(element)
        else:
            # Skip dates with invalid years
            if date_val.year < EARLIEST_YEAR:
                return
            if element is None:
                element = ET.SubElement(root, tag)
            element.text = date_val.strftime("%Y-%m-%d")

    def _add_basic_children(
        self, root: ET.Element, parent_tag: str, child_tag: str, items: list[Basic]
    ) -> None:
        """Add basic child elements with optional IDs.

        Args:
            root: Root element.
            parent_tag: Parent container tag.
            child_tag: Child element tag.
            items: List of basic items to add.
        """
        if not items:
            return

        parent_node = self._get_or_create_element(root, parent_tag)
        for item in items:
            child_node = ET.SubElement(parent_node, child_tag)
            child_node.text = item.name
            if item.id_:
                child_node.attrib["id"] = str(item.id_)

    def _add_arcs(self, root: ET.Element, arcs: list[Arc]) -> None:
        """Add story arcs to XML.

        Args:
            root: Root element.
            arcs: List of story arcs.
        """
        if not arcs:
            return

        parent_node = self._get_or_create_element(root, "Arcs")
        for arc in arcs:
            attributes = {"id": str(arc.id_)} if arc.id_ else {}
            arc_node = ET.SubElement(parent_node, "Arc", attrib=attributes)
            ET.SubElement(arc_node, "Name").text = arc.name
            if arc.number:
                ET.SubElement(arc_node, "Number").text = str(arc.number)

    def _add_publisher(self, root: ET.Element, publisher: Publisher | None) -> None:
        """Add publisher information to XML.

        Args:
            root: Root element.
            publisher: Publisher information.
        """
        if not publisher:
            return

        publisher_node = self._get_or_create_element(root, "Publisher")
        if publisher.id_:
            publisher_node.attrib = {"id": str(publisher.id_)}

        ET.SubElement(publisher_node, "Name").text = publisher.name

        if publisher.imprint:
            imprint_attrib = {"id": str(publisher.imprint.id_)} if publisher.imprint.id_ else {}
            imprint_node = ET.SubElement(publisher_node, "Imprint", imprint_attrib)
            imprint_node.text = publisher.imprint.name

    def _add_series(self, root: ET.Element, series: Series | None) -> None:  # noqa: C901,PLR0912
        """Add series information to XML.

        Args:
            root: Root element.
            series: Series information.
        """
        if not series:
            return

        series_node = self._get_or_create_element(root, "Series")

        # Set attributes
        if series.id_ or series.language:
            series_node.attrib = {}
        if series.id_:
            series_node.attrib["id"] = str(series.id_)
        if series.language:
            series_node.attrib["lang"] = series.language

        # Add child elements
        ET.SubElement(series_node, "Name").text = series.name

        if series.sort_name is not None:
            ET.SubElement(series_node, "SortName").text = series.sort_name

        if series.volume is not None and series.volume < VOLUME_THRESHOLD:
            ET.SubElement(series_node, "Volume").text = str(series.volume)

        series_format = self._normalize_series_format(series.format)
        if series_format is not None:
            ET.SubElement(series_node, "Format").text = series_format

        if series.start_year:
            ET.SubElement(series_node, "StartYear").text = str(series.start_year)
        elif series.volume is not None and series.volume >= VOLUME_THRESHOLD:
            ET.SubElement(series_node, "StartYear").text = str(series.volume)

        if series.issue_count:
            ET.SubElement(series_node, "IssueCount").text = str(series.issue_count)
        if series.volume_count:
            ET.SubElement(series_node, "VolumeCount").text = str(series.volume_count)

        if series.alternative_names:
            alt_names_node = ET.SubElement(series_node, "AlternativeNames")
            for alt_name in series.alternative_names:
                attrib = {}
                if alt_name.id_:
                    attrib["id"] = str(alt_name.id_)
                if alt_name.language:
                    attrib["lang"] = alt_name.language
                ET.SubElement(alt_names_node, "AlternativeName", attrib=attrib).text = alt_name.name

    def _add_info_sources(self, root: ET.Element, info_sources: list[InfoSources]) -> None:
        """Add information sources to XML.

        Args:
            root: Root element.
            info_sources: List of information sources.
        """
        if not info_sources:
            return

        id_node = self._get_or_create_element(root, "IDS")
        for source in info_sources:
            attributes = {"source": str(source.name)}
            if source.primary:
                attributes["primary"] = "true"
            child_node = ET.SubElement(id_node, "ID", attrib=attributes)
            child_node.text = str(source.id_)

    def _add_gtin(self, root: ET.Element, gtin: GTIN | None) -> None:
        """Add GTIN information to XML.

        Args:
            root: Root element.
            gtin: GTIN information.
        """
        if not gtin:
            return

        gtin_node = self._get_or_create_element(root, "GTIN")
        if gtin.isbn:
            ET.SubElement(gtin_node, "ISBN").text = str(gtin.isbn)
        if gtin.upc:
            ET.SubElement(gtin_node, "UPC").text = str(gtin.upc)

    def _add_prices(self, root: ET.Element, prices: list[Price]) -> None:
        """Add price information to XML.

        Args:
            root: Root element.
            prices: List of prices.
        """
        if not prices:
            return

        price_node = self._get_or_create_element(root, "Prices")
        for price in prices:
            child_node = ET.SubElement(price_node, "Price", attrib={"country": price.country})
            child_node.text = str(price.amount)

    def _add_universes(self, root: ET.Element, universes: list[Universe]) -> None:
        """Add universe information to XML.

        Args:
            root: Root element.
            universes: List of universes.
        """
        if not universes:
            return

        universes_node = self._get_or_create_element(root, "Universes")
        for universe in universes:
            universe_node = ET.SubElement(universes_node, "Universe")
            if universe.id_:
                universe_node.attrib["id"] = str(universe.id_)
            ET.SubElement(universe_node, "Name").text = universe.name
            if universe.designation:
                ET.SubElement(universe_node, "Designation").text = universe.designation

    def _add_urls(self, root: ET.Element, links: list[Links]) -> None:
        """Add URL links to XML.

        Args:
            root: Root element.
            links: List of links.
        """
        if not links:
            return

        urls_node = self._get_or_create_element(root, "URLs")
        for link in links:
            child_node = ET.SubElement(urls_node, "URL")
            child_node.text = link.url
            if link.primary:
                child_node.attrib["primary"] = "true"

    def _add_credits(self, root: ET.Element, credits_: list[Credit]) -> None:
        """Add credit information to XML.

        Args:
            root: Root element.
            credits_: List of credits.
        """
        if not credits_:
            return

        parent_node = self._get_or_create_element(root, "Credits")
        for credit in credits_:
            credit_node = ET.SubElement(parent_node, "Credit")

            # Add creator
            creator_attrib = {"id": str(credit.id_)} if credit.id_ else {}
            creator_node = ET.SubElement(credit_node, "Creator", attrib=creator_attrib)
            creator_node.text = credit.person

            # Add roles
            roles_node = ET.SubElement(credit_node, "Roles")
            for role in credit.role:
                role_attrib = {"id": str(role.id_)} if role.id_ else {}
                role_node = ET.SubElement(roles_node, "Role", attrib=role_attrib)
                role_node.text = role.name if role.name.lower() in VALID_ROLES else "Other"

    def _convert_metadata_to_xml(  # noqa: C901,PLR0912
        self, metadata: Metadata, xml_bytes: bytes | None = None
    ) -> ET.ElementTree:
        """Convert a Metadata object to an XML ElementTree.

        Args:
            metadata: The Metadata object to convert.
            xml_bytes: Optional XML bytes to include.

        Returns:
            The resulting XML ElementTree.
        """
        root = self._get_root(xml_bytes)

        # Add all metadata elements
        if metadata.info_source:
            self._add_info_sources(root, metadata.info_source)
        self._add_publisher(root, metadata.publisher)
        self._add_series(root, metadata.series)
        self._set_element_text(root, "CollectionTitle", metadata.collection_title)
        self._set_element_text(root, "Number", metadata.issue)

        if metadata.stories:
            self._add_basic_children(root, "Stories", "Story", metadata.stories)

        self._set_element_text(root, "Summary", metadata.comments)

        if metadata.prices:
            self._add_prices(root, metadata.prices)

        self._set_date_element(root, "CoverDate", metadata.cover_date)
        self._set_date_element(root, "StoreDate", metadata.store_date)
        self._set_element_text(root, "PageCount", metadata.page_count)

        if metadata.notes and metadata.notes.metron_info:
            self._set_element_text(root, "Notes", metadata.notes.metron_info)

        if metadata.genres:
            self._add_basic_children(root, "Genres", "Genre", metadata.genres)
        if metadata.tags:
            self._add_basic_children(root, "Tags", "Tag", metadata.tags)
        if metadata.story_arcs:
            self._add_arcs(root, metadata.story_arcs)
        if metadata.characters:
            self._add_basic_children(root, "Characters", "Character", metadata.characters)
        if metadata.teams:
            self._add_basic_children(root, "Teams", "Team", metadata.teams)
        if metadata.universes:
            self._add_universes(root, metadata.universes)
        if metadata.locations:
            self._add_basic_children(root, "Locations", "Location", metadata.locations)
        if metadata.reprints:
            self._add_basic_children(root, "Reprints", "Reprint", metadata.reprints)

        if metadata.gtin:
            self._add_gtin(root, metadata.gtin)

        if metadata.age_rating and (
            metadata.age_rating.metron_info or metadata.age_rating.comic_rack
        ):
            self._set_element_text(
                root, "AgeRating", self._normalize_age_rating(metadata.age_rating)
            )

        if metadata.web_link:
            self._add_urls(root, metadata.web_link)

        self._set_datetime_element(root, "LastModified", metadata.modified)

        if metadata.credits:
            self._add_credits(root, metadata.credits)

        ET.indent(root)
        return ET.ElementTree(root)

    def _convert_xml_to_metadata(self, tree: ET.ElementTree) -> Metadata:  # noqa: PLR0915, C901
        """Convert an XML ElementTree to a Metadata object.

        This method parses the provided XML ElementTree and converts it into a Metadata object representation.

        Args:
            tree (ET.ElementTree): The XML ElementTree to convert.

        Returns:
            Metadata: The resulting Metadata object.

        Raises:
            ValueError: If the XML does not conform to the MetronInfo schema.
        """
        root = tree.getroot()

        if root.tag != "MetronInfo":
            msg = "XML is not a MetronInfo schema"
            raise ValueError(msg)

        # Pre-cache all element lookups to avoid repeated tree traversal
        element_cache = {
            "IDS": root.find("IDS"),
            "GTIN": root.find("GTIN"),
            "Publisher": root.find("Publisher"),
            "Series": root.find("Series"),
            "LastModified": root.find("LastModified"),
            "Arcs": root.find("Arcs"),
            "Credits": root.find("Credits"),
            "Prices": root.find("Prices"),
            "URLs": root.find("URLs"),
            "Notes": root.find("Notes"),
            "AgeRating": root.find("AgeRating"),
            "Stories": root.find("Stories"),
            "Genres": root.find("Genres"),
            "Tags": root.find("Tags"),
            "Characters": root.find("Characters"),
            "Teams": root.find("Teams"),
            "Locations": root.find("Locations"),
            "Reprints": root.find("Reprints"),
            "Universes": root.find("Universes"),
        }

        def parse_gtin(gtin_element: ET.Element) -> GTIN | None:
            """Parse GTIN element into GTIN object."""
            if gtin_element is None:
                return None

            gtin = GTIN()
            gtin_mapping = {"UPC": "upc", "ISBN": "isbn"}
            found_data = False

            for item in gtin_element:
                if item.text and item.tag in gtin_mapping:
                    try:
                        setattr(gtin, gtin_mapping[item.tag], int(item.text))
                        found_data = True
                    except ValueError:
                        continue

            return gtin if found_data else None

        def parse_info_sources(ids_element: ET.Element) -> list[InfoSources] | None:
            """Parse IDS element into list of InfoSources."""
            if ids_element is None:
                return None

            sources = []
            for child in ids_element.findall("ID"):
                source_name = child.attrib.get("source")
                if not MetronInfo._is_valid_info_source(source_name) or not child.text:
                    continue

                source_id = int(child.text) if child.text.isdigit() else child.text
                is_primary = child.attrib.get("primary", "").lower() == "true"
                sources.append(InfoSources(source_name, source_id, is_primary))

            return sources or None

        def parse_basic_list(element: ET.Element) -> list[Basic]:
            """Parse element containing Basic objects."""
            if element is None:
                return []
            return [
                Basic(item.text, self._get_id_from_attrib(item.attrib))
                for item in element
                if item.text
            ]

        def parse_prices(prices_element: ET.Element) -> list[Price]:
            """Parse Prices element into list of Price objects."""
            if prices_element is None:
                return []

            prices = []
            for item in prices_element:
                if item.text:
                    try:
                        amount = Decimal(item.text)
                        country = item.attrib.get("country", DEFAULT_COUNTRY)
                        prices.append(Price(amount, country))
                    except (ValueError, TypeError):
                        continue
            return prices

        def parse_publisher(publisher_element: ET.Element) -> Publisher | None:
            """Parse Publisher element into Publisher object."""
            if publisher_element is None:
                return None

            publisher_name = None
            imprint = None

            name_elem = publisher_element.find("Name")
            if name_elem is not None:
                publisher_name = name_elem.text

            imprint_elem = publisher_element.find("Imprint")
            if imprint_elem is not None and imprint_elem.text:
                imprint = Basic(imprint_elem.text, self._get_id_from_attrib(imprint_elem.attrib))

            publisher_id = self._get_id_from_attrib(publisher_element.attrib)
            return Publisher(publisher_name, publisher_id, imprint)

        def parse_series(series_element: ET.Element) -> Series | None:
            """Parse Series element into Series object."""
            if series_element is None:
                return None

            series = Series("None")
            series.id_ = self._get_id_from_attrib(series_element.attrib)
            series.language = series_element.attrib.get("lang")

            # Define mapping for simple text elements
            text_mappings = {"Name": "name", "SortName": "sort_name", "Format": "format"}

            # Define mapping for integer elements
            int_mappings = {
                "Volume": "volume",
                "StartYear": "start_year",
                "IssueCount": "issue_count",
                "VolumeCount": "volume_count",
            }

            for child in series_element:
                if child.tag in text_mappings:
                    setattr(series, text_mappings[child.tag], child.text)
                elif child.tag in int_mappings:
                    if parsed_int := self._parse_int(child.text):
                        setattr(series, int_mappings[child.tag], parsed_int)
                elif child.tag == "AlternativeNames":
                    alt_names = []
                    for name_elem in child.findall("AlternativeName"):
                        if name_elem.text:
                            alt_name = AlternativeNames(
                                name_elem.text,
                                self._get_id_from_attrib(name_elem.attrib),
                                name_elem.attrib.get("lang"),
                            )
                            alt_names.append(alt_name)
                    series.alternative_names = alt_names

            return series

        def parse_arcs(arcs_element: ET.Element) -> list[Arc]:
            """Parse Arcs element into list of Arc objects."""
            if arcs_element is None:
                return []

            arcs = []
            for arc_elem in arcs_element.findall("Arc"):
                name_elem = arc_elem.find("Name")
                if name_elem is None or not name_elem.text:
                    continue

                arc_id = self._get_id_from_attrib(arc_elem.attrib)
                number_elem = arc_elem.find("Number")
                number = self._parse_int(number_elem.text) if number_elem is not None else None

                arcs.append(Arc(name_elem.text, arc_id, number))

            return arcs

        def parse_universes(universes_element: ET.Element) -> list[Universe]:
            """Parse Universes element into list of Universe objects."""
            if universes_element is None:
                return []

            universes = []
            for universe_elem in universes_element.findall("Universe"):
                name_elem = universe_elem.find("Name")
                if name_elem is None or not name_elem.text:
                    continue

                universe_id = self._get_id_from_attrib(universe_elem.attrib)
                designation_elem = universe_elem.find("Designation")
                designation = designation_elem.text if designation_elem is not None else None

                universes.append(Universe(name_elem.text, universe_id, designation))

            return universes

        def parse_urls(urls_element: ET.Element) -> list[Links] | None:
            """Parse URLs element into list of Links objects."""
            if urls_element is None:
                return None

            links = []
            for url_elem in urls_element.findall("URL"):
                if url_elem.text:
                    is_primary = url_elem.attrib.get("primary", "").lower() == "true"
                    links.append(Links(url_elem.text, is_primary))

            return links or None

        def parse_credits(credits_element: ET.Element) -> list[Credit] | None:
            """Parse Credits element into list of Credit objects."""
            if credits_element is None:
                return None

            credits_ = []
            for credit_elem in credits_element.findall("Credit"):
                creator_elem = credit_elem.find("Creator")
                if creator_elem is None or not creator_elem.text:
                    continue

                # Parse roles
                roles = []
                roles_elem = credit_elem.find("Roles")
                if roles_elem is not None:
                    for role_elem in roles_elem.findall("Role"):
                        if role_elem.text:
                            role_id = self._get_id_from_attrib(role_elem.attrib)
                            roles.append(Role(role_elem.text, role_id))

                creator_id = self._get_id_from_attrib(creator_elem.attrib)
                credits_.append(Credit(creator_elem.text, roles, creator_id))

            return credits_ or None

        # Build the metadata object using parsed data
        md = Metadata()
        md.info_source = parse_info_sources(element_cache["IDS"])
        md.publisher = parse_publisher(element_cache["Publisher"])
        md.series = parse_series(element_cache["Series"])
        md.collection_title = self._get_text_content(root, "CollectionTitle")

        # Handle issue number with IssueString
        issue_number = self._get_text_content(root, "Number")
        md.issue = IssueString(issue_number).as_string() if issue_number else None

        md.stories = parse_basic_list(element_cache["Stories"])
        md.comments = self._get_text_content(root, "Summary")
        md.prices = parse_prices(element_cache["Prices"])
        md.cover_date = self._parse_date(self._get_text_content(root, "CoverDate"))
        md.store_date = self._parse_date(self._get_text_content(root, "StoreDate"))
        md.page_count = self._parse_int(self._get_text_content(root, "PageCount"))

        # Handle notes
        notes_elem = element_cache["Notes"]
        md.notes = Notes(notes_elem.text) if notes_elem is not None and notes_elem.text else None

        md.genres = parse_basic_list(element_cache["Genres"])
        md.tags = parse_basic_list(element_cache["Tags"])
        md.story_arcs = parse_arcs(element_cache["Arcs"])
        md.characters = parse_basic_list(element_cache["Characters"])
        md.teams = parse_basic_list(element_cache["Teams"])
        md.universes = parse_universes(element_cache["Universes"])
        md.locations = parse_basic_list(element_cache["Locations"])
        md.reprints = parse_basic_list(element_cache["Reprints"])
        md.gtin = parse_gtin(element_cache["GTIN"])

        # Handle age rating
        age_rating_elem = element_cache["AgeRating"]
        md.age_rating = (
            AgeRatings(metron_info=age_rating_elem.text)
            if age_rating_elem is not None and age_rating_elem.text
            else None
        )

        md.web_link = parse_urls(element_cache["URLs"])

        # Handle last modified
        modified_elem = element_cache["LastModified"]
        md.modified = (
            self._parse_datetime(modified_elem.text) if modified_elem is not None else None
        )

        md.credits = parse_credits(element_cache["Credits"])
        md.is_empty = False

        return md
