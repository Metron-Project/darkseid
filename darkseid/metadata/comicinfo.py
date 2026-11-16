"""A class to encapsulate ComicRack's ComicInfo.xml data."""

# Copyright 2012-2014 Anthony Beville
# Copyright 2020 Brian Pepple
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from datetime import date
from typing import Any, ClassVar, cast

from defusedxml.ElementTree import fromstring

from darkseid.issue_string import IssueString
from darkseid.metadata.base_handler import BaseMetadataHandler, XmlError
from darkseid.metadata.data_classes import (
    AgeRatings,
    Arc,
    Basic,
    Credit,
    ImageMetadata,
    InfoSources,
    Links,
    Metadata,
    Notes,
    Publisher,
    Role,
    Series,
)
from darkseid.utils import get_issue_id_from_note, list_to_string

# Constants
CREDIT_TAGS = frozenset({"Writer", "Penciller", "Inker", "Colorist", "Letterer", "Editor"})


class ComicInfo(BaseMetadataHandler):
    """Handles the conversion between Metadata objects and ComicInfo XML representations.

    Includes methods for converting Metadata to XML, XML to Metadata, and writing/reading Metadata to/from external files.
    """

    ci_age_ratings: ClassVar[frozenset[str]] = frozenset(
        {
            "Unknown",
            "Adults Only 18+",
            "Early Childhood",
            "Everyone",
            "Everyone 10+",
            "G",
            "Kids to Adults",
            "M",
            "MA15+",
            "Mature 17+",
            "PG",
            "R18+",
            "Rating Pending",
            "Teen",
            "X18+",
        }
    )

    ci_manga: ClassVar[frozenset[str]] = frozenset({"Unknown", "Yes", "No", "YesAndRightToLeft"})

    writer_synonyms: ClassVar[frozenset[str]] = frozenset(
        {
            "writer",
            "plotter",
            "scripter",
            "script",
            "story",
            "plot",
        }
    )
    penciller_synonyms: ClassVar[frozenset[str]] = frozenset(
        {
            "artist",
            "breakdowns",
            "illustrator",
            "layouts",
            "penciller",
            "penciler",
        }
    )
    inker_synonyms: ClassVar[frozenset[str]] = frozenset(
        {
            "artist",
            "embellisher",
            "finishes",
            "illustrator",
            "ink assists",
            "inker",
        }
    )
    colorist_synonyms: ClassVar[frozenset[str]] = frozenset(
        {
            "colorist",
            "colourist",
            "colorer",
            "colourer",
            "color assists",
            "color flats",
        }
    )
    letterer_synonyms: ClassVar[frozenset[str]] = frozenset({"letterer"})
    cover_synonyms: ClassVar[frozenset[str]] = frozenset(
        {
            "cover",
            "covers",
            "coverartist",
            "cover artist",
        }
    )
    editor_synonyms: ClassVar[frozenset[str]] = frozenset(
        {
            "assistant editor",
            "associate editor",
            "consulting editor",
            "editor",
            "editor in chief",
            "executive editor",
            "group editor",
            "senior editor",
            "supervising editor",
        }
    )

    @staticmethod
    def _get_resource_list(resource: list[Basic] | list[Arc]) -> str | None:
        """Convert a list of resources to a comma-separated string.

        Args:
            resource: List of Basic or Arc objects.

        Returns:
            Comma-separated string of resource names, or None if list is empty.

        """
        return list_to_string([i.name for i in resource]) if resource else None

    @staticmethod
    def _create_url_string(links: list[Links]) -> str:
        """Create a comma-separated string of URLs from Links objects.

        Args:
            links: List of Links objects.

        Returns:
            Comma-separated string of URLs.

        """
        return ",".join(link.url for link in links)

    def _parse_urls(self, txt: str | None) -> list[Links] | None:
        """Parse URL string into list of Links objects.

        Args:
            txt: Comma or space-separated URL string.

        Returns:
            List of Links with first marked as primary, or None if no URLs.

        """
        if not txt:
            return None
        # ComicInfo schema states URL string can be separated by a comma or space
        urls = self._split_string(txt, [",", " "])
        # We're assuming the first link is the main source url.
        return [Links(urls[0], primary=True)] + [Links(url) for url in urls[1:]]

    @staticmethod
    def _parse_note(note_txt: str | None) -> Notes | None:
        """Parse note text into Notes object.

        Args:
            note_txt: The note text.

        Returns:
            Notes object or None if text is empty.

        """
        return Notes(comic_rack=note_txt) if note_txt else None

    @staticmethod
    def _parse_age_rating(age_text: str | None) -> AgeRatings | None:
        """Parse age rating text into AgeRatings object.

        Args:
            age_text: The age rating text.

        Returns:
            AgeRatings object or None if text is empty.

        """
        return AgeRatings(comic_rack=age_text) if age_text else None

    @staticmethod
    def _set_cover_date(
        tmp_year: int | None, tmp_month: int | None, tmp_day: int | None
    ) -> date | None:
        """Set cover date from year, month, and day components.

        Args:
            tmp_year: Year value.
            tmp_month: Month value.
            tmp_day: Day value (optional).

        Returns:
            Date object or None if invalid.

        """
        if tmp_year is None or tmp_month is None:
            return None

        try:
            cov_date = (
                date(tmp_year, tmp_month, 1)
                if tmp_day is None
                else date(tmp_year, tmp_month, tmp_day)
            )
        except ValueError:
            return None
        return cov_date

    def metadata_from_string(self, xml_string: str) -> Metadata:
        """Parse an XML string representation into a Metadata object.

        Args:
            xml_string: The XML string to parse.

        Returns:
            The parsed Metadata object.

        Raises:
            XmlError: If the XML string cannot be parsed.

        """
        try:
            tree = ET.ElementTree(fromstring(xml_string))
        except ET.ParseError as e:
            msg = f"Failed to parse ComicInfo XML: {e!r}"
            raise XmlError(msg) from e
        return self._convert_xml_to_metadata(tree)

    def string_from_metadata(
        self,
        metadata: Metadata,
        xml_bytes: bytes = b"",
    ) -> str:
        """Convert Metadata object to an XML string representation.

        Args:
            metadata: The Metadata object to convert.
            xml_bytes: Additional XML content, defaults to an empty byte string.

        Returns:
            The XML string representation of the Metadata object.

        """
        tree = self._convert_metadata_to_xml(metadata, xml_bytes)
        root = self._require_root(tree)
        return ET.tostring(root, encoding="utf-8", xml_declaration=True).decode()

    @staticmethod
    def _get_root(xml_bytes: bytes | None) -> ET.Element:
        """Return the root element of an XML object.

        Args:
            xml_bytes: The XML object to extract the root element from.

        Returns:
            The root element of the XML object.

        """
        if xml_bytes:
            try:
                root = fromstring(xml_bytes)
            except ET.ParseError:
                root = ET.Element("ComicInfo")
        else:
            root = ET.Element("ComicInfo")

        root.attrib["xmlns:xsi"] = "https://www.w3.org/2001/XMLSchema-instance"
        root.attrib["xmlns:xsd"] = "https://www.w3.org/2001/XMLSchema"

        return root

    @staticmethod
    def _page_attrib_value(value: object) -> str:
        """Convert a page attribute value to its XML string form.

        Args:
            value: The attribute value from ImageMetadata.

        Returns:
            ``"true"``/``"false"`` for a bool, as xs:boolean expects, else ``str(value)``.

        """
        if isinstance(value, bool):
            return "true" if value else "false"
        return str(value)

    def _convert_metadata_to_xml(  # noqa: C901, PLR0912, PLR0915
        self,
        metadata: Metadata,
        xml_bytes: bytes | None = None,
    ) -> ET.ElementTree:
        """Convert Metadata object to an XML representation.

        Args:
            metadata: The Metadata object to convert.
            xml_bytes: Additional XML content, defaults to None.

        Returns:
            The XML representation of the Metadata object.

        """
        root = self._get_root(xml_bytes)

        if stories_txt := self._get_resource_list(metadata.stories):
            self._set_element_text(root, "Title", stories_txt)
        if metadata.series is not None:
            self._set_element_text(root, "Series", metadata.series.name)
        self._set_element_text(root, "Number", metadata.issue)
        if metadata.series is not None and metadata.series.issue_count is not None:
            self._set_element_text(root, "Count", metadata.series.issue_count)
        if metadata.series is not None:
            self._set_element_text(root, "Volume", metadata.series.volume)

        self._set_element_text(root, "AlternateSeries", metadata.alternate_series)
        self._set_element_text(root, "AlternateNumber", metadata.alternate_number)
        self._set_element_text(root, "SeriesGroup", metadata.series_group)
        self._set_element_text(root, "AlternateCount", metadata.alternate_count)
        self._set_element_text(root, "Summary", metadata.comments)
        if metadata.notes is not None and metadata.notes.comic_rack:
            self._set_element_text(root, "Notes", metadata.notes.comic_rack)
        if metadata.cover_date is not None:
            self._set_element_text(root, "Year", metadata.cover_date.year)
            self._set_element_text(root, "Month", metadata.cover_date.month)
            self._set_element_text(root, "Day", metadata.cover_date.day)

        credit_roles = {
            "Writer": self.writer_synonyms,
            "Penciller": self.penciller_synonyms,
            "Inker": self.inker_synonyms,
            "Colorist": self.colorist_synonyms,
            "Letterer": self.letterer_synonyms,
            "CoverArtist": self.cover_synonyms,
            "Editor": self.editor_synonyms,
        }

        credit_lists = {role: [] for role in credit_roles}

        for credit in metadata.credits:
            for r in credit.role:
                role_name = r.name.casefold()
                for role, synonyms in credit_roles.items():
                    if role_name in synonyms:
                        credit_lists[role].append(credit.person.replace(",", ""))

        for role, names in credit_lists.items():
            self._set_element_text(root, role, list_to_string(names))

        if metadata.publisher:
            self._set_element_text(root, "Publisher", metadata.publisher.name)
            if metadata.publisher.imprint:
                self._set_element_text(root, "Imprint", metadata.publisher.imprint.name)
        self._set_element_text(root, "Genre", self._get_resource_list(metadata.genres))
        if metadata.web_link:
            self._set_element_text(root, "Web", self._create_url_string(metadata.web_link))
        self._set_element_text(root, "PageCount", metadata.page_count)
        if metadata.series is not None:
            self._set_element_text(root, "LanguageISO", metadata.series.language)
        if metadata.series is not None:
            self._set_element_text(root, "Format", metadata.series.format)
        self._set_element_text(root, "BlackAndWhite", "Yes" if metadata.black_and_white else None)
        self._set_element_text(root, "Manga", self._validate_value(metadata.manga, self.ci_manga))
        self._set_element_text(root, "Characters", self._get_resource_list(metadata.characters))
        self._set_element_text(root, "Teams", self._get_resource_list(metadata.teams))
        self._set_element_text(root, "Locations", self._get_resource_list(metadata.locations))
        self._set_element_text(root, "ScanInformation", metadata.scan_info)
        self._set_element_text(root, "StoryArc", self._get_resource_list(metadata.story_arcs))
        if metadata.age_rating is not None and metadata.age_rating.comic_rack:
            self._set_element_text(
                root,
                "AgeRating",
                self._validate_value(metadata.age_rating.comic_rack, self.ci_age_ratings),
            )

        #  loop and add the page entries under pages node
        pages_node = root.find("Pages")
        if pages_node is not None:
            pages_node.clear()
        else:
            pages_node = ET.SubElement(root, "Pages")

        for page_dict in metadata.pages:
            page_attrib = {"Image": "", **page_dict}
            ET.SubElement(
                pages_node,
                "Page",
                {key: self._page_attrib_value(value) for key, value in sorted(page_attrib.items())},
            )

        # CommunityRating comes after Pages in the schema
        self._set_element_text(root, "CommunityRating", metadata.community_rating)
        self._set_element_text(root, "MainCharacterOrTeam", metadata.main_character_or_team)
        self._set_element_text(root, "Review", metadata.review)

        ET.indent(root)
        return ET.ElementTree(root)

    def _convert_xml_to_metadata(self, tree: ET.ElementTree) -> Metadata:  # noqa: C901, PLR0912, PLR0915
        """Convert an XML representation to a Metadata object.

        Args:
            tree: The XML tree to convert to Metadata.

        Returns:
            The Metadata object extracted from the XML tree.

        """
        root = tree.getroot()
        if root is None:
            msg = "XML tree has no root element"
            raise ValueError(msg)

        if root.tag != "ComicInfo":
            msg = "Metadata is not ComicInfo format"
            raise ValueError(msg)

        md = Metadata()
        md.series = Series(name=self._get_text_content(root, "Series"))
        md.stories = self._string_to_resource(self._get_text_content(root, "Title"))
        md.issue = IssueString(self._get_text_content(root, "Number")).as_string()
        md.series.issue_count = self._parse_int(self._get_text_content(root, "Count"))
        md.series.volume = self._parse_int(self._get_text_content(root, "Volume"))
        md.alternate_series = self._get_text_content(root, "AlternateSeries")
        md.alternate_number = IssueString(
            self._get_text_content(root, "AlternateNumber")
        ).as_string()
        md.alternate_count = self._parse_int(self._get_text_content(root, "AlternateCount"))
        md.comments = self._get_text_content(root, "Summary")
        md.notes = self._parse_note(self._get_text_content(root, "Notes"))
        if md.notes is not None and md.notes.comic_rack is not None:
            src = get_issue_id_from_note(md.notes.comic_rack)
            if src is not None:
                md.info_source = [InfoSources(src["source"], src["id"], primary=True)]
        # Cover Year
        tmp_year = self._parse_int(self._get_text_content(root, "Year"))
        tmp_month = self._parse_int(self._get_text_content(root, "Month"))
        tmp_day = self._parse_int(self._get_text_content(root, "Day"))
        cover_date = self._set_cover_date(tmp_year, tmp_month, tmp_day)
        if cover_date is not None:
            md.cover_date = cover_date
        # Publisher info
        pub = self._get_text_content(root, "Publisher")
        imprint = self._get_text_content(root, "Imprint")
        md.publisher = Publisher(pub, imprint=Basic(imprint) if imprint else None)

        md.genres = self._string_to_resource(self._get_text_content(root, "Genre"))
        md.web_link = self._parse_urls(self._get_text_content(root, "Web"))
        md.series.language = self._parse_language(self._get_text_content(root, "LanguageISO"))
        md.series.format = self._get_text_content(root, "Format")
        md.manga = self._get_text_content(root, "Manga")
        md.characters = self._string_to_resource(self._get_text_content(root, "Characters"))
        md.teams = self._string_to_resource(self._get_text_content(root, "Teams"))
        md.locations = self._string_to_resource(self._get_text_content(root, "Locations"))
        md.page_count = self._parse_int(self._get_text_content(root, "PageCount"))
        md.scan_info = self._get_text_content(root, "ScanInformation")
        md.story_arcs = self._string_to_arc(self._get_text_content(root, "StoryArc"))
        md.series_group = self._get_text_content(root, "SeriesGroup")
        md.age_rating = self._parse_age_rating(self._get_text_content(root, "AgeRating"))
        md.community_rating = self._parse_decimal(self._get_text_content(root, "CommunityRating"))
        md.main_character_or_team = self._get_text_content(root, "MainCharacterOrTeam")
        md.review = self._get_text_content(root, "Review")

        tmp = self._get_text_content(root, "BlackAndWhite")
        md.black_and_white = False
        if tmp is not None and tmp.casefold() in ["yes", "true", "1"]:
            md.black_and_white = True
        # Now extract the credit info
        for n in root:
            if n.tag in CREDIT_TAGS and n.text is not None:
                for name in self._split_string(n.text, [";", ","]):
                    md.add_credit(Credit(name.strip(), [Role(n.tag)]))

            if n.tag == "CoverArtist" and n.text is not None:
                for name in self._split_string(n.text, [";", ","]):
                    md.add_credit(Credit(name.strip(), [Role("Cover")]))

        # parse page data now
        pages_node = root.find("Pages")
        if pages_node is not None:
            for page in pages_node:
                p: dict[str, Any] = page.attrib
                if "Image" in p:
                    p["Image"] = int(p["Image"])
                md.pages.append(cast("ImageMetadata", p))

        md.is_empty = False

        return md

    @staticmethod
    def _clean_resource_list(string: str) -> list[str]:
        """Clean and filter a string to create a list of non-empty values.

        Args:
            string: The string to clean and filter.

        Returns:
            The list of cleaned and filtered non-empty values.

        """
        return [item.strip() for item in re.split(r',|"(.*?)"', string) if item and item.strip()]

    @staticmethod
    def _string_to_resource(string: str | None) -> list[Basic]:
        """Convert a string to a list of Basic objects.

        Args:
            string: The string to convert to Basic objects.

        Returns:
            The list of Basic objects created from the string, or an empty list if the
            string is None.

        """
        if string is None:
            return []
        return [Basic(item) for item in ComicInfo._clean_resource_list(string)]

    @staticmethod
    def _string_to_arc(string: str | None) -> list[Arc]:
        """Convert a string to a list of Arc objects.

        Args:
            string: The string to convert to Arc objects.

        Returns:
            The list of Arc objects created from the string, or an empty list if the
            string is None.

        """
        if string is None:
            return []
        return [Arc(item) for item in ComicInfo._clean_resource_list(string)]
