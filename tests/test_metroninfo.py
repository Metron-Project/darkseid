# ruff: noqa: SLF001, ARG001
import xml.etree.ElementTree as ET
from datetime import date, datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from darkseid.metadata.data_classes import (
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
from darkseid.metadata.metroninfo import MetronInfo


@pytest.fixture
def metron_info():
    return MetronInfo()


# Test data fixtures
@pytest.fixture
def sample_xml_bytes():
    return b"""<MetronInfo>
        <Publisher><Name>Marvel</Name></Publisher>
        <Series><Name>Spider-Man</Name></Series>
    </MetronInfo>"""


@pytest.fixture
def complex_metadata():
    """More comprehensive metadata for testing edge cases."""
    metadata = Metadata()
    metadata.info_source = [
        InfoSources("Metron", 12345, True),
        InfoSources("Comic Vine", 67890),
        InfoSources("Grand Comics Database", 999),
    ]
    metadata.publisher = Publisher("Marvel Comics", id_=1, imprint=Basic("Epic", 100))
    metadata.series = Series(
        name="The Amazing Spider-Man",
        sort_name="Amazing Spider-Man, The",
        volume=1,
        format="Single Issue",
        id_=200,
        language="en",
        start_year=1963,
        issue_count=800,
        volume_count=1,
        alternative_names=[
            AlternativeNames("Spidey", 50, "en"),
            AlternativeNames("Spider-Man", 51, "de"),
            AlternativeNames("蜘蛛人", language="zh"),
        ],
    )
    metadata.issue = "1"
    metadata.title = "With Great Power..."
    metadata.cover_date = date(1963, 8, 1)
    metadata.store_date = date(1963, 8, 10)
    metadata.page_count = 22
    metadata.summary = "The origin story of Spider-Man"

    # Multiple story arcs
    metadata.story_arcs = [
        Arc("Origin Stories", id_=1, number=1),
        Arc("Spider-Verse", id_=2, number=10),
    ]

    # Rich credit information
    metadata.credits = [
        Credit("Stan Lee", id_=1, role=[Role("Writer", 1), Role("Editor", 2)]),
        Credit("Steve Ditko", id_=2, role=[Role("Artist", 3), Role("Cover Artist", 4)]),
        Credit("Unknown Letterer", role=[Role("Letterer", 5)]),  # No ID
    ]

    # Multiple characters, teams, locations
    metadata.characters = [
        Basic("Spider-Man", 1),
        Basic("Aunt May", 2),
        Basic("Uncle Ben", 3),
        Basic("J. Jonah Jameson"),  # No ID
    ]
    metadata.teams = [Basic("Daily Bugle Staff")]
    metadata.locations = [Basic("New York City", 100), Basic("Queens", 101)]

    # Genres and tags
    metadata.genres = [Basic("Super-Hero", 1), Basic("Action", 2)]
    metadata.tags = [Basic("Origin", 10), Basic("Classic")]

    # Pricing and GTIN
    metadata.prices = [
        Price(Decimal("0.12"), "US"),
        Price(Decimal("0.15"), "CA"),
    ]
    metadata.gtin = GTIN(isbn=1234567890123, upc=76194130593600111)

    # Web links
    metadata.web_link = [
        Links("https://example.com/primary", True),
        Links("https://example.com/secondary"),
    ]

    # Additional metadata
    metadata.universes = [Universe(id_=616, name="Marvel Universe", designation="Earth-616")]
    metadata.reprints = [Basic("Amazing Fantasy #15", 999)]
    metadata.collection_title = "Spider-Man Origins"
    metadata.notes = Notes(metron_info="Test note", comic_rack="CR note")
    metadata.age_rating = AgeRatings(metron_info="Everyone")
    metadata.black_and_white = False
    metadata.manga = None
    metadata.is_empty = False
    metadata.modified = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    return metadata


# Enhanced _get_root tests
@pytest.mark.parametrize(
    ("xml_input", "expected_root_tag", "description"),
    [
        (b"<MetronInfo></MetronInfo>", "MetronInfo", "basic_xml"),
        (b"<MetronInfo><Test/></MetronInfo>", "MetronInfo", "xml_with_child"),
        ("", "MetronInfo", "empty_string"),
        (None, "MetronInfo", "none_input"),
        (b"", "MetronInfo", "empty_bytes"),
        (b"<MetronInfo version='1.0'></MetronInfo>", "MetronInfo", "xml_with_attributes"),
    ],
)
def test_get_root_comprehensive(metron_info, xml_input, expected_root_tag, description):
    """Test _get_root with various input scenarios."""
    result = metron_info._get_root(xml_input)
    assert result.tag == expected_root_tag


def test_get_root_malformed_xml(metron_info):
    """Test _get_root with malformed XML."""
    malformed_xml = b"<MetronInfo><Unclosed>"
    result = metron_info._get_root(malformed_xml)
    # Should still return a MetronInfo root even with malformed input
    assert result.tag == "MetronInfo"


# Enhanced info source validation tests
@pytest.mark.parametrize(
    ("source", "expected", "description"),
    [
        ("Metron", True, "metron_source"),
        ("Comic Vine", True, "comic_vine_source"),
        ("Grand Comics Database", True, "gcd_source"),
        ("Marvel", True, "marvel_source"),
        ("DC", False, "dc_source"),
        ("metron", True, "case_insensitive_metron"),
        ("COMIC VINE", True, "case_insensitive_comic_vine"),
        ("", False, "empty_string"),
        ("InvalidSource", False, "invalid_source"),
        ("Metron Comics", False, "partial_match"),
        ("   Metron   ", True, "whitespace_around_valid"),
        (123, False, "numeric_input"),
        (None, False, "none_input"),
    ],
)
def test_valid_info_source_comprehensive(metron_info, source, expected, description):
    """Comprehensive test for info source validation."""
    result = metron_info._is_valid_info_source(source)
    assert result == expected


# Enhanced series format tests
def test_series_format_edge_cases(metron_info):
    """Test series format normalization edge cases."""
    test_cases = [
        ("TRADE PAPERBACK", "Trade Paperback"),  # All caps
        ("trade paperback", "Trade Paperback"),  # All lowercase
        ("Trade paperback", "Trade Paperback"),  # Mixed case
        ("  Annual  ", "Annual"),  # Whitespace
        ("one-shot", "One-Shot"),  # Hyphenated lowercase
        ("GRAPHIC NOVEL", "Graphic Novel"),  # Multi-word caps
    ]

    for input_val, expected in test_cases:
        result = metron_info._normalize_series_format(input_val)
        assert result == expected, f"Failed for input: {input_val}"


# Enhanced age rating tests
@pytest.mark.parametrize(
    ("rating_input", "expected", "description"),
    [
        (AgeRatings(metron_info="Everyone"), "Everyone", "everyone_rating"),
        (AgeRatings(metron_info="Teen"), "Teen", "teen_rating"),
        (AgeRatings(metron_info="Mature"), "Mature", "mature_rating"),
        (AgeRatings(comic_rack="G"), "Everyone", "comic_rack_g"),
        (AgeRatings(comic_rack="PG"), "Teen", "comic_rack_pg"),
        (AgeRatings(comic_rack="R18+"), "Mature", "comic_rack_r18"),
        (AgeRatings(comic_rack="M"), "Mature", "comic_rack_m"),
        (AgeRatings(metron_info=""), None, "empty_metron_rating"),
        (AgeRatings(comic_rack=""), None, "empty_comic_rack_rating"),
        (AgeRatings(), None, "empty_ratings_object"),
    ],
)
def test_age_rating_comprehensive(metron_info, rating_input, expected, description):
    """Comprehensive age rating normalization tests."""
    result = metron_info._normalize_age_rating(rating_input)
    assert result == expected


# XML Conversion Tests
def test_convert_complex_metadata_to_xml(metron_info, complex_metadata):
    """Test XML conversion with complex metadata."""
    result = metron_info._convert_metadata_to_xml(complex_metadata)

    assert isinstance(result, ET.ElementTree)
    root = result.getroot()
    assert root.tag == "MetronInfo"

    # Verify specific elements exist
    assert root.find("Publisher") is not None
    assert root.find("Series") is not None
    assert root.find("Credits") is not None
    assert root.find("Prices") is not None

    # Check for multiple items
    credits_ = root.find("Credits")
    assert len(list(credits_)) >= 3  # Should have multiple credits

    prices = root.find("Prices")
    assert len(list(prices)) == 2  # US and CA prices


def test_convert_minimal_metadata_to_xml(metron_info):
    """Test XML conversion with minimal metadata."""
    minimal_metadata = Metadata()
    minimal_metadata.series = Series(name="Test Series")

    result = metron_info._convert_metadata_to_xml(minimal_metadata)
    assert isinstance(result, ET.ElementTree)
    assert result.getroot().tag == "MetronInfo"


def test_convert_empty_metadata_to_xml(metron_info):
    """Test XML conversion with completely empty metadata."""
    empty_metadata = Metadata()

    result = metron_info._convert_metadata_to_xml(empty_metadata)
    assert isinstance(result, ET.ElementTree)
    assert result.getroot().tag == "MetronInfo"


# String parsing tests
def test_metadata_from_string_with_unicode(metron_info):
    """Test parsing XML with unicode characters."""
    xml_string = """
    <MetronInfo>
        <Series>
            <Name>蜘蛛人</Name>
            <AlternativeNames>
                <AlternativeName lang="zh">蜘蛛侠</AlternativeName>
                <AlternativeName lang="ja">スパイダーマン</AlternativeName>
            </AlternativeNames>
        </Series>
        <Publisher>
            <Name>Marvel Comics</Name>
        </Publisher>
    </MetronInfo>
    """

    result = metron_info.metadata_from_string(xml_string)
    assert result.series.name == "蜘蛛人"
    assert len(result.series.alternative_names) == 2
    assert result.series.alternative_names[0].name == "蜘蛛侠"
    assert result.series.alternative_names[0].language == "zh"


def test_metadata_from_string_malformed_xml(metron_info):
    """Test parsing malformed XML."""
    malformed_xml = """
    <MetronInfo>
        <Series>
            <Name>Test Series
        </Series>
    </MetronInfo>
    """

    # Should handle gracefully and return some metadata
    result = metron_info.metadata_from_string(malformed_xml)
    assert isinstance(result, Metadata)


def test_metadata_from_string_empty_elements(metron_info):
    """Test parsing XML with empty elements."""
    xml_string = """
    <MetronInfo>
        <Series>
            <Name></Name>
            <Volume></Volume>
        </Series>
        <Publisher>
            <Name></Name>
        </Publisher>
        <Credits>
        </Credits>
    </MetronInfo>
    """

    result = metron_info.metadata_from_string(xml_string)
    assert isinstance(result, Metadata)
    # Empty names should be handled appropriately


# File I/O tests
def test_write_xml_with_special_characters(metron_info, tmp_path):
    """Test writing XML with special characters and unicode."""
    metadata = Metadata()
    metadata.series = Series(name="Test & Special <Characters>")
    metadata.publisher = Publisher("Marvel Comics™")
    metadata.summary = "Story with special chars: <>&\"'"

    filename = tmp_path / "special_chars.xml"
    metron_info.write_xml(filename, metadata)

    assert filename.exists()

    # Verify the file can be read back
    result = metron_info.read_xml(filename)
    assert result.series.name == "Test & Special <Characters>"
    assert result.publisher.name == "Marvel Comics™"


def test_write_xml_creates_directory(metron_info, tmp_path):
    """Test that write_xml creates directories if they don't exist."""
    nested_path = tmp_path / "nested" / "dir" / "test.xml"

    metadata = Metadata()
    metadata.series = Series(name="Test Series")

    metron_info.write_xml(nested_path, metadata)
    assert nested_path.exists()


def test_read_xml_file_not_found(metron_info, tmp_path):
    """Test reading non-existent XML file."""
    non_existent = tmp_path / "does_not_exist.xml"

    with pytest.raises(FileNotFoundError):
        metron_info.read_xml(non_existent)


def test_read_xml_invalid_xml_file(metron_info, tmp_path):
    """Test reading file with invalid XML."""
    invalid_xml_file = tmp_path / "invalid.xml"
    with Path.open(invalid_xml_file, "w") as f:
        f.write("This is not XML content")

    # Should handle gracefully
    result = metron_info.read_xml(invalid_xml_file)
    assert isinstance(result, Metadata)


def test_round_trip_xml_conversion(metron_info, complex_metadata, tmp_path):
    """Test writing and reading back complex metadata."""
    filename = tmp_path / "roundtrip_test.xml"

    # Write metadata to file
    metron_info.write_xml(filename, complex_metadata)

    # Read it back
    result = metron_info.read_xml(filename)

    # Verify key fields are preserved
    assert result.series.name == complex_metadata.series.name
    assert result.publisher.name == complex_metadata.publisher.name
    assert len(result.credits) == len(complex_metadata.credits)
    assert len(result.characters) == len(complex_metadata.characters)
    assert result.cover_date == complex_metadata.cover_date


# Performance and edge case tests
def test_large_metadata_performance(metron_info, tmp_path):
    """Test performance with large metadata sets."""
    large_metadata = Metadata()
    large_metadata.series = Series(name="Large Test Series")

    # Add many characters, teams, etc.
    large_metadata.characters = [Basic(f"Character {i}", i) for i in range(100)]
    large_metadata.teams = [Basic(f"Team {i}", i) for i in range(50)]
    large_metadata.locations = [Basic(f"Location {i}", i) for i in range(30)]
    large_metadata.genres = [Basic(f"Genre {i}", i) for i in range(20)]
    large_metadata.tags = [Basic(f"Tag {i}", i) for i in range(40)]

    filename = tmp_path / "large_metadata.xml"

    # Should complete without issues
    metron_info.write_xml(filename, large_metadata)
    result = metron_info.read_xml(filename)

    assert len(result.characters) == 100
    assert len(result.teams) == 50


def test_xml_with_mixed_content(metron_info):
    """Test parsing XML with mixed content patterns."""
    xml_string = """
    <MetronInfo>
        <Series id="123">
            <Name>Mixed Content Series</Name>
            <Volume>1</Volume>
            Some random text that shouldn't break parsing
            <Format>Single Issue</Format>
        </Series>
        <Publisher>Marvel</Publisher>
        <!-- This is a comment -->
        <Credits>
            <Credit>
                <Creator>Test Creator</Creator>
                <Roles>
                    <Role>Writer</Role>
                    <Role>Artist</Role>
                </Roles>
            </Credit>
        </Credits>
    </MetronInfo>
    """

    result = metron_info.metadata_from_string(xml_string)
    assert result.series.name == "Mixed Content Series"
    assert result.series.volume == 1
    assert result.series.format == "Single Issue"
    assert len(result.credits) == 1
    assert len(result.credits[0].role) == 2


# Validation and error handling tests
def test_metadata_validation_edge_cases(metron_info):
    """Test various validation scenarios."""
    # Test with None values
    result = metron_info._is_valid_info_source(None)
    assert result is False

    # Test with empty age rating
    result = metron_info._normalize_age_rating(None)
    assert result is None

    # Test with invalid format
    result = metron_info._normalize_series_format("NotAValidFormat")
    assert result is None


# Property-based testing helpers
def generate_valid_series_formats():
    """Generate valid series format test cases."""
    valid_formats = [
        "Annual",
        "Digital Chapter",
        "Graphic Novel",
        "Hardcover",
        "Limited Series",
        "Omnibus",
        "One-Shot",
        "Single Issue",
        "Trade Paperback",
    ]

    test_cases = []
    for fmt in valid_formats:
        test_cases.extend(
            [
                (fmt, fmt),  # Exact match
                (fmt.upper(), fmt),  # Uppercase
                (fmt.lower(), fmt),  # Lowercase
                (f"  {fmt}  ", fmt),  # With whitespace
            ]
        )

    return test_cases


@pytest.mark.parametrize(("input_format", "expected"), generate_valid_series_formats())
def test_all_valid_series_formats(metron_info, input_format, expected):
    """Test all valid series formats with various casings."""
    result = metron_info._normalize_series_format(input_format)
    assert result == expected


# Integration test
def test_full_workflow_integration(metron_info, tmp_path):
    """Test complete workflow from creation to file I/O."""
    # Create metadata
    metadata = Metadata()
    metadata.series = Series(name="Integration Test", volume=1)
    metadata.publisher = Publisher("Test Publisher")
    metadata.issue = "1"
    metadata.cover_date = date(2023, 1, 1)

    # Convert to XML
    xml_tree = metron_info._convert_metadata_to_xml(metadata)
    assert xml_tree is not None

    # Write to file
    filename = tmp_path / "integration_test.xml"
    metron_info.write_xml(filename, metadata)
    assert filename.exists()

    # Read back from file
    result = metron_info.read_xml(filename)
    assert result.series.name == "Integration Test"
    assert result.publisher.name == "Test Publisher"

    # Convert to string and parse
    with Path.open(filename) as f:
        xml_content = f.read()

    string_result = metron_info.metadata_from_string(xml_content)
    assert string_result.series.name == "Integration Test"
