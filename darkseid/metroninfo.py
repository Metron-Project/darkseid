"""A class to encapsulate MetronInfo.xml data."""

# Copyright 2024 Brian Pepple

from __future__ import annotations

import xml.etree.ElementTree as ET  # noqa: N817
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING, ClassVar, cast

from defusedxml.ElementTree import fromstring, parse

from darkseid.issue_string import IssueString
from darkseid.metadata import (
    GTIN,
    AlternativeNames,
    Arc,
    Basic,
    Credit,
    ImageMetadata,
    Metadata,
    Price,
    Publisher,
    Role,
    Series,
    Universe,
)

if TYPE_CHECKING:
    from pathlib import Path


class MetronInfo:
    mix_info_sources = frozenset(
        {"comic vine", "grand comics database", "marvel", "metron", "league of comic geeks"}
    )
    mix_age_ratings: ClassVar[frozenset[str]] = frozenset(
        {
            "unknown",
            "everyone",
            "teen",
            "teen plus",
            "mature",
        }
    )
    mix_series_format = frozenset(
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
    mix_genres = frozenset(
        {
            "adult",
            "crime",
            "espionage",
            "fantasy",
            "historical",
            "horror",
            "humor",
            "manga",
            "parody",
            "romance",
            "science fiction",
            "sport",
            "super-hero",
            "war",
            "western",
        }
    )
    mix_roles = frozenset(
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

    def metadata_from_string(self, string: str) -> Metadata:
        tree = ET.ElementTree(fromstring(string))
        return self.convert_xml_to_metadata(tree)

    def string_from_metadata(
        self,
        md: Metadata,
        xml: bytes = b"",
    ) -> str:
        tree = self.convert_metadata_to_xml(md, xml)
        return ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True).decode()

    @staticmethod
    def _get_root(xml: any) -> ET.Element:
        root = ET.ElementTree(fromstring(xml)).getroot() if xml else ET.Element("MetronInfo")
        root.attrib["xmlns:xsi"] = "https://www.w3.org/2001/XMLSchema-instance"
        root.attrib["xmlns:xsd"] = "https://www.w3.org/2001/XMLSchema"
        return root

    @classmethod
    def valid_info_source(cls, val: Basic | None = None) -> bool:
        return val is not None and val.name.lower() in cls.mix_info_sources

    @classmethod
    def list_contains_valid_genre(cls, vals: list[Basic]) -> bool:
        return any(val.name.lower() in cls.mix_genres for val in vals)

    @classmethod
    def valid_age_rating(cls, val: str | None = None) -> str | None:
        if val is None:
            return None
        return "Unknown" if val.lower() not in cls.mix_age_ratings else val

    @staticmethod
    def get_or_create_element(parent: ET.Element, tag: str) -> ET.Element:
        element = parent.find(tag)
        if element is None:
            return ET.SubElement(parent, tag)
        element.clear()
        return element

    @staticmethod
    def assign(root: ET.Element, element: str, val: str | int | date | None = None) -> None:
        et_entry = root.find(element)
        if val is None:
            if et_entry is not None:
                root.remove(et_entry)
        else:
            if et_entry is None:
                et_entry = ET.SubElement(root, element)
            et_entry.text = val.strftime("%Y-%m-%d") if isinstance(val, date) else str(val)

    @staticmethod
    def assign_datetime(root: ET.Element, element: str, val: datetime | None = None) -> None:
        et_entry = root.find(element)
        if val is None:
            if et_entry is not None:
                root.remove(et_entry)
        else:
            if et_entry is None:
                et_entry = ET.SubElement(root, element)
            et_entry.text = val.isoformat(sep="T")

    @staticmethod
    def assign_basic_children(root: ET.Element, parent: str, child: str, vals: list[Basic]) -> None:
        parent_node = MetronInfo.get_or_create_element(root, parent)
        create_sub_element = ET.SubElement
        for val in vals:
            child_node = create_sub_element(parent_node, child)
            name = val.name
            child_node.text = name
            if id_ := val.id_:
                child_node.attrib["id"] = str(id_)

    @staticmethod
    def assign_basic_resource(root: ET.Element, element: str, val: Basic) -> None:
        resource_node = MetronInfo.get_or_create_element(root, element)
        resource_node.text = val.name
        if val.id_:
            resource_node.attrib["id"] = str(val.id_)

    @staticmethod
    def assign_arc(root: ET.Element, vals: list[Arc]) -> None:
        parent_node = MetronInfo.get_or_create_element(root, "Arcs")
        for val in vals:
            attributes = {"id": str(val.id_)} if val.id_ else {}
            child_node = ET.SubElement(parent_node, "Arc", attrib=attributes)
            ET.SubElement(child_node, "Name").text = val.name
            if val.number:
                ET.SubElement(child_node, "Number").text = str(val.number)

    @staticmethod
    def assign_publisher(root: ET.Element, publisher: Publisher) -> None:
        if publisher is None:
            return
        publisher_node = MetronInfo.get_or_create_element(root, "Publisher")
        if publisher.id_:
            publisher_node.attrib = {"id": str(publisher.id_)}

        ET.SubElement(publisher_node, "Name").text = publisher.name

        if publisher.imprint:
            imprint_node = ET.SubElement(
                publisher_node,
                "Imprint",
                {"id": str(publisher.imprint.id_)} if publisher.imprint.id_ else {},
            )
            imprint_node.text = publisher.imprint.name

    @staticmethod
    def assign_series(root: ET.Element, series: Series) -> None:
        if series is None:
            return
        series_node = MetronInfo.get_or_create_element(root, "Series")
        if series.id_ or series.language:
            series_node.attrib = {
                k: v for k, v in (("id", str(series.id_)), ("lang", series.language)) if v
            }

        ET.SubElement(series_node, "Name").text = series.name
        ET.SubElement(series_node, "SortName").text = series.sort_name
        ET.SubElement(series_node, "Volume").text = str(series.volume)
        ET.SubElement(series_node, "Format").text = (
            series.format if series.format in MetronInfo.mix_series_format else "Single Issue"
        )
        if series.alternative_names:
            alt_names_node = ET.SubElement(series_node, "AlternativeNames")
            for alt_name in series.alternative_names:
                alt_attrib = {
                    k: v for k, v in (("id", str(alt_name.id_)), ("lang", alt_name.language)) if v
                }
                ET.SubElement(alt_names_node, "Name", attrib=alt_attrib).text = alt_name.name

    @staticmethod
    def assign_info_source(root: ET.Element, primary: Basic, alt_lst: list[Basic]) -> None:
        id_node = MetronInfo.get_or_create_element(root, "ID")
        primary_node = ET.SubElement(id_node, "Primary")
        primary_node.text = str(primary.id_)
        primary_node.attrib["source"] = primary.name

        create_sub_element = ET.SubElement
        for alt in (alt for alt in alt_lst if MetronInfo.valid_info_source(alt)):
            alt_node = create_sub_element(id_node, "Alternative")
            alt_node.text = str(alt.id_)
            alt_node.attrib["source"] = alt.name

    @staticmethod
    def assign_gtin(root: ET.Element, gtin: GTIN) -> None:
        gtin_node = MetronInfo.get_or_create_element(root, "GTIN")
        if gtin.isbn:
            ET.SubElement(gtin_node, "ISBN").text = str(gtin.isbn)
        if gtin.upc:
            ET.SubElement(gtin_node, "UPC").text = str(gtin.upc)

    @staticmethod
    def assign_price(root: ET.Element, prices: list[Price]) -> None:
        price_node = MetronInfo.get_or_create_element(root, "Prices")
        create_sub_element = ET.SubElement
        for p in prices:
            child_node = create_sub_element(price_node, "Price", attrib={"country": p.country})
            child_node.text = str(p.amount)

    @staticmethod
    def assign_universes(root: ET.Element, universes: list[Universe]) -> None:
        universes_node = MetronInfo.get_or_create_element(root, "Universes")
        sub_element = ET.SubElement
        for u in universes:
            universe_node = sub_element(universes_node, "Universe")
            if u.id_:
                universe_node.attrib["id"] = str(u.id_)
            sub_element(universe_node, "Name").text = u.name
            if u.designation:
                sub_element(universe_node, "Designation").text = u.designation

    @staticmethod
    def assign_credits(root: ET.Element, credits_lst: list[Credit]) -> None:
        parent_node = MetronInfo.get_or_create_element(root, "Credits")
        sub_element = ET.SubElement
        mix_roles = MetronInfo.mix_roles

        for item in credits_lst:
            credit_node = sub_element(parent_node, "Credit")
            creator_node = sub_element(
                credit_node, "Creator", attrib={"id": str(item.id_)} if item.id_ else {}
            )
            creator_node.text = item.person
            roles_node = sub_element(credit_node, "Roles")

            for r in item.role:
                role_node = sub_element(
                    roles_node, "Role", attrib={"id": str(r.id_)} if r.id_ else {}
                )
                role_node.text = r.name if r.name in mix_roles else "Other"

    def convert_metadata_to_xml(self, md: Metadata, xml=None) -> ET.ElementTree:  # noqa: PLR0912,C901
        root = self._get_root(xml)

        if self.valid_info_source(md.info_source):
            self.assign_info_source(root, md.info_source, md.alt_sources)
        self.assign_publisher(root, md.publisher)
        self.assign_series(root, md.series)
        self.assign(root, "CollectionTitle", md.collection_title)
        self.assign(root, "Number", md.issue)
        if md.stories:
            self.assign_basic_children(root, "Stories", "Story", md.stories)
        self.assign(root, "Summary", md.comments)
        if md.prices:
            self.assign_price(root, md.prices)
        self.assign(root, "CoverDate", md.cover_date)
        self.assign(root, "StoreDate", md.store_date)
        self.assign(root, "PageCount", md.page_count)
        self.assign(root, "Notes", md.notes)
        if md.genres and self.list_contains_valid_genre(md.genres):
            self.assign_basic_children(root, "Genres", "Genre", md.genres)
        if md.tags:
            self.assign_basic_children(root, "Tags", "Tag", md.tags)
        if md.story_arcs:
            self.assign_arc(root, md.story_arcs)
        if md.characters:
            self.assign_basic_children(root, "Characters", "Character", md.characters)
        if md.teams:
            self.assign_basic_children(root, "Teams", "Team", md.teams)
        if md.universes:
            self.assign_universes(root, md.universes)
        if md.locations:
            self.assign_basic_children(root, "Locations", "Location", md.locations)
        if md.reprints:
            self.assign_basic_children(root, "Reprints", "Reprint", md.reprints)
        if md.gtin:
            self.assign_gtin(root, md.gtin)
        self.assign(root, "AgeRating", self.valid_age_rating(md.age_rating))
        self.assign(root, "URL", md.web_link)
        self.assign_datetime(root, "LastModified", md.modified)
        if md.credits:
            self.assign_credits(root, md.credits)

        if md.pages:
            pages_node = self.get_or_create_element(root, "Pages")
            for page_dict in md.pages:
                page = page_dict
                if "Image" in page:
                    page["Image"] = str(page["Image"])
                page_node = ET.SubElement(pages_node, "Page")
                page_node.attrib = dict(sorted(page_dict.items()))

        ET.indent(root)
        return ET.ElementTree(root)

    @staticmethod
    def convert_xml_to_metadata(tree: ET.ElementTree) -> Metadata:  # noqa: C901,PLR0915
        root = tree.getroot()

        if root.tag != "MetronInfo":
            msg = "XML is not a MetronInfo schema"
            raise ValueError(msg)

        def get_id_from_attrib(attrib: dict[str, str]) -> int | None:
            return int(attrib["id"]) if attrib and "id" in attrib else None

        def get(element: str) -> str | None:
            tag = root.find(element)
            return None if tag is None else tag.text

        def get_gtin() -> GTIN | None:
            resource = root.find("GTIN")
            if resource is None:
                return None

            gtin = GTIN()
            found = False
            for item in resource:
                if item.text:
                    match item.tag:
                        case "UPC":
                            gtin.upc = int(item.text)
                            found = True
                        case "ISBN":
                            gtin.isbn = int(item.text)
                            found = True
                        case _:
                            pass

            return gtin if found else None

        def get_info_sources() -> Basic | None:
            id_node = root.find("ID")
            if id_node is None:
                return None
            primary_node = id_node.find("Primary")
            if primary_node is None:
                return None
            return Basic(primary_node.attrib.get("source"), int(primary_node.text))

        def get_alt_sources() -> list[Basic] | None:
            id_node = root.find("ID")
            if id_node is None:
                return None
            alt_nodes = id_node.findall("Alternative")
            if alt_nodes is None:
                return None
            return [
                Basic(alt_node.attrib.get("source"), int(alt_node.text)) for alt_node in alt_nodes
            ]

        def get_resource_list(element: str) -> list[Basic]:
            resource = root.find(element)
            if resource is None:
                return []
            return [Basic(item.text, get_id_from_attrib(item.attrib)) for item in resource]

        def get_prices() -> list[Price]:
            resource = root.find("Prices")
            if resource is None:
                return []
            return [
                Price(Decimal(item.text), item.attrib.get("country", "US")) for item in resource
            ]

        def get_publisher() -> Publisher | None:
            resource = root.find("Publisher")
            if resource is None:
                return None

            publisher_name: str | None = None
            imprint: Basic | None = None

            tag_actions = {
                "Name": lambda obj: obj.text,
                "Imprint": lambda obj: Basic(obj.text, get_id_from_attrib(obj.attrib)),
            }

            for item in resource:
                if item.tag in tag_actions:
                    if item.tag == "Name":
                        publisher_name = tag_actions[item.tag](item)
                    elif item.tag == "Imprint":
                        imprint = tag_actions[item.tag](item)

            publisher_id = get_id_from_attrib(resource.attrib)

            return Publisher(publisher_name, publisher_id, imprint)

        def get_modified() -> datetime | None:
            resource = root.find("LastModified")
            if resource is None:
                return None
            return datetime.fromisoformat(resource.text)

        def _create_alt_name_list(element: ET.Element) -> list[AlternativeNames]:
            return [
                AlternativeNames(
                    name.text, get_id_from_attrib(name.attrib), name.attrib.get("lang")
                )
                for name in element.findall("Name")
            ]

        def get_series() -> Series | None:
            resource = root.find("Series")
            if resource is None:
                return None

            series_md = Series("None")
            attrib = resource.attrib
            series_md.id_ = get_id_from_attrib(attrib)
            if attrib and "lang" in attrib:
                series_md.language = attrib["lang"]

            for item in resource:
                match item.tag:
                    case "Name":
                        series_md.name = item.text
                    case "SortName":
                        series_md.sort_name = item.text
                    case "Volume":
                        series_md.volume = int(item.text)
                    case "Format":
                        series_md.format = item.text
                    case "AlternativeNames":
                        series_md.alternative_names = _create_alt_name_list(item)
                    case _:
                        pass

            return series_md

        def get_arcs() -> list[Arc]:
            arcs_node = root.find("Arcs")
            if arcs_node is None:
                return []
            resources = arcs_node.findall("Arc")
            if resources is None:
                return []

            return [
                Arc(
                    resource.find("Name").text,
                    get_id_from_attrib(resource.attrib),
                    int(resource.find("Number").text)
                    if resource.find("Number") is not None
                    else None,
                )
                for resource in resources
            ]

        def get_credits() -> list[Credit] | None:
            credits_node = root.find("Credits")
            if credits_node is None:
                return None
            resources = credits_node.findall("Credit")
            if resources is None:
                return None

            credits_list = []
            for resource in resources:
                roles_node = resource.find("Roles")
                roles = roles_node.findall("Role")
                role_list = (
                    [Role(role.text, get_id_from_attrib(role.attrib)) for role in roles]
                    if roles is not None
                    else []
                )

                creator = resource.find("Creator")
                attrib = creator.attrib
                credit = Credit(creator.text, role_list, get_id_from_attrib(attrib))
                credits_list.append(credit)
            return credits_list

        md = Metadata()
        md.info_source = get_info_sources()
        md.alt_sources = get_alt_sources()
        md.publisher = get_publisher()
        md.series = get_series()
        md.collection_title = get("CollectionTitle")
        md.issue = IssueString(get("Number")).as_string()
        md.stories = get_resource_list("Stories")
        md.comments = get("Summary")
        md.prices = get_prices()
        if cov_date := get("CoverDate"):
            md.cover_date = (
                datetime.strptime(cov_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).date()
            )
        if store_date := get("StoreDate"):
            md.store_date = (
                datetime.strptime(store_date, "%Y-%m-%d").replace(tzinfo=timezone.utc).date()
            )
        p_count = get("PageCount")
        md.page_count = int(p_count) if p_count is not None and p_count.isdigit() else None
        md.notes = get("Notes")
        md.genres = get_resource_list("Genres")
        md.tags = get_resource_list("Tags")
        md.story_arcs = get_arcs()
        md.characters = get_resource_list("Characters")
        md.teams = get_resource_list("Teams")
        md.locations = get_resource_list("Locations")
        md.reprints = get_resource_list("Reprints")
        md.gtin = get_gtin()
        md.age_rating = get("AgeRating")
        md.web_link = get("URL")
        md.modified = get_modified()
        md.credits = get_credits()

        pages_node = root.find("Pages")
        if pages_node is not None:
            for page in pages_node:
                p: dict[str, str | int] = page.attrib
                if "Image" in p:
                    p["Image"] = int(p["Image"])
                md.pages.append(cast(ImageMetadata, p))

        md.is_empty = False
        return md

    def write_xml(self, filename: Path, md: Metadata, xml=None) -> None:
        tree = self.convert_metadata_to_xml(md, xml)
        tree.write(filename, encoding="UTF-8", xml_declaration=True)

    def read_xml(self, filename: Path) -> Metadata:
        tree = parse(filename)
        return self.convert_xml_to_metadata(tree)
