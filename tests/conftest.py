from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from darkseid.metadata import (
    URLS,
    AlternativeNames,
    Arc,
    Basic,
    Metadata,
    Price,
    Publisher,
    Series,
    Universe,
)


@pytest.fixture(scope="module")
def fake_metadata() -> Metadata:
    md = Metadata()
    md.series = Series(
        name="Aquaman",
        sort_name="Aquaman",
        volume=1,
        format="Annual",
    )
    md.issue = "0"
    md.stories = [Basic("A Crash of Symbols")]
    md.publisher = Publisher("DC Comics", imprint=Basic("Vertigo", 9))
    md.cover_date = date(1994, 12, 1)
    md.story_arcs = [Arc("Final Crisis, Inc")]
    md.characters = [
        Basic("Aquaman"),
        Basic("Mera"),
        Basic("Garth"),
    ]
    md.teams = [Basic("Justice League"), Basic("Infinity, Inc")]
    md.universes = [Universe(id_=25, name="ABC", designation="Earth 25")]
    md.comments = "Just some sample metadata."
    md.black_and_white = True
    md.is_empty = False
    md.modified = datetime(
        2024, 8, 12, 12, 13, 54, 87728, tzinfo=timezone(timedelta(days=-1, seconds=72000))
    )
    md.web_link = URLS(
        "https://metron.cloud/issue/ultramega-2021-5/",
        [
            "https://metron.cloud/issue/the-body-trade-2024-1/",
            "https://metron.cloud/issue/the-body-trade-2024-2/",
        ],
    )

    return md


@pytest.fixture(scope="session")
def fake_overlay_metadata() -> Metadata:
    overlay_md = Metadata()
    overlay_md.series = Series(
        name="Aquaman",
        sort_name="Aquaman",
        volume=1,
        format="Annual",
        alternative_names=[AlternativeNames("Water Boy"), AlternativeNames("Fishy", 60, "de")],
    )
    overlay_md.cover_date = date(1994, 10, 1)
    overlay_md.reprints = [Basic("Aquaman (1964) #64", 12345)]
    overlay_md.prices = [Price(Decimal("3.99")), Price(Decimal("1.5"), "CA")]
    overlay_md.collection_title = "Just another TPB"
    return overlay_md
