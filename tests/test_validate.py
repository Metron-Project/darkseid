# ruff: noqa: SLF001, ARG001
"""Tests for validate.py module using function-based pytest approach."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from xmlschema import XMLSchema10, XMLSchema11

from darkseid.validate import SchemaVersion, ValidateMetadata, ValidationError


# Test data fixtures
@pytest.fixture
def valid_xml_bytes():
    """Sample valid XML content as bytes."""
    return b'<?xml version="1.0"?><ComicInfo><Title>Test Comic</Title></ComicInfo>'


@pytest.fixture
def invalid_xml_bytes():
    """Sample invalid XML content as bytes."""
    return b'<?xml version="1.0"?><InvalidRoot><BadElement></BadElement>'


@pytest.fixture
def empty_xml_bytes():
    """Empty XML bytes."""
    return b""


@pytest.fixture
def mock_schema_path(tmp_path):
    """Create a temporary schema file path."""
    schema_file = tmp_path / "test_schema.xsd"
    schema_file.write_text(
        '<?xml version="1.0"?><xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"></xs:schema>'
    )
    return schema_file


# SchemaVersion enum tests
def test_schema_version_enum_values():
    """Test that SchemaVersion enum has expected values."""
    expected_values = ["METRON_INFO_V1", "COMIC_INFO_V2", "COMIC_INFO_V1", "UNKNOWN"]
    actual_values = [version.name for version in SchemaVersion]
    assert actual_values == expected_values


def test_schema_version_string_representation():
    """Test SchemaVersion string representation."""
    assert str(SchemaVersion.COMIC_INFO_V1) == "Comic Info V1"
    assert str(SchemaVersion.COMIC_INFO_V2) == "Comic Info V2"
    assert str(SchemaVersion.METRON_INFO_V1) == "Metron Info V1"
    assert str(SchemaVersion.UNKNOWN) == "Unknown"


# ValidationError tests
def test_validation_error_creation():
    """Test ValidationError exception creation."""
    error = ValidationError("Test error message")
    assert str(error) == "Test error message"
    assert error.schema_version is None


def test_validation_error_with_schema_version():
    """Test ValidationError with schema version."""
    error = ValidationError("Test error", SchemaVersion.COMIC_INFO_V1)
    assert str(error) == "Test error"
    assert error.schema_version == SchemaVersion.COMIC_INFO_V1


# ValidateMetadata initialization tests
def test_validate_metadata_init_success(valid_xml_bytes):
    """Test successful ValidateMetadata initialization."""
    validator = ValidateMetadata(valid_xml_bytes)
    assert validator.xml == valid_xml_bytes
    assert isinstance(validator._schema_cache, dict)
    assert len(validator._schema_cache) == 0


def test_validate_metadata_init_empty_xml():
    """Test ValidateMetadata initialization with empty XML raises error."""
    with pytest.raises(ValidationError, match="XML data cannot be empty"):
        ValidateMetadata(b"")


def test_validate_metadata_init_none_xml():
    """Test ValidateMetadata initialization with None XML raises error."""
    with pytest.raises(ValidationError, match="XML data cannot be empty"):
        ValidateMetadata(None)  # type: ignore


def test_validate_metadata_repr(valid_xml_bytes):
    """Test ValidateMetadata string representation."""
    validator = ValidateMetadata(valid_xml_bytes)
    expected = f"ValidateMetadata(xml_size={len(valid_xml_bytes)} bytes)"
    assert repr(validator) == expected


# Schema path retrieval tests
def test_get_schema_path_unknown_version():
    """Test _get_schema_path with unknown schema version."""
    result = ValidateMetadata._get_schema_path(SchemaVersion.UNKNOWN)
    assert result is None


@patch("darkseid.validate.files")
@patch("darkseid.validate.as_file")
def test_get_schema_path_comic_info_v1(mock_as_file, mock_files):
    """Test _get_schema_path for ComicInfo v1."""
    mock_path = Mock()
    mock_files.return_value.joinpath.return_value = mock_path
    mock_as_file.return_value.__enter__.return_value = Path("/fake/path/ComicInfo.xsd")

    result = ValidateMetadata._get_schema_path(SchemaVersion.COMIC_INFO_V1)

    mock_files.assert_called_once_with("darkseid.schemas.ComicInfo.v1")
    mock_files.return_value.joinpath.assert_called_once_with("ComicInfo.xsd")
    assert result == Path("/fake/path/ComicInfo.xsd")


@patch("darkseid.validate.files")
@patch("darkseid.validate.as_file")
def test_get_schema_path_metron_info_v1(mock_as_file, mock_files):
    """Test _get_schema_path for MetronInfo v1."""
    mock_path = Mock()
    mock_files.return_value.joinpath.return_value = mock_path
    mock_as_file.return_value.__enter__.return_value = Path("/fake/path/MetronInfo.xsd")

    result = ValidateMetadata._get_schema_path(SchemaVersion.METRON_INFO_V1)

    mock_files.assert_called_once_with("darkseid.schemas.MetronInfo.v1")
    mock_files.return_value.joinpath.assert_called_once_with("MetronInfo.xsd")
    assert result == Path("/fake/path/MetronInfo.xsd")


@patch("darkseid.validate.files", side_effect=ImportError("Module not found"))
def test_get_schema_path_import_error(mock_files):
    """Test _get_schema_path handles ImportError gracefully."""
    result = ValidateMetadata._get_schema_path(SchemaVersion.COMIC_INFO_V1)
    assert result is None


# Schema context manager tests
def test_get_schema_unknown_version(valid_xml_bytes):
    """Test _get_schema with unknown schema version."""
    validator = ValidateMetadata(valid_xml_bytes)

    with validator._get_schema(SchemaVersion.UNKNOWN) as schema:
        assert schema is None


def test_get_schema_cached_schema(valid_xml_bytes):
    """Test _get_schema returns cached schema."""
    validator = ValidateMetadata(valid_xml_bytes)
    mock_schema = Mock()
    validator._schema_cache[SchemaVersion.COMIC_INFO_V1] = mock_schema

    with validator._get_schema(SchemaVersion.COMIC_INFO_V1) as schema:
        assert schema is mock_schema


@patch("darkseid.validate.ValidateMetadata._get_schema_path", return_value=None)
def test_get_schema_no_path_available(mock_get_path, valid_xml_bytes):
    """Test _get_schema when schema path is not available."""
    validator = ValidateMetadata(valid_xml_bytes)

    with validator._get_schema(SchemaVersion.COMIC_INFO_V1) as schema:
        assert schema is None


# Validation tests
def test_is_valid_no_schema_available(valid_xml_bytes):
    """Test _is_valid returns False when schema is not available."""
    validator = ValidateMetadata(valid_xml_bytes)

    with patch.object(validator, "_get_schema") as mock_get_schema:
        mock_get_schema.return_value.__enter__.return_value = None

        result = validator._is_valid(SchemaVersion.COMIC_INFO_V1)
        assert result is False


def test_is_valid_successful_validation(valid_xml_bytes):
    """Test _is_valid returns True for successful validation."""
    validator = ValidateMetadata(valid_xml_bytes)
    mock_schema = Mock()
    mock_schema.validate.return_value = None

    with patch.object(validator, "_get_schema") as mock_get_schema:
        mock_get_schema.return_value.__enter__.return_value = mock_schema

        result = validator._is_valid(SchemaVersion.COMIC_INFO_V1)
        assert result is True
        mock_schema.validate.assert_called_once()


def test_is_valid_unexpected_exception(valid_xml_bytes):
    """Test _is_valid handles unexpected exceptions."""
    validator = ValidateMetadata(valid_xml_bytes)
    mock_schema = Mock()
    mock_schema.validate.side_effect = Exception("Unexpected error")

    with patch.object(validator, "_get_schema") as mock_get_schema:
        mock_get_schema.return_value.__enter__.return_value = mock_schema

        result = validator._is_valid(SchemaVersion.COMIC_INFO_V1)
        assert result is False


# Main validation method tests
def test_validate_first_schema_valid(valid_xml_bytes):
    """Test validate returns first valid schema version."""
    validator = ValidateMetadata(valid_xml_bytes)

    with patch.object(validator, "_is_valid") as mock_is_valid:
        mock_is_valid.side_effect = lambda schema: schema == SchemaVersion.METRON_INFO_V1

        result = validator.validate()
        assert result == SchemaVersion.METRON_INFO_V1


def test_validate_second_schema_valid(valid_xml_bytes):
    """Test validate returns second valid schema when first fails."""
    validator = ValidateMetadata(valid_xml_bytes)

    with patch.object(validator, "_is_valid") as mock_is_valid:
        mock_is_valid.side_effect = lambda schema: schema == SchemaVersion.COMIC_INFO_V2

        result = validator.validate()
        assert result == SchemaVersion.COMIC_INFO_V2


def test_validate_no_valid_schemas(valid_xml_bytes):
    """Test validate returns UNKNOWN when no schemas are valid."""
    validator = ValidateMetadata(valid_xml_bytes)

    with patch.object(validator, "_is_valid", return_value=False):
        result = validator.validate()
        assert result == SchemaVersion.UNKNOWN


# validate_all method tests
def test_validate_all_returns_all_results(valid_xml_bytes):
    """Test validate_all returns results for all schema versions."""
    validator = ValidateMetadata(valid_xml_bytes)

    expected_results = {
        SchemaVersion.METRON_INFO_V1: True,
        SchemaVersion.COMIC_INFO_V2: False,
        SchemaVersion.COMIC_INFO_V1: True,
    }

    with patch.object(validator, "_is_valid") as mock_is_valid:
        mock_is_valid.side_effect = lambda schema: expected_results[schema]

        results = validator.validate_all()
        assert results == expected_results
        assert len(results) == 3


# get_validation_errors method tests
def test_get_validation_errors_no_schema(valid_xml_bytes):
    """Test get_validation_errors when schema is not available."""
    validator = ValidateMetadata(valid_xml_bytes)

    with patch.object(validator, "_get_schema") as mock_get_schema:
        mock_get_schema.return_value.__enter__.return_value = None

        errors = validator.get_validation_errors(SchemaVersion.COMIC_INFO_V1)
        assert len(errors) == 1
        assert "Schema not available" in errors[0]


def test_get_validation_errors_unexpected_error(valid_xml_bytes):
    """Test get_validation_errors handles unexpected errors."""
    validator = ValidateMetadata(valid_xml_bytes)
    mock_schema = Mock()
    mock_schema.validate.side_effect = Exception("Unexpected error")

    with patch.object(validator, "_get_schema") as mock_get_schema:
        mock_get_schema.return_value.__enter__.return_value = mock_schema

        errors = validator.get_validation_errors(SchemaVersion.COMIC_INFO_V1)
        assert len(errors) == 1
        assert "Unexpected validation error" in errors[0]


def test_get_validation_errors_no_errors(valid_xml_bytes):
    """Test get_validation_errors returns empty list for valid XML."""
    validator = ValidateMetadata(valid_xml_bytes)
    mock_schema = Mock()
    mock_schema.validate.return_value = None

    with patch.object(validator, "_get_schema") as mock_get_schema:
        mock_get_schema.return_value.__enter__.return_value = mock_schema

        errors = validator.get_validation_errors(SchemaVersion.COMIC_INFO_V1)
        assert errors == []


# Parametrized tests
@pytest.mark.parametrize(
    ("schema_version", "expected_module", "expected_file"),
    [
        (SchemaVersion.COMIC_INFO_V1, "darkseid.schemas.ComicInfo.v1", "ComicInfo.xsd"),
        (SchemaVersion.COMIC_INFO_V2, "darkseid.schemas.ComicInfo.v2", "ComicInfo.xsd"),
        (SchemaVersion.METRON_INFO_V1, "darkseid.schemas.MetronInfo.v1", "MetronInfo.xsd"),
    ],
)
def test_schema_config_mapping(schema_version, expected_module, expected_file):
    """Test schema configuration mapping for different versions."""
    config = ValidateMetadata._SCHEMA_CONFIG.get(schema_version)
    assert config is not None
    assert config["module_path"] == expected_module
    assert config["file_name"] == expected_file


@pytest.mark.parametrize(
    ("schema_version", "expected_class"),
    [
        (SchemaVersion.COMIC_INFO_V1, XMLSchema10),
        (SchemaVersion.COMIC_INFO_V2, XMLSchema10),
        (SchemaVersion.METRON_INFO_V1, XMLSchema11),
    ],
)
def test_schema_class_mapping(schema_version, expected_class):
    """Test schema class mapping for different versions."""
    config = ValidateMetadata._SCHEMA_CONFIG.get(schema_version)  # type: ignore
    assert config["schema_class"] == expected_class


# Edge cases and error conditions
def test_validation_order_consistency():
    """Test that validation order is consistent with class definition."""
    expected_order = [
        SchemaVersion.METRON_INFO_V1,
        SchemaVersion.COMIC_INFO_V2,
        SchemaVersion.COMIC_INFO_V1,
    ]
    assert expected_order == ValidateMetadata._VALIDATION_ORDER


def test_xml_bytes_preserved_through_validation(valid_xml_bytes):
    """Test that XML bytes are not modified during validation."""
    original_xml = valid_xml_bytes[:]
    validator = ValidateMetadata(valid_xml_bytes)

    with patch.object(validator, "_is_valid", return_value=False):
        validator.validate()

    assert validator.xml == original_xml
