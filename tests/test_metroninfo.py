# ruff: noqa: SLF001
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from darkseid.metadata import (
    GTIN,
    AgeRatings,
    AlternativeNames,
    Arc,
    Basic,
    Credit,
    InfoSources,
    Metadata,
    Notes,
    Price,
    Publisher,
    Role,
    Series,
    Universe,
)
from darkseid.metroninfo import MetronInfo


@pytest.fixture
def metron_info():
    return MetronInfo()


@pytest.mark.parametrize(
    ("xml", "expected_root_tag"),
    [
        # Happy path
        (b"<MetronInfo></MetronInfo>", "MetronInfo"),
        # Edge case: empty XML
        ("", "MetronInfo"),
    ],
    ids=["happy_path", "empty_xml"],
)
def test_get_root(metron_info, xml, expected_root_tag):
    # Act
    result = metron_info._get_root(xml)

    # Assert
    assert result.tag == expected_root_tag


@pytest.mark.parametrize(
    ("val", "expected_result"),
    [
        # Happy path
        ("Marvel", True),
        # Edge case: None value
        (None, False),
        # Error case: invalid source
        ("InvalidSource", False),
    ],
    ids=["valid_source", "none_value", "invalid_source"],
)
def test_valid_info_source(metron_info, val, expected_result):
    # Act
    result = metron_info._is_valid_info_source(val)

    # Assert
    assert result == expected_result


@pytest.mark.parametrize(
    ("val", "expected"),
    [
        ("Annual", "Annual"),  # happy path
        ("Digital Chapter", "Digital Chapter"),  # happy path
        ("Graphic Novel", "Graphic Novel"),  # happy path
        ("Hardcover", "Hardcover"),  # happy path
        ("Limited Series", "Limited Series"),  # happy path
        ("Omnibus", "Omnibus"),  # happy path
        ("One-Shot", "One-Shot"),  # happy path
        ("Single Issue", "Single Issue"),  # happy path
        ("Trade Paperback", "Trade Paperback"),  # happy path
        ("", None),  # edge case: empty string
        (None, None),  # edge case: None value
        ("Unknown Format", None),  # edge case: unknown format
        ("annual", "Annual"),  # edge case: case insensitivity
        ("ANNUAL", "Annual"),  # edge case: uppercase
    ],
    ids=[
        "valid_annual",
        "valid_digital_chapter",
        "valid_graphic_novel",
        "valid_hardcover",
        "valid_limited_series",
        "valid_omnibus",
        "valid_one_shot",
        "valid_single_issue",
        "valid_trade_paperback",
        "empty_string",
        "none_value",
        "unknown_format",
        "case_insensitivity_lower",
        "case_insensitivity_upper",
    ],
)
def test_valid_series_format(metron_info, val, expected):
    # Act
    result = metron_info._normalize_series_format(val)

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    ("val", "expected_result"),
    [
        # Happy path
        (AgeRatings(metron_info="Teen"), "Teen"),
        (AgeRatings(comic_rack="R18+"), "Mature"),
        (AgeRatings(comic_rack="G"), "Everyone"),
        (AgeRatings(comic_rack="M"), "Mature"),
        # Edge case: None value
        (None, None),
        # Error case: invalid rating
        (AgeRatings(metron_info="InvalidRating"), "Unknown"),
    ],
    ids=[
        "valid_mi_rating",
        "valid_ci_rating",
        "valid_ci_g_rating",
        "valid_ci_m_rating",
        "none_value",
        "invalid_rating",
    ],
)
def test_valid_age_rating(metron_info, val, expected_result):
    # Act
    result = metron_info._normalize_age_rating(val)

    # Assert
    assert result == expected_result


def test_convert_metadata_to_xml(metron_info):
    # Arrange
    metadata = Metadata(
        info_source=[InfoSources("Metron", 54, True), InfoSources("Comic Vine", 1234)],
        publisher=Publisher("Marvel", id_=1),
        series=Series(
            name="Spider-Man",
            volume=1,
            format="Single Issue",
            id_=50,
            language="en",
            start_year=1990,
            issue_count=650,
            volume_count=5,
            alternative_names=[
                AlternativeNames("Bug Boy", 50),
                AlternativeNames("Spider", language="de"),
            ],
        ),
        issue="50",
        story_arcs=[Arc("Final Crisis, Inc", id_=80, number=1)],
        cover_date=date(2020, 1, 1),
        store_date=date(2020, 1, 1),
        characters=[Basic("Aquaman", 1)],
        genres=[Basic("Humor"), Basic("Super-Hero", id_=10)],
        teams=[Basic("Justice League"), Basic("Infinity, Inc")],
        universes=[Universe(id_=25, name="ABC", designation="Earth 25")],
        prices=[Price(amount=Decimal("3.99"), country="US")],
        gtin=GTIN(isbn=1234567890123, upc=76194130593600111),
        credits=[Credit(person="Stan Lee", role=[Role(name="Writer", id_=5)], id_=10)],
        tags=[Basic("Good", id_=1)],
        locations=[Basic("Atlantis", id_=90)],
        reprints=[Basic("Action Comics #1", id_=1)],
        notes=Notes(metron_info="This is a test"),
    )

    # Act
    result = metron_info._convert_metadata_to_xml(metadata)

    # Assert
    assert isinstance(result, ET.ElementTree)
    assert result.getroot().tag == "MetronInfo"


def test_metadata_from_string(metron_info):
    # Arrange
    xml_string = """
    <MetronInfo>
         <IDS>
            <ID source="Metron" primary="true">290431</ID>
            <ID source="Comic Vine">12345</ID>
            <ID source="Grand Comics Database">543</ID>
        </IDS>
        <Publisher id="12345">
            <Name>Marvel</Name>
            <Imprint id="1234">Epic</Imprint>
        </Publisher>
        <Series id="65478" lang="en">
            <Name>Spider-Man</Name>
            <SortName>Spider-Man</SortName>
            <Volume>1</Volume>
            <Format>Omnibus</Format>
            <StartYear>1964</StartYear>
            <IssueCount>650</IssueCount>
            <VolumeCount>5</VolumeCount>
            <AlternativeNames>
                <Name id="1234">Foo</Name>
                <Name lang="de">Hüsker Dü</Name>
            </AlternativeNames>
        </Series>
        <Prices>
            <Price country="US">3.99</Price>
        </Prices>
        <CoverDate>2011-10-01</CoverDate>
        <StoreDate>2011-08-31</StoreDate>
        <GTIN>
            <ISBN>1234567890123</ISBN>
            <UPC>76194130593600111</UPC>
        </GTIN>
        <Genres>
            <Genre id="1">Super-Hero</Genre>
        </Genres>
        <URLs>
            <URL primary="true">https://comicvine.gamespot.com/justice-league-1-justice-league-part-one/4000-290431/</URL>
            <URL>https://foo.bar</URL>
            <URL>https://bar.foo</URL>
        </URLs>
        <Arcs>
            <Arc>
                <Name>Arc1</Name>
            </Arc>
        </Arcs>
        <Notes>This is a test</Notes>
        <LastModified>2024-08-12T12:13:54.087728-04:00</LastModified>
        <Credits>
            <Credit>
                <Creator id="123">Stan Lee</Creator>
                <Roles>
                    <Role>Writer</Role>
                </Roles>
            </Credit>
        </Credits>
    </MetronInfo>
    """
    # Act
    result = metron_info.metadata_from_string(xml_string)

    # Assert
    assert result.info_source[0].name == "Metron"
    assert result.info_source[0].id_ == 290431
    assert result.info_source[0].primary is True
    assert result.info_source[1].name == "Comic Vine"
    assert result.info_source[1].id_ == 12345
    assert result.publisher.name == "Marvel"
    assert result.series.name == "Spider-Man"
    assert result.series.format == "Omnibus"
    assert result.series.start_year == 1964
    assert result.series.issue_count == 650
    assert result.series.volume_count == 5
    assert len(result.series.alternative_names) == 2
    assert result.series.alternative_names[0].name == "Foo"
    assert result.series.alternative_names[0].id_ == 1234
    assert result.series.alternative_names[1].language == "de"
    assert result.series.alternative_names[1].name == "Hüsker Dü"
    assert result.prices[0].amount == Decimal("3.99")
    assert result.gtin.isbn == 1234567890123
    assert result.gtin.upc == 76194130593600111
    assert result.story_arcs[0].name == "Arc1"
    assert (
        result.web_link[0].url
        == "https://comicvine.gamespot.com/justice-league-1-justice-league-part-one/4000-290431/"
    )
    assert result.web_link[0].primary is True
    assert len(result.web_link) == 3
    assert result.web_link[1].url == "https://foo.bar"
    assert result.genres[0].id_ == 1
    assert result.genres[0].name == "Super-Hero"
    assert result.credits[0].person == "Stan Lee"
    assert result.credits[0].id_ == 123
    assert result.credits[0].role[0].name == "Writer"
    assert result.modified == datetime(
        2024, 8, 12, 12, 13, 54, 87728, tzinfo=timezone(timedelta(days=-1, seconds=72000))
    )
    assert result.notes is not None
    assert result.notes.metron_info == "This is a test"


def test_write_xml(fake_metadata, metron_info, tmp_path):
    # Arrange
    filename = tmp_path / "mi_test.xml"

    md = fake_metadata
    md.add_credit(Credit("John Byrne", id_=1, role=[Role("Writer", 2), Role("Artist", 1)]))
    md.add_credit(Credit("Terry Austin", id_=2, role=[Role("Inker", 5)]))

    # Act
    metron_info.write_xml(filename, md)

    # Assert
    assert filename.exists()


def test_read_xml(metron_info, tmp_path):
    # Arrange
    xml_string = "<MetronInfo><Publisher><Name>Marvel</Name></Publisher></MetronInfo>"
    filename = tmp_path / "test.xml"
    with Path.open(filename, "w") as f:
        f.write(xml_string)

    # Act
    result = metron_info.read_xml(filename)

    # Assert
    assert result.publisher.name == "Marvel"
