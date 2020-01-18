"""A class to encapsulate ComicRack's ComicInfo.xml data"""

# Copyright 2012-2014 Anthony Beville


import xml.etree.ElementTree as ET

from . import utils
from .genericmetadata import GenericMetadata


class ComicInfoXml:

    writer_synonyms = ["writer", "plotter", "scripter"]
    penciller_synonyms = ["artist", "penciller", "penciler", "breakdowns", "illustrator"]
    inker_synonyms = ["inker", "artist", "finishes", "illustrator"]
    colorist_synonyms = ["colorist", "colourist", "colorer", "colourer"]
    letterer_synonyms = ["letterer"]
    cover_synonyms = ["cover", "covers", "coverartist", "cover artist"]
    editor_synonyms = ["editor"]

    def get_parseable_credits(self):
        parsable_credits = []
        parsable_credits.extend(self.writer_synonyms)
        parsable_credits.extend(self.penciller_synonyms)
        parsable_credits.extend(self.inker_synonyms)
        parsable_credits.extend(self.colorist_synonyms)
        parsable_credits.extend(self.letterer_synonyms)
        parsable_credits.extend(self.cover_synonyms)
        parsable_credits.extend(self.editor_synonyms)
        return parsable_credits

    def metadata_from_string(self, string):

        tree = ET.ElementTree(ET.fromstring(string))
        return self.convert_xml_to_metadata(tree)

    def string_from_metadata(self, metadata):

        header = '<?xml version="1.0"?>\n'

        tree = self.convert_metadata_to_xml(self, metadata)
        tree_str = ET.tostring(tree.getroot()).decode()
        return header + tree_str

    def indent(self, elem, level=0):
        # for making the XML output readable
        i = "\n" + level * "  "
        if elem:
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                self.indent(elem, level + 1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    def convert_metadata_to_xml(self, filename, metadata):

        # build a tree structure
        root = ET.Element("ComicInfo")
        root.attrib["xmlns:xsi"] = "http://www.w3.org/2001/XMLSchema-instance"
        root.attrib["xmlns:xsd"] = "http://www.w3.org/2001/XMLSchema"
        # helper func

        def assign(cix_entry, md_entry):
            if md_entry is not None:
                ET.SubElement(root, cix_entry).text = "{0}".format(md_entry)

        assign("Title", metadata.title)
        assign("Series", metadata.series)
        assign("Number", metadata.issue)
        assign("Count", metadata.issue_count)
        assign("Volume", metadata.volume)
        assign("AlternateSeries", metadata.alternate_series)
        assign("AlternateNumber", metadata.alternate_number)
        assign("StoryArc", metadata.story_arc)
        assign("SeriesGroup", metadata.series_group)
        assign("AlternateCount", metadata.alternate_count)
        assign("Summary", metadata.comments)
        assign("Notes", metadata.notes)
        assign("Year", metadata.year)
        assign("Month", metadata.month)
        assign("Day", metadata.day)

        # need to specially process the credits, since they are structured
        # differently than CIX
        credit_writer_list = list()
        credit_penciller_list = list()
        credit_inker_list = list()
        credit_colorist_list = list()
        credit_letterer_list = list()
        credit_cover_list = list()
        credit_editor_list = list()

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
        if len(credit_writer_list) > 0:
            node = ET.SubElement(root, "Writer")
            node.text = utils.list_to_string(credit_writer_list)

        if len(credit_penciller_list) > 0:
            node = ET.SubElement(root, "Penciller")
            node.text = utils.list_to_string(credit_penciller_list)

        if len(credit_inker_list) > 0:
            node = ET.SubElement(root, "Inker")
            node.text = utils.list_to_string(credit_inker_list)

        if len(credit_colorist_list) > 0:
            node = ET.SubElement(root, "Colorist")
            node.text = utils.list_to_string(credit_colorist_list)

        if len(credit_letterer_list) > 0:
            node = ET.SubElement(root, "Letterer")
            node.text = utils.list_to_string(credit_letterer_list)

        if len(credit_cover_list) > 0:
            node = ET.SubElement(root, "CoverArtist")
            node.text = utils.list_to_string(credit_cover_list)

        if len(credit_editor_list) > 0:
            node = ET.SubElement(root, "Editor")
            node.text = utils.list_to_string(credit_editor_list)

        assign("Publisher", metadata.publisher)
        assign("Imprint", metadata.imprint)
        assign("Genre", metadata.genre)
        assign("Web", metadata.web_link)
        assign("PageCount", metadata.page_count)
        assign("LanguageISO", metadata.language)
        assign("Format", metadata.format)
        assign("AgeRating", metadata.maturity_rating)
        if metadata.black_and_white is not None and metadata.black_and_white:
            ET.SubElement(root, "BlackAndWhite").text = "Yes"
        assign("Manga", metadata.manga)
        assign("Characters", metadata.characters)
        assign("Teams", metadata.teams)
        assign("Locations", metadata.locations)
        assign("ScanInformation", metadata.scan_info)

        #  loop and add the page entries under pages node
        if len(metadata.pages) > 0:
            pages_node = ET.SubElement(root, "Pages")
            for page_dict in metadata.pages:
                page_node = ET.SubElement(pages_node, "Page")
                page_node.attrib = page_dict

        # self pretty-print
        self.indent(root)

        # wrap it in an ElementTree instance, and save as XML
        tree = ET.ElementTree(root)
        return tree

    @classmethod
    def convert_xml_to_metadata(cls, tree):

        root = tree.getroot()

        if root.tag != "ComicInfo":
            raise ValueError("Metadata is not ComicInfo format")

        metadata = GenericMetadata()

        # Helper function
        def xlate(tag):
            node = root.find(tag)
            if node is not None:
                return node.text
            else:
                return None

        metadata.series = xlate("Series")
        metadata.title = xlate("Title")
        metadata.issue = xlate("Number")
        metadata.issue_count = xlate("Count")
        metadata.volume = xlate("Volume")
        metadata.alternate_series = xlate("AlternateSeries")
        metadata.alternate_number = xlate("AlternateNumber")
        metadata.alternate_count = xlate("AlternateCount")
        metadata.comments = xlate("Summary")
        metadata.notes = xlate("Notes")
        metadata.year = xlate("Year")
        metadata.month = xlate("Month")
        metadata.day = xlate("Day")
        metadata.publisher = xlate("Publisher")
        metadata.imprint = xlate("Imprint")
        metadata.genre = xlate("Genre")
        metadata.web_link = xlate("Web")
        metadata.language = xlate("LanguageISO")
        metadata.format = xlate("Format")
        metadata.manga = xlate("Manga")
        metadata.characters = xlate("Characters")
        metadata.teams = xlate("Teams")
        metadata.locations = xlate("Locations")
        metadata.page_count = xlate("PageCount")
        metadata.scan_info = xlate("ScanInformation")
        metadata.story_arc = xlate("StoryArc")
        metadata.series_group = xlate("SeriesGroup")
        metadata.maturity_rating = xlate("AgeRating")

        tmp = xlate("BlackAndWhite")
        metadata.black_and_white = False
        if tmp is not None and tmp.lower() in ["yes", "true", "1"]:
            metadata.black_and_white = True
        # Now extract the credit info
        for credit_node in root:
            if (
                credit_node.tag == "Writer"
                or credit_node.tag == "Penciller"
                or credit_node.tag == "Inker"
                or credit_node.tag == "Colorist"
                or credit_node.tag == "Letterer"
                or credit_node.tag == "Editor"
            ):
                if credit_node.text is not None:
                    for name in credit_node.text.split(","):
                        metadata.add_credit(name.strip(), credit_node.tag)

            if credit_node.tag == "CoverArtist":
                if credit_node.text is not None:
                    for name in credit_node.text.split(","):
                        metadata.add_credit(name.strip(), "Cover")

        # parse page data now
        pages_node = root.find("Pages")
        if pages_node is not None:
            for page in pages_node:
                metadata.pages.append(page.attrib)
                # print page.attrib

        metadata.isEmpty = False

        return metadata

    def write_to_external_file(self, filename, metadata):

        tree = self.convert_metadata_to_xml(self, metadata)
        # ET.dump(tree)
        tree.write(filename, encoding="utf-8")

    def read_from_external_file(self, filename):

        tree = ET.parse(filename)
        return self.convert_xml_to_metadata(tree)
