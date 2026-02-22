"""Base class for metadata handlers that convert between Metadata objects and XML representations."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from defusedxml.ElementTree import parse

from darkseid.metadata.data_classes import Metadata


class XmlError(Exception):
    """Class for an XML error."""


class BaseMetadataHandler(ABC):
    """Abstract base class for metadata handlers.

    Provides common functionality for converting between Metadata objects and XML representations.
    Subclasses must implement the specific conversion logic for their XML format.
    """

    @abstractmethod
    def metadata_from_string(self, xml_string: str) -> Metadata:
        """Convert an XML string to a Metadata object.

        Args:
            xml_string: The XML string to be converted.

        Returns:
            The resulting Metadata object.

        """

    @abstractmethod
    def string_from_metadata(self, metadata: Metadata, xml_bytes: bytes = b"") -> str:
        """Convert a Metadata object to an XML string.

        Args:
            metadata: The Metadata object to convert.
            xml_bytes: Optional XML bytes to include.

        Returns:
            The resulting XML string.

        """

    @abstractmethod
    def _convert_metadata_to_xml(
        self, metadata: Metadata, xml_bytes: bytes | None = None
    ) -> ET.ElementTree:
        """Convert a Metadata object to an XML ElementTree.

        Args:
            metadata: The Metadata object to convert.
            xml_bytes: Optional XML bytes to include.

        Returns:
            The resulting XML ElementTree.

        """

    @abstractmethod
    def _convert_xml_to_metadata(self, tree: ET.ElementTree) -> Metadata:
        """Convert an XML ElementTree to a Metadata object.

        Args:
            tree: The XML ElementTree to convert.

        Returns:
            The resulting Metadata object.

        """

    def write_xml(self, filename: Path, metadata: Metadata, xml_bytes: bytes = b"") -> None:
        """Write Metadata to an external file in XML format.

        Args:
            filename: The path to the file where the XML will be written.
            metadata: The Metadata object to write to the file.
            xml_bytes: Additional XML content, defaults to an empty byte string.

        """
        tree = self._convert_metadata_to_xml(metadata, xml_bytes)
        # Create parent directories if they don't exist
        Path(filename.parent).mkdir(parents=True, exist_ok=True)
        tree.write(filename, encoding="utf-8", xml_declaration=True)

    def read_xml(self, filename: Path) -> Metadata:
        """Read Metadata from an external file in XML format.

        Args:
            filename: The path to the XML file to read.

        Returns:
            The resulting Metadata object.

        """
        try:
            tree = parse(filename)
        except ET.ParseError:
            return Metadata()
        return self._convert_xml_to_metadata(tree)

    @staticmethod
    def _get_or_create_element(parent: ET.Element, tag: str) -> ET.Element:
        """Get existing element or create new one.

        Args:
            parent: Parent element.
            tag: Tag name.

        Returns:
            Element (existing or new).

        """
        element = parent.find(tag)
        if element is None:
            return ET.SubElement(parent, tag)
        element.clear()
        return element

    @staticmethod
    def _set_element_text(root: ET.Element, tag: str, value: Any | None = None) -> None:
        """Set or remove element text value.

        Args:
            root: Root element.
            tag: Element tag name.
            value: Value to set (removes element if None).

        """
        element = root.find(tag)
        if value is None:
            if element is not None:
                root.remove(element)
        else:
            if element is None:
                element = ET.SubElement(root, tag)
            element.text = str(value)

    @staticmethod
    def _set_datetime_element(root: ET.Element, tag: str, dt: datetime | None = None) -> None:
        """Set datetime element in ISO format.

        Args:
            root: Root element.
            tag: Element tag name.
            dt: Datetime value.

        """
        element = root.find(tag)
        if dt is None:
            if element is not None:
                root.remove(element)
        else:
            if element is None:
                element = ET.SubElement(root, tag)
            element.text = dt.isoformat(sep="T")

    @staticmethod
    def _get_text_content(root: ET.Element, element_name: str) -> str | None:
        """Get text content from an element.

        Args:
            root: Root element to search in.
            element_name: Name of the element to find.

        Returns:
            Text content of the element or None if not found.

        """
        element = root.find(element_name)
        return element.text if element is not None else None

    @staticmethod
    def _parse_decimal(value: str | None) -> Decimal | None:
        """Safely parse string to Decimal.

        Args:
            value: String value to parse.

        Returns:
            Decimal value or None if parsing fails.

        """
        if not value:
            return None
        try:
            return Decimal(value)
        except InvalidOperation:
            return None

    @staticmethod
    def _parse_int(value: str | None) -> int | None:
        """Safely parse string to int.

        Args:
            value: String value to parse.

        Returns:
            Integer value or None if parsing fails.

        """
        return int(value) if value and value.isdigit() else None

    @staticmethod
    def _parse_date(value: str | None) -> date | None:
        """Safely parse string to a date.

        Args:
            value: String value to parse.

        Returns:
            date value or None if parsing fails.

        """
        if not value:
            return None
        try:
            return datetime.strptime(value, "%Y-%m-%d").replace(tzinfo=timezone.utc).date()
        except ValueError:
            return None

    @staticmethod
    def _parse_datetime(value: str | None) -> datetime | None:
        """Safely parse string to a datetime.

        Args:
            value: String value to parse.

        Returns:
            datetime value or None if parsing fails.

        """
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    @staticmethod
    def _get_id_from_attrib(attrib: dict[str, str]) -> int | str | None:
        """Extract ID from element attributes, converting to int if possible.

        Args:
            attrib: Element attributes dictionary.

        Returns:
            ID as int or string, or None if not found.

        """
        if id_ := attrib.get("id"):
            return int(id_) if id_.isdigit() else id_
        return None

    @staticmethod
    def _split_string(string: str, delimiters: list[str]) -> list[str]:
        """Split a string based on the provided delimiters.

        Args:
            string: The string to split.
            delimiters: List of delimiters to use for splitting.

        Returns:
            The list of substrings after splitting the string.

        """
        for delimiter in delimiters:
            string = string.replace(delimiter, delimiters[0])
        return string.split(delimiters[0])

    @staticmethod
    def _validate_value(val: str | None, valid_set: frozenset[str]) -> str | None:
        """Validate a value against a predefined set.

        Args:
            val: The value to validate.
            valid_set: The set of valid values.

        Returns:
            The validated value, or "Unknown" if the value is not in the set.

        """
        if val is not None:
            return "Unknown" if val not in valid_set else val
        return None
