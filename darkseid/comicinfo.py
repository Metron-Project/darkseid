# ruff: noqa: C901, PLR0912, PLR0915, TRY003, EM101
"""A class to encapsulate ComicRack's ComicInfo.xml data."""

# Copyright 2012-2014 Anthony Beville
# Copyright 2020 Brian Pepple
from __future__ import annotations

import xml.etree.ElementTree as ET  # noqa: N817
from datetime import date
import re
from typing import Any, ClassVar, cast

from defusedxml.ElementTree import fromstring, parse

from darkseid.issue_string import IssueString
from darkseid.metadata import Arc, Basic, Credit, ImageMetadata, Metadata, Role, Series
from darkseid.utils import list_to_string, xlate


class ComicInfo:
    """
    Handles the conversion between Metadata objects and XML representations.

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

    def metadata_from_string(self: ComicInfo, string: str) -> Metadata:
        """
        Parses an XML string representation into a Metadata object.

        Args:
            string (str): The XML string to parse.

        Returns:
            Metadata: The parsed Metadata object.
        """

        tree = ET.ElementTree(fromstring(string))
        return self.convert_xml_to_metadata(tree)

    def string_from_metadata(
        self: ComicInfo,
        md: Metadata,
        xml: bytes = b"",
    ) -> str:
        """
        Converts Metadata object to an XML string representation.

        Args:
            md (Metadata): The Metadata object to convert.
            xml (bytes): Additional XML content, defaults to an empty byte string.

        Returns:
            str: The XML string representation of the Metadata object.
        """

        tree = self.convert_metadata_to_xml(md, xml)
        return ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True).decode()

    @classmethod
    def _split_sting(cls: type[ComicInfo], string: str, delimiters: list[str]) -> list[str]:
        """
        Splits a string based on the provided delimiters.

        Args:
            string (str): The string to split.
            delimiters (list[str]): List of delimiters to use for splitting.

        Returns:
            list[str]: The list of substrings after splitting the string.
        """
        for delimiter in delimiters:
            string = string.replace(delimiter, delimiters[0])
        return string.split(delimiters[0])

    @staticmethod
    def _get_root(xml: any) -> ET.Element:
        """
        Returns the root element of an XML object.

        Args:
            xml (any): The XML object to extract the root element from.

        Returns:
            ET.Element: The root element of the XML object.
        """

        root = (
            ET.ElementTree(ET.fromstring(xml)).getroot()  # noqa: S314
            if xml
            else ET.Element("ComicInfo")
        )
        root.attrib["xmlns:xsi"] = "https://www.w3.org/2001/XMLSchema-instance"
        root.attrib["xmlns:xsd"] = "https://www.w3.org/2001/XMLSchema"

        return root

    @classmethod
    def validate_age_rating(
        cls: type[ComicInfo],
        val: str | None = None,
    ) -> str | None:
        """
        Validates an age rating value.

        Args:
            val (str | None): The age rating value to validate.

        Returns:
            str | None: The validated age rating value, or None if the value is not in the predefined set.
        """

        if val is not None:
            return "Unknown" if val not in cls.ci_age_ratings else val
        return None

    @classmethod
    def validate_manga(cls: type[ComicInfo], val: str | None = None) -> str | None:
        """
        Validates a manga value.

        Args:
            val (str | None): The manga value to validate.

        Returns:
            str | None: The validated manga value, or None if the value is not in the predefined set.
        """

        if val is not None:
            return "Unknown" if val not in cls.ci_manga else val
        return None

    def convert_metadata_to_xml(
        self: ComicInfo,
        md: Metadata,
        xml: bytes = b"",
    ) -> ET.ElementTree:
        """
        Converts Metadata object to an XML representation.

        Args:
            md (Metadata): The Metadata object to convert.
            xml (bytes): Additional XML content, defaults to an empty byte string.

        Returns:
            ET.ElementTree: The XML representation of the Metadata object.
        """

        root = self._get_root(xml)

        # helper func
        def assign(cix_entry: str, md_entry: str | int | None) -> None:
            if md_entry is not None and md_entry:
                et_entry = root.find(cix_entry)
                if et_entry is not None:
                    et_entry.text = str(md_entry)
                else:
                    ET.SubElement(root, cix_entry).text = str(md_entry)
            else:
                et_entry = root.find(cix_entry)
                if et_entry is not None:
                    root.remove(et_entry)

        def get_resource_list(resource: list[Basic] | list[Arc]) -> str | None:
            return list_to_string([i.name for i in resource]) if resource else None

        assign("Title", get_resource_list(md.stories))
        if md.series is not None:
            assign("Series", md.series.name)
        assign("Number", md.issue)
        assign("Count", md.issue_count)
        if md.series is not None:
            assign("Volume", md.series.volume)
        assign("AlternateSeries", md.alternate_series)
        assign("AlternateNumber", md.alternate_number)
        assign("SeriesGroup", md.series_group)
        assign("AlternateCount", md.alternate_count)
        assign("Summary", md.comments)
        assign("Notes", md.notes)
        if md.cover_date is not None:
            assign("Year", md.cover_date.year)
            assign("Month", md.cover_date.month)
            assign("Day", md.cover_date.day)

        # need to specially process the credits, since they are structured
        # differently than CIX
        credit_writer_list: list[str] = []
        credit_penciller_list: list[str] = []
        credit_inker_list: list[str] = []
        credit_colorist_list: list[str] = []
        credit_letterer_list: list[str] = []
        credit_cover_list: list[str] = []
        credit_editor_list: list[str] = []

        # first, loop through credits, and build a list for each role that CIX
        # supports
        for credit in md.credits:
            for r in credit.role:
                if r.name.casefold() in self.writer_synonyms:
                    credit_writer_list.append(credit.person.replace(",", ""))

                if r.name.casefold() in self.penciller_synonyms:
                    credit_penciller_list.append(credit.person.replace(",", ""))

                if r.name.casefold() in self.inker_synonyms:
                    credit_inker_list.append(credit.person.replace(",", ""))

                if r.name.casefold() in self.colorist_synonyms:
                    credit_colorist_list.append(credit.person.replace(",", ""))

                if r.name.casefold() in self.letterer_synonyms:
                    credit_letterer_list.append(credit.person.replace(",", ""))

                if r.name.casefold() in self.cover_synonyms:
                    credit_cover_list.append(credit.person.replace(",", ""))

                if r.name.casefold() in self.editor_synonyms:
                    credit_editor_list.append(credit.person.replace(",", ""))

        # second, convert each list to string, and add to XML struct
        assign("Writer", list_to_string(credit_writer_list))
        assign("Penciller", list_to_string(credit_penciller_list))
        assign("Inker", list_to_string(credit_inker_list))
        assign("Colorist", list_to_string(credit_colorist_list))
        assign("Letterer", list_to_string(credit_letterer_list))
        assign("CoverArtist", list_to_string(credit_cover_list))
        assign("Editor", list_to_string(credit_editor_list))

        if md.publisher:
            assign("Publisher", md.publisher.name)
        assign("Imprint", md.imprint)
        assign("Genre", get_resource_list(md.genres))
        assign("Web", md.web_link)
        assign("PageCount", md.page_count)
        if md.series is not None:
            assign("LanguageISO", md.series.language)
        if md.series is not None:
            assign("Format", md.series.format)
        assign("BlackAndWhite", "Yes" if md.black_and_white else None)
        assign("Manga", self.validate_manga(md.manga))
        assign("Characters", get_resource_list(md.characters))
        assign("Teams", get_resource_list(md.teams))
        assign("Locations", get_resource_list(md.locations))
        assign("ScanInformation", md.scan_info)
        assign("StoryArc", get_resource_list(md.story_arcs))
        assign("AgeRating", self.validate_age_rating(md.age_rating))

        #  loop and add the page entries under pages node
        pages_node = root.find("Pages")
        if pages_node is not None:
            pages_node.clear()
        else:
            pages_node = ET.SubElement(root, "Pages")

        for page_dict in md.pages:
            page = page_dict
            if "Image" in page:
                page["Image"] = str(page["Image"])
            page_node = ET.SubElement(pages_node, "Page")
            page_node.attrib = dict(sorted(page_dict.items()))

        # self pretty-print
        ET.indent(root)

        # wrap it in an ElementTree instance, and save as XML
        return ET.ElementTree(root)

    def convert_xml_to_metadata(self: ComicInfo, tree: ET.ElementTree) -> Metadata:
        """
        Converts an XML representation to a Metadata object.

        Args:
            tree (ET.ElementTree): The XML tree to convert to Metadata.

        Returns:
            Metadata: The Metadata object extracted from the XML tree.
        """

        root = tree.getroot()

        if root.tag != "ComicInfo":
            raise ValueError("Metadata is not ComicInfo format")

        def get(txt: str) -> str | int | None:
            """
            Finds and returns the text content of a specific tag in an XML tree.

            Args:
                txt (str): The tag to search for.

            Returns:
                str | int | None: The text content of the tag, or None if the tag is not found.
            """

            tag = root.find(txt)
            return None if tag is None else tag.text

        def clean_resource_list(string: str) -> list[str]:
            """
            Cleans and filters a string to create a list of non-empty values.

            Args:
                string (str): The string to clean and filter.

            Returns:
                list[str]: The list of cleaned and filtered non-empty values.
            """
            return [item.strip() for item in re.split(r',|"(.*?)"', string) if item and item.strip()]

        def string_to_resource(string: str) -> list[Basic] | None:
            """
            Converts a string to a list of Basic objects.

            Args:
                string (str): The string to convert to Basic objects.

            Returns:
                list[Basic] | None: The list of Basic objects created from the string, or None if the string is None.
            """

            if string is not None:
                res: list[str | Basic] = clean_resource_list(string)
                # Now let's add the dataclass
                for count, item in enumerate(res):
                    res[count] = Basic(item)
                return res
            return None

        def string_to_arc(string: str) -> list[Arc] | None:
            """
            Converts a string to a list of Arc objects.

            Args:
                string (str): The string to convert to Arc objects.

            Returns:
                list[Arc] | None: The list of Arc objects created from the string, or None if the string is None.
            """

            if string is not None:
                res: list[str | Arc] = clean_resource_list(string)
                # Now let's add the dataclass
                for count, item in enumerate(res):
                    res[count] = Arc(item)
                return res
            return None

        md = Metadata()
        md.series = Series(name=xlate(get("Series")))
        md.stories = string_to_resource(xlate(get("Title")))
        md.issue = IssueString(xlate(get("Number"))).as_string()
        md.issue_count = xlate(get("Count"), True)
        md.series.volume = xlate(get("Volume"), True)
        md.alternate_series = xlate(get("AlternateSeries"))
        md.alternate_number = IssueString(xlate(get("AlternateNumber"))).as_string()
        md.alternate_count = xlate(get("AlternateCount"), True)
        md.comments = xlate(get("Summary"))
        md.notes = xlate(get("Notes"))
        # Cover Year
        tmp_year = xlate(get("Year"), True)
        tmp_month = xlate(get("Month"), True)
        tmp_day = xlate(get("Day"), True)
        if tmp_year is not None and tmp_month is not None:
            if tmp_day is not None:
                md.cover_date = date(tmp_year, tmp_month, tmp_day)
            else:
                md.cover_date = date(tmp_year, tmp_month, 1)

        md.publisher = Basic(xlate(get("Publisher")))
        md.imprint = xlate(get("Imprint"))
        md.genres = string_to_resource(xlate(get("Genre")))
        md.web_link = xlate(get("Web"))
        md.series.language = xlate(get("LanguageISO"))
        md.series.format = xlate(get("Format"))
        md.manga = xlate(get("Manga"))
        md.characters = string_to_resource(xlate(get("Characters")))
        md.teams = string_to_resource(xlate(get("Teams")))
        md.locations = string_to_resource(xlate(get("Locations")))
        md.page_count = xlate(get("PageCount"), True)
        md.scan_info = xlate(get("ScanInformation"))
        md.story_arcs = string_to_arc(xlate(get("StoryArc")))
        md.series_group = xlate(get("SeriesGroup"))
        md.age_rating = xlate(get("AgeRating"))

        tmp = xlate(get("BlackAndWhite"))
        md.black_and_white = False
        if tmp is not None and tmp.casefold() in ["yes", "true", "1"]:
            md.black_and_white = True
        # Now extract the credit info
        for n in root:
            if (
                n.tag in ["Writer", "Penciller", "Inker", "Colorist", "Letterer", "Editor"]
                and n.text is not None
            ):
                for name in self._split_sting(n.text, [";"]):
                    md.add_credit(Credit(name.strip(), [Role(n.tag)]))

            if n.tag == "CoverArtist" and n.text is not None:
                for name in self._split_sting(n.text, [";"]):
                    md.add_credit(Credit(name.strip(), [Role("Cover")]))

        # parse page data now
        pages_node = root.find("Pages")
        if pages_node is not None:
            for page in pages_node:
                p: dict[str, Any] = page.attrib
                if "Image" in p:
                    p["Image"] = int(p["Image"])
                md.pages.append(cast(ImageMetadata, p))

        md.is_empty = False

        return md

    def write_to_external_file(
        self: ComicInfo,
        filename: str,
        md: Metadata,
        xml: bytes = b"",
    ) -> None:
        """
        Writes Metadata to an external file in XML format.

        Args:
            filename (str): The name of the file to write the Metadata to.
            md (Metadata): The Metadata object to write to the file.
            xml (bytes): Additional XML content, defaults to an empty byte string.

        Returns:
            None
        """

        tree = self.convert_metadata_to_xml(md, xml)
        tree.write(filename, encoding="utf-8", xml_declaration=True)

    def read_from_external_file(self: ComicInfo, filename: str) -> Metadata:
        """
        Reads Metadata from an external file in XML format.

        Args:
            filename (str): The name of the file to read the Metadata from.

        Returns:
            Metadata: The Metadata object extracted from the file.
        """

        tree = parse(filename)
        return self.convert_xml_to_metadata(tree)
