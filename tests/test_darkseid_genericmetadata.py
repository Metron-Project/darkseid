from darkseid.genericmetadata import GenericMetadata

MARTY = "Martin Egeland"
PETER = "Peter David"
WRITER = "Writer"
PENCILLER = "Penciller"
COVER = "Cover"


def test_metadata_print_str(fake_metadata):
    expect_res = (
        "series:          Aquaman\n"
        "issue:           0\n"
        "stories:         ['A Crash of Symbols']\n"
        "publisher:       DC Comics\n"
        "year:            1994\n"
        "month:           12\n"
        "day:             1\n"
        "volume:          1\n"
        "black_and_white: True\n"
        "story_arcs:      ['Final Crisis']\n"
        "characters:      ['Aquaman', 'Mera', 'Garth']\n"
        "teams:           ['Justice League', 'Teen Titans']\n"
        "comments:        Just some sample metadata.\n"
    )
    assert str(fake_metadata) == expect_res


def test_no_metadata_print_str():
    m_data = GenericMetadata()
    assert str(m_data) == "No metadata"


def test_metadata_overlay(
    fake_metadata: GenericMetadata, fake_overlay_metadata: GenericMetadata
) -> None:
    md = fake_metadata
    # Fake overlay cover date info.
    md.overlay(fake_overlay_metadata)

    assert md.series == "Aquaman"
    assert md.issue == "0"
    assert md.stories == fake_metadata.stories
    assert md.year == "1994"
    assert md.month == "10"
    assert md.day == "1"
    assert md.characters == fake_metadata.characters
    assert md.story_arcs == fake_metadata.story_arcs
    assert md.teams == fake_metadata.teams


def test_metadata_credits(fake_metadata: GenericMetadata) -> None:
    result = [
        {"person": PETER, "role": WRITER, "primary": True},
        {"person": MARTY, "role": PENCILLER, "primary": False},
        {"person": MARTY, "role": COVER, "primary": False},
    ]

    md = fake_metadata
    md.add_credit(PETER, WRITER, True)
    md.add_credit(MARTY, PENCILLER)
    md.add_credit(MARTY, COVER)

    assert md.credits == result
