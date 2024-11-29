"""A class to encapsulate MetronInfo.xml data."""

# Copyright 2024 Brian Pepple

from __future__ import annotations

import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

from defusedxml.ElementTree import fromstring, parse
from xmlschema import XMLSchema11, XMLSchemaValidationError

from darkseid.exceptions import XmlError
from darkseid.issue_string import IssueString
from darkseid.metadata import (
    GTIN,
    AgeRatings,
    AlternativeNames,
    Arc,
    Basic,
    Credit,
    InfoSources,
    Links,
    Metadata,
    Notes,
    Price,
    Publisher,
    Role,
    Series,
    Universe,
)
from darkseid.utils import cast_id_as_str

EARLIEST_YEAR = 1900
ONE_THOUSAND = 1000


class MetronInfo:
    """A class to manage comic metadata and its MetronInfo XML representation.

    This class provides methods to convert metadata to and from XML format, validate information sources,
    and manage various attributes related to comic series, genres, and roles.

    Attributes:
        mix_info_sources (frozenset): A set of valid information sources.
        mix_age_ratings (frozenset): A set of valid age ratings.
        mix_series_format (frozenset): A set of valid series formats.
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
        {
            "anilist",
            "comic vine",
            "grand comics database",
            "kitsu",
            "mangadex",
            "mangaupdates",
            "marvel",
            "metron",
            "myanimelist",
            "league of comic geeks",
        }
    )
    mix_age_ratings = frozenset(
        {"unknown", "everyone", "teen", "teen plus", "mature", "explicit", "adult"}
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

    # Ratings Mapping
    unknown_synonyms = frozenset({"rating pending", "unknown"})
    everyone_synonyms = frozenset(
        {"everyone", "everyone 10+", "g", "kids to adults", "early childhood"}
    )
    teen_synonyms = frozenset({"pg", "teen"})
    teen_plus_synonyms = frozenset({"ma15+"})
    mature_synonyms = frozenset({"adults only 18+", "mature 17+", "r18+", "m"})
    explicit_synonyms = frozenset({"x18+"})

    # Series Format Mapping
    annual_synonyms = frozenset({"annual"})
    digital_chapter_synonyms = frozenset({"digital chapter", "digital"})
    graphic_novel_synonyms = frozenset({"graphic novel"})
    hardcover_synonyms = frozenset({"hardcover", "hard-cover"})
    limited_series_synonyms = frozenset({"limited series"})
    omnibus_synonyms = frozenset({"omnibus"})
    one_shot_synonyms = frozenset({"1 shot", "1-shot", "fcbd", "one shot", "one-shot", "preview"})
    single_issue_synonyms = frozenset(
        {"single issue", "magazine", "series", "giant", "giant size", "giant-size"}
    )
    trade_paperback_synonyms = frozenset({"trade paperback", "tpb", "trade paper back"})

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
        return ET.ElementTree(fromstring(xml)).getroot() if xml else ET.Element("MetronInfo")

    @classmethod
    def _valid_info_source(cls, val: str | None = None) -> bool:
        return val is not None and val.lower() in cls.mix_info_sources

    @classmethod
    def _valid_age_rating(cls, val: AgeRatings | None = None) -> str | None:
        if val is None:
            return None
        if val.metron_info:
            return (
                "Unknown" if val.metron_info.lower() not in cls.mix_age_ratings else val.metron_info
            )

        if val.comic_rack:
            ratings_mapping = {
                "Unknown": cls.unknown_synonyms,
                "Everyone": cls.everyone_synonyms,
                "Teen": cls.teen_synonyms,
                "Teen Plus": cls.teen_plus_synonyms,
                "Mature": cls.mature_synonyms,
                "Explicit": cls.explicit_synonyms,
            }
            lower_val = val.comic_rack.lower()
            for rating, synonyms in ratings_mapping.items():
                if lower_val in synonyms:
                    return rating
        return None

    @classmethod
    def _valid_series_format(cls, val: str | None) -> str | None:
        if not val or val is None:
            return None

        format_mapping = {
            "Annual": cls.annual_synonyms,
            "Digital Chapter": cls.digital_chapter_synonyms,
            "Graphic Novel": cls.graphic_novel_synonyms,
            "Hardcover": cls.hardcover_synonyms,
            "Limited Series": cls.limited_series_synonyms,
            "Omnibus": cls.omnibus_synonyms,
            "One-Shot": cls.one_shot_synonyms,
            "Single Issue": cls.single_issue_synonyms,
            "Trade Paperback": cls.trade_paperback_synonyms,
        }
        lower_val = val.lower()
        return next(
            (fmt for fmt, synonyms in format_mapping.items() if lower_val in synonyms),
            None,
        )

    @staticmethod
    def _get_or_create_element(parent: ET.Element, tag: str) -> ET.Element:
        element = parent.find(tag)
        if element is None:
            return ET.SubElement(parent, tag)
        element.clear()
        return element

    @staticmethod
    def _assign(root: ET.Element, element: str, val: str | int | None = None) -> None:
        et_entry = root.find(element)
        if val is None:
            if et_entry is not None:
                root.remove(et_entry)
        else:
            if et_entry is None:
                et_entry = ET.SubElement(root, element)
            et_entry.text = str(val) if isinstance(val, int) else val

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
                child_node.attrib["id"] = cast_id_as_str(id_)

    @staticmethod
    def _assign_date(root: ET.Element, element: str, val: date | None = None) -> None:
        et_entry = root.find(element)
        if val is None:
            if et_entry is not None:
                root.remove(et_entry)
        else:
            if val.year < EARLIEST_YEAR:  # Info source has a bad year
                return
            if et_entry is None:
                et_entry = ET.SubElement(root, element)
            et_entry.text = val.strftime("%Y-%m-%d")

    @staticmethod
    def _assign_arc(root: ET.Element, vals: list[Arc]) -> None:
        parent_node = MetronInfo._get_or_create_element(root, "Arcs")
        create_sub_element = ET.SubElement
        for val in vals:
            attributes = {"id": cast_id_as_str(val.id_)} if val.id_ else {}
            child_node = create_sub_element(parent_node, "Arc", attrib=attributes)
            create_sub_element(child_node, "Name").text = val.name
            if val.number:
                create_sub_element(child_node, "Number").text = str(val.number)

    @staticmethod
    def _assign_publisher(root: ET.Element, publisher: Publisher) -> None:
        if publisher is None:
            return
        publisher_node = MetronInfo._get_or_create_element(root, "Publisher")
        if publisher.id_:
            publisher_node.attrib = {"id": cast_id_as_str(publisher.id_)}

        ET.SubElement(publisher_node, "Name").text = publisher.name

        if publisher.imprint:
            imprint_node = ET.SubElement(
                publisher_node,
                "Imprint",
                {"id": cast_id_as_str(publisher.imprint.id_)} if publisher.imprint.id_ else {},
            )
            imprint_node.text = publisher.imprint.name

    @classmethod
    def _assign_series(cls, root: ET.Element, series: Series) -> None:  # NOQA: PLR0912, C901
        if series is None:
            return
        series_node = MetronInfo._get_or_create_element(root, "Series")
        if series.id_ or series.language:
            series_node.attrib = {}
        if series.id_:
            series_node.attrib["id"] = cast_id_as_str(series.id_)
        if series.language:
            series_node.attrib["lang"] = series.language

        create_sub_element = ET.SubElement

        create_sub_element(series_node, "Name").text = series.name
        if series.sort_name is not None:
            create_sub_element(series_node, "SortName").text = series.sort_name
        if series.volume is not None and series.volume < ONE_THOUSAND:
            create_sub_element(series_node, "Volume").text = str(series.volume)
        series_fmt = cls._valid_series_format(series.format)
        if series_fmt is not None:
            create_sub_element(series_node, "Format").text = series_fmt
        if series.start_year:
            create_sub_element(series_node, "StartYear").text = str(series.start_year)
        elif series.volume is not None and series.volume >= ONE_THOUSAND:
            create_sub_element(series_node, "StartYear").text = str(series.volume)
        if series.issue_count:
            create_sub_element(series_node, "IssueCount").text = str(series.issue_count)
        if series.volume_count:
            create_sub_element(series_node, "VolumeCount").text = str(series.volume_count)
        if series.alternative_names:
            alt_names_node = create_sub_element(series_node, "AlternativeNames")
            for alt_name in series.alternative_names:
                alt_attrib = {}
                if alt_name.id_:
                    alt_attrib["id"] = cast_id_as_str(alt_name.id_)
                if alt_name.language:
                    alt_attrib["lang"] = alt_name.language
                create_sub_element(alt_names_node, "Name", attrib=alt_attrib).text = alt_name.name

    @staticmethod
    def _assign_info_source(root: ET.Element, info_source: list[InfoSources]) -> None:
        id_node = MetronInfo._get_or_create_element(root, "IDS")
        create_sub_element = ET.SubElement

        for src in info_source:
            attributes = {"source": str(src.name)}
            if src.primary:
                attributes["primary"] = "true"

            child_node = create_sub_element(id_node, "ID", attrib=attributes)
            child_node.text = cast_id_as_str(src.id_)

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
                universe_node.attrib["id"] = cast_id_as_str(u.id_)
            sub_element(universe_node, "Name").text = u.name
            if u.designation:
                sub_element(universe_node, "Designation").text = u.designation

    @staticmethod
    def _assign_urls(root: ET.Element, links: list[Links]) -> None:
        urls_node = MetronInfo._get_or_create_element(root, "URLs")
        sub_element = ET.SubElement
        elements = [(sub_element(urls_node, "URL"), link.url, link.primary) for link in links]
        for child_node, url, primary in elements:
            child_node.text = url
            if primary:
                child_node.attrib["primary"] = "true"

    @staticmethod
    def _assign_credits(root: ET.Element, credits_lst: list[Credit]) -> None:
        parent_node = MetronInfo._get_or_create_element(root, "Credits")
        sub_element = ET.SubElement
        mix_roles = MetronInfo.mix_roles

        for item in credits_lst:
            credit_node = sub_element(parent_node, "Credit")
            creator_node = sub_element(
                credit_node,
                "Creator",
                attrib={"id": cast_id_as_str(item.id_)} if item.id_ else {},
            )
            creator_node.text = item.person
            roles_node = sub_element(credit_node, "Roles")

            for r in item.role:
                role_node = sub_element(
                    roles_node,
                    "Role",
                    attrib={"id": cast_id_as_str(r.id_)} if r.id_ else {},
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

        if md.info_source:
            self._assign_info_source(root, md.info_source)
        self._assign_publisher(root, md.publisher)
        self._assign_series(root, md.series)
        self._assign(root, "CollectionTitle", md.collection_title)
        self._assign(root, "Number", md.issue)
        if md.stories:
            self._assign_basic_children(root, "Stories", "Story", md.stories)
        self._assign(root, "Summary", md.comments)
        if md.prices:
            self._assign_price(root, md.prices)
        self._assign_date(root, "CoverDate", md.cover_date)
        self._assign_date(root, "StoreDate", md.store_date)
        self._assign(root, "PageCount", md.page_count)
        if md.notes is not None and md.notes.metron_info:
            self._assign(root, "Notes", md.notes.metron_info)
        if md.genres:
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
        if md.age_rating is not None and (md.age_rating.metron_info or md.age_rating.comic_rack):
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

        def get_id_from_attrib(attrib: dict[str, str]) -> int | str | None:
            if id_ := attrib.get("id"):
                return int(id_) if id_.isdigit() else id_
            return None

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

        def get_info_sources(id_node: ET.Element) -> list[InfoSources] | None:
            if id_node is None:
                return None

            child_nodes = id_node.findall("ID")
            return [
                InfoSources(
                    child.attrib.get("source"),
                    int(child.text) if child.text.isdigit() else child.text,
                    bool(primary.title()) if (primary := child.attrib.get("primary")) else False,
                )
                for child in child_nodes
                if MetronInfo._valid_info_source(child.attrib.get("source"))
            ] or None

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
                "IssueCount": "issue_count",
                "VolumeCount": "volume_count",
                "AlternativeNames": "_create_alt_name_list",
            }

            for item in resource:
                attr = tag_to_attr.get(item.tag)
                if attr:
                    if attr == "_create_alt_name_list":
                        series_md.alternative_names = _create_alt_name_list(item)
                    elif attr in ["volume", "start_year", "issue_count", "volume_count"]:
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

        def get_urls(url_node: ET.Element) -> list[Links] | None:
            if url_node is None:
                return None

            child_nodes = url_node.findall("URL")
            if child_nodes is None:
                return None

            return [
                Links(child.text, child.attrib.get("primary", "") == "true")
                for child in child_nodes
            ]

        def get_note(note_node: ET.Element) -> Notes | None:
            return None if note_node is None else Notes(note_node.text)

        def get_age_rating(node: ET.Element) -> AgeRatings | None:
            return None if node is None else AgeRatings(metron_info=node.text)

        def get_credits(credits_node: ET.Element) -> list[Credit] | None:
            if credits_node is None:
                return None
            resources = credits_node.findall("Credit")
            if resources is None:
                return None

            credits_list = []
            for resource in resources:
                roles_node = resource.find("Roles")
                if roles_node is not None:
                    roles = roles_node.findall("Role")
                    role_list = (
                        [Role(role.text, get_id_from_attrib(role.attrib)) for role in roles]
                        if roles is not None
                        else []
                    )
                else:
                    role_list = []

                creator = resource.find("Creator")
                attrib = creator.attrib
                credit = Credit(creator.text, role_list, get_id_from_attrib(attrib))
                credits_list.append(credit)
            return credits_list

        # Cache root.find() results
        id_node = root.find("IDS")
        gtin_node = root.find("GTIN")
        publisher_node = root.find("Publisher")
        modified_node = root.find("LastModified")
        series_node = root.find("Series")
        arcs_node = root.find("Arcs")
        credits_node = root.find("Credits")
        prices_node = root.find("Prices")
        url_node = root.find("URLs")
        note_node = root.find("Notes")
        age_rating_node = root.find("AgeRating")

        md = Metadata()
        md.info_source = get_info_sources(id_node)
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
        md.notes = get_note(note_node)
        md.genres = get_resource_list(root.find("Genres"))
        md.tags = get_resource_list(root.find("Tags"))
        md.story_arcs = get_arcs(arcs_node)
        md.characters = get_resource_list(root.find("Characters"))
        md.teams = get_resource_list(root.find("Teams"))
        md.locations = get_resource_list(root.find("Locations"))
        md.reprints = get_resource_list(root.find("Reprints"))
        md.gtin = get_gtin(gtin_node)
        md.age_rating = get_age_rating(age_rating_node)
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
        mi_xsd = Path("darkseid") / "schemas" / "MetronInfo" / "v1" / "MetronInfo.xsd"
        schema = XMLSchema11(mi_xsd)
        # Let's validate the xml
        try:
            schema.validate(tree)
        except XMLSchemaValidationError as e:
            msg = f"Failed to validate XML: {e!r}"
            raise XmlError(msg) from e

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
