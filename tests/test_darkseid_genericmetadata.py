from darkseid.genericmetadata import GenericMetadata

MARTY = "Martin Egeland"
PETER = "Peter David"
WRITER = "Writer"
PENCILLER = "Penciller"
COVER = "Cover"


def test_metadata_print_str(fake_metadata):
    assert str(fake_metadata) == "series: Aquaman\nissue:  0\ntitle:  A Crash of Symbols\n"


def test_no_metadata_print_str():
    m_data = GenericMetadata()
    assert str(m_data) == "No metadata"


def test_metadata_overlay(fake_metadata, fake_overlay_metadata):
    md = fake_metadata
    md.overlay(fake_overlay_metadata)

    assert md.series == "Aquaman"
    assert md.issue == "0"
    assert md.title == "A Crash of Symbols"
    assert md.year == "1994"
    assert md.month == "10"
    assert md.day == "1"


def test_metadata_credits(fake_metadata):
    result = [
        {"person": PETER, "role": WRITER},
        {"person": MARTY, "role": PENCILLER},
        {"person": MARTY, "role": COVER},
    ]

    md = fake_metadata
    md.add_credit(PETER, WRITER)
    md.add_credit(MARTY, PENCILLER)
    md.add_credit(MARTY, COVER)

    assert md.credits == result
