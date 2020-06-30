from darkseid.genericmetadata import GenericMetadata


def test_metadata_print_str(fake_metadata):
    assert (
        str(fake_metadata) == "series: Aquaman\nissue:  0\ntitle:  A Crash of Symbols\n"
    )


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
        {"person": "Peter David", "primary": True, "role": "Writer"},
        {"person": "Martin Egeland", "role": "Penciller"},
        {"person": "Martin Egeland", "role": "Cover"},
    ]

    md = fake_metadata
    md.add_credit("Peter David", "Writer", primary=True)
    md.add_credit("Martin Egeland", "Penciller")
    md.add_credit("Martin Egeland", "Cover")

    assert md.credits == result
