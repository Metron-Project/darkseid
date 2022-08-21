"""A class to encapsulate ComicRack's ComicInfo.xml data"""

# Copyright 2012-2014 Anthony Beville
# Copyright 2020 Brian Pepple


import xml.etree.ElementTree as ET
from datetime import date
from re import split
from typing import Any, List, Optional, Union, cast

from darkseid.issue_string import IssueString
from darkseid.metadata import Arc, Basic, Credit, ImageMetadata, Metadata, Role, Series
from darkseid.utils import list_to_string, xlate


class ComicInfo:
    ci_age_ratings = [
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

    ci_manga = ["Unknown", "Yes", "No", "YesAndRightToLeft"]

    writer_synonyms: List[str] = [
        "writer",
        "plotter",
        "scripter",
        "script",
        "story",
        "plot",
    ]
    penciller_synonyms: List[str] = [
        "artist",
        "breakdowns",
        "illustrator",
        "layouts",
        "penciller",
        "penciler",
    ]
    inker_synonyms: List[str] = [
        "artist",
        "embellisher",
        "finishes",
        "illustrator",
        "ink assists",
        "inker",
    ]
    colorist_synonyms: List[str] = [
        "colorist",
        "colourist",
        "colorer",
        "colourer",
        "color assists",
        "color flats",
    ]
    letterer_synonyms: List[str] = ["letterer"]
    cover_synonyms: List[str] = ["cover", "covers", "coverartist", "cover artist"]
    editor_synonyms: List[str] = [
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

    def metadata_from_string(self, string: str) -> Metadata:
        tree = ET.ElementTree(ET.fromstring(string))
        return self.convert_xml_to_metadata(tree)

    def string_from_metadata(self, metadata: Metadata, xml: Optional[any] = None) -> str:
        tree = self.convert_metadata_to_xml(metadata, xml)
        return ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True).decode()

    @classmethod
    def _split_sting(cls, string: str, delimiters: List[str]) -> List[str]:
        pattern = r"|".join(delimiters)
        return split(pattern, string)

    def _get_root(self, xml) -> ET.Element:
        if xml:
            root = ET.ElementTree(ET.fromstring(xml)).getroot()
        else:
            # build a tree structure
            root = ET.Element("ComicInfo")
            root.attrib["xmlns:xsi"] = "https://www.w3.org/2001/XMLSchema-instance"
            root.attrib["xmlns:xsd"] = "https://www.w3.org/2001/XMLSchema"

        return root

    @classmethod
    def validate_age_rating(cls, val: Optional[str] = None) -> Optional[str]:
        if val is not None:
            return "Unknown" if val not in cls.ci_age_ratings else val

    @classmethod
    def validate_manga(cls, val: Optional[str] = None) -> Optional[str]:
        if val is not None:
            return "Unknown" if val not in cls.ci_manga else val

    def convert_metadata_to_xml(self, metadata: Metadata, xml=None) -> ET.ElementTree:
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

        def get_resource_list(resource: List[Basic]) -> str:
            return list_to_string([i.name for i in resource])

        assign("Title", get_resource_list(metadata.stories))
        assign("Series", metadata.series.name)
        assign("Number", metadata.issue)
        assign("Count", metadata.issue_count)
        assign("Volume", metadata.series.volume)
        assign("AlternateSeries", metadata.alternate_series)
        assign("AlternateNumber", metadata.alternate_number)
        assign("SeriesGroup", metadata.series_group)
        assign("AlternateCount", metadata.alternate_count)
        assign("Summary", metadata.comments)
        assign("Notes", metadata.notes)
        if metadata.cover_date is not None:
            assign("Year", metadata.cover_date.year)
            assign("Month", metadata.cover_date.month)
            assign("Day", metadata.cover_date.day)

        # need to specially process the credits, since they are structured
        # differently than CIX
        credit_writer_list: List[str] = []
        credit_penciller_list: List[str] = []
        credit_inker_list: List[str] = []
        credit_colorist_list: List[str] = []
        credit_letterer_list: List[str] = []
        credit_cover_list: List[str] = []
        credit_editor_list: List[str] = []

        # first, loop thru credits, and build a list for each role that CIX
        # supports
        for credit in metadata.credits:
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

        if metadata.publisher:
            assign("Publisher", metadata.publisher.name)
        assign("Imprint", metadata.imprint)
        assign("Genre", get_resource_list(metadata.genres))
        assign("Web", metadata.web_link)
        assign("PageCount", metadata.page_count)
        assign("LanguageISO", metadata.language)
        assign("Format", metadata.series.format)
        assign("BlackAndWhite", "Yes" if metadata.black_and_white else None)
        assign("Manga", self.validate_manga(metadata.manga))
        assign("Characters", get_resource_list(metadata.characters))
        assign("Teams", get_resource_list(metadata.teams))
        assign("Locations", get_resource_list(metadata.locations))
        assign("ScanInformation", metadata.scan_info)
        assign("StoryArc", get_resource_list(metadata.story_arcs))
        assign("AgeRating", self.validate_age_rating(metadata.age_rating))

        #  loop and add the page entries under pages node
        pages_node = root.find("Pages")
        if pages_node is not None:
            pages_node.clear()
        else:
            pages_node = ET.SubElement(root, "Pages")

        for page_dict in metadata.pages:
            page = page_dict
            if "Image" in page:
                page["Image"] = str(page["Image"])
            page_node = ET.SubElement(pages_node, "Page")
            page_node.attrib = dict(sorted(page_dict.items()))

        # self pretty-print
        ET.indent(root)

        # wrap it in an ElementTree instance, and save as XML
        tree = ET.ElementTree(root)
        return tree

    def convert_xml_to_metadata(self, tree: ET.ElementTree) -> Metadata:
        root = tree.getroot()

        if root.tag != "ComicInfo":
            raise ValueError("Metadata is not ComicInfo format")

        def get(name):
            tag = root.find(name)
            return None if tag is None else tag.text

        def string_to_resource(string: str) -> List[Basic]:
            if string is not None:
                # TODO: Make the delimiter also check for ','
                return [Basic(x.strip()) for x in string.split(";")]

        def string_to_arc(string: str) -> List[Arc]:
            if string is not None:
                return [Arc(x.strip()) for x in string.split(";")]

        metadata = Metadata()
        metadata.series = Series(name=xlate(get("Series")))
        metadata.stories = string_to_resource(xlate(get("Title")))
        metadata.issue = IssueString(xlate(get("Number"))).as_string()
        metadata.issue_count = xlate(get("Count"), True)
        metadata.series.volume = xlate(get("Volume"), True)
        metadata.alternate_series = xlate(get("AlternateSeries"))
        metadata.alternate_number = IssueString(xlate(get("AlternateNumber"))).as_string()
        metadata.alternate_count = xlate(get("AlternateCount"), True)
        metadata.comments = xlate(get("Summary"))
        metadata.notes = xlate(get("Notes"))
        # Cover Year
        tmp_year = xlate(get("Year"), True)
        tmp_month = xlate(get("Month"), True)
        tmp_day = xlate(get("Day"), True)
        if tmp_year is not None and tmp_month is not None and tmp_day is not None:
            metadata.cover_date = date(tmp_year, tmp_month, tmp_day)

        metadata.publisher = Basic(xlate(get("Publisher")))
        metadata.imprint = xlate(get("Imprint"))
        metadata.genres = string_to_resource(xlate(get("Genre")))
        metadata.web_link = xlate(get("Web"))
        metadata.language = xlate(get("LanguageISO"))
        metadata.series.format = xlate(get("Format"))
        metadata.manga = xlate(get("Manga"))
        metadata.characters = string_to_resource(xlate(get("Characters")))
        metadata.teams = string_to_resource(xlate(get("Teams")))
        metadata.locations = string_to_resource(xlate(get("Locations")))
        metadata.page_count = xlate(get("PageCount"), True)
        metadata.scan_info = xlate(get("ScanInformation"))
        metadata.story_arcs = string_to_arc(xlate(get("StoryArc")))
        metadata.series_group = xlate(get("SeriesGroup"))
        metadata.age_rating = xlate(get("AgeRating"))

        tmp = xlate(get("BlackAndWhite"))
        metadata.black_and_white = False
        if tmp is not None and tmp.casefold() in ["yes", "true", "1"]:
            metadata.black_and_white = True
        # Now extract the credit info
        for n in root:
            if (
                n.tag in ["Writer", "Penciller", "Inker", "Colorist", "Letterer", "Editor"]
                and n.text is not None
            ):
                for name in self._split_sting(n.text, [";"]):
                    metadata.add_credit(Credit(name.strip(), [Role(n.tag)]))

            if n.tag == "CoverArtist" and n.text is not None:
                for name in self._split_sting(n.text, [";"]):
                    metadata.add_credit(Credit(name.strip(), [Role("Cover")]))

        # parse page data now
        pages_node = root.find("Pages")
        if pages_node is not None:
            for page in pages_node:
                p: dict[str, Any] = page.attrib
                if "Image" in p:
                    p["Image"] = int(p["Image"])
                metadata.pages.append(cast(ImageMetadata, p))

        metadata.is_empty = False

        return metadata

    def write_to_external_file(
        self, filename: str, metadata: Metadata, xml: Optional[any] = None
    ) -> None:
        tree = self.convert_metadata_to_xml(metadata, xml)
        tree.write(filename, encoding="utf-8", xml_declaration=True)

    def read_from_external_file(self, filename: str) -> Metadata:
        tree = ET.parse(filename)
        return self.convert_xml_to_metadata(tree)
