"""A class to represent a single comic."""

# Copyright 2012-2014 Anthony Beville
# Copyright 2019 Brian Pepple
from __future__ import annotations

import io
import logging
import os
import zipfile
from enum import Enum, auto
from pathlib import Path

import rarfile
from natsort import natsorted, ns
from PIL import Image

from darkseid.archivers import ArchiverFactory
from darkseid.archivers.zip import ZipArchiver
from darkseid.comicinfo import ComicInfo
from darkseid.metadata import Metadata
from darkseid.metroninfo import MetronInfo

logger = logging.getLogger(__name__)


class MetadataFormat(Enum):
    """
    An enumeration of metadata formats for comic books.

    This enum defines different metadata formats for comic books, including METRON_INFO and COMIC_RACK.
    """

    METRON_INFO = auto()
    COMIC_RACK = auto()
    UNKNOWN = auto()

    def __str__(self) -> str:
        """
        Returns a string representation of the object.

        Returns:
            str: A string representation of the object.
        """
        return "".join(word.capitalize() for word in self.name.split("_"))


class Comic:
    """
    The Comic class represents a comic object with methods for interacting with comic archives.
    """

    def __init__(self: Comic, path: Path | str) -> None:
        """
        Initializes a Comic object with the provided path.

        Args:
            path (Path | str): The path to the comic file.

        Returns:
            None
        """
        self._path: Path = Path(path) if isinstance(path, str) else path
        self._archiver = ArchiverFactory.create_archiver(self._path)
        self._ci_xml_filename: str = "ComicInfo.xml"  # Comic Rack format
        self._mi_xml_filename: str = "MetronInfo.xml"
        self._has_ci: bool | None = None
        self._has_mi: bool | None = None
        self._page_count: int | None = None
        self._page_list: list[str] | None = None
        self._metadata: Metadata | None = None

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

    def _reset_cache(self: Comic) -> None:
        """
        Clears the cached data.
        """

        self._has_ci = None
        self._has_mi = None
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

        return self._path.suffix in {".cbr", ".rar"}

    def is_zip(self: Comic) -> bool:
        """
        Returns a boolean indicating whether the archive is a zipfile.
        """

        return self._path.suffix in {".cbz", ".zip"}

    def is_writable(self: Comic) -> bool:
        """
        Returns a boolean indicating whether the archive is writable.

        Returns:
            bool: True if the archive is writable, False otherwise.
        """
        if not self._archiver.is_write_operation_expected():
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

    def read_metadata(self, metadata_format: MetadataFormat) -> Metadata:
        """Reads metadata based on the specified format.

        This function retrieves metadata from a comic object according to the given
        metadata format. It supports different formats and returns an instance of
        Metadata, which may be empty if the format is not recognized.

        Args:
            metadata_format (MetadataFormat): The format of the metadata to read.

        Returns:
            Metadata: The metadata retrieved from the comic, or an empty Metadata
            instance if the format is not recognized.
        """

        match metadata_format:
            case MetadataFormat.COMIC_RACK:
                return self._read_comicinfo()
            case MetadataFormat.METRON_INFO:
                return self._read_metroninfo()
            case _:
                return Metadata()

    def _read_comicinfo(self) -> Metadata:
        if self._metadata is None:
            raw_metadata = self.read_raw_ci_metadata()
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

    def _read_metroninfo(self) -> Metadata:
        if self._metadata is None:
            raw_metadata = self.read_raw_mi_metadata()
            if raw_metadata is None or raw_metadata == "":
                self._metadata = Metadata()
            else:
                self._metadata = MetronInfo().metadata_from_string(raw_metadata)

            # validate the existing page list (make sure count is correct)
            if len(self._metadata.pages) not in [0, self.get_number_of_pages()]:
                # pages array doesn't match the actual number of images we're seeing
                # in the archive, so discard the data
                self._metadata.pages = []

            if len(self._metadata.pages) == 0:
                self._metadata.set_default_page_list(self.get_number_of_pages())

        return self._metadata

    def _read_raw_metadata(self: Comic, metadata_format: MetadataFormat) -> str | None:
        if not self.has_metadata(metadata_format):
            return None

        match metadata_format:
            case MetadataFormat.COMIC_RACK:
                filename = self._ci_xml_filename
            case MetadataFormat.METRON_INFO:
                filename = self._mi_xml_filename
            case _:
                return None
        try:
            tmp_raw_metadata = self._archiver.read_file(filename)
            # Convert bytes to str. Is it safe to decode with utf-8?
            raw_metadata = tmp_raw_metadata.decode("utf-8")
        except OSError:
            logger.exception("Error reading in raw metadata!")
            raw_metadata = None
        return raw_metadata

    def read_raw_ci_metadata(self) -> str | None:
        """Retrieves raw Comic Rack metadata.

        This function calls an internal method to read raw metadata specifically
        for the Comic Rack format. It returns the metadata as a string or None if
        no metadata is available.

        Returns:
            str | None: The raw Comic Rack metadata as a string, or None if no
            metadata is found.
        """
        return self._read_raw_metadata(MetadataFormat.COMIC_RACK)

    def read_raw_mi_metadata(self) -> str | None:
        """Retrieves raw Metron Info metadata.

        This function calls an internal method to read raw metadata specifically
        for the Metron Info format. It returns the metadata as a string or None if
        no metadata is available.

        Returns:
            str | None: The raw Metron Info metadata as a string, or None if no
            metadata is found.
        """
        return self._read_raw_metadata(MetadataFormat.METRON_INFO)

    def write_metadata(self, metadata: Metadata, metadata_format: MetadataFormat) -> bool:
        """Writes metadata to a comic based on the specified format.

        This function handles the writing of metadata for different formats,
        specifically Comic Rack and Metron Info. It returns a boolean indicating
        whether the writing operation was successful.

        Args:
            metadata (Metadata): The metadata to be written.
            metadata_format (MetadataFormat): The format of the metadata to write.

        Returns:
            bool: True if the metadata was successfully written, False otherwise.
        """
        match metadata_format:
            case MetadataFormat.COMIC_RACK:
                return self._write_ci(metadata)
            case MetadataFormat.METRON_INFO:
                return self._write_mi(metadata)
            case _:
                return False

    def _write_ci(self: Comic, metadata: Metadata | None) -> bool:
        if metadata is None or not self.is_writable():
            return False
        self.apply_archive_info_to_metadata(metadata, calc_page_sizes=True)
        if raw_metadata := self.read_raw_ci_metadata():
            md_string = ComicInfo().string_from_metadata(metadata, raw_metadata.encode("utf-8"))
        else:
            md_string = ComicInfo().string_from_metadata(metadata)
        write_success = self._archiver.write_file(self._ci_xml_filename, md_string)
        if write_success:
            self._has_ci = True
        return self._successful_write(write_success, metadata)

    def _write_mi(self: Comic, metadata: Metadata | None) -> bool:
        if metadata is None or not self.is_writable():
            return False
        self.apply_archive_info_to_metadata(metadata, calc_page_sizes=False)
        if raw_metadata := self.read_raw_mi_metadata():
            md_string = MetronInfo().string_from_metadata(metadata, raw_metadata.encode("utf-8"))
        else:
            md_string = MetronInfo().string_from_metadata(metadata)
        write_success = self._archiver.write_file(self._mi_xml_filename, md_string)
        if write_success:
            self._has_mi = True
        return self._successful_write(write_success, metadata)

    def remove_metadata(self, metadata_format: MetadataFormat) -> bool:
        """Removes metadata from a comic based on the specified format.

        This function checks if the provided metadata format is supported and
        attempts to remove the corresponding metadata. It returns a boolean
        indicating whether the removal operation was successful.

        Args:
            metadata_format (MetadataFormat): The format of the metadata to remove.

        Returns:
            bool: True if the metadata was successfully removed, False if the
            format is not supported.
        """
        if metadata_format not in {
            MetadataFormat.COMIC_RACK,
            MetadataFormat.METRON_INFO,
        } or not self.has_metadata(metadata_format):
            return False

        filename_lower = (
            self._ci_xml_filename.lower()
            if metadata_format == MetadataFormat.COMIC_RACK
            else self._mi_xml_filename.lower()
        )

        metadata_files = [
            path
            for path in self._archiver.get_filename_list()
            if Path(path).name.lower() == filename_lower
        ]
        if not metadata_files:
            return False
        write_success = self._archiver.remove_files(metadata_files)
        if write_success:
            if metadata_format == MetadataFormat.METRON_INFO:
                self._has_mi = False
            elif metadata_format == MetadataFormat.COMIC_RACK:
                self._has_ci = False
        return self._successful_write(write_success, None)

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
        if write_success:
            self._has_mi = False
            self._has_ci = False
        return self._successful_write(write_success, None)

    def _successful_write(
        self: Comic,
        write_success: bool,
        metadata: Metadata | None,
    ) -> bool:
        """
        Updates the state based on the success of a write operation.

        Args:
            write_success (bool): Indicates if the write operation was successful.
            metadata (Metadata | None): The metadata object.

        Returns:
            bool: The success status of the write operation.
        """

        if write_success:
            self._metadata = metadata
        self._reset_cache()
        return write_success

    def _has_metadata_file(self: Comic, has_attr: str, filename_attr: str) -> bool:
        if getattr(self, has_attr) is None:
            if not self.seems_to_be_a_comic_archive():
                return False
            target_filename = getattr(self, filename_attr).lower()
            filenames = {Path(path).name.lower() for path in self._archiver.get_filename_list()}
            return target_filename in filenames
        return getattr(self, has_attr)

    def _has_comicinfo(self: Comic) -> bool:
        return self._has_metadata_file("_has_ci", "_ci_xml_filename")

    def _has_metroninfo(self: Comic) -> bool:
        return self._has_metadata_file("_has_mi", "_mi_xml_filename")

    def has_metadata(self, fmt: MetadataFormat) -> bool:
        """
        Checks if the archive contains metadata based on the specified format.

        This function evaluates the provided metadata format and determines if the corresponding
        metadata is present in the comic archive. It returns True if the metadata exists, and False otherwise.

        Args:
            fmt (MetadataFormat): The format of the metadata to check for.

        Returns:
            bool: True if the archive has the specified metadata, False otherwise.
        """

        match fmt:
            case MetadataFormat.COMIC_RACK:
                return self._has_comicinfo()
            case MetadataFormat.METRON_INFO:
                return self._has_metroninfo()
            case _:
                return False

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

        metadata.page_count = self.get_number_of_pages()

        if calc_page_sizes:
            for page in metadata.pages:
                if "ImageSize" not in page or "ImageHeight" not in page or "ImageWidth" not in page:
                    idx = int(page["Image"])  # type: ignore
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
                        except Image.DecompressionBombError:  # Let's skip these images
                            continue

    def export_as_zip(self: Comic, zip_filename: Path) -> bool:
        """
        Export CBR archives to CBZ format.

        Args:
            zip_filename (Path): The filename for the zip archive.

        Returns:
            bool: True if the export operation was successful, False otherwise.
        """

        if self.is_zip():
            # nothing to do, we're already a zip
            return True

        zip_archiver = ZipArchiver(zip_filename)

        return zip_archiver.copy_from_archive(self._archiver)
