from datetime import date

from darkseid.genericmetadata import CreditMetadata, GenericMetadata, RoleMetadata

MARTY = "Martin Egeland"
PETER = "Peter David"
WRITER = "Writer"
PENCILLER = "Penciller"
COVER = "Cover"


# def test_metadata_print_str(fake_metadata):
#     expect_res = (
#         "series:          SeriesMetadata(name='Aquaman', sort_name='Aquaman', "
#         "volume=1, format='Annual', id=None)\n"
#         "issue:           0\n"
#         "stories:         ['A Crash of Symbols']\n"
#         "publisher:       DC Comics\n"
#         "cover_date:      1994-12-01\n"
#         "black_and_white: True\n"
#         "story_arcs:      ['Final Crisis']\n"
#         "characters:      ['Aquaman', 'Mera', 'Garth']\n"
#         "teams:           ['Justice League', 'Teen Titans']\n"
#         "comments:        Just some sample metadata.\n"
#     )
#     assert str(fake_metadata) == expect_res


def test_metadata_overlay(
    fake_metadata: GenericMetadata, fake_overlay_metadata: GenericMetadata
) -> None:
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


def test_metadata_credits(fake_metadata: GenericMetadata) -> None:
    result = [
        CreditMetadata(PETER, [RoleMetadata(WRITER, primary=True)]),
        CreditMetadata(
            MARTY, [RoleMetadata(PENCILLER), RoleMetadata(COVER), RoleMetadata("Inker")]
        ),
    ]

    md = fake_metadata
    md.add_credit(CreditMetadata(PETER, [RoleMetadata(WRITER, None, True)]))
    md.add_credit(CreditMetadata(MARTY, [RoleMetadata(PENCILLER), RoleMetadata(COVER)]))
    md.add_credit(CreditMetadata(MARTY, [RoleMetadata("Inker")]))
    # Try to add role for creator a 2nd time
    md.add_credit(CreditMetadata(MARTY, [RoleMetadata(PENCILLER)]))

    assert md.credits == result
