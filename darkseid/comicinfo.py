"""A class to encapsulate ComicRack's ComicInfo.xml data."""

# Copyright 2012-2014 Anthony Beville
# Copyright 2020 Brian Pepple


import xml.etree.ElementTree as ET  # noqa: N817
from datetime import date
from re import split
from typing import Any, ClassVar, Optional, Union, cast

from darkseid.issue_string import IssueString
from darkseid.metadata import Arc, Basic, Credit, ImageMetadata, Metadata, Role, Series
from darkseid.utils import list_to_string, xlate


class ComicInfo:
    ci_age_ratings: ClassVar[list[str]] = [
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
    ]

    ci_manga: ClassVar[list[str]] = ["Unknown", "Yes", "No", "YesAndRightToLeft"]

    writer_synonyms: ClassVar[list[str]] = [
        "writer",
        "plotter",
        "scripter",
        "script",
        "story",
        "plot",
    ]
    penciller_synonyms: ClassVar[list[str]] = [
        "artist",
        "breakdowns",
        "illustrator",
        "layouts",
        "penciller",
        "penciler",
    ]
    inker_synonyms: ClassVar[list[str]] = [
        "artist",
        "embellisher",
        "finishes",
        "illustrator",
        "ink assists",
        "inker",
    ]
    colorist_synonyms: ClassVar[list[str]] = [
        "colorist",
        "colourist",
        "colorer",
        "colourer",
        "color assists",
        "color flats",
    ]
    letterer_synonyms: ClassVar[list[str]] = ["letterer"]
    cover_synonyms: ClassVar[list[str]] = ["cover", "covers", "coverartist", "cover artist"]
    editor_synonyms: ClassVar[list[str]] = [
        "assistant editor",
        "associate editor",
        "consulting editor",
        "editor",
        "editor in chief",
        "executive editor",
        "group editor",
        "senior editor",
        "supervising editor",
    ]

    def metadata_from_string(self: "ComicInfo", string: str) -> Metadata:
        tree = ET.ElementTree(ET.fromstring(string))  # noqa: S314
        return self.convert_xml_to_metadata(tree)

    def string_from_metadata(
        self: "ComicInfo",
        md: Metadata,
        xml: Optional[any] = None,
    ) -> str:
        tree = self.convert_metadata_to_xml(md, xml)
        return ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True).decode()

    @classmethod
    def _split_sting(cls: type["ComicInfo"], string: str, delimiters: list[str]) -> list[str]:
        pattern = r"|".join(delimiters)
        return split(pattern, string)

    def _get_root(self: "ComicInfo", xml: any) -> ET.Element:
        if xml:
            root = ET.ElementTree(ET.fromstring(xml)).getroot()  # noqa: S314
        else:
            # build a tree structure
            root = ET.Element("ComicInfo")
            root.attrib["xmlns:xsi"] = "https://www.w3.org/2001/XMLSchema-instance"
            root.attrib["xmlns:xsd"] = "https://www.w3.org/2001/XMLSchema"

        return root

    @classmethod
    def validate_age_rating(
        cls: type["ComicInfo"],
        val: Optional[str] = None,
    ) -> Optional[str]:
        if val is not None:
            return "Unknown" if val not in cls.ci_age_ratings else val
        return None

    @classmethod
    def validate_manga(cls: type["ComicInfo"], val: Optional[str] = None) -> Optional[str]:
        if val is not None:
            return "Unknown" if val not in cls.ci_manga else val
        return None

    def convert_metadata_to_xml(
        self: "ComicInfo",
        md: Metadata,
        xml: Optional[any] = None,
    ) -> ET.ElementTree:
        root = self._get_root(xml)

        # helper func
        def assign(cix_entry: str, md_entry: Optional[Union[str, int]]) -> None:
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

        def get_resource_list(resource: list[Basic]) -> Optional[str]:
            return list_to_string([i.name for i in resource]) if resource else None

        assign("Title", get_resource_list(md.stories))
        assign("Series", md.series.name)
        assign("Number", md.issue)
        assign("Count", md.issue_count)
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

        # first, loop thru credits, and build a list for each role that CIX
        # supports
        for credit in md.credits:
            for r in credit.role:
                if r.name.casefold() in set(self.writer_synonyms):
                    credit_writer_list.append(credit.person.replace(",", ""))

                if r.name.casefold() in set(self.penciller_synonyms):
                    credit_penciller_list.append(credit.person.replace(",", ""))

                if r.name.casefold() in set(self.inker_synonyms):
                    credit_inker_list.append(credit.person.replace(",", ""))

                if r.name.casefold() in set(self.colorist_synonyms):
                    credit_colorist_list.append(credit.person.replace(",", ""))

                if r.name.casefold() in set(self.letterer_synonyms):
                    credit_letterer_list.append(credit.person.replace(",", ""))

                if r.name.casefold() in set(self.cover_synonyms):
                    credit_cover_list.append(credit.person.replace(",", ""))

                if r.name.casefold() in set(self.editor_synonyms):
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
        if md.series.language:
            assign("LanguageISO", md.series.language)
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

    def convert_xml_to_metadata(self: "ComicInfo", tree: ET.ElementTree) -> Metadata:
        root = tree.getroot()

        if root.tag != "ComicInfo":
            raise ValueError("Metadata is not ComicInfo format")

        def get(name: str) -> Optional[Union[str, int]]:
            tag = root.find(name)
            return None if tag is None else tag.text

        def string_to_resource(string: str) -> list[Basic]:
            if string is not None:
                # TODO: Make the delimiter also check for ','
                return [Basic(x.strip()) for x in string.split(";")]
            return None

        def string_to_arc(string: str) -> list[Arc]:
            if string is not None:
                return [Arc(x.strip()) for x in string.split(";")]
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
        self: "ComicInfo",
        filename: str,
        md: Metadata,
        xml: Optional[any] = None,
    ) -> None:
        tree = self.convert_metadata_to_xml(md, xml)
        tree.write(filename, encoding="utf-8", xml_declaration=True)

    def read_from_external_file(self: "ComicInfo", filename: str) -> Metadata:
        tree = ET.parse(filename)  # noqa: S314
        return self.convert_xml_to_metadata(tree)
