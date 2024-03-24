"""A class to represent a single comic."""

# Copyright 2012-2014 Anthony Beville
# Copyright 2019 Brian Pepple

import io
import logging
import os
import zipfile
from pathlib import Path

import rarfile
from natsort import natsorted, ns
from PIL import Image

from darkseid.archivers import UnknownArchiver
from darkseid.archivers.rar import RarArchiver
from darkseid.archivers.zip import ZipArchiver
from darkseid.comicinfo import ComicInfo
from darkseid.metadata import Metadata

logger = logging.getLogger(__name__)


class Comic:
    """Comic implementation."""

    class ArchiveType:
        """Types of archives supported. Currently .cbr and .cbz."""

        zip, rar, unknown = list(range(3))  # noqa: RUF012

    def __init__(self: "Comic", path: Path | str) -> None:
        self.path: Path | str = Path(path) if isinstance(path, str) else path
        self.ci_xml_filename: str = "ComicInfo.xml"
        self.has_md: bool | None = None
        self.page_count: int | None = None
        self.page_list: list[str] | None = None
        self.metadata: Metadata | None = None

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

    def get_page(self: "Comic", index: int) -> bytes | None:
        """Returns an image(page) from an archive."""
        image_data = None

        filename = self.get_page_name(index)

        if filename is not None:
            try:
                image_data = self.archiver.read_file(filename)
            except OSError:
                logger.exception("Error reading '%s' from '%s'", filename, self.path)

        return image_data

    def get_page_name(self: "Comic", index: int) -> str | None:
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

    def read_raw_metadata(self: "Comic") -> str | None:
        if not self.has_metadata():
            return None
        try:
            tmp_raw_metadata = self.archiver.read_file(self.ci_xml_filename)
            # Convert bytes to str. Is it safe to decode with utf-8?
            raw_metadata = tmp_raw_metadata.decode("utf-8")
        except OSError:
            logger.exception("Error reading in raw CIX!")
            raw_metadata = None
        return raw_metadata

    def write_metadata(self: "Comic", metadata: Metadata | None) -> bool:
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
        metadata: Metadata | None,
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
                if "ImageSize" not in page or "ImageHeight" not in page or "ImageWidth" not in page:
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

    def export_as_zip(self: "Comic", zipfilename: Path) -> bool:
        """Export CBR archives to CBZ format."""
        if self.archive_type == self.ArchiveType.zip:
            # nothing to do, we're already a zip
            return True

        zip_archiver = ZipArchiver(zipfilename)

        return zip_archiver.copy_from_archive(self.archiver)
