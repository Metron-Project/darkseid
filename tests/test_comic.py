# ruff: noqa: SLF001
from pathlib import Path

import pytest

from darkseid.archivers import UnknownArchiver
from darkseid.archivers.rar import RarArchiver
from darkseid.archivers.zip import ZipArchiver
from darkseid.comic import Comic
from darkseid.metadata import Metadata


@pytest.mark.parametrize(
    ("path", "expected_archiver"),
    [
        ("/path/to/comic.cbz", ZipArchiver),
        ("/path/to/comic.cbr", RarArchiver),
        ("/path/to/comic.unknown", UnknownArchiver),
    ],
    ids=["zip file", "rar file", "unknown file"],
)
def test_comic_initialization(mocker, path, expected_archiver):
    # Arrange
    mocker.patch("zipfile.is_zipfile", return_value=path.endswith(".cbz"))
    mocker.patch("rarfile.is_rarfile", return_value=path.endswith(".cbr"))

    # Act
    comic = Comic(path)

    # Assert
    assert isinstance(comic.archiver, expected_archiver)


def test_comic_str():
    # Arrange
    path = "/path/to/comic.cbz"
    comic = Comic(path)

    # Act
    result = str(comic)

    # Assert
    assert result == "comic.cbz"


def test_comic_path():
    # Arrange
    path = "/path/to/comic.cbz"
    comic = Comic(path)

    # Act
    result = comic.path

    # Assert
    assert result == Path(path)


def test_reset_cache():
    # Arrange
    comic = Comic("/path/to/comic.cbz")
    comic._has_md = True
    comic._page_count = 10
    comic._page_list = ["page1", "page2"]
    comic._metadata = Metadata()

    # Act
    comic.reset_cache()

    # Assert
    assert comic._has_md is None
    assert comic._page_count is None
    assert comic._page_list is None
    assert comic._metadata is None


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/path/to/comic.cbr", True),
        ("/path/to/comic.cbz", False),
    ],
    ids=["rar file", "not rar file"],
)
def test_rar_test(mocker, path, expected):
    # Arrange
    mocker.patch("rarfile.is_rarfile", return_value=path.endswith(".cbr"))
    comic = Comic(path)

    # Act
    result = comic.rar_test()

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("/path/to/comic.cbz", True),
        ("/path/to/comic.cbr", False),
    ],
    ids=["zip file", "not zip file"],
)
def test_zip_test(mocker, path, expected):
    # Arrange
    mocker.patch("zipfile.is_zipfile", return_value=path.endswith(".cbz"))
    comic = Comic(path)

    # Act
    result = comic.zip_test()

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    ("archive_type", "expected"),
    [
        (Comic.ArchiveType.rar, True),
        (Comic.ArchiveType.zip, False),
    ],
    ids=["rar archive", "not rar archive"],
)
def test_is_rar(archive_type, expected):
    # Arrange
    comic = Comic("/path/to/comic.cbz")
    comic._archive_type = archive_type

    # Act
    result = comic.is_rar()

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    ("archive_type", "expected"),
    [
        (Comic.ArchiveType.zip, True),
        (Comic.ArchiveType.rar, False),
    ],
    ids=["zip archive", "not zip archive"],
)
def test_is_zip(archive_type, expected):
    # Arrange
    comic = Comic("/path/to/comic.cbz")
    comic._archive_type = archive_type

    # Act
    result = comic.is_zip()

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    ("archive_type", "expected"),
    [
        (Comic.ArchiveType.zip, True),
        (Comic.ArchiveType.rar, False),
        (Comic.ArchiveType.unknown, False),
    ],
    ids=["zip writable", "rar not writable", "unknown not writable"],
)
def test_is_writable(mocker, archive_type, expected):
    # Arrange
    path = "/path/to/comic.cbz"
    comic = Comic(path)
    comic._archive_type = archive_type
    mocker.patch("os.access", return_value=True)

    # Act
    result = comic.is_writable()

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    ("is_zip", "is_rar", "page_count", "expected"),
    [
        (True, False, 5, True),
        (False, True, 5, True),
        (False, False, 5, False),
        (True, False, 0, False),
    ],
    ids=["zip with pages", "rar with pages", "not zip or rar", "zip with no pages"],
)
def test_seems_to_be_a_comic_archive(mocker, is_zip, is_rar, page_count, expected):
    # Arrange
    comic = Comic("/path/to/comic.cbz")
    mocker.patch.object(comic, "is_zip", return_value=is_zip)
    mocker.patch.object(comic, "is_rar", return_value=is_rar)
    mocker.patch.object(comic, "get_number_of_pages", return_value=page_count)

    # Act
    result = comic.seems_to_be_a_comic_archive()

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    ("index", "expected"),
    [
        (0, b"image data"),
        (1, None),
    ],
    ids=["valid index", "invalid index"],
)
def test_get_page(mocker, index, expected):
    # Arrange
    comic = Comic("/path/to/comic.cbz")
    mocker.patch.object(comic, "get_page_name", return_value="page1.jpg" if index == 0 else None)
    mocker.patch.object(comic._archiver, "read_file", return_value=b"image data")

    # Act
    result = comic.get_page(index)

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    ("index", "expected"),
    [
        (0, "page1.jpg"),
        (1, None),
    ],
    ids=["valid index", "invalid index"],
)
def test_get_page_name(mocker, index, expected):
    # Arrange
    comic = Comic("/path/to/comic.cbz")
    mocker.patch.object(comic, "get_page_name_list", return_value=["page1.jpg"])

    # Act
    result = comic.get_page_name(index)

    # Assert
    assert result == expected


@pytest.mark.parametrize(
    ("name_path", "expected"),
    [
        (Path("image.jpg"), True),
        (Path("image.txt"), False),
        (Path(".hidden.jpg"), False),
    ],
    ids=["valid image", "invalid image", "hidden image"],
)
def test_is_image(name_path, expected):
    # Act
    result = Comic.is_image(name_path)

    # Assert
    assert result == expected


def test_get_page_name_list(mocker):
    # Arrange
    comic = Comic("/path/to/comic.cbz")
    mocker.patch.object(
        comic._archiver,
        "get_filename_list",
        return_value=["page1.jpg", "page2.png", "not_image.txt"],
    )
    mocker.patch(
        "darkseid.comic.Comic.is_image", side_effect=lambda x: x.suffix in [".jpg", ".png"]
    )

    # Act
    result = comic.get_page_name_list()

    # Assert
    assert result == ["page1.jpg", "page2.png"]


def test_get_number_of_pages(mocker):
    # Arrange
    comic = Comic("/path/to/comic.cbz")
    mocker.patch.object(comic, "get_page_name_list", return_value=["page1.jpg", "page2.png"])

    # Act
    result = comic.get_number_of_pages()

    # Assert
    assert result == 2


def test_read_metadata(mocker):
    # Arrange
    comic = Comic("/path/to/comic.cbz")
    mocker.patch.object(comic, "read_raw_metadata", return_value="<ComicInfo></ComicInfo>")
    mocker.patch("darkseid.comic.ComicInfo.metadata_from_string", return_value=Metadata())

    # Act
    result = comic.read_metadata()

    # Assert
    assert isinstance(result, Metadata)


def test_read_raw_metadata(mocker):
    # Arrange
    comic = Comic("/path/to/comic.cbz")
    mocker.patch.object(comic, "has_metadata", return_value=True)
    mocker.patch.object(comic._archiver, "read_file", return_value=b"<ComicInfo></ComicInfo>")

    # Act
    result = comic.read_raw_metadata()

    # Assert
    assert result == "<ComicInfo></ComicInfo>"


def test_write_metadata(mocker):
    # Arrange
    comic = Comic("/path/to/comic.cbz")
    metadata = Metadata()
    mocker.patch.object(comic, "is_writable", return_value=True)
    mocker.patch.object(comic, "apply_archive_info_to_metadata")
    mocker.patch.object(comic, "read_raw_metadata", return_value=None)
    mocker.patch(
        "darkseid.comic.ComicInfo.string_from_metadata", return_value="<ComicInfo></ComicInfo>"
    )
    mocker.patch.object(comic._archiver, "write_file", return_value=True)
    mocker.patch.object(comic, "_successful_write", return_value=True)

    # Act
    result = comic.write_metadata(metadata)

    # Assert
    assert result is True


def test_remove_metadata(mocker):
    # Arrange
    comic = Comic("/path/to/comic.cbz")
    mocker.patch.object(comic, "has_metadata", return_value=True)
    mocker.patch.object(comic._archiver, "remove_file", return_value=True)
    mocker.patch.object(comic, "_successful_write", return_value=True)

    # Act
    result = comic.remove_metadata()

    # Assert
    assert result is True


def test_remove_pages(mocker):
    # Arrange
    comic = Comic("/path/to/comic.cbz")
    mocker.patch.object(comic, "get_page_name", side_effect=["page1.jpg", "page2.png"])
    mocker.patch.object(comic._archiver, "remove_files", return_value=True)
    mocker.patch.object(comic, "_successful_write", return_value=True)

    # Act
    result = comic.remove_pages([0, 1])

    # Assert
    assert result is True


def test_has_metadata(mocker):
    # Arrange
    comic = Comic("/path/to/comic.cbz")
    mocker.patch.object(comic, "seems_to_be_a_comic_archive", return_value=True)
    mocker.patch.object(comic._archiver, "get_filename_list", return_value=["ComicInfo.xml"])

    # Act
    result = comic.has_metadata()

    # Assert
    assert result is True


def test_apply_archive_info_to_metadata(mocker):
    # Arrange
    comic = Comic("/path/to/comic.cbz")
    metadata = Metadata()
    mocker.patch.object(comic, "get_number_of_pages", return_value=2)
    mocker.patch.object(comic, "get_page", return_value=b"image data")
    mocker.patch("PIL.Image.open", return_value=mocker.Mock(size=(100, 200)))

    # Act
    comic.apply_archive_info_to_metadata(metadata, calc_page_sizes=True)

    # Assert
    assert metadata.page_count == 2


def test_export_as_zip(mocker):
    # Arrange
    comic = Comic("/path/to/comic.cbr")
    mocker.patch("darkseid.archivers.zip.ZipArchiver.copy_from_archive", return_value=True)

    # Act
    result = comic.export_as_zip(Path("/path/to/comic.cbz"))

    # Assert
    assert result is True
