# ruff: noqa: SLF001

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest

from darkseid.metadata.data_classes import (
    GTIN,
    AgeRatings,
    AlternativeNames,
    Arc,
    Basic,
    Credit,
    ImageMetadata,
    InfoSources,
    Links,
    Metadata,
    Notes,
    PageType,
    Price,
    Publisher,
    Role,
    Series,
    Universe,
)


# Test Basic class functionality
def test_basic_creation():
    """Test Basic class with name and optional id."""
    basic = Basic("Superman")
    assert basic.name == "Superman"
    assert basic.id_ is None

    basic_with_id = Basic("Batman", 123)
    assert basic_with_id.name == "Batman"
    assert basic_with_id.id_ == 123


def test_universe_creation():
    """Test Universe class with designation."""
    universe = Universe("Marvel Universe", 616, "Earth-616")
    assert universe.name == "Marvel Universe"
    assert universe.id_ == 616
    assert universe.designation == "Earth-616"


def test_role_creation():
    """Test Role class with primary flag."""
    role = Role("Writer", 1, primary=True)
    assert role.name == "Writer"
    assert role.id_ == 1
    assert role.primary is True

    secondary_role = Role("Artist")
    assert secondary_role.primary is False


def test_alternative_names_validation():
    """Test AlternativeNames language validation."""
    # Valid language codes
    alt_name = AlternativeNames("Superman", language="en")
    assert alt_name.language == "en"

    alt_name_german = AlternativeNames("Superman", language="de")
    assert alt_name_german.language == "de"

    # None/empty language
    alt_name_none = AlternativeNames("Superman", language=None)
    assert alt_name_none.language is None

    alt_name_empty = AlternativeNames("Superman", language="")
    assert alt_name_empty.language is None


def test_alternative_names_invalid_language():
    """Test AlternativeNames with invalid language codes."""
    with pytest.raises(ValueError, match="Couldn't find language"):
        AlternativeNames("Superman", language="xyz", id_=1)


def test_publisher_with_imprint():
    """Test Publisher class with imprint."""
    imprint = Basic("Vertigo", 9)
    publisher = Publisher("DC Comics", 1, imprint)
    assert publisher.name == "DC Comics"
    assert publisher.id_ == 1
    assert publisher.imprint.name == "Vertigo"
    assert publisher.imprint.id_ == 9


def test_arc_with_number():
    """Test Arc class with number."""
    arc = Arc("Crisis on Infinite Earths", 1, 5)
    assert arc.name == "Crisis on Infinite Earths"
    assert arc.id_ == 1
    assert arc.number == 5


def test_credit_creation():
    """Test Credit class creation."""
    roles = [Role("Writer"), Role("Penciller")]
    credit = Credit("Stan Lee", roles, 123)
    assert credit.person == "Stan Lee"
    assert len(credit.role) == 2
    assert credit.id_ == 123


def test_info_sources():
    """Test InfoSources class."""
    source = InfoSources("Metron", 1, primary=True)
    assert source.name == "Metron"
    assert source.id_ == 1
    assert source.primary is True


def test_links():
    """Test Links class."""
    link = Links("https://example.com", primary=True)
    assert link.url == "https://example.com"
    assert link.primary is True

    secondary_link = Links("https://secondary.com")
    assert secondary_link.primary is False


def test_notes():
    """Test Notes class."""
    notes = Notes("Metron info", "Comic rack info")
    assert notes.metron_info == "Metron info"
    assert notes.comic_rack == "Comic rack info"

    empty_notes = Notes()
    assert empty_notes.metron_info == ""
    assert empty_notes.comic_rack == ""


def test_age_ratings():
    """Test AgeRatings class."""
    ratings = AgeRatings("Teen", "T")
    assert ratings.metron_info == "Teen"
    assert ratings.comic_rack == "T"


def test_series_invalid_language():
    """Test SeriesLanguage class."""
    with pytest.raises(ValueError, match="Couldn't find language"):
        Series("Foo Bar", language="xyz")


def test_series_start_year_validation():
    """Test Series start_year validation."""
    # Valid year
    series = Series("Superman", start_year=1938)
    assert series.start_year == 1938

    # None/empty year
    series_none = Series("Superman", start_year=None)
    assert series_none.start_year is None

    # Invalid year length
    with pytest.raises(ValueError, match="Year: .* length must be 4"):
        Series("Superman", start_year=38)


def test_metadata_empty_initialization():
    """Test Metadata initialization and is_empty flag."""
    # Empty metadata
    empty_md = Metadata()
    assert empty_md.is_empty is True

    # Non-empty metadata
    non_empty_md = Metadata(series=Series("Superman"))
    assert non_empty_md.is_empty is False


def test_metadata_post_init():
    """Test Metadata __post_init__ method."""
    # Create metadata with some data
    md = Metadata(issue="1", comments="Test comment")
    assert md.is_empty is False

    # Create truly empty metadata
    empty_md = Metadata(is_empty=True)
    # Manually call post_init to test the logic
    empty_md.__post_init__()
    assert empty_md.is_empty is True


def test_metadata_set_default_page_list():
    """Test setting default page list."""
    md = Metadata()
    md.set_default_page_list(3)

    assert len(md.pages) == 3
    assert md.pages[0]["Image"] == 0
    assert md.pages[0]["Type"] == PageType.FrontCover
    assert md.pages[1]["Image"] == 1
    assert "Type" not in md.pages[1]
    assert md.pages[2]["Image"] == 2


def test_metadata_get_archive_page_index():
    """Test getting archive page index."""
    md = Metadata()
    md.pages = [ImageMetadata(Image=0), ImageMetadata(Image=1), ImageMetadata(Image=2)]

    assert md.get_archive_page_index(0) == 0
    assert md.get_archive_page_index(1) == 1
    assert md.get_archive_page_index(2) == 2
    assert md.get_archive_page_index(5) == 0  # Out of range


def test_metadata_get_cover_page_index_list():
    """Test getting cover page indices."""
    md = Metadata()
    md.pages = [
        ImageMetadata(Image=0, Type=PageType.FrontCover),
        ImageMetadata(Image=1),
        ImageMetadata(Image=2, Type=PageType.FrontCover),
    ]

    cover_indices = md.get_cover_page_index_list()
    assert cover_indices == [0, 2]

    # Test with no covers
    md_no_covers = Metadata()
    md_no_covers.pages = [ImageMetadata(Image=0), ImageMetadata(Image=1)]
    cover_indices_empty = md_no_covers.get_cover_page_index_list()
    assert cover_indices_empty == [0]


def test_metadata_existing_credit():
    """Test _existing_credit method."""
    md = Metadata()
    roles = [Role("Writer")]
    md.credits = [Credit("Stan Lee", roles)]

    exists, idx = md._existing_credit("Stan Lee")
    assert exists is True
    assert idx == 0

    exists, idx = md._existing_credit("Jack Kirby")
    assert exists is False
    assert idx is None

    # Test case insensitive
    exists, idx = md._existing_credit("STAN LEE")
    assert exists is True
    assert idx == 0


def test_metadata_role_exists():
    """Test _role_exists static method."""
    roles = [Role("Writer"), Role("Penciller")]
    new_role = Role("Writer")

    assert Metadata._role_exists(new_role, roles) is True

    new_role_2 = Role("Inker")
    assert Metadata._role_exists(new_role_2, roles) is False

    # Test case-insensitive
    new_role_3 = Role("WRITER")
    assert Metadata._role_exists(new_role_3, roles) is True


def test_metadata_add_credit_new_person():
    """Test adding credit for new person."""
    md = Metadata()
    roles = [Role("Writer")]
    credit = Credit("Stan Lee", roles)

    md.add_credit(credit)
    assert len(md.credits) == 1
    assert md.credits[0].person == "Stan Lee"
    assert len(md.credits[0].role) == 1


def test_metadata_add_credit_existing_person():
    """Test adding credit for existing person."""
    md = Metadata()
    roles1 = [Role("Writer")]
    roles2 = [Role("Penciller")]

    credit1 = Credit("Stan Lee", roles1)
    credit2 = Credit("Stan Lee", roles2)

    md.add_credit(credit1)
    md.add_credit(credit2)

    assert len(md.credits) == 1
    assert len(md.credits[0].role) == 2
    assert md.credits[0].role[0].name == "Writer"
    assert md.credits[0].role[1].name == "Penciller"


def test_metadata_add_credit_duplicate_role():
    """Test adding duplicate role for existing person."""
    md = Metadata()
    roles1 = [Role("Writer")]
    roles2 = [Role("Writer")]  # Duplicate

    credit1 = Credit("Stan Lee", roles1)
    credit2 = Credit("Stan Lee", roles2)

    md.add_credit(credit1)
    md.add_credit(credit2)

    assert len(md.credits) == 1
    assert len(md.credits[0].role) == 1  # No duplicate


def test_metadata_overlay_empty_lists():
    """Test overlay behavior with empty lists."""
    md1 = Metadata()
    md1.characters = [Basic("Superman")]
    md1.genres = [Basic("Action")]

    md2 = Metadata()
    # md2 has empty lists

    md1.overlay(md2)

    # Original lists should be preserved when overlay has empty lists
    assert len(md1.characters) == 1
    assert len(md1.genres) == 1


def test_metadata_overlay_non_empty_lists():
    """Test overlay behavior with non-empty lists."""
    md1 = Metadata()
    md1.characters = [Basic("Superman")]

    md2 = Metadata()
    md2.characters = [Basic("Batman")]

    md1.overlay(md2)

    # md2's list should replace md1's list
    assert len(md1.characters) == 1
    assert md1.characters[0].name == "Batman"


def test_metadata_overlay_string_fields():
    """Test overlay behavior with string fields."""
    md1 = Metadata()
    md1.issue = "1"
    md1.comments = "Original comment"

    md2 = Metadata()
    md2.issue = "2"
    md2.comments = ""  # Empty string

    md1.overlay(md2)

    assert md1.issue == "2"
    assert md1.comments is None  # Empty string becomes None


def test_metadata_overlay_credits():
    """Test overlay_credits method."""
    md = Metadata()
    md.credits = [Credit("Stan Lee", [Role("Writer")], 1)]

    new_credits = [
        Credit("Jack Kirby", [Role("Penciller")], 2),
        Credit("Stan Lee", [Role("Editor")], 1),  # Additional role for existing person
    ]

    md.overlay_credits(new_credits)

    assert len(md.credits) == 2
    # Stan Lee should have both Writer and Editor roles
    stan_credit = next(c for c in md.credits if c.person == "Stan Lee")
    assert len(stan_credit.role) == 2
    role_names = [r.name for r in stan_credit.role]
    assert "Writer" in role_names
    assert "Editor" in role_names


def test_metadata_overlay_remove_credit():
    """Test removing credit with blank person name."""
    md = Metadata()
    md.credits = [Credit("Stan Lee", [Role("Writer")])]

    # Credit with empty person name should remove the role
    new_credits = [Credit("", [Role("Writer")])]

    md.overlay_credits(new_credits)

    assert len(md.credits) == 1
    assert "Stan Lee" in [item.person for item in md.credits]


def test_gtin_none_values():
    """Test GTIN with None values."""
    gtin = GTIN(None, None)
    assert gtin.upc is None
    assert gtin.isbn is None


def test_gtin_string_values():
    """Test GTIN validation with string values."""
    gtin = GTIN("invalid", "also_invalid")  # type: ignore
    assert gtin.upc is None
    assert gtin.isbn is None


def test_gtin_upc_invalid_values():
    """Test GTIN validation with invalid UPC."""
    with pytest.raises(ValueError, match="UPC has a length greater than"):
        GTIN(upc=1234567890123456789)


def test_gtin_isbn_valid_values():
    """Test GTIN validation with ISBN."""
    with pytest.raises(ValueError, match="ISBN has a length greater than"):
        GTIN(isbn=1234567890123456789)


def test_price_none_country():
    """Test Price with None country."""
    price = Price(Decimal("2.99"), None)  # type: ignore
    assert price.country == "US"  # Should default to US


def test_price_whitespace_country():
    """Test Price with whitespace-only country."""
    with pytest.raises(ValueError, match="No value given for country"):
        Price(Decimal("2.99"), "   ")


def test_price_with_bad_country():
    """Test Price with bad country."""
    with pytest.raises(ValueError, match="Couldn't find country for"):
        Price(Decimal("2.99"), "xyz")


def test_metadata_str_empty():
    """Test string representation of empty metadata."""
    md = Metadata()
    assert str(md) == "Metadata(empty)"


def test_metadata_str_with_data():
    """Test string representation with data."""
    series = Series("Superman", volume=1, start_year=1938)
    publisher = Publisher("DC Comics")
    md = Metadata(
        series=series, issue="1", publisher=publisher, cover_date=date(1938, 6, 1), page_count=22
    )

    result = str(md)
    assert "Metadata:" in result
    assert "Series: Superman (v1) [1938]" in result
    assert "Issue: 1" in result
    assert "Publisher: DC Comics" in result
    assert "22 pages" in result


def test_page_type_constants():
    """Test PageType constants."""
    assert PageType.FrontCover == "FrontCover"
    assert PageType.InnerCover == "InnerCover"
    assert PageType.Story == "Story"
    assert PageType.Advertisement == "Advertisement"
    assert PageType.BackCover == "BackCover"
    assert PageType.Other == "Other"
    assert PageType.Deleted == "Deleted"


def test_image_metadata_structure():
    """Test ImageMetadata TypedDict structure."""
    img_meta = ImageMetadata(
        Type=PageType.FrontCover,
        Bookmark="Cover Page",
        DoublePage=True,
        Image=0,
        ImageSize="1920x1080",
        ImageHeight="1080",
        ImageWidth="1920",
    )

    assert img_meta["Type"] == PageType.FrontCover
    assert img_meta["Bookmark"] == "Cover Page"
    assert img_meta["DoublePage"] is True
    assert img_meta["Image"] == 0


def test_metadata_modified_field():
    """Test metadata modified field."""
    now = datetime.now(tz=timezone.utc)
    md = Metadata(modified=now)
    assert md.modified == now


def test_series_alternative_names():
    """Test Series with alternative names."""
    alt_names = [
        AlternativeNames("Superman", language="en"),
        AlternativeNames("L'Homme d'Acier", language="fr"),
    ]
    series = Series("Superman", alternative_names=alt_names)

    assert len(series.alternative_names) == 2
    assert series.alternative_names[0].name == "Superman"
    assert series.alternative_names[1].name == "L'Homme d'Acier"


def test_metadata_comprehensive_str():
    """Test comprehensive string representation with many fields."""
    # Create a metadata object with many fields populated
    series = Series("Superman", volume=1, start_year=1938)
    publisher = Publisher("DC Comics", imprint=Basic("Vertigo"))
    prices = [Price(Decimal("2.99"), "US"), Price(Decimal("3.99"), "CA")]
    gtin = GTIN(upc=123456789012345, isbn=9781234567890)
    credits_ = [
        Credit("Jerry Siegel", [Role("Writer", primary=True)]),
        Credit("Joe Shuster", [Role("Artist")]),
    ]
    characters = [Basic(f"Character {i}") for i in range(10)]  # Test truncation
    teams = [Basic(f"Team {i}") for i in range(10)]
    genres = [Basic(f"Genre {i}") for i in range(10)]
    arcs = [Arc(f"Arc {i}", i, 3) for i in range(10)]
    locations = [Basic(f"Location {i}") for i in range(20)]
    universes = [Universe(f"Universe {i}", i, designation=f"Earth {i}") for i in range(10)]
    stories = [Basic(f"Story {i}") for i in range(10)]
    tags = [Basic(f"Tag {i}") for i in range(10)]
    weblink = [Links("https://foo.com/", primary=True)]
    info_source = [
        InfoSources("Metron", 1, primary=True),
        InfoSources("Comic Vine", 2, primary=False),
    ]
    modified = datetime.now(tz=timezone.utc)

    md = Metadata(
        info_source=info_source,
        series=series,
        issue="1",
        stories=stories,
        publisher=publisher,
        collection_title="A Long Day",
        cover_date=date(1938, 6, 1),
        store_date=date(1938, 5, 15),
        prices=prices,
        gtin=gtin,
        page_count=22,
        black_and_white=False,
        credits=credits_,
        characters=characters,
        teams=teams,
        genres=genres,
        story_arcs=arcs,
        locations=locations,
        universes=universes,
        tags=tags,
        web_link=weblink,
        comments="A" * 200,  # Long comment to test truncation
        age_rating=AgeRatings("Teen", "T"),
        notes=Notes("Metron note", "ComicRack note"),
        modified=modified,
    )

    result = str(md)

    # Test various parts of the output
    assert "Superman (v1) [1938]" in result
    assert "DC Comics (Vertigo)" in result
    assert "Cover: 1938-06-01 | Store: 1938-05-15" in result
    assert "$2.99 (US), $3.99 (CA)" in result
    assert "22 pages | Color" in result
    assert "and 5 more" in result  # Character truncation
    assert "..." in result  # Comment truncation
    assert "Writer (Primary): Jerry Siegel" in result
    assert "Artist: Joe Shuster" in result
