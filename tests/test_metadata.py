from datetime import date
from decimal import Decimal

import pytest

from darkseid.metadata import GTIN, Credit, Metadata, Price, Role

MARTY = "Martin Egeland"
PETER = "Peter David"
WRITER = "Writer"
PENCILLER = "Penciller"
COVER = "Cover"


def test_metadata_print_str(fake_metadata):
    expect_res = """Metadata(
    is_empty = False,
    series = Series(name='Aquaman', id_=None, sort_name='Aquaman', volume=1, format='Annual'),
    issue = '0',
    stories = [Basic(name='A Crash of Symbols', id_=None)],
    publisher = Basic(name='DC Comics', id_=None),
    cover_date = datetime.date(1994, 12, 1),
    prices = [],
    genres = [],
    comments = 'Just some sample metadata.',
    black_and_white = True,
    story_arcs = [Arc(name='Final Crisis', id_=None, number=None)],
    characters = [Basic(name='Aquaman', id_=None), Basic(name='Mera', id_=None), Basic(name='Garth', id_=None)],
    teams = [Basic(name='Justice League', id_=None), Basic(name='Teen Titans', id_=None)],
    locations = [],
    credits = [],
    reprints = [],
    tags = [],
    pages = [],\n)"""  # noqa: #B950
    assert str(fake_metadata) == expect_res


def test_metadata_overlay(fake_metadata: Metadata, fake_overlay_metadata: Metadata) -> None:
    md = fake_metadata
    # Fake overlay cover date info.
    md.overlay(fake_overlay_metadata)

    assert md.series.name == "Aquaman"
    assert md.issue == "0"
    assert md.stories == fake_metadata.stories
    assert md.cover_date == date(1994, 10, 1)
    assert md.characters == fake_metadata.characters
    assert md.story_arcs == fake_metadata.story_arcs
    assert md.teams == fake_metadata.teams
    assert md.reprints == fake_overlay_metadata.reprints
    assert md.prices == fake_metadata.prices
    assert md.collection_title == fake_metadata.collection_title


def test_metadata_credits(fake_metadata: Metadata) -> None:
    result = [
        Credit(PETER, [Role(WRITER, primary=True)]),
        Credit(MARTY, [Role(PENCILLER), Role(COVER), Role("Inker")]),
    ]

    md = fake_metadata
    md.add_credit(Credit(PETER, [Role(WRITER, None, True)]))
    md.add_credit(Credit(MARTY, [Role(PENCILLER), Role(COVER)]))
    md.add_credit(Credit(MARTY, [Role("Inker")]))
    # Try to add role for creator a 2nd time
    md.add_credit(Credit(MARTY, [Role(PENCILLER)]))

    assert md.credits == result


good_prices = [
    pytest.param(
        Price(Decimal("2.50"), "CA"),
        Price(Decimal("2.5"), "CA"),
        "Valid 2 letter country code",
    ),
    pytest.param(
        Price(Decimal("1.99"), "Canada"), Price(Decimal("1.99"), "CA"), "Valid country name"
    ),
    pytest.param(Price(Decimal("3.99")), Price(Decimal("3.99"), "US"), "No country given"),
]


@pytest.mark.parametrize("price, expected, reason", good_prices)
def test_price_metadata(price, expected, reason) -> None:
    assert price == expected


bad_prices = [
    pytest.param(Decimal("2.5"), "ZZZ", "Invalid country name"),
    pytest.param(Decimal("1"), " ", "Space-only country value"),
    pytest.param(Decimal("5.99"), "ZZ", "Invalid 2 letter country code"),
]


@pytest.mark.parametrize("amount, country, reason", bad_prices)
def test_invalid_price_metadata(amount, country, reason) -> None:
    with pytest.raises(ValueError):
        Price(amount, country)


bad_gtin = [
    pytest.param(75960620237900411123446, None, "Bad UPC length"),
    pytest.param(None, 97816841565111234, "Bad ISBN"),
]

good_gtin = [
    pytest.param(75960620237900511, None, GTIN(upc=75960620237900511), "Good UPC"),
    pytest.param(None, 9781684156511, GTIN(isbn=9781684156511), "Good ISBN"),
]


@pytest.mark.parametrize("upc, isbn, reason", bad_gtin)
def test_bad_gtin(upc, isbn, reason) -> None:
    with pytest.raises(ValueError):
        GTIN(upc, isbn)


@pytest.mark.parametrize("upc, isbn, expected, reason", good_gtin)
def test_good_gtin(upc, isbn, expected, reason) -> None:
    assert GTIN(upc, isbn) == expected
