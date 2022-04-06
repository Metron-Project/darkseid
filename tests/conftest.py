import zipfile
from pathlib import Path

import py7zr
import pytest

from darkseid.comicarchive import ComicArchive
from darkseid.genericmetadata import GenericMetadata

IMG_DIR = Path("tests/test_files/Captain_Science_001")


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


@pytest.fixture()
def fake_cb7(tmp_path: Path) -> ComicArchive:

    z_file: Path = tmp_path / "Captain Science v1 #001 (2000).cb7"
    with py7zr.SevenZipFile(z_file, "w") as cb7:
        cb7.writeall(IMG_DIR)

    return ComicArchive(z_file)


@pytest.fixture()
def fake_cbz(tmp_path: Path) -> ComicArchive:

    z_file: Path = tmp_path / "Aquaman v1 #001 (of 08) (1994).cbz"
    with zipfile.ZipFile(z_file, "w") as zf:
        for p in IMG_DIR.iterdir():
            zf.write(p)

    return ComicArchive(z_file)
