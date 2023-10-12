"""A class to represent a single comic."""

# Copyright 2012-2014 Anthony Beville
# Copyright 2019 Brian Pepple

import io
import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Optional, cast

import rarfile
from natsort import natsorted, ns
from PIL import Image

from darkseid.comicinfo import ComicInfo
from darkseid.exceptions import RarError
from darkseid.filename import FileNameParser
from darkseid.metadata import Metadata, Series

logger = logging.getLogger(__name__)


class UnknownArchiver:
    """Unknown implementation."""

    def __init__(self: "UnknownArchiver", path: Path) -> None:
        self.path = path

    def read_file(self: "UnknownArchiver", archive_file: str) -> bytes:
        raise NotImplementedError

    def write_file(
        self: "UnknownArchiver",
        archive_file: str,  # noqa: ARG002
        data: str,  # noqa: ARG002
    ) -> bool:
        return False

    def remove_file(self: "UnknownArchiver", archive_file: str) -> bool:  # noqa: ARG002
        return False

    def remove_files(
        self: "UnknownArchiver",
        filename_lst: list[str],  # noqa: ARG002
    ) -> bool:
        return False

    def get_filename_list(self: "UnknownArchiver") -> list[str]:
        return []

    def copy_from_archive(
        self: "UnknownArchiver",
        other_archive: "UnknownArchiver",  # noqa: ARG002
    ) -> bool:
        return False


# ------------------------------------------------------------------
class RarArchiver(UnknownArchiver):
    """Rar implementation."""

    def __init__(self: "RarArchiver", path: Path) -> None:
        super().__init__(path)

    def read_file(self: "RarArchiver", archive_file: str) -> bytes:
        """Read the contents of a comic archive."""
        try:
            with rarfile.RarFile(self.path) as rf:
                data: bytes = rf.read(archive_file)
            return data
        except rarfile.RarCannotExec as e:
            raise RarError(e) from e
        except io.UnsupportedOperation:
            """If rar directory doesn't contain any data, return None."""
            return b""

    def remove_file(self: "RarArchiver", archive_file: str) -> bool:
        """Rar files are read-only, so we return False."""
        return False

    def remove_files(self: "RarArchiver", filename_lst: list[str]) -> bool:  # noqa: ARG002
        """Rar files are read-only, so we return False."""
        return False

    def write_file(self: "RarArchiver", archive_file: str, data: str) -> bool:
        """Rar files are read-only, so we return False."""
        return False

    def get_filename_list(self: "RarArchiver") -> list[str]:
        """Returns a list of the filenames in an archive."""
        try:
            with rarfile.RarFile(self.path) as rf:
                return sorted(rf.namelist())
        except rarfile.RarCannotExec as e:
            raise RarError(e) from e

    def copy_from_archive(self: "RarArchiver", other_archive: "UnknownArchiver") -> bool:
        """Rar files are read-only, so we return False."""
        return False


# ------------------------------------------------------------------


class ZipArchiver(UnknownArchiver):
    """ZIP implementation."""

    def __init__(self: "ZipArchiver", path: Path) -> None:
        super().__init__(path)

    def read_file(self: "ZipArchiver", archive_file: str) -> bytes:
        """Read the contents of a comic archive."""
        try:
            with zipfile.ZipFile(self.path, mode="r") as zf:
                return zf.read(archive_file)
        except (zipfile.BadZipfile, OSError) as e:
            logger.error(
                "Error reading zip archive [%s]: %s :: %s",
                e,
                self.path,
                archive_file,
            )
            raise OSError from e

    def remove_file(self: "ZipArchiver", archive_file: str) -> bool:
        """Returns a boolean when attempting to remove a file from an archive."""
        return self._rebuild([archive_file])

    def remove_files(self: "ZipArchiver", filename_lst: list[str]) -> bool:
        """Returns a boolean when attempting to remove a list of files from an archive."""
        return self._rebuild(filename_lst)

    def write_file(self: "ZipArchiver", archive_file: str, data: str) -> bool:
        #  At the moment, no other option but to rebuild the whole
        #  zip archive w/o the indicated file. Very sucky, but maybe
        # another solution can be found
        files = self.get_filename_list()
        if archive_file in files:
            self._rebuild([archive_file])

        try:
            # now just add the archive file as a new one
            with zipfile.ZipFile(
                self.path,
                mode="a",
                allowZip64=True,
                compression=zipfile.ZIP_DEFLATED,
            ) as zf:
                zf.writestr(archive_file, data)
            return True
        except (zipfile.BadZipfile, OSError) as e:
            logger.error(
                "Error writing zip archive [%s]: %s :: %s",
                e,
                self.path,
                archive_file,
            )
            return False

    def get_filename_list(self: "ZipArchiver") -> list[str]:
        """Returns a list of the filenames in an archive."""
        try:
            with zipfile.ZipFile(self.path, mode="r") as zf:
                return zf.namelist()
        except (zipfile.BadZipfile, OSError) as e:
            logger.error("Error listing files in zip archive [%s]: %s", e, self.path)
            return []

    def _rebuild(self: "ZipArchiver", exclude_list: list[str]) -> bool:
        """Zip helper func.

        This recompresses the zip archive, without the files in the exclude_list
        """
        try:
            with zipfile.ZipFile(
                tempfile.NamedTemporaryFile(dir=self.path.parent, delete=False),
                "w",
                allowZip64=True,
            ) as zout:
                with zipfile.ZipFile(self.path, mode="r") as zin:
                    for item in zin.infolist():
                        buffer = zin.read(item.filename)
                        if item.filename not in exclude_list:
                            zout.writestr(item, buffer)

                # replace with the new file
                self.path.unlink()
                shutil.move(cast(str, zout.filename), self.path)
            return True
        except (zipfile.BadZipfile, OSError) as e:
            logger.error("Error rebuilding zip file [%s]: %s", e, self.path)
            return False

    def copy_from_archive(self: "ZipArchiver", other_archive: UnknownArchiver) -> bool:
        """Replace the current zip with one copied from another archive."""
        try:
            with zipfile.ZipFile(self.path, mode="w", allowZip64=True) as zout:
                for filename in other_archive.get_filename_list():
                    try:
                        data = other_archive.read_file(filename)
                    except rarfile.BadRarFile:
                        # Skip any bad images in the file.
                        continue
                    if data is not None:
                        zout.writestr(filename, data)
            return True
        except (zipfile.BadZipfile, OSError) as e:
            # Remove any partial files created
            if self.path.exists():
                self.path.unlink()
            logger.warning("Error while copying to %s: %s", self.path, e)
            return False


# ------------------------------------------------------------------


class Comic:
    """Comic implementation."""

    class ArchiveType:
        """Types of archives supported. Currently .cbr and .cbz."""

        zip, rar, unknown = list(range(3))  # noqa: RUF012

    def __init__(self: "Comic", path: str) -> None:
        self.path = Path(path)

        self.ci_xml_filename = "ComicInfo.xml"
        self.has_md: Optional[bool] = None
        self.page_count: Optional[int] = None
        self.page_list: Optional[list[str]] = None
        self.metadata: Optional[Metadata] = None

        if self.zip_test():
            self.archive_type: int = self.ArchiveType.zip
            self.archiver = ZipArchiver(self.path)
        elif self.rar_test():
            self.archive_type: int = self.ArchiveType.rar
            self.archiver = RarArchiver(self.path)
        else:
            self.archive_type = self.ArchiveType.unknown
            self.archiver = UnknownArchiver(self.path)

    def __str__(self: "Comic") -> str:
        return f"{self.path.name}"

    def reset_cache(self: "Comic") -> None:
        """Clears the cached data."""
        self.has_md = None
        self.page_count = None
        self.page_list = None
        self.metadata = None

    def rar_test(self: "Comic") -> bool:
        """Test whether an archive is a rar file."""
        return rarfile.is_rarfile(self.path)

    def zip_test(self: "Comic") -> bool:
        """Tests whether an archive is a zipfile."""
        return zipfile.is_zipfile(self.path)

    def is_rar(self: "Comic") -> bool:
        """Returns a boolean whether an archive is a rarfile."""
        return self.archive_type == self.ArchiveType.rar

    def is_zip(self: "Comic") -> bool:
        """Returns a boolean whether an archive is a zipfile."""
        return self.archive_type == self.ArchiveType.zip

    def is_writable(self: "Comic") -> bool:
        """Returns a boolean whether an archive is writable."""
        if self.archive_type in [self.ArchiveType.unknown, self.ArchiveType.rar]:
            return False

        return bool(os.access(self.path, os.W_OK))

    def seems_to_be_a_comic_archive(self: "Comic") -> bool:
        """Returns a boolean whether the file is a comic archive."""
        return bool(
            (self.is_zip() or self.is_rar()) and (self.get_number_of_pages() > 0),
        )

    def get_page(self: "Comic", index: int) -> Optional[bytes]:
        """Returns an image(page) from an archive."""
        image_data = None

        filename = self.get_page_name(index)

        if filename is not None:
            try:
                image_data = self.archiver.read_file(filename)
            except OSError:
                logger.exception("Error reading '%s' from '%s'", filename, self.path)

        return image_data

    def get_page_name(self: "Comic", index: int) -> Optional[str]:
        """Returns the page name from an index."""
        if index is None:
            return None

        page_list = self.get_page_name_list()

        num_pages = len(page_list)
        return None if num_pages == 0 or index >= num_pages else page_list[index]

    @staticmethod
    def is_image(name_path: Path) -> bool:
        suffix_list = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        return name_path.suffix.casefold() in suffix_list and name_path.name[0] != "."

    def get_page_name_list(self: "Comic", sort_list: bool = True) -> list[str]:
        """Returns a list of page names from an archive."""
        if self.page_list is None:
            # get the list file names in the archive, and sort
            files = self.archiver.get_filename_list()

            # seems like some archive creators are on  Windows, and don't know
            # about case-sensitivity!
            if sort_list:
                files = natsorted(files, alg=ns.IGNORECASE)

            # make a sub-list of image files
            self.page_list = []
            for name in files:
                name_str = str(name)
                if self.is_image(Path(name_str)):
                    self.page_list.append(name_str)

        return self.page_list

    def get_number_of_pages(self: "Comic") -> int:
        """Returns the number of pages in an archive."""
        if self.page_count is None:
            self.page_count = len(self.get_page_name_list())
        return self.page_count

    def read_metadata(self: "Comic") -> Metadata:
        """Reads the metadata from an archive if present."""
        if self.metadata is None:
            raw_metadata = self.read_raw_metadata()
            if raw_metadata is None or raw_metadata == "":
                self.metadata = Metadata()
            else:
                self.metadata = ComicInfo().metadata_from_string(raw_metadata)

            # validate the existing page list (make sure count is correct)
            if len(self.metadata.pages) not in [0, self.get_number_of_pages()]:
                # pages array doesn't match the actual number of images we're seeing
                # in the archive, so discard the data
                self.metadata.pages = []

            if len(self.metadata.pages) == 0:
                self.metadata.set_default_page_list(self.get_number_of_pages())

        return self.metadata

    def read_raw_metadata(self: "Comic") -> Optional[str]:
        if not self.has_metadata():
            return None
        try:
            tmp_raw_metadata = self.archiver.read_file(self.ci_xml_filename)
            # Convert bytes to str. Is it safe to decode with utf-8?
            raw_metadata = tmp_raw_metadata.decode("utf-8")
        except OSError:
            logger.error("Error reading in raw CIX!")
            raw_metadata = None
        return raw_metadata

    def write_metadata(self: "Comic", metadata: Optional[Metadata]) -> bool:
        """Write the metadata to the archive."""
        if metadata is None or not self.is_writable():
            return False
        self.apply_archive_info_to_metadata(metadata, calc_page_sizes=True)
        if raw_cix := self.read_raw_metadata():
            md_string = ComicInfo().string_from_metadata(metadata, raw_cix.encode("utf-8"))
        else:
            md_string = ComicInfo().string_from_metadata(metadata)
        write_success = self.archiver.write_file(self.ci_xml_filename, md_string)
        return self._successful_write(write_success, True, metadata)

    def remove_metadata(self: "Comic") -> bool:
        """Remove the metadata from the archive if present."""
        if self.has_metadata():
            write_success = self.archiver.remove_file(self.ci_xml_filename)
            return self._successful_write(write_success, False, None)
        return True

    def remove_pages(self: "Comic", pages_index: list[int]) -> bool:
        """Remove page from the archive."""
        if not pages_index:
            return False
        pages_name_lst = []
        for idx in pages_index:
            page_name = self.get_page_name(idx)
            pages_name_lst.append(page_name)
        write_success = self.archiver.remove_files(pages_name_lst)
        return self._successful_write(write_success, False, None)

    def _successful_write(
        self: "Comic",
        write_success: bool,
        has_md: bool,
        metadata: Optional[Metadata],
    ) -> bool:
        if write_success:
            self.has_md = has_md
            self.metadata = metadata
        self.reset_cache()
        return write_success

    def has_metadata(self: "Comic") -> bool:
        """Checks to see if the archive has metadata."""
        if self.has_md is None:
            self.has_md = bool(
                self.seems_to_be_a_comic_archive()
                and (
                    not self.seems_to_be_a_comic_archive()
                    or self.ci_xml_filename in self.archiver.get_filename_list()
                ),
            )

        return self.has_md

    def apply_archive_info_to_metadata(
        self: "Comic",
        metadata: Metadata,
        calc_page_sizes: bool = False,
    ) -> None:
        """Apply page information from the archive to the metadata."""
        metadata.page_count = str(self.get_number_of_pages())

        if calc_page_sizes:
            for page in metadata.pages:
                if (
                    "ImageSize" not in page
                    or "ImageHeight" not in page
                    or "ImageWidth" not in page
                ):
                    idx = int(page["Image"])
                    data = self.get_page(idx)
                    if data is not None:
                        try:
                            page_image = Image.open(io.BytesIO(data))
                            width, height = page_image.size

                            page["ImageSize"] = str(len(data))
                            page["ImageHeight"] = str(height)
                            page["ImageWidth"] = str(width)
                        except OSError:
                            page["ImageSize"] = str(len(data))

    def metadata_from_filename(self: "Comic", parse_scan_info: bool = True) -> Metadata:
        """Attempts to get the metadata from the filename."""
        metadata = Metadata()

        fnp = FileNameParser()
        fnp.parse_filename(self.path)

        if fnp.issue != "":
            metadata.issue = fnp.issue
        if fnp.series != "":
            series = Series(name=fnp.series)
            if fnp.volume != "":
                series.volume = fnp.volume
            metadata.series = series
        if fnp.year != "":
            metadata.cover_date.year = fnp.year
        if fnp.issue_count != "":
            metadata.issue_count = fnp.issue_count
        if parse_scan_info and fnp.remainder != "":
            metadata.scan_info = fnp.remainder

        metadata.is_empty = False

        return metadata

    def export_as_zip(self: "Comic", zipfilename: Path) -> bool:
        """Export CBR archives to CBZ format."""
        if self.archive_type == self.ArchiveType.zip:
            # nothing to do, we're already a zip
            return True

        zip_archiver = ZipArchiver(zipfilename)

        return zip_archiver.copy_from_archive(self.archiver)
