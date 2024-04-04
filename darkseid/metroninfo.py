import xml.etree.ElementTree as ET  # noqa: N817
from datetime import date
from pathlib import Path

from defusedxml.ElementTree import fromstring

from darkseid.metadata import GTIN, Arc, Basic, Credit, Metadata, Price, Series, Universe


class MetronInfo:
    mix_info_sources = frozenset(
        {
            "Comic Vine",
            "Grand Comics Database",
            "Marvel",
            "Metron",
            "League of Comic Geeks",
        }
    )
    mix_age_ratings = frozenset({"Unknown", "Everyone", "Teen", "Teen Plus", "Mature"})
    mix_series_format = frozenset(
        {"Annual", "Graphic Novel", "Limited", "One-Shot", "Series", "Trade Paperback"}
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
            format_node.text = series.format

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
                    role_node.text = r.name
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
        if md.genres:
            assign_basic_children("Genres", "Genre", md.genres)
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

    def write_xml(self, filename: Path, md: Metadata, xml=None) -> None:
        tree = self.convert_metadata_to_xml(md, xml)
        tree.write(filename, encoding="UTF-8", xml_declaration=True)
