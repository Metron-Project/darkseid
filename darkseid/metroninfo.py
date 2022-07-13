"""A class to encapsulate Metron's MetronInfo.xml data"""


import xml.etree.ElementTree as ET
from typing import List, Optional, Union

from darkseid.genericmetadata import (
    GenericMetadata,
    InfoSourceMetadata,
    PriceMetadata,
    SeriesMetadata,
)


class MetronInfoXML:
    mix_info_sources = [
        "Comic Vine",
        "Grand Comics Database",
        "Metron",
        "League of Comic Geeks",
    ]
    mix_age_ratings = ["Unknown", "Everyone", "Teen", "Teen Plus", "Mature"]
    mix_series_types = [
        "Annual",
        "Graphic Novel",
        "Limited",
        "One-Shot",
        "Series",
        "Trade Paperback",
    ]

    def metadata_from_string(self, string: str) -> GenericMetadata:
        tree = ET.ElementTree(ET.fromstring(string))
        return self.convert_xml_to_metadata(tree)

    def string_from_metadata(
        self, metadata: GenericMetadata, xml: Optional[any] = None
    ) -> str:
        tree = self.convert_metadata_to_xml(metadata, xml)
        return ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True).decode()

    def _get_root(self, xml) -> ET.Element:
        if xml:
            root = ET.ElementTree(ET.fromstring(xml)).getroot()
        else:
            # build a tree structure
            root = ET.Element("MetronInfo")
            root.attrib["xmlns:xsi"] = "https://www.w3.org/2001/XMLSchema-instance"
            root.attrib["xmlns:xsd"] = "https://www.w3.org/2001/XMLSchema"

        return root

    @classmethod
    def validate_age_rating(cls, val: Optional[str] = None) -> Optional[str]:
        if val is not None:
            return "Unknown" if val not in cls.mix_age_ratings else val

    def convert_metadata_to_xml(self, metadata: GenericMetadata, xml=None) -> ET.ElementTree:

        root = self._get_root(xml)

        # helper funcs
        def assign(mix_entry: str, md_entry: Optional[Union[str, int]]) -> None:
            if md_entry is not None and md_entry:
                et_entry = root.find(mix_entry)
                if et_entry is not None:
                    et_entry.text = str(md_entry)
                else:
                    ET.SubElement(root, mix_entry).text = str(md_entry)
            else:
                et_entry = root.find(mix_entry)
                if et_entry is not None:
                    root.remove(et_entry)

        def assign_basic_children(parent: str, child: str, vals: List[str]) -> None:
            parent_node = root.find(parent)
            if parent_node is None:
                parent_node = ET.SubElement(root, parent)
            else:
                parent_node.clear()

            for item in vals:
                child_node = ET.SubElement(parent_node, child)
                child_node.text = item

        def assign_series(series: SeriesMetadata) -> None:
            parent_node = root.find("Series")
            if parent_node is None:
                parent_node = ET.SubElement(root, "Series")
            else:
                parent_node.clear()

            name_node = ET.SubElement(parent_node, "Name")
            name_node.text = series.name
            sort_node = ET.SubElement(parent_node, "SortName")
            sort_node.text = series.sort_name
            volume_node = ET.SubElement(parent_node, "Volume")
            volume_node.text = str(metadata.series.volume)
            type_node = ET.SubElement(parent_node, "Format")
            type_node.text = series.format

        def assign_info_source(info: InfoSourceMetadata) -> None:
            id_entry = root.find("ID")
            if id_entry is None:
                id_entry = ET.SubElement(root, "ID")
            else:
                id_entry.clear()
            id_entry.text = str(info.id)
            id_entry.attrib = {"source": info.source}

        def assign_price(price: PriceMetadata) -> None:
            price_entry = root.find("Price")
            if price_entry is None:
                price_entry = ET.SubElement(root, "Price")
            else:
                price_entry.clear()
            price_entry.text = str(price.val)
            price_entry.attrib = {"currency": price.currency}

        if metadata.info_source:
            assign_info_source(metadata.info_source)
        assign("Publisher", metadata.publisher)
        assign_series(metadata.series)  # Should always have Series info.
        assign("CollectionTitle", metadata.collection_title)
        assign("Number", metadata.issue)
        assign_basic_children("Stories", "Story", metadata.stories)
        assign("Summary", metadata.comments)
        if metadata.price:
            assign_price(metadata.price)
        assign("CoverDate", metadata.cover_date)
        assign("StoreDate", metadata.store_date)
        assign("PageCount", metadata.page_count)
        assign_basic_children("Genres", "Genre", metadata.genres)
        assign_basic_children("Tags", "Tag", metadata.tags)
        assign_basic_children("Arcs", "Arc", metadata.story_arcs)
        assign_basic_children("Characters", "Character", metadata.characters)
        assign_basic_children("Teams", "Team", metadata.teams)
        assign_basic_children("Locations", "Location", metadata.locations)
        assign("URL", metadata.web_link)
        assign("AgeRating", self.validate_age_rating(metadata.age_rating))
        assign("BlackAndWhite", "Yes" if metadata.black_and_white else None)

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

    def write_to_external_file(
        self, filename: str, metadata: GenericMetadata, xml: Optional[any] = None
    ) -> None:
        tree = self.convert_metadata_to_xml(metadata, xml)
        tree.write(filename, encoding="utf-8", xml_declaration=True)

    def read_from_external_file(self, filename: str) -> GenericMetadata:
        tree = ET.parse(filename)
        return self.convert_xml_to_metadata(tree)
