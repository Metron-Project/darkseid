import xml.etree.ElementTree as ET  # noqa: N817
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import cast

from defusedxml.ElementTree import fromstring, parse

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
    Universe,
)


class MetronInfo:
    mix_info_sources = frozenset(
        {"Comic Vine", "Grand Comics Database", "Marvel", "Metron", "League of Comic Geeks"}
    )
    mix_age_ratings = frozenset({"Unknown", "Everyone", "Teen", "Teen Plus", "Mature"})
    mix_series_format = frozenset(
        {
            "Annual",
            "Graphic Novel",
            "Limited Series",
            "One-Shot",
            "Series",
            "Trade Paperback",
            "Hardcover",
        }
    )
    mix_genres = frozenset(
        {
            "Adult",
            "Crime",
            "Espionage",
            "Fantasy",
            "Historical",
            "Horror",
            "Humor",
            "Manga",
            "Parody",
            "Romance",
            "Science Fiction",
            "Sport",
            "Super-Hero",
            "War",
            "Western",
        }
    )
    mix_roles = frozenset(
        {
            "Writer",
            "Script",
            "Story",
            "Plot",
            "Interviewer",
            "Artist",
            "Penciller",
            "Breakdowns",
            "Illustrator" "Layouts",
            "Inker",
            "Embellisher",
            "Finishes",
            "Ink Assists",
            "Colorist",
            "Color Separations",
            "Color Assists",
            "Color Flats",
            "Digital Art Technician",
            "Gray Tone",
            "Letterer",
            "Cover",
            "Editor",
            "Consulting Editor",
            "Assistant Editor",
            "Associate Editor",
            "Group Editor",
            "Senior Editor",
            "Managing Editor",
            "Collection Editor",
            "Production",
            "Designer",
            "Logo Design",
            "Translator",
            "Supervising Editor",
            "Executive Editor",
            "Editor In Chief",
            "President",
            "Publisher",
            "Chief Creative Officer",
            "Executive Producer",
            "Other",
        }
    )

    @staticmethod
    def _get_root(xml) -> ET.Element:
        if xml:
            root = ET.ElementTree(fromstring(xml)).getroot()
        else:
            root = ET.Element("MetronInfo")
            root.attrib["xmlns:xsi"] = "http://www.w3.org/2001/XMLSchema-instance"
            root.attrib["xmlns:xsd"] = "http://www.w3.org/2001/XMLSchema"
        return root

    @classmethod
    def valid_info_source(cls, val: Basic | None = None) -> bool:
        return val is not None and val.name in cls.mix_info_sources

    @classmethod
    def valid_genre(cls, val: Basic) -> bool:
        return val.name in cls.mix_genres

    @classmethod
    def list_contains_valid_genre(cls, vals: list[Basic]) -> bool:
        return any(val.name in cls.mix_genres for val in vals)

    @classmethod
    def valid_age_rating(cls, val: str | None = None) -> str | None:
        if val is None:
            return None
        return "Unknown" if val not in cls.mix_age_ratings else val

    def convert_metadata_to_xml(self, md: Metadata, xml=None) -> ET.ElementTree:  # noqa: C901, PLR0915, PLR0912
        root = self._get_root(xml)

        # Helper functions
        def get_parent_node(element: str) -> ET.Element:
            parent_node = root.find(element)
            if parent_node is None:
                parent_node = ET.SubElement(root, element)
            else:
                parent_node.clear()
            return parent_node

        def assign(element: str, val: str | int | date | None = None) -> None:
            et_entry = root.find(element)
            if val is None:
                if et_entry is not None:
                    root.remove(et_entry)
            elif et_entry is not None:
                if isinstance(val, date):
                    et_entry.text = val.strftime("%Y-%m-%d")
                else:
                    et_entry.text = str(val) if isinstance(val, int) else val
            elif isinstance(val, date):
                ET.SubElement(root, element).text = val.strftime("%Y-%m-%d")
            else:
                ET.SubElement(root, element).text = str(val) if isinstance(val, int) else val

        def assign_basic_children(parent: str, child: str, vals: list[Basic]) -> None:
            parent_node = get_parent_node(parent)
            for val in vals:
                child_node = ET.SubElement(parent_node, child)
                child_node.text = val.name
                if val.id_:
                    child_node.attrib["id"] = str(val.id_)

        def assign_genres(vals: list[Basic]) -> None:
            genres_node = get_parent_node("Genres")
            for val in vals:
                # Let's only write the valid genres.
                if val.name in self.mix_genres:
                    genre_node = ET.SubElement(genres_node, "Genre")
                    genre_node.text = val.name
                    if val.id_:
                        genre_node.attrib["id"] = str(val.id_)

        def assign_basic_resource(element: str, val: Basic) -> None:
            resource_node = get_parent_node(element)
            resource_node.text = val.name
            if val.id_:
                resource_node.attrib["id"] = str(val.id_)

        def assign_arc(vals: list[Arc]) -> None:
            parent_node = get_parent_node("Arcs")
            for val in vals:
                child_node = ET.SubElement(parent_node, "Arc")
                if val.id_:
                    child_node.attrib = {"id": str(val.id_)}
                name_node = ET.SubElement(child_node, "Name")
                name_node.text = val.name
                if val.number:
                    number_node = ET.SubElement(child_node, "Number")
                    number_node.text = str(val.number)

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
            volume_node.text = str(series.volume)
            format_node = ET.SubElement(series_node, "Format")
            # Let's use a default of `Series` if invalid format.
            format_node.text = (
                series.format if series.format in self.mix_series_format else "Series"
            )

        def assign_info_source(primary: Basic, alt_lst: list[Basic]) -> None:
            id_node = get_parent_node("ID")
            primary_node = ET.SubElement(id_node, "Primary")
            primary_node.text = str(primary.id_)
            primary_node.attrib["source"] = primary.name
            if alt_lst:
                for alt in alt_lst:
                    if self.valid_info_source(alt):
                        alt_node = ET.SubElement(id_node, "Alternative")
                        alt_node.text = str(alt.id_)
                        alt_node.attrib["source"] = alt.name

        def assign_gtin(gtin: GTIN) -> None:
            gtin_node = get_parent_node("GTIN")
            if gtin.isbn:
                isbn_node = ET.SubElement(gtin_node, "ISBN")
                isbn_node.text = str(gtin.isbn)
            if gtin.upc:
                upc_node = ET.SubElement(gtin_node, "UPC")
                upc_node.text = str(gtin.upc)

        def assign_price(prices: list[Price]) -> None:
            price_node = get_parent_node("Prices")
            for p in prices:
                child_node = ET.SubElement(price_node, "Price")
                child_node.text = str(p.amount)
                if p.country:
                    child_node.attrib["country"] = p.country

        def assign_universes(universes: list[Universe]) -> None:
            universes_node = get_parent_node("Universes")
            for u in universes:
                universe_node = ET.SubElement(universes_node, "Universe")
                if u.id_:
                    universe_node.attrib["id"] = str(u.id_)
                name_node = ET.SubElement(universe_node, "Name")
                name_node.text = u.name
                if u.designation:
                    designation_node = ET.SubElement(universe_node, "Designation")
                    designation_node.text = u.designation

        def assign_credits(credits_lst: list[Credit]) -> None:
            parent_node = root.find("Credits")
            if parent_node is None:
                parent_node = ET.SubElement(root, "Credits")
            else:
                parent_node.clear()

            for item in credits_lst:
                credit_node = ET.SubElement(parent_node, "Credit")
                creator_node = ET.SubElement(credit_node, "Creator")
                creator_node.text = item.person
                if item.id_:
                    creator_node.attrib["id"] = str(item.id_)
                roles_node = ET.SubElement(credit_node, "Roles")
                for r in item.role:
                    role_node = ET.SubElement(roles_node, "Role")
                    # If the role is a valid value, let's use `Other`.
                    role_node.text = r.name if r.name in self.mix_roles else "Other"
                    if r.id_:
                        role_node.attrib["id"] = str(r.id_)

        # OK, let's create the xml
        if self.valid_info_source(md.info_source):
            assign_info_source(md.info_source, md.alt_sources)
        # We always need a Publisher for it to be valid.
        assign_basic_resource("Publisher", md.publisher if md.publisher else Basic("Unknown"))
        assign_series(md.series)
        assign("CollectionTitle", md.collection_title)
        assign("Number", md.issue)
        if md.stories:
            assign_basic_children("Stories", "Story", md.stories)
        assign("Summary", md.comments)
        if md.prices:
            assign_price(md.prices)
        assign("CoverDate", md.cover_date)
        assign("StoreDate", md.store_date)
        assign("PageCount", md.page_count)
        assign("Notes", md.notes)
        if md.genres and self.list_contains_valid_genre(md.genres):
            assign_genres(md.genres)
        if md.tags:
            assign_basic_children("Tags", "Tag", md.tags)
        if md.story_arcs:
            assign_arc(md.story_arcs)
        if md.characters:
            assign_basic_children("Characters", "Character", md.characters)
        if md.teams:
            assign_basic_children("Teams", "Team", md.teams)
        if md.universes:
            assign_universes(md.universes)
        if md.locations:
            assign_basic_children("Locations", "Location", md.locations)
        if md.reprints:
            assign_basic_children("Reprints", "Reprint", md.reprints)
        if md.gtin:
            assign_gtin(md.gtin)
        assign("AgeRating", self.valid_age_rating(md.age_rating))
        assign("URL", md.web_link)
        if md.credits:
            assign_credits(md.credits)

        #  loop and add the page entries under pages node
        if md.pages:
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

    @staticmethod
    def convert_xml_to_metadata(tree: ET.ElementTree) -> Metadata:  # noqa: C901, PLR0915
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
                        case "ISBN":
                            gtin.isbn = int(item.text)
                        case _:
                            # This shouldn't occur if the xml is valid.
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
            alt_lst = []
            for alt_node in alt_nodes:
                alt = Basic(alt_node.attrib.get("source"), int(alt_node.text))
                alt_lst.append(alt)
            return alt_lst

        def get_resource(element: str) -> Basic | None:
            resource = root.find(element)
            if resource is None:
                return None
            attrib = resource.attrib
            return Basic(resource.text, get_id_from_attrib(attrib))

        def get_resource_list(element: str) -> list[Basic]:
            resource = root.find(element)
            if resource is None:
                return []

            resource_list = []
            for item in resource:
                attrib = item.attrib
                resource_list.append(Basic(item.text, get_id_from_attrib(attrib)))
            return resource_list

        def get_prices() -> list[Price]:
            resource = root.find("Prices")
            if resource is None:
                return []

            resource_list = []
            for item in resource:
                attrib = item.attrib
                # TODO: Isn't country attrib required? Need to verify and modify this if necessary.
                if attrib and "country" in attrib:
                    resource_list.append(Price(Decimal(item.text), attrib["country"]))
                else:
                    resource_list.append(Price(Decimal(item.text)))
            return resource_list

        def get_series() -> Series | None:
            resource = root.find("Series")
            if resource is None:
                return None

            series_md = Series("None")  # Needs dummy name to init.
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
                    case _:
                        pass

            return series_md

        def get_arcs() -> list[Arc]:
            arcs_node = root.find("Arcs")
            resources = arcs_node.findall("Arc")
            if resources is None:
                return []

            arcs_list = []
            for resource in resources:
                name = resource.find("Name")
                number = resource.find("Number")
                attrib = resource.attrib
                arc = Arc(
                    name.text,
                    get_id_from_attrib(attrib),
                    int(number.text) if number is not None else None,
                )
                arcs_list.append(arc)
            return arcs_list

        def get_credits() -> list[Credit] | None:
            credits_node = root.find("Credits")
            if credits_node is None:
                return None
            resources = credits_node.findall("Credit")
            if resources is None:
                return None

            credits_list = []
            for resource in resources:
                # Let's create the role list first.
                roles_node = resource.find("Roles")
                roles = roles_node.findall("Role")
                role_list = []
                if roles is not None:
                    for role in roles:
                        r_attrib = role.attrib
                        role_obj = Role(role.text, get_id_from_attrib(r_attrib))
                        role_list.append(role_obj)

                # Now let's create the Credit.
                creator = resource.find("Creator")
                attrib = creator.attrib
                credit = Credit(creator.text, role_list, get_id_from_attrib(attrib))
                credits_list.append(credit)
            return credits_list

        md = Metadata()
        md.info_source = get_info_sources()
        md.alt_sources = get_alt_sources()
        md.publisher = get_resource("Publisher")
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
        md.credits = get_credits()

        # parse page data now
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
