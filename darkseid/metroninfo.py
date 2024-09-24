"""A class to encapsulate MetronInfo.xml data."""

# Copyright 2024 Brian Pepple

from __future__ import annotations

import xml.etree.ElementTree as ET  # noqa: N817
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import TYPE_CHECKING

from defusedxml.ElementTree import fromstring, parse

from darkseid.issue_string import IssueString
from darkseid.metadata import (
    GTIN,
    URLS,
    AlternativeNames,
    Arc,
    Basic,
    Credit,
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
    """A class to manage comic metadata and its MetronInfo XML representation.

    This class provides methods to convert metadata to and from XML format, validate information sources,
    and manage various attributes related to comic series, genres, and roles.

    Attributes:
        mix_info_sources (frozenset): A set of valid information sources.
        mix_age_ratings (frozenset): A set of valid age ratings.
        mix_series_format (frozenset): A set of valid series formats.
        mix_genres (frozenset): A set of valid genres.
        mix_roles (frozenset): A set of valid roles for creators.

    Methods:
        metadata_from_string(string): Converts an XML string to a Metadata object.
        string_from_metadata(md, xml): Converts a Metadata object to an XML string.
        convert_metadata_to_xml(md, xml): Converts a Metadata object into an XML ElementTree.
        convert_xml_to_metadata(tree): Converts an XML ElementTree into a Metadata object.
        write_xml(filename, md, xml): Writes the XML representation of metadata to a file.
        read_xml(filename): Reads XML data from a file and converts it into a Metadata object.
    """

    mix_info_sources = frozenset(
        {"comic vine", "grand comics database", "marvel", "metron", "league of comic geeks"}
    )
    mix_age_ratings = frozenset(
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
        """Convert an XML string to a Metadata object.

        This method parses the provided XML string and converts it into a Metadata object representation.

        Args:
            string (str): The XML string to be converted.

        Returns:
            Metadata: The resulting Metadata object.
        """
        tree = ET.ElementTree(fromstring(string))
        return self.convert_xml_to_metadata(tree)

    def string_from_metadata(
        self,
        md: Metadata,
        xml: bytes = b"",
    ) -> str:
        """Convert a Metadata object to an XML string.

        This method generates an XML string representation of the provided Metadata object.

        Args:
            md (Metadata): The Metadata object to convert.
            xml (bytes, optional): Optional XML bytes to include. Defaults to b''.

        Returns:
            str: The resulting XML string.
        """
        tree = self.convert_metadata_to_xml(md, xml)
        return ET.tostring(tree.getroot(), encoding="utf-8", xml_declaration=True).decode()

    @staticmethod
    def _get_root(xml: any) -> ET.Element:
        root = ET.ElementTree(fromstring(xml)).getroot() if xml else ET.Element("MetronInfo")
        root.attrib["xmlns:xsi"] = "https://www.w3.org/2001/XMLSchema-instance"
        root.attrib["xmlns:xsd"] = "https://www.w3.org/2001/XMLSchema"
        return root

    @classmethod
    def _valid_info_source(cls, val: Basic | None = None) -> bool:
        return val is not None and val.name.lower() in cls.mix_info_sources

    @classmethod
    def _list_contains_valid_genre(cls, vals: list[Basic]) -> bool:
        return any(val.name.lower() in cls.mix_genres for val in vals)

    @classmethod
    def _valid_age_rating(cls, val: str | None = None) -> str | None:
        if val is None:
            return None
        return "Unknown" if val.lower() not in cls.mix_age_ratings else val

    @staticmethod
    def _get_or_create_element(parent: ET.Element, tag: str) -> ET.Element:
        element = parent.find(tag)
        if element is None:
            return ET.SubElement(parent, tag)
        element.clear()
        return element

    @staticmethod
    def _assign(root: ET.Element, element: str, val: str | int | date | None = None) -> None:
        et_entry = root.find(element)
        if val is None:
            if et_entry is not None:
                root.remove(et_entry)
        else:
            if et_entry is None:
                et_entry = ET.SubElement(root, element)
            et_entry.text = val.strftime("%Y-%m-%d") if isinstance(val, date) else str(val)

    @staticmethod
    def _assign_datetime(root: ET.Element, element: str, val: datetime | None = None) -> None:
        et_entry = root.find(element)
        if val is None:
            if et_entry is not None:
                root.remove(et_entry)
        else:
            if et_entry is None:
                et_entry = ET.SubElement(root, element)
            et_entry.text = val.isoformat(sep="T")

    @staticmethod
    def _assign_basic_children(
        root: ET.Element, parent: str, child: str, vals: list[Basic]
    ) -> None:
        parent_node = MetronInfo._get_or_create_element(root, parent)
        create_sub_element = ET.SubElement
        for val in vals:
            child_node = create_sub_element(parent_node, child)
            name = val.name
            child_node.text = name
            if id_ := val.id_:
                child_node.attrib["id"] = str(id_)

    @staticmethod
    def _assign_arc(root: ET.Element, vals: list[Arc]) -> None:
        parent_node = MetronInfo._get_or_create_element(root, "Arcs")
        for val in vals:
            attributes = {"id": str(val.id_)} if val.id_ else {}
            child_node = ET.SubElement(parent_node, "Arc", attrib=attributes)
            ET.SubElement(child_node, "Name").text = val.name
            if val.number:
                ET.SubElement(child_node, "Number").text = str(val.number)

    @staticmethod
    def _assign_publisher(root: ET.Element, publisher: Publisher) -> None:
        if publisher is None:
            return
        publisher_node = MetronInfo._get_or_create_element(root, "Publisher")
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
    def _assign_series(root: ET.Element, series: Series) -> None:
        if series is None:
            return
        series_node = MetronInfo._get_or_create_element(root, "Series")
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
        if series.start_year:
            ET.SubElement(series_node, "StartYear").text = str(series.start_year)
        if series.alternative_names:
            alt_names_node = ET.SubElement(series_node, "AlternativeNames")
            for alt_name in series.alternative_names:
                alt_attrib = {
                    k: v for k, v in (("id", str(alt_name.id_)), ("lang", alt_name.language)) if v
                }
                ET.SubElement(alt_names_node, "Name", attrib=alt_attrib).text = alt_name.name

    @staticmethod
    def _assign_info_source(root: ET.Element, primary: Basic, alt_lst: list[Basic]) -> None:
        id_node = MetronInfo._get_or_create_element(root, "ID")
        primary_node = ET.SubElement(id_node, "Primary")
        primary_node.text = str(primary.id_)
        primary_node.attrib["source"] = primary.name

        create_sub_element = ET.SubElement
        for alt in (alt for alt in alt_lst if MetronInfo._valid_info_source(alt)):
            alt_node = create_sub_element(id_node, "Alternative")
            alt_node.text = str(alt.id_)
            alt_node.attrib["source"] = alt.name

    @staticmethod
    def _assign_gtin(root: ET.Element, gtin: GTIN) -> None:
        gtin_node = MetronInfo._get_or_create_element(root, "GTIN")
        if gtin.isbn:
            ET.SubElement(gtin_node, "ISBN").text = str(gtin.isbn)
        if gtin.upc:
            ET.SubElement(gtin_node, "UPC").text = str(gtin.upc)

    @staticmethod
    def _assign_price(root: ET.Element, prices: list[Price]) -> None:
        price_node = MetronInfo._get_or_create_element(root, "Prices")
        create_sub_element = ET.SubElement
        for p in prices:
            child_node = create_sub_element(price_node, "Price", attrib={"country": p.country})
            child_node.text = str(p.amount)

    @staticmethod
    def _assign_universes(root: ET.Element, universes: list[Universe]) -> None:
        universes_node = MetronInfo._get_or_create_element(root, "Universes")
        sub_element = ET.SubElement
        for u in universes:
            universe_node = sub_element(universes_node, "Universe")
            if u.id_:
                universe_node.attrib["id"] = str(u.id_)
            sub_element(universe_node, "Name").text = u.name
            if u.designation:
                sub_element(universe_node, "Designation").text = u.designation

    @staticmethod
    def _assign_urls(root: ET.Element, urls: URLS) -> None:
        urls_node = MetronInfo._get_or_create_element(root, "URL")
        sub_element = ET.SubElement
        if urls.primary:
            sub_element(urls_node, "Primary").text = urls.primary
        if urls.alternatives:
            for alt in urls.alternatives:
                sub_element(urls_node, "Alternative").text = alt

    @staticmethod
    def _assign_credits(root: ET.Element, credits_lst: list[Credit]) -> None:
        parent_node = MetronInfo._get_or_create_element(root, "Credits")
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
                role_node.text = r.name if r.name.lower() in mix_roles else "Other"

    def convert_metadata_to_xml(self, md: Metadata, xml=None) -> ET.ElementTree:  # noqa: PLR0912,C901
        """Convert a Metadata object to an XML ElementTree.

        This method generates an XML representation of the provided Metadata object, including all relevant details.

        Args:
            md (Metadata): The Metadata object to convert.
            xml (optional): Optional XML bytes to include.

        Returns:
            ET.ElementTree: The resulting XML ElementTree.
        """
        root = self._get_root(xml)

        if self._valid_info_source(md.info_source):
            self._assign_info_source(root, md.info_source, md.alt_sources)
        self._assign_publisher(root, md.publisher)
        self._assign_series(root, md.series)
        self._assign(root, "CollectionTitle", md.collection_title)
        self._assign(root, "Number", md.issue)
        if md.stories:
            self._assign_basic_children(root, "Stories", "Story", md.stories)
        self._assign(root, "Summary", md.comments)
        if md.prices:
            self._assign_price(root, md.prices)
        self._assign(root, "CoverDate", md.cover_date)
        self._assign(root, "StoreDate", md.store_date)
        self._assign(root, "PageCount", md.page_count)
        self._assign(root, "Notes", md.notes)
        if md.genres and self._list_contains_valid_genre(md.genres):
            self._assign_basic_children(root, "Genres", "Genre", md.genres)
        if md.tags:
            self._assign_basic_children(root, "Tags", "Tag", md.tags)
        if md.story_arcs:
            self._assign_arc(root, md.story_arcs)
        if md.characters:
            self._assign_basic_children(root, "Characters", "Character", md.characters)
        if md.teams:
            self._assign_basic_children(root, "Teams", "Team", md.teams)
        if md.universes:
            self._assign_universes(root, md.universes)
        if md.locations:
            self._assign_basic_children(root, "Locations", "Location", md.locations)
        if md.reprints:
            self._assign_basic_children(root, "Reprints", "Reprint", md.reprints)
        if md.gtin:
            self._assign_gtin(root, md.gtin)
        self._assign(root, "AgeRating", self._valid_age_rating(md.age_rating))
        if md.web_link:
            self._assign_urls(root, md.web_link)
        self._assign_datetime(root, "LastModified", md.modified)
        if md.credits:
            self._assign_credits(root, md.credits)

        ET.indent(root)
        return ET.ElementTree(root)

    @staticmethod
    def convert_xml_to_metadata(tree: ET.ElementTree) -> Metadata:  # noqa: C901,PLR0915
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

        def get_id_from_attrib(attrib: dict[str, str]) -> int | None:
            return int(id_) if (id_ := attrib.get("id")) else None

        def get(element: str) -> str | None:
            tag = root.find(element)
            return None if tag is None else tag.text

        def get_gtin(resource: ET.Element) -> GTIN | None:
            if resource is None:
                return None

            gtin = GTIN()
            tag_to_attr = {"UPC": "upc", "ISBN": "isbn"}
            found = False

            for item in resource:
                if item.text and item.tag in tag_to_attr:
                    setattr(gtin, tag_to_attr[item.tag], int(item.text))
                    found = True

            return gtin if found else None

        def get_info_sources(primary_node: ET.Element) -> Basic | None:
            if primary_node is None:
                return None
            return Basic(primary_node.attrib.get("source"), int(primary_node.text))

        def get_alt_sources(id_node: ET.Element) -> list[Basic] | None:
            if id_node is None:
                return None
            return [
                Basic(alt_node.attrib.get("source"), int(alt_node.text))
                for alt_node in id_node.findall("Alternative")
            ]

        def get_resource_list(resource: ET.Element) -> list[Basic]:
            if resource is None:
                return []
            return [Basic(item.text, get_id_from_attrib(item.attrib)) for item in resource]

        def get_prices(resource: ET.Element) -> list[Price]:
            if resource is None:
                return []
            return [
                Price(Decimal(item.text), item.attrib.get("country", "US")) for item in resource
            ]

        def get_publisher(resource: ET.Element) -> Publisher | None:
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
                    if publisher_name and imprint:
                        break

            publisher_id = get_id_from_attrib(resource.attrib)

            return Publisher(publisher_name, publisher_id, imprint)

        def get_modified(resource: ET.Element) -> datetime | None:
            return None if resource is None else datetime.fromisoformat(resource.text)

        def _create_alt_name_list(element: ET.Element) -> list[AlternativeNames]:
            names = element.findall("Name")
            return [
                AlternativeNames(
                    name.text, get_id_from_attrib(name.attrib), name.attrib.get("lang")
                )
                for name in names
            ]

        def get_series(resource: ET.Element) -> Series | None:
            if resource is None:
                return None

            series_md = Series("None")
            attrib = resource.attrib
            series_md.id_ = get_id_from_attrib(attrib)
            series_md.language = attrib.get("lang")

            tag_to_attr = {
                "Name": "name",
                "SortName": "sort_name",
                "Volume": "volume",
                "Format": "format",
                "StartYear": "start_year",
                "AlternativeNames": "_create_alt_name_list",
            }

            for item in resource:
                attr = tag_to_attr.get(item.tag)
                if attr:
                    if attr == "_create_alt_name_list":
                        series_md.alternative_names = _create_alt_name_list(item)
                    elif attr in ["volume", "start_year"]:
                        setattr(series_md, attr, int(item.text))
                    else:
                        setattr(series_md, attr, item.text)

            return series_md

        def get_arcs(arcs_node: ET.Element) -> list[Arc]:
            if arcs_node is None:
                return []
            resources = arcs_node.findall("Arc")
            if resources is None:
                return []

            return [
                Arc(
                    resource.find("Name").text,
                    get_id_from_attrib(resource.attrib),
                    int(number.text) if (number := resource.find("Number")) is not None else None,
                )
                for resource in resources
            ]

        def get_urls(url_node: ET.Element) -> URLS | None:
            if url_node is None:
                return None
            alt_urls_node = url_node.findall("Alternative")
            url_lst = [alt_url.text for alt_url in alt_urls_node] if alt_urls_node else None
            primary = url_node.find("Primary").text
            return URLS(primary, url_lst)

        def get_credits(credits_node: ET.Element) -> list[Credit] | None:
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

        # Cache root.find() results
        primary_node = root.find("ID/Primary")
        id_node = root.find("ID")
        gtin_node = root.find("GTIN")
        publisher_node = root.find("Publisher")
        modified_node = root.find("LastModified")
        series_node = root.find("Series")
        arcs_node = root.find("Arcs")
        credits_node = root.find("Credits")
        prices_node = root.find("Prices")
        url_node = root.find("URL")

        md = Metadata()
        md.info_source = get_info_sources(primary_node)
        md.alt_sources = get_alt_sources(id_node)
        md.publisher = get_publisher(publisher_node)
        md.series = get_series(series_node)
        md.collection_title = get("CollectionTitle")
        md.issue = IssueString(get("Number")).as_string()
        md.stories = get_resource_list(root.find("Stories"))
        md.comments = get("Summary")
        md.prices = get_prices(prices_node)
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
        md.genres = get_resource_list(root.find("Genres"))
        md.tags = get_resource_list(root.find("Tags"))
        md.story_arcs = get_arcs(arcs_node)
        md.characters = get_resource_list(root.find("Characters"))
        md.teams = get_resource_list(root.find("Teams"))
        md.locations = get_resource_list(root.find("Locations"))
        md.reprints = get_resource_list(root.find("Reprints"))
        md.gtin = get_gtin(gtin_node)
        md.age_rating = get("AgeRating")
        md.web_link = get_urls(url_node)
        md.modified = get_modified(modified_node)
        md.credits = get_credits(credits_node)

        md.is_empty = False
        return md

    def write_xml(self, filename: Path, md: Metadata, xml=None) -> None:
        """Write a Metadata object to an XML file.

        This method converts the provided Metadata object to XML and writes it to the specified file.

        Args:
            filename (Path): The path to the file where the XML will be written.
            md (Metadata): The Metadata object to write.
            xml (optional): Optional XML bytes to include.
        """
        tree = self.convert_metadata_to_xml(md, xml)
        tree.write(filename, encoding="UTF-8", xml_declaration=True)

    def read_xml(self, filename: Path) -> Metadata:
        """Read a Metadata object from an XML file.

        This method reads the XML from the specified file and converts it into a Metadata object.

        Args:
            filename (Path): The path to the XML file to read.

        Returns:
            Metadata: The resulting Metadata object.
        """
        tree = parse(filename)
        return self.convert_xml_to_metadata(tree)
