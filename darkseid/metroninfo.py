"""A class to encapsulate Metron's MetronInfo.xml data"""
import xml.etree.ElementTree as ET
from datetime import datetime
from decimal import Decimal
from typing import Any, List, Optional, Union, cast

from darkseid.issue_string import IssueString
from darkseid.metadata import (
    GTIN,
    Arc,
    Basic,
    Credit,
    ImageMetadata,
    Metadata,
    Price,
    Role,
    Series,
)
from darkseid.utils import xlate


class MetronInfo:
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

    def metadata_from_string(self, string: str) -> Metadata:
        tree = ET.ElementTree(ET.fromstring(string))
        return self.convert_xml_to_metadata(tree)

    def string_from_metadata(self, md: Metadata, xml: Optional[any] = None) -> str:
        tree = self.convert_metadata_to_xml(md, xml)
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
    def valid_info_source(cls, val: Optional[Basic] = None) -> bool:
        return val is not None and val.name in cls.mix_info_sources

    @classmethod
    def valid_age_rating(cls, val: Optional[str] = None) -> Optional[str]:
        if val is not None:
            return "Unknown" if val not in cls.mix_age_ratings else val
        else:
            return None

    def convert_metadata_to_xml(self, md: Metadata, xml=None) -> ET.ElementTree:
        root = self._get_root(xml)

        # helper funcs
        def assign(element: str, val: Optional[Union[str, int]]) -> None:
            if val is not None and val:
                et_entry = root.find(element)
                if et_entry is not None:
                    et_entry.text = str(val)
                else:
                    ET.SubElement(root, element).text = str(val)
            else:
                et_entry = root.find(element)
                if et_entry is not None:
                    root.remove(et_entry)

        def get_parent_node(element: str) -> ET.Element:
            parent_node = root.find(element)
            if parent_node is None:
                parent_node = ET.SubElement(root, element)
            else:
                parent_node.clear()

            return parent_node

        def assign_arc(vals: List[Arc]) -> None:
            parent_node = get_parent_node("Arcs")
            for item in vals:
                arc_node = ET.SubElement(parent_node, "Arc")
                if item.id_:
                    arc_node.attrib = {"id": str(item.id_)}
                name_node = ET.SubElement(arc_node, "Name")
                name_node.text = item.name
                if item.number:
                    number_node = ET.SubElement(arc_node, "Number")
                    number_node.text = str(item.number)

        def assign_basic_children(parent: str, child: str, vals: List[Basic]) -> None:
            parent_node = get_parent_node(parent)

            for item in vals:
                child_node = ET.SubElement(parent_node, child)
                child_node.text = item.name
                if item.id_:
                    child_node.attrib = {"id": str(item.id_)}

        def assign_series(series: Series) -> None:
            series_node = get_parent_node("Series")
            if series.id_ or series.language:
                attrib = {}
                if series.id_:
                    attrib["id"] = str(series.id_)
                if series.language:
                    attrib["lang"] = series.language
                series_node.attrib = attrib

            name_node = ET.SubElement(series_node, "Name")
            name_node.text = series.name

            sort_node = ET.SubElement(series_node, "SortName")
            sort_node.text = series.sort_name
            volume_node = ET.SubElement(series_node, "Volume")
            volume_node.text = str(md.series.volume)
            type_node = ET.SubElement(series_node, "Format")
            type_node.text = series.format_

        def assign_info_source(info: Basic) -> None:
            id_node = get_parent_node("ID")
            id_node.text = str(info.id_)
            id_node.attrib = {"source": info.name}

        def assign_gtin(gtin: GTIN) -> None:
            gtin_node = get_parent_node("GTIN")
            if gtin.isbn:
                isbn_node = ET.SubElement(gtin_node, "ISBN")
                isbn_node.text = str(gtin.isbn)
            if gtin.upc:
                upc_node = ET.SubElement(gtin_node, "UPC")
                upc_node.text = str(gtin.upc)

        def assign_basic_resource(element: str, info: Basic) -> None:
            resource_node = get_parent_node(element)
            resource_node.text = info.name
            if info.id_:
                resource_node.attrib = {"id": str(info.id_)}

        def assign_price(prices: List[Price]) -> None:
            price_node = get_parent_node("Prices")

            for p in prices:
                child_node = ET.SubElement(price_node, "Price")
                child_node.text = str(p.amount)
                if p.country:
                    child_node.attrib = {"country": p.country}

        def assign_credits(credits: List[Credit]) -> None:
            parent_node = root.find("Credits")
            if parent_node is None:
                parent_node = ET.SubElement(root, "Credits")
            else:
                parent_node.clear()

            for item in credits:
                credit_node = ET.SubElement(parent_node, "Credit")
                creator_node = ET.SubElement(credit_node, "Creator")
                creator_node.text = item.person
                if item.id_:
                    creator_node.attrib = {"id": str(item.id_)}
                roles_node = ET.SubElement(credit_node, "Roles")
                for r in item.role:
                    role_node = ET.SubElement(roles_node, "Role")
                    role_node.text = r.name
                    if r.id_:
                        role_node.attrib = {"id": str(r.id_)}

        if self.valid_info_source(md.info_source):
            assign_info_source(md.info_source)
        assign_basic_resource("Publisher", md.publisher)
        assign_series(md.series)
        assign("CollectionTitle", md.collection_title)
        assign("Number", md.issue)
        assign_basic_children("Stories", "Story", md.stories)
        assign("Summary", md.comments)
        if md.prices:
            assign_price(md.prices)
        assign("CoverDate", md.cover_date)
        assign("StoreDate", md.store_date)
        assign("PageCount", md.page_count)
        assign("Notes", md.notes)
        assign_basic_children("Genres", "Genre", md.genres)
        assign_basic_children("Tags", "Tag", md.tags)
        assign_arc(md.story_arcs)
        assign_basic_children("Characters", "Character", md.characters)
        assign_basic_children("Teams", "Team", md.teams)
        assign_basic_children("Locations", "Location", md.locations)
        assign_basic_children("Reprints", "Reprint", md.reprints)
        if md.gtin:
            assign_gtin(md.gtin)
        # XML booleans expect 'true' or 'false'
        assign("BlackAndWhite", "true" if md.black_and_white else None)
        assign("AgeRating", self.valid_age_rating(md.age_rating))
        assign("URL", md.web_link)
        assign_credits(md.credits)

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
        tree = ET.ElementTree(root)
        return tree

    def convert_xml_to_metadata(self, tree: ET.ElementTree) -> Metadata:
        root = tree.getroot()

        if root.tag != "MetronInfo":
            raise ValueError("Metadata is not MetronInfo format")

        def get(element: str) -> Optional[str]:
            tag = root.find(element)
            return None if tag is None else tag.text

        def get_gtin() -> Optional[GTIN]:
            resource = root.find("GTIN")
            gtin = GTIN()
            found = False
            for item in resource:
                if item.text:
                    found = True
                    if item.tag == "UPC":
                        gtin.upc = int(item.text)
                    if item.tag == "ISBN":
                        gtin.isbn = int(item.text)

            return gtin if found else None

        def get_info_source() -> Optional[Basic]:
            resource = root.find("ID")
            if resource is not None:
                return Basic(resource.attrib["source"], int(resource.text))
            else:
                return None

        def get_resource(element: str) -> Optional[Basic]:
            resource = root.find(element)
            if resource is not None:
                attrib: dict[str, Any] = resource.attrib
                if attrib and "id" in attrib:
                    return Basic(resource.text, int(attrib["id"]))
                else:
                    return Basic(resource.text)
            else:
                return None

        def get_resource_list(element: str) -> List[Basic]:
            resource = root.find(element)
            if resource is not None:
                resource_list = []
                for item in resource:
                    attrib: dict[str, Any] = item.attrib
                    if attrib and "id" in attrib:
                        resource_list.append(Basic(item.text, int(attrib["id"])))
                    else:
                        resource_list.append(Basic(item.text))
                return resource_list
            return []

        def get_prices() -> List[Price]:
            resource = root.find("Prices")
            if resource is not None:
                resource_list = []
                for item in resource:
                    attrib: dict[str, Any] = item.attrib
                    if attrib and "country" in attrib:
                        resource_list.append(Price(Decimal(item.text), attrib["country"]))
                    else:
                        resource_list.append(Price(Decimal(item.text)))
                return resource_list

        def get_series() -> Optional[Series]:
            resource = root.find("Series")
            if resource is not None:
                series_md = Series("None")  # Use a dummy series name.
                attrib: dict[str, Any] = resource.attrib
                if attrib and "id" in attrib:
                    series_md.id_ = int(attrib["id"])
                if attrib and "lang" in attrib:
                    series_md.language = attrib["lang"]

                for item in resource:
                    if item.text:
                        if item.tag == "Name":
                            series_md.name = item.text
                        if item.tag == "SortName":
                            series_md.sort_name = item.text
                        if item.tag == "Volume":
                            series_md.volume = int(item.text)
                        if item.tag == "Format":
                            series_md.format_ = item.text
                return series_md
            return None

        def get_arcs() -> List[Arc]:
            arcs_node = root.find("Arcs")
            resource = arcs_node.findall("Arc")
            if resource is not None:
                arcs_list = []
                for item in resource:
                    name = item.find("Name")
                    attrib: dict[str, Any] = item.attrib
                    if attrib and "id" in attrib:
                        a = Arc(name.text, int(attrib["id"]))
                    else:
                        a = Arc(name.text)
                    number = item.find("Number")
                    if number is not None:
                        a.number = int(number.text)
                    arcs_list.append(a)
                return arcs_list
            else:
                return []

        def get_credits() -> Optional[Credit]:
            parent = root.find("Credits")
            resource = parent.findall("Credit")
            if resource is not None:
                credits_list = []
                for credit in resource:
                    creator = credit.find("Creator")
                    if creator.attrib and "id" in creator.attrib:
                        c = Credit(creator.text, [], int(creator.attrib["id"]))
                    else:
                        c = Credit(creator.text, [])
                    # Now handle roles
                    roles = credit.find("Roles")
                    if roles is not None:
                        role_list = []
                        for r in roles:
                            role = Role(r.text)
                            if r.attrib and "id" in r.attrib:
                                role.id_ = int(r.attrib["id"])
                            role_list.append(role)
                        if role_list:
                            c.role = role_list
                    credits_list.append(c)
                return credits_list
            else:
                return None

        md = Metadata()
        md.info_source = get_info_source()
        md.publisher = get_resource("Publisher")
        md.series = get_series()
        md.collection_title = get("CollectionTitle")
        md.issue = IssueString(get("Number")).as_string()
        md.stories = get_resource_list("Stories")
        md.comments = get("Summary")
        md.prices = get_prices()
        md.cover_date = datetime.strptime(get("CoverDate"), "%Y-%m-%d").date()
        md.store_date = datetime.strptime(get("StoreDate"), "%Y-%m-%d").date()
        md.page_count = xlate(get("PageCount"), True)
        md.notes = get("Notes")
        md.genres = get_resource_list("Genres")
        md.tags = get_resource_list("Tags")
        md.story_arcs = get_arcs()
        md.characters = get_resource_list("Characters")
        md.teams = get_resource_list("Teams")
        md.locations = get_resource_list("Locations")
        md.reprints = get_resource_list("Reprints")
        md.gtin = get_gtin()
        black_white = get("BlackAndWhite")
        if black_white is not None and black_white.casefold() in ["yes", "true", "1"]:
            md.black_and_white = True
        md.age_rating = get("AgeRating")
        md.web_link = get("URL")
        # Credits
        md.credits = get_credits()

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
        self, filename: str, md: Metadata, xml: Optional[any] = None
    ) -> None:
        tree = self.convert_metadata_to_xml(md, xml)
        tree.write(filename, encoding="utf-8", xml_declaration=True)

    def read_from_external_file(self, filename: str) -> Metadata:
        tree = ET.parse(filename)
        return self.convert_xml_to_metadata(tree)
