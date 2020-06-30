import pytest

from darkseid.genericmetadata import GenericMetadata


@pytest.fixture(scope="session")
def fake_metadata():
    meta_data = GenericMetadata()
    meta_data.series = "Aquaman"
    meta_data.issue = "0"
    meta_data.title = "A Crash of Symbols"
    meta_data.is_empty = False

    return meta_data


@pytest.fixture(scope="session")
def fake_overlay_metadata():
    overlay_md = GenericMetadata()
    overlay_md.year = "1994"
    overlay_md.month = "10"
    overlay_md.day = "1"

    return overlay_md
