"""A class to encapsulate ComicRack's ComicInfo.xml data"""

# Copyright 2012-2014 Anthony Beville
# Copyright 2020 Brian Pepple


import xml.etree.ElementTree as ET
from re import split
from typing import Any, List, Optional, Union, cast

from .genericmetadata import GenericMetadata, ImageMetadata, SeriesMetadata
from .issuestring import IssueString
from .utils import list_to_string, string_to_list, xlate


class ComicInfoXml:

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

    def metadata_from_string(self, string: str) -> GenericMetadata:
        tree = ET.ElementTree(ET.fromstring(string))
        return self.convert_xml_to_metadata(tree)

    def string_from_metadata(
        self, metadata: GenericMetadata, xml: Optional[any] = None
    ) -> str:
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

    def convert_metadata_to_xml(self, metadata: GenericMetadata, xml=None) -> ET.ElementTree:
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

        assign("Title", list_to_string(metadata.stories))
        assign("Series", metadata.series.name)
        assign("Number", metadata.issue)
        assign("Count", metadata.issue_count)
        assign("Volume", metadata.volume)
        assign("AlternateSeries", metadata.alternate_series)
        assign("AlternateNumber", metadata.alternate_number)
        assign("SeriesGroup", metadata.series_group)
        assign("AlternateCount", metadata.alternate_count)
        assign("Summary", metadata.comments)
        assign("Notes", metadata.notes)
        assign("Year", metadata.year)
        assign("Month", metadata.month)
        assign("Day", metadata.day)

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

            if credit["role"].lower() in set(self.writer_synonyms):
                credit_writer_list.append(credit["person"].replace(",", ""))

            if credit["role"].lower() in set(self.penciller_synonyms):
                credit_penciller_list.append(credit["person"].replace(",", ""))

            if credit["role"].lower() in set(self.inker_synonyms):
                credit_inker_list.append(credit["person"].replace(",", ""))

            if credit["role"].lower() in set(self.colorist_synonyms):
                credit_colorist_list.append(credit["person"].replace(",", ""))

            if credit["role"].lower() in set(self.letterer_synonyms):
                credit_letterer_list.append(credit["person"].replace(",", ""))

            if credit["role"].lower() in set(self.cover_synonyms):
                credit_cover_list.append(credit["person"].replace(",", ""))

            if credit["role"].lower() in set(self.editor_synonyms):
                credit_editor_list.append(credit["person"].replace(",", ""))

        # second, convert each list to string, and add to XML struct
        assign("Writer", list_to_string(credit_writer_list))
        assign("Penciller", list_to_string(credit_penciller_list))
        assign("Inker", list_to_string(credit_inker_list))
        assign("Colorist", list_to_string(credit_colorist_list))
        assign("Letterer", list_to_string(credit_letterer_list))
        assign("CoverArtist", list_to_string(credit_cover_list))
        assign("Editor", list_to_string(credit_editor_list))

        assign("Publisher", metadata.publisher)
        assign("Imprint", metadata.imprint)
        assign("Genre", list_to_string(metadata.genres))
        assign("Web", metadata.web_link)
        assign("PageCount", metadata.page_count)
        assign("LanguageISO", metadata.language)
        assign("Format", metadata.format)
        assign("BlackAndWhite", "Yes" if metadata.black_and_white else None)
        assign("Manga", self.validate_manga(metadata.manga))
        assign("Characters", list_to_string(metadata.characters))
        assign("Teams", list_to_string(metadata.teams))
        assign("Locations", list_to_string(metadata.locations))
        assign("ScanInformation", metadata.scan_info)
        assign("StoryArc", list_to_string(metadata.story_arcs))
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

    def convert_xml_to_metadata(self, tree: ET.ElementTree) -> GenericMetadata:
        root = tree.getroot()

        if root.tag != "ComicInfo":
            raise ValueError("Metadata is not ComicInfo format")

        def get(name):
            tag = root.find(name)
            if tag is None:
                return None
            return tag.text

        metadata = GenericMetadata()
        metadata.series = SeriesMetadata(name=xlate(get("Series")))
        metadata.stories = string_to_list(xlate(get("Title")))
        metadata.issue = IssueString(xlate(get("Number"))).as_string()
        metadata.issue_count = xlate(get("Count"), True)
        metadata.volume = xlate(get("Volume"), True)
        metadata.alternate_series = xlate(get("AlternateSeries"))
        metadata.alternate_number = IssueString(xlate(get("AlternateNumber"))).as_string()
        metadata.alternate_count = xlate(get("AlternateCount"), True)
        metadata.comments = xlate(get("Summary"))
        metadata.notes = xlate(get("Notes"))
        metadata.year = xlate(get("Year"), True)
        metadata.month = xlate(get("Month"), True)
        metadata.day = xlate(get("Day"), True)
        metadata.publisher = xlate(get("Publisher"))
        metadata.imprint = xlate(get("Imprint"))
        metadata.genres = string_to_list(xlate(get("Genre")))
        metadata.web_link = xlate(get("Web"))
        metadata.language = xlate(get("LanguageISO"))
        metadata.format = xlate(get("Format"))
        metadata.manga = xlate(get("Manga"))
        metadata.characters = string_to_list(xlate(get("Characters")))
        metadata.teams = string_to_list(xlate(get("Teams")))
        metadata.locations = string_to_list(xlate(get("Locations")))
        metadata.page_count = xlate(get("PageCount"), True)
        metadata.scan_info = xlate(get("ScanInformation"))
        metadata.story_arcs = string_to_list(xlate(get("StoryArc")))
        metadata.series_group = xlate(get("SeriesGroup"))
        metadata.age_rating = xlate(get("AgeRating"))

        tmp = xlate(get("BlackAndWhite"))
        metadata.black_and_white = False
        if tmp is not None and tmp.lower() in ["yes", "true", "1"]:
            metadata.black_and_white = True
        # Now extract the credit info
        for n in root:
            if (
                n.tag == "Writer"
                or n.tag == "Penciller"
                or n.tag == "Inker"
                or n.tag == "Colorist"
                or n.tag == "Letterer"
                or n.tag == "Editor"
            ) and n.text is not None:
                for name in self._split_sting(n.text, [";"]):
                    metadata.add_credit(name.strip(), n.tag)

            if n.tag == "CoverArtist" and n.text is not None:
                for name in self._split_sting(n.text, [";"]):
                    metadata.add_credit(name.strip(), "Cover")

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
        self, filename: str, metadata: GenericMetadata, xml: Optional[any] = None
    ) -> None:
        tree = self.convert_metadata_to_xml(metadata, xml)
        tree.write(filename, encoding="utf-8", xml_declaration=True)

    def read_from_external_file(self, filename: str) -> GenericMetadata:
        tree = ET.parse(filename)
        return self.convert_xml_to_metadata(tree)
