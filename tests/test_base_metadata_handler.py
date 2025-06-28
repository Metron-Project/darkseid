# ruff: noqa: SLF001
"""Tests for BaseMetadataHandler class."""

import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest
from defusedxml.ElementTree import fromstring

from darkseid.base_metadata_handler import BaseMetadataHandler, XmlError
from darkseid.metadata import Metadata


# Concrete implementation for testing
class TestMetadataHandler(BaseMetadataHandler):
    """Test implementation of BaseMetadataHandler."""

    def metadata_from_string(self, xml_string: str) -> Metadata:
        """Simple implementation for testing."""
        try:
            tree = ET.ElementTree(fromstring(xml_string))
            return self._convert_xml_to_metadata(tree)
        except ET.ParseError as e:
            msg = f"Failed to parse XML: {e}"
            raise XmlError(msg) from e

    def string_from_metadata(self, metadata: Metadata, xml_bytes: bytes = b"") -> str:
        """Simple implementation for testing."""
        tree = self._convert_metadata_to_xml(metadata, xml_bytes)
        return ET.tostring(tree.getroot(), encoding="unicode")

    def _convert_metadata_to_xml(
        self, metadata: Metadata, _: bytes | None = None
    ) -> ET.ElementTree:
        """Simple implementation for testing."""
        root = ET.Element("metadata")
        if hasattr(metadata, "title") and metadata.title:
            title_elem = ET.SubElement(root, "title")
            title_elem.text = metadata.title
        return ET.ElementTree(root)

    def _convert_xml_to_metadata(self, tree: ET.ElementTree) -> Metadata:
        """Simple implementation for testing."""
        metadata = Metadata()
        root = tree.getroot()
        title_elem = root.find("title")
        if title_elem is not None:
            metadata.title = title_elem.text
        return metadata


@pytest.fixture
def handler():
    """Create a test handler instance."""
    return TestMetadataHandler()


@pytest.fixture
def sample_metadata():
    """Create sample metadata for testing."""
    metadata = Metadata()
    metadata.title = "Test Comic"
    return metadata


@pytest.fixture
def temp_xml_file():
    """Create a temporary XML file for testing."""
    with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write(
            '<?xml version="1.0" encoding="utf-8"?>\n<metadata><title>Test Title</title></metadata>'
        )
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink(missing_ok=True)


@pytest.fixture
def invalid_xml_file():
    """Create a temporary invalid XML file for testing."""
    with NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
        f.write("<invalid><unclosed>")
        temp_path = Path(f.name)
    yield temp_path
    temp_path.unlink(missing_ok=True)


def test_xml_error_exception():
    """Test XmlError exception can be raised and caught."""
    with pytest.raises(XmlError):  # noqa: PT012
        msg = "Test error message"
        raise XmlError(msg)


def test_abstract_methods_must_be_implemented():
    """Test that BaseMetadataHandler cannot be instantiated directly."""
    with pytest.raises(TypeError):
        BaseMetadataHandler()  # type: ignore


def test_write_xml_creates_file(handler, sample_metadata, tmp_path):
    """Test that write_xml creates an XML file."""
    output_file = tmp_path / "test_output.xml"

    handler.write_xml(output_file, sample_metadata)

    assert output_file.exists()
    content = output_file.read_text()
    assert "Test Comic" in content
    assert "<?xml version='1.0' encoding='utf-8'?>" in content


def test_write_xml_creates_parent_directories(handler, sample_metadata, tmp_path):
    """Test that write_xml creates parent directories if they don't exist."""
    nested_path = tmp_path / "nested" / "dir" / "test.xml"

    handler.write_xml(nested_path, sample_metadata)

    assert nested_path.exists()
    assert nested_path.parent.exists()


def test_write_xml_with_xml_bytes(handler, sample_metadata, tmp_path):
    """Test write_xml with additional xml_bytes parameter."""
    output_file = tmp_path / "test_with_bytes.xml"
    xml_bytes = b"<extra>content</extra>"

    handler.write_xml(output_file, sample_metadata, xml_bytes)

    assert output_file.exists()


def test_read_xml_valid_file(handler, temp_xml_file):
    """Test reading a valid XML file."""
    metadata = handler.read_xml(temp_xml_file)

    assert isinstance(metadata, Metadata)
    assert metadata.title == "Test Title"


def test_read_xml_invalid_file_returns_empty_metadata(handler, invalid_xml_file):
    """Test that reading an invalid XML file returns empty Metadata."""
    metadata = handler.read_xml(invalid_xml_file)

    assert isinstance(metadata, Metadata)
    # Should return empty metadata when parse fails
    assert not hasattr(metadata, "title") or metadata.title is None


def test_read_xml_nonexistent_file(handler, tmp_path):
    """Test reading a nonexistent file."""
    nonexistent_file = tmp_path / "does_not_exist.xml"

    # This should handle the file not found gracefully
    with pytest.raises(FileNotFoundError):
        handler.read_xml(nonexistent_file)


def test_get_or_create_element_existing():
    """Test _get_or_create_element with existing element."""
    parent = ET.Element("parent")
    existing = ET.SubElement(parent, "child")
    existing.text = "old text"

    result = BaseMetadataHandler._get_or_create_element(parent, "child")

    assert result.tag == "child"
    assert result.text is None  # Should be cleared
    assert len(parent) == 1  # Should still have only one child


def test_get_or_create_element_new():
    """Test _get_or_create_element with new element."""
    parent = ET.Element("parent")

    result = BaseMetadataHandler._get_or_create_element(parent, "child")

    assert result.tag == "child"
    assert len(parent) == 1


def test_set_element_text_new_element():
    """Test _set_element_text creating new element."""
    root = ET.Element("root")

    BaseMetadataHandler._set_element_text(root, "test", "value")

    element = root.find("test")
    assert element is not None
    assert element.text == "value"


def test_set_element_text_update_existing():
    """Test _set_element_text updating existing element."""
    root = ET.Element("root")
    existing = ET.SubElement(root, "test")
    existing.text = "old"

    BaseMetadataHandler._set_element_text(root, "test", "new")

    element = root.find("test")
    assert element.text == "new"


def test_set_element_text_remove_when_none():
    """Test _set_element_text removes element when value is None."""
    root = ET.Element("root")
    existing = ET.SubElement(root, "test")
    existing.text = "old"

    BaseMetadataHandler._set_element_text(root, "test", None)

    element = root.find("test")
    assert element is None


def test_set_element_text_no_op_when_none_and_not_exists():
    """Test _set_element_text does nothing when value is None and element doesn't exist."""
    root = ET.Element("root")

    BaseMetadataHandler._set_element_text(root, "test", None)

    element = root.find("test")
    assert element is None
    assert len(root) == 0


def test_set_datetime_element_new():
    """Test _set_datetime_element creating new element."""
    root = ET.Element("root")
    dt = datetime(2023, 1, 15, 12, 30, 45, tzinfo=timezone.utc)

    BaseMetadataHandler._set_datetime_element(root, "date", dt)

    element = root.find("date")
    assert element is not None
    assert element.text == "2023-01-15T12:30:45+00:00"


def test_set_datetime_element_remove_when_none():
    """Test _set_datetime_element removes element when datetime is None."""
    root = ET.Element("root")
    existing = ET.SubElement(root, "date")
    existing.text = "2023-01-01T00:00:00"

    BaseMetadataHandler._set_datetime_element(root, "date", None)

    element = root.find("date")
    assert element is None


def test_get_text_content_existing():
    """Test _get_text_content with existing element."""
    root = ET.Element("root")
    child = ET.SubElement(root, "child")
    child.text = "test content"

    result = BaseMetadataHandler._get_text_content(root, "child")

    assert result == "test content"


def test_get_text_content_missing():
    """Test _get_text_content with missing element."""
    root = ET.Element("root")

    result = BaseMetadataHandler._get_text_content(root, "missing")

    assert result is None


def test_get_text_content_empty():
    """Test _get_text_content with empty element."""
    root = ET.Element("root")
    ET.SubElement(root, "child")

    result = BaseMetadataHandler._get_text_content(root, "child")

    assert result is None


def test_parse_int_valid():
    """Test _parse_int with valid integer string."""
    result = BaseMetadataHandler._parse_int("123")
    assert result == 123


def test_parse_int_invalid():
    """Test _parse_int with invalid string."""
    result = BaseMetadataHandler._parse_int("not_a_number")
    assert result is None


def test_parse_int_none():
    """Test _parse_int with None."""
    result = BaseMetadataHandler._parse_int(None)
    assert result is None


def test_parse_int_empty():
    """Test _parse_int with empty string."""
    result = BaseMetadataHandler._parse_int("")
    assert result is None


def test_parse_int_float_string():
    """Test _parse_int with float string."""
    result = BaseMetadataHandler._parse_int("123.45")
    assert result is None


def test_parse_date_valid():
    """Test _parse_date with valid date string."""
    result = BaseMetadataHandler._parse_date("2023-01-15")
    assert result == date(2023, 1, 15)


def test_parse_date_invalid():
    """Test _parse_date with invalid date string."""
    result = BaseMetadataHandler._parse_date("not-a-date")
    assert result is None


def test_parse_date_none():
    """Test _parse_date with None."""
    result = BaseMetadataHandler._parse_date(None)
    assert result is None


def test_parse_date_empty():
    """Test _parse_date with empty string."""
    result = BaseMetadataHandler._parse_date("")
    assert result is None


def test_parse_date_wrong_format():
    """Test _parse_date with wrong format."""
    result = BaseMetadataHandler._parse_date("01/15/2023")
    assert result is None


def test_parse_datetime_valid():
    """Test _parse_datetime with valid datetime string."""
    result = BaseMetadataHandler._parse_datetime("2023-01-15T12:30:45 -0000")
    assert result == datetime(2023, 1, 15, 12, 30, 45, tzinfo=timezone.utc)


def test_parse_datetime_with_timezone():
    """Test _parse_datetime with timezone info."""
    result = BaseMetadataHandler._parse_datetime("2023-01-15T12:30:45+00:00")
    expected = datetime(2023, 1, 15, 12, 30, 45, tzinfo=timezone.utc)
    assert result == expected


def test_parse_datetime_invalid():
    """Test _parse_datetime with invalid datetime string."""
    result = BaseMetadataHandler._parse_datetime("not-a-datetime")
    assert result is None


def test_parse_datetime_none():
    """Test _parse_datetime with None."""
    result = BaseMetadataHandler._parse_datetime(None)
    assert result is None


def test_parse_datetime_empty():
    """Test _parse_datetime with empty string."""
    result = BaseMetadataHandler._parse_datetime("")
    assert result is None


def test_get_id_from_attrib_string_id():
    """Test _get_id_from_attrib with string ID."""
    attrib = {"id": "test_id", "other": "value"}
    result = BaseMetadataHandler._get_id_from_attrib(attrib)
    assert result == "test_id"


def test_get_id_from_attrib_numeric_id():
    """Test _get_id_from_attrib with numeric ID."""
    attrib = {"id": "123", "other": "value"}
    result = BaseMetadataHandler._get_id_from_attrib(attrib)
    assert result == 123


def test_get_id_from_attrib_no_id():
    """Test _get_id_from_attrib with no ID attribute."""
    attrib = {"other": "value"}
    result = BaseMetadataHandler._get_id_from_attrib(attrib)
    assert result is None


def test_get_id_from_attrib_empty_dict():
    """Test _get_id_from_attrib with empty dictionary."""
    attrib = {}
    result = BaseMetadataHandler._get_id_from_attrib(attrib)
    assert result is None


def test_split_string_single_delimiter():
    """Test _split_string with single delimiter."""
    result = BaseMetadataHandler._split_string("a,b,c", [","])
    assert result == ["a", "b", "c"]


def test_split_string_multiple_delimiters():
    """Test _split_string with multiple delimiters."""
    result = BaseMetadataHandler._split_string("a,b;c|d", [",", ";", "|"])
    assert result == ["a", "b", "c", "d"]


def test_split_string_no_delimiters():
    """Test _split_string with no delimiters found."""
    result = BaseMetadataHandler._split_string("abc", [","])
    assert result == ["abc"]


def test_split_string_empty_string():
    """Test _split_string with empty string."""
    result = BaseMetadataHandler._split_string("", [","])
    assert result == [""]


def test_validate_value_valid():
    """Test _validate_value with valid value."""
    valid_set = frozenset(["option1", "option2", "option3"])
    result = BaseMetadataHandler._validate_value("option1", valid_set)
    assert result == "option1"


def test_validate_value_invalid():
    """Test _validate_value with invalid value."""
    valid_set = frozenset(["option1", "option2", "option3"])
    result = BaseMetadataHandler._validate_value("invalid", valid_set)
    assert result == "Unknown"


def test_validate_value_none():
    """Test _validate_value with None."""
    valid_set = frozenset(["option1", "option2", "option3"])
    result = BaseMetadataHandler._validate_value(None, valid_set)
    assert result is None


def test_validate_value_empty_set():
    """Test _validate_value with empty valid set."""
    valid_set = frozenset()
    result = BaseMetadataHandler._validate_value("anything", valid_set)
    assert result == "Unknown"


# Integration tests
def test_write_read_roundtrip(handler, sample_metadata, tmp_path):
    """Test writing and reading XML creates equivalent metadata."""
    xml_file = tmp_path / "roundtrip.xml"

    handler.write_xml(xml_file, sample_metadata)
    read_metadata = handler.read_xml(xml_file)

    assert read_metadata.title == sample_metadata.title


def test_string_conversion_roundtrip(handler, sample_metadata):
    """Test string conversion roundtrip."""
    xml_string = handler.string_from_metadata(sample_metadata)
    converted_metadata = handler.metadata_from_string(xml_string)

    assert converted_metadata.title == sample_metadata.title


@pytest.mark.parametrize(
    ("test_value", "expected"),
    [
        ("123", 123),
        ("0", 0),
        ("-123", None),  # negative numbers treated as invalid by isdigit()
        ("12.34", None),
        ("abc", None),
        ("", None),
        (None, None),
    ],
)
def test_parse_int_parametrized(test_value, expected):
    """Parametrized test for _parse_int method."""
    result = BaseMetadataHandler._parse_int(test_value)
    assert result == expected


@pytest.mark.parametrize(
    ("test_date", "is_valid"),
    [
        ("2023-01-01", True),
        ("2023-12-31", True),
        ("2023-02-29", False),  # Not a leap year
        ("2024-02-29", True),  # Leap year
        ("invalid-date", False),
        ("2023/01/01", False),  # Wrong format
        ("", False),
        (None, False),
    ],
)
def test_parse_date_parametrized(test_date, is_valid):
    """Parametrized test for _parse_date method."""
    result = BaseMetadataHandler._parse_date(test_date)
    if is_valid:
        assert result is not None
        assert isinstance(result, date)
    else:
        assert result is None
