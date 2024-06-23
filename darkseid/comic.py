"""A class to represent a single comic."""

# Copyright 2012-2014 Anthony Beville
# Copyright 2019 Brian Pepple
from __future__ import annotations

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
    """
    The Comic class represents a comic object with methods for interacting with comic archives.
    """

    class ArchiveType:
        """
        Types of archives supported.

        The ArchiveType class defines the types of archives supported, including zip, rar, and unknown.
        """

        zip, rar, unknown = list(range(3))  # noqa: RUF012

    def __init__(self: Comic, path: Path | str) -> None:
        """
        Initializes a Comic object with the provided path.

        Args:
            path (Path | str): The path to the comic file.

        Returns:
            None
        """
        self._path: Path | str = Path(path) if isinstance(path, str) else path
        self._ci_xml_filename: str = "ComicInfo.xml"
        self._has_md: bool | None = None
        self._page_count: int | None = None
        self._page_list: list[str] | None = None
        self._metadata: Metadata | None = None

        if self.zip_test():
            self._archive_type: int = self.ArchiveType.zip
            self._archiver = ZipArchiver(self._path)
        elif self.rar_test():
            self._archive_type: int = self.ArchiveType.rar
            self._archiver = RarArchiver(self._path)
        else:
            self._archive_type = self.ArchiveType.unknown
            self._archiver = UnknownArchiver(self._path)

    def __str__(self: Comic) -> str:
        """
        Returns the name of the comic file.
        """

        return f"{self._path.name}"

    @property
    def path(self: Comic) -> Path:
        """
        Returns the path of the comic.

        Returns:
            Path: The path of the comic.
        """

        return self._path

    @property
    def archiver(self: Comic) -> RarArchiver | ZipArchiver | UnknownArchiver:
        """
        Returns the archiver used for the comic.

        Returns:
            RarArchiver | ZipArchiver | UnknownArchiver: The archiver object used for the comic.
        """

        return self._archiver

    def reset_cache(self: Comic) -> None:
        """
        Clears the cached data.
        """

        self._has_md = None
        self._page_count = None
        self._page_list = None
        self._metadata = None

    def rar_test(self: Comic) -> bool:
        """
        Tests whether the provided path is a rar file.

        Returns:
            bool: True if the path is a rar file, False otherwise.
        """

        return rarfile.is_rarfile(self._path)

    def zip_test(self: Comic) -> bool:
        """
        Tests whether the provided path is a zipfile.

        Returns:
            bool: True if the path is a zipfile, False otherwise.
        """

        return zipfile.is_zipfile(self._path)

    def is_rar(self: Comic) -> bool:
        """
        Returns a boolean indicating whether the archive is a rarfile.
        """

        return self._archive_type == self.ArchiveType.rar

    def is_zip(self: Comic) -> bool:
        """
        Returns a boolean indicating whether the archive is a zipfile.
        """

        return self._archive_type == self.ArchiveType.zip

    def is_writable(self: Comic) -> bool:
        """
        Returns a boolean indicating whether the archive is writable.

        Returns:
            bool: True if the archive is writable, False otherwise.
        """

        if self._archive_type in [self.ArchiveType.unknown, self.ArchiveType.rar]:
            return False

        return bool(os.access(self._path, os.W_OK))

    def seems_to_be_a_comic_archive(self: Comic) -> bool:
        """
        Returns a boolean indicating whether the file is a comic archive.
        """

        return bool(
            (self.is_zip() or self.is_rar()) and (self.get_number_of_pages() > 0),
        )

    def get_page(self: Comic, index: int) -> bytes | None:
        """
        Returns an image(page) from an archive.

        Args:
            index (int): The index of the page to retrieve.

        Returns:
            bytes | None: The image data of the page, or None if an error occurs.
        """

        image_data = None

        filename = self.get_page_name(index)

        if filename is not None:
            try:
                image_data = self._archiver.read_file(filename)
            except OSError:
                logger.exception("Error reading '%s' from '%s'", filename, self._path)

        return image_data

    def get_page_name(self: Comic, index: int) -> str | None:
        """
        Returns the page name from an index.

        Args:
            index (int): The index of the page.

        Returns:
            str | None: The name of the page, or None if the index is out of range.
        """

        if index is None:
            return None

        page_list = self.get_page_name_list()

        num_pages = len(page_list)
        return None if num_pages == 0 or index >= num_pages else page_list[index]

    @staticmethod
    def is_image(name_path: Path) -> bool:
        """
        Checks if the given path is an image file based on its suffix.

        Args:
            name_path (Path): The path to check.

        Returns:
            bool: True if the path is an image file, False otherwise.
        """

        suffix_list = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        return name_path.suffix.casefold() in suffix_list and name_path.name[0] != "."

    def get_page_name_list(self: Comic, sort_list: bool = True) -> list[str]:
        """
        Returns a list of page names from an archive.

        Args:
            sort_list (bool): Indicates whether to sort the list. Default is True.

        Returns:
            list[str]: A list of page names from the archive.
        """

        if self._page_list is None:
            # get the list file names in the archive, and sort
            files = self._archiver.get_filename_list()

            # seems like some archive creators are on  Windows, and don't know
            # about case-sensitivity!
            if sort_list:
                files = natsorted(files, alg=ns.IGNORECASE)

            # make a sub-list of image files
            self._page_list = []
            for name in files:
                name_str = str(name)
                if self.is_image(Path(name_str)):
                    self._page_list.append(name_str)

        return self._page_list

    def get_number_of_pages(self: Comic) -> int:
        """
        Returns the number of pages in an archive.
        """

        if self._page_count is None:
            self._page_count = len(self.get_page_name_list())
        return self._page_count

    def read_metadata(self: Comic) -> Metadata:
        """
        Reads the metadata from an archive if present.

        Returns:
            Metadata: The metadata object.
        """

        if self._metadata is None:
            raw_metadata = self.read_raw_metadata()
            if raw_metadata is None or raw_metadata == "":
                self._metadata = Metadata()
            else:
                self._metadata = ComicInfo().metadata_from_string(raw_metadata)

            # validate the existing page list (make sure count is correct)
            if len(self._metadata.pages) not in [0, self.get_number_of_pages()]:
                # pages array doesn't match the actual number of images we're seeing
                # in the archive, so discard the data
                self._metadata.pages = []

            if len(self._metadata.pages) == 0:
                self._metadata.set_default_page_list(self.get_number_of_pages())

        return self._metadata

    def read_raw_metadata(self: Comic) -> str | None:
        """
        Reads the raw metadata from the comic file.

        Returns:
            str | None: The raw metadata as a string, or None if metadata is not available or an error occurs.
        """

        if not self.has_metadata():
            return None
        try:
            tmp_raw_metadata = self._archiver.read_file(self._ci_xml_filename)
            # Convert bytes to str. Is it safe to decode with utf-8?
            raw_metadata = tmp_raw_metadata.decode("utf-8")
        except OSError:
            logger.exception("Error reading in raw CIX!")
            raw_metadata = None
        return raw_metadata

    def write_metadata(self: Comic, metadata: Metadata | None) -> bool:
        """
        Write the metadata to the archive.

        Args:
            metadata (Metadata | None): The metadata object to write.

        Returns:
            bool: True if the write operation was successful, False otherwise.
        """

        if metadata is None or not self.is_writable():
            return False
        self.apply_archive_info_to_metadata(metadata, calc_page_sizes=True)
        if raw_cix := self.read_raw_metadata():
            md_string = ComicInfo().string_from_metadata(metadata, raw_cix.encode("utf-8"))
        else:
            md_string = ComicInfo().string_from_metadata(metadata)
        write_success = self._archiver.write_file(self._ci_xml_filename, md_string)
        return self._successful_write(write_success, True, metadata)

    def remove_metadata(self: Comic) -> bool:
        """
        Remove the metadata from the archive if present.

        Returns:
            bool: True if the metadata was successfully removed, False otherwise.
        """

        if self.has_metadata():
            write_success = self._archiver.remove_file(self._ci_xml_filename)
            return self._successful_write(write_success, False, None)
        return True

    def remove_pages(self: Comic, pages_index: list[int]) -> bool:
        """
        Remove pages from the archive.

        Args:
            pages_index (list[int]): List of page indices to remove.

        Returns:
            bool: True if the pages were successfully removed, False otherwise.
        """

        if not pages_index:
            return False
        pages_name_lst = []
        for idx in pages_index:
            page_name = self.get_page_name(idx)
            pages_name_lst.append(page_name)
        write_success = self._archiver.remove_files(pages_name_lst)
        return self._successful_write(write_success, False, None)

    def _successful_write(
        self: Comic,
        write_success: bool,
        has_md: bool,
        metadata: Metadata | None,
    ) -> bool:
        """
        Updates the state based on the success of a write operation.

        Args:
            write_success (bool): Indicates if the write operation was successful.
            has_md (bool): Indicates if metadata is present.
            metadata (Metadata | None): The metadata object.

        Returns:
            bool: The success status of the write operation.
        """

        if write_success:
            self._has_md = has_md
            self._metadata = metadata
        self.reset_cache()
        return write_success

    def has_metadata(self: Comic) -> bool:
        """
        Checks to see if the archive has metadata.

        Returns:
            bool: True if the archive has metadata, False otherwise.
        """

        if self._has_md is None:
            self._has_md = bool(
                self.seems_to_be_a_comic_archive()
                and (
                    not self.seems_to_be_a_comic_archive()
                    or self._ci_xml_filename in self._archiver.get_filename_list()
                ),
            )

        return self._has_md

    def apply_archive_info_to_metadata(
        self: Comic,
        metadata: Metadata,
        calc_page_sizes: bool = False,
    ) -> None:
        """
        Apply page information from the archive to the metadata.

        Args:
            metadata (Metadata): The metadata object to update.
            calc_page_sizes (bool): Indicates whether to calculate page sizes. Default is False.

        Returns:
            None
        """

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

    def export_as_zip(self: Comic, zip_filename: Path) -> bool:
        """
        Export CBR archives to CBZ format.

        Args:
            zip_filename (Path): The filename for the zip archive.

        Returns:
            bool: True if the export operation was successful, False otherwise.
        """

        if self._archive_type == self.ArchiveType.zip:
            # nothing to do, we're already a zip
            return True

        zip_archiver = ZipArchiver(zip_filename)

        return zip_archiver.copy_from_archive(self._archiver)
