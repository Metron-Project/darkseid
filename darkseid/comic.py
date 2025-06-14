"""A class to represent a single comic."""

# Copyright 2012-2014 Anthony Beville
# Copyright 2019 Brian Pepple
from __future__ import annotations

__all__ = ["Comic", "ComicArchiveError", "ComicError", "ComicMetadataError", "MetadataFormat"]

import io
import logging
import os
import zipfile
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING

import rarfile
from natsort import natsorted, ns
from PIL import Image

from darkseid.archivers import ArchiverFactory
from darkseid.archivers.zip import ZipArchiver
from darkseid.comicinfo import ComicInfo
from darkseid.metadata import ImageMetadata, Metadata
from darkseid.metroninfo import MetronInfo

if TYPE_CHECKING:
    from darkseid.archivers.archiver import Archiver

logger = logging.getLogger(__name__)

# Constants
SUPPORTED_IMAGE_EXTENSIONS = frozenset([".jpg", ".jpeg", ".png", ".gif", ".webp"])
COMIC_RACK_FILENAME = "ComicInfo.xml"
METRON_INFO_FILENAME = "MetronInfo.xml"


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


class ComicError(Exception):
    """Base exception for comic-related errors."""


class ComicArchiveError(ComicError):
    """Exception raised when there are issues with the comic archive."""


class ComicMetadataError(ComicError):
    """Exception raised when there are issues with comic metadata."""


class Comic:
    """
    The Comic class represents a comic object with methods for interacting with comic archives.

    This class provides functionality to read, write, and manipulate comic book archives
    and their associated metadata in various formats.
    """

    # Class-level constants for better maintainability
    _RAR_EXTENSIONS = frozenset([".cbr", ".rar"])
    _ZIP_EXTENSIONS = frozenset([".cbz", ".zip"])

    def __init__(self, path: Path | str) -> None:
        """
        Initializes a Comic object with the provided path.

        Args:
            path: The path to the comic file.

        Raises:
            ComicArchiveError: If the path doesn't exist or isn't a valid archive.
        """
        self._path: Path = Path(path) if isinstance(path, str) else path

        if not self._path.exists():
            msg = f"Comic file does not exist: {self._path}"
            raise ComicArchiveError(msg)

        try:
            self._archiver: Archiver = ArchiverFactory.create_archiver(self._path)
        except Exception as e:
            msg = f"Failed to create archiver for {self._path}: {e}"
            raise ComicArchiveError(msg) from e

        # Use constants for filenames
        self._ci_xml_filename: str = COMIC_RACK_FILENAME
        self._mi_xml_filename: str = METRON_INFO_FILENAME

        # Cache attributes
        self._has_ci: bool | None = None
        self._has_mi: bool | None = None
        self._page_count: int | None = None
        self._page_list: list[str] | None = None
        self._metadata: Metadata | None = None

    def __str__(self) -> str:
        """Returns the name of the comic file."""
        return self._path.name

    def __repr__(self) -> str:
        """Returns a detailed string representation of the Comic object."""
        return f"Comic(path={self._path!r}, pages={self.get_number_of_pages()})"

    @property
    def path(self) -> Path:
        """
        Returns the path of the comic.

        Returns:
            The path of the comic.
        """
        return self._path

    @property
    def name(self) -> str:
        """Returns the name of the comic file."""
        return self._path.name

    @property
    def size(self) -> int:
        """Returns the size of the comic file in bytes."""
        return self._path.stat().st_size

    def _reset_cache(self) -> None:
        """Clears the cached data."""
        self._has_ci = None
        self._has_mi = None
        self._page_count = None
        self._page_list = None
        self._metadata = None

    def _validate_page_index(self, index: int) -> None:
        """
        Validates that the page index is within valid range.

        Args:
            index: The page index to validate.

        Raises:
            ValueError: If the index is out of range.
        """
        if index < 0:
            msg = f"Page index cannot be negative: {index}"
            raise ValueError(msg)

        page_count = self.get_number_of_pages()
        if index >= page_count:
            msg = f"Page index {index} is out of range (0-{page_count - 1})"
            raise ValueError(msg)

    def is_archive_valid(self) -> bool:
        """
        Tests whether the archive is valid (either RAR or ZIP).

        Returns:
            True if the archive is valid, False otherwise.
        """
        try:
            return self.rar_test() or self.zip_test()
        except Exception:
            return False

    def rar_test(self) -> bool:
        """
        Tests whether the provided path is a rar file.

        Returns:
            True if the path is a rar file, False otherwise.
        """
        try:
            return rarfile.is_rarfile(self._path)
        except Exception:
            return False

    def zip_test(self) -> bool:
        """
        Tests whether the provided path is a zipfile.

        Returns:
            True if the path is a zipfile, False otherwise.
        """
        try:
            return zipfile.is_zipfile(self._path)
        except Exception:
            return False

    def is_rar(self) -> bool:
        """Returns a boolean indicating whether the archive is a rarfile."""
        return self._path.suffix.lower() in self._RAR_EXTENSIONS

    def is_zip(self) -> bool:
        """Returns a boolean indicating whether the archive is a zipfile."""
        return self._path.suffix.lower() in self._ZIP_EXTENSIONS

    def is_writable(self) -> bool:
        """
        Returns a boolean indicating whether the archive is writable.

        Returns:
            True if the archive is writable, False otherwise.
        """
        if not self._archiver.is_write_operation_expected():
            return False

        return os.access(self._path, os.W_OK)

    def seems_to_be_a_comic_archive(self) -> bool:
        """
        Returns a boolean indicating whether the file is a comic archive.

        A file is considered a comic archive if it's either a ZIP or RAR file
        and contains at least one page.
        """
        return (self.is_zip() or self.is_rar()) and (self.get_number_of_pages() > 0)

    def get_page(self, index: int) -> bytes | None:
        """
        Returns an image(page) from an archive.

        Args:
            index: The index of the page to retrieve.

        Returns:
            The image data of the page, or None if an error occurs.

        Raises:
            ValueError: If the index is out of range.
        """
        try:
            self._validate_page_index(index)
        except ValueError:
            logger.warning("Invalid page index %d for comic %s", index, self._path)
            return None

        filename = self.get_page_name(index)
        if filename is None:
            return None

        try:
            return self._archiver.read_file(filename)
        except OSError:
            logger.exception("Error reading '%s' from '%s'", filename, self._path)
            return None

    def get_page_name(self, index: int) -> str | None:
        """
        Returns the page name from an index.

        Args:
            index: The index of the page.

        Returns:
            The name of the page, or None if the index is out of range.
        """
        if index < 0:
            return None

        page_list = self.get_page_name_list()
        return page_list[index] if index < len(page_list) else None

    @staticmethod
    def is_image(name_path: Path) -> bool:
        """
        Checks if the given path is an image file based on its suffix.

        Args:
            name_path: The path to check.

        Returns:
            True if the path is an image file, False otherwise.
        """
        return (
            name_path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
            and not name_path.name.startswith(".")
        )

    def get_page_name_list(self, sort_list: bool = True) -> list[str]:
        """
        Returns a list of page names from an archive.

        Args:
            sort_list: Indicates whether to sort the list. Default is True.

        Returns:
            A list of page names from the archive.
        """
        if self._page_list is not None:
            return self._page_list

        try:
            # Get the list of file names in the archive
            files = self._archiver.get_filename_list()

            # Sort files if requested (case-insensitive natural sort)
            if sort_list:
                files = natsorted(files, alg=ns.IGNORECASE)

            # Filter for image files only
            self._page_list = [str(name) for name in files if self.is_image(Path(str(name)))]

        except Exception:
            logger.exception("Error getting page list from %s", self._path)
            self._page_list = []

        return self._page_list

    def get_number_of_pages(self) -> int:
        """Returns the number of pages in an archive."""
        if self._page_count is None:
            self._page_count = len(self.get_page_name_list())
        return self._page_count

    def read_metadata(self, metadata_format: MetadataFormat) -> Metadata:
        """
        Reads metadata based on the specified format.

        Args:
            metadata_format: The format of the metadata to read.

        Returns:
            The metadata retrieved from the comic, or an empty Metadata
            instance if the format is not recognized.
        """
        match metadata_format:
            case MetadataFormat.COMIC_RACK:
                return self._read_comicinfo()
            case MetadataFormat.METRON_INFO:
                return self._read_metroninfo()
            case _:
                logger.warning("Unknown metadata format: %s", metadata_format)
                return Metadata()

    def _read_comicinfo(self) -> Metadata:
        """Reads ComicInfo metadata from the archive."""
        if self._metadata is not None:
            return self._metadata

        if raw_metadata := self.read_raw_ci_metadata():
            try:
                self._metadata = ComicInfo().metadata_from_string(raw_metadata)
            except Exception:
                logger.exception("Error parsing ComicInfo metadata from %s", self._path)
                self._metadata = Metadata()
        else:
            self._metadata = Metadata()
        self._validate_and_fix_page_list()
        return self._metadata

    def _read_metroninfo(self) -> Metadata:
        """Reads MetronInfo metadata from the archive."""
        if self._metadata is not None:
            return self._metadata

        if raw_metadata := self.read_raw_mi_metadata():
            try:
                self._metadata = MetronInfo().metadata_from_string(raw_metadata)
            except Exception:
                logger.exception("Error parsing MetronInfo metadata from %s", self._path)
                self._metadata = Metadata()
        else:
            self._metadata = Metadata()
        self._validate_and_fix_page_list()
        return self._metadata

    def _validate_and_fix_page_list(self) -> None:
        """Validates and fixes the page list in metadata."""
        if self._metadata is None:
            return

        actual_page_count = self.get_number_of_pages()
        metadata_page_count = len(self._metadata.pages)

        # If page counts don't match, reset the page list
        if metadata_page_count not in (0, actual_page_count):
            logger.warning(
                "Page count mismatch in %s: metadata has %d pages, archive has %d",
                self._path,
                metadata_page_count,
                actual_page_count,
            )
            self._metadata.pages = []

        # Set default page list if empty
        if not self._metadata.pages:
            self._metadata.set_default_page_list(actual_page_count)

    def _read_raw_metadata(self, metadata_format: MetadataFormat) -> str | None:
        """
        Reads raw metadata from the archive.

        Args:
            metadata_format: The format of metadata to read.

        Returns:
            The raw metadata as a string, or None if not found.
        """
        if not self.has_metadata(metadata_format):
            return None

        filename = self._get_metadata_filename(metadata_format)
        if filename is None:
            return None

        try:
            raw_bytes = self._archiver.read_file(filename)
            return raw_bytes.decode("utf-8")
        except (OSError, UnicodeDecodeError):
            logger.exception("Error reading raw metadata from %s", self._path)
            return None

    def _get_metadata_filename(self, metadata_format: MetadataFormat) -> str | None:
        """Gets the filename for the specified metadata format."""
        match metadata_format:
            case MetadataFormat.COMIC_RACK:
                return self._ci_xml_filename
            case MetadataFormat.METRON_INFO:
                return self._mi_xml_filename
            case _:
                return None

    def read_raw_ci_metadata(self) -> str | None:
        """
        Retrieves raw Comic Rack metadata.

        Returns:
            The raw Comic Rack metadata as a string, or None if no metadata is found.
        """
        return self._read_raw_metadata(MetadataFormat.COMIC_RACK)

    def read_raw_mi_metadata(self) -> str | None:
        """
        Retrieves raw Metron Info metadata.

        Returns:
            The raw Metron Info metadata as a string, or None if no metadata is found.
        """
        return self._read_raw_metadata(MetadataFormat.METRON_INFO)

    def write_metadata(self, metadata: Metadata, metadata_format: MetadataFormat) -> bool:
        """
        Writes metadata to a comic based on the specified format.

        Args:
            metadata: The metadata to be written.
            metadata_format: The format of the metadata to write.

        Returns:
            True if the metadata was successfully written, False otherwise.

        Raises:
            ComicMetadataError: If the metadata format is not supported.
        """
        if not self.is_writable():
            logger.warning("Cannot write metadata to read-only archive: %s", self._path)
            return False

        match metadata_format:
            case MetadataFormat.COMIC_RACK:
                return self._write_ci(metadata)
            case MetadataFormat.METRON_INFO:
                return self._write_mi(metadata)
            case _:
                msg = f"Unsupported metadata format: {metadata_format}"
                raise ComicMetadataError(msg)

    def _write_ci(self, metadata: Metadata | None) -> bool:
        """Writes ComicInfo metadata to the archive."""
        if metadata is None:
            return False

        try:
            self.apply_archive_info_to_metadata(metadata, calc_page_sizes=True)

            # Get existing raw metadata if available
            raw_metadata = self.read_raw_ci_metadata()
            raw_bytes = raw_metadata.encode("utf-8") if raw_metadata else None

            md_string = ComicInfo().string_from_metadata(metadata, raw_bytes)
            write_success = self._archiver.write_file(self._ci_xml_filename, md_string)

            if write_success:
                self._has_ci = True

            return self._successful_write(write_success, metadata)

        except Exception:
            logger.exception("Error writing ComicInfo metadata to %s", self._path)
            return False

    def _write_mi(self, metadata: Metadata | None) -> bool:
        """Writes MetronInfo metadata to the archive."""
        if metadata is None:
            return False

        try:
            self.apply_archive_info_to_metadata(metadata, calc_page_sizes=False)

            # Get existing raw metadata if available
            raw_metadata = self.read_raw_mi_metadata()
            raw_bytes = raw_metadata.encode("utf-8") if raw_metadata else None

            md_string = MetronInfo().string_from_metadata(metadata, raw_bytes)
            write_success = self._archiver.write_file(self._mi_xml_filename, md_string)

            if write_success:
                self._has_mi = True

            return self._successful_write(write_success, metadata)

        except Exception:
            logger.exception("Error writing MetronInfo metadata to %s", self._path)
            return False

    def remove_metadata(self, metadata_format: MetadataFormat) -> bool:
        """
        Removes metadata from a comic based on the specified format.

        Args:
            metadata_format: The format of the metadata to remove.

        Returns:
            True if the metadata was successfully removed, False otherwise.
        """
        supported_formats = {MetadataFormat.COMIC_RACK, MetadataFormat.METRON_INFO}

        if metadata_format not in supported_formats:
            logger.warning("Unsupported metadata format for removal: %s", metadata_format)
            return False

        if not self.has_metadata(metadata_format):
            logger.info("No %s metadata found in %s", metadata_format, self._path)
            return True  # Already removed, consider it success

        filename = self._get_metadata_filename(metadata_format)
        if filename is None:
            return False

        try:
            # Find all metadata files (case-insensitive)
            filename_lower = filename.lower()
            metadata_files = [
                path
                for path in self._archiver.get_filename_list()
                if Path(str(path)).name.lower() == filename_lower
            ]

            if not metadata_files:
                return True  # No files to remove

            write_success = self._archiver.remove_files(metadata_files)

            if write_success:
                # Update cache flags
                if metadata_format == MetadataFormat.METRON_INFO:
                    self._has_mi = False
                elif metadata_format == MetadataFormat.COMIC_RACK:
                    self._has_ci = False

            return self._successful_write(write_success, None)

        except Exception:
            logger.exception("Error removing %s metadata from %s", metadata_format, self._path)
            return False

    def remove_pages(self, pages_index: list[int]) -> bool:
        """
        Remove pages from the archive.

        Args:
            pages_index: List of page indices to remove.

        Returns:
            True if the pages were successfully removed, False otherwise.
        """
        if not pages_index:
            logger.warning("No pages specified for removal")
            return False

        if not self.is_writable():
            logger.warning("Cannot remove pages from read-only archive: %s", self._path)
            return False

        try:
            # Validate all indices first
            for idx in pages_index:
                self._validate_page_index(idx)

            # Get page names to remove
            pages_to_remove = []
            for idx in pages_index:
                page_name = self.get_page_name(idx)
                if page_name:
                    pages_to_remove.append(page_name)

            if not pages_to_remove:
                logger.warning("No valid pages found for removal")
                return False

            write_success = self._archiver.remove_files(pages_to_remove)

            if write_success:
                # Invalidate metadata cache since page structure changed
                self._has_mi = False
                self._has_ci = False

            return self._successful_write(write_success, None)

        except ValueError:
            logger.exception("Invalid page index for removal")
            return False
        except Exception:
            logger.exception("Error removing pages from %s", self._path)
            return False

    def _successful_write(self, write_success: bool, metadata: Metadata | None) -> bool:
        """
        Updates the state based on the success of a write operation.

        Args:
            write_success: Indicates if the write operation was successful.
            metadata: The metadata object.

        Returns:
            The success status of the write operation.
        """
        if write_success:
            self._metadata = metadata
        self._reset_cache()
        return write_success

    def _has_metadata_file(self, has_attr: str, filename_attr: str) -> bool:
        """
        Checks if a metadata file exists in the archive.

        Args:
            has_attr: The attribute name for the cached result.
            filename_attr: The attribute name for the filename.

        Returns:
            True if the metadata file exists, False otherwise.
        """
        cached_result = getattr(self, has_attr)
        if cached_result is not None:
            return cached_result

        if not self.seems_to_be_a_comic_archive():
            setattr(self, has_attr, False)
            return False

        try:
            target_filename = getattr(self, filename_attr).lower()
            filenames = {
                Path(str(path)).name.lower() for path in self._archiver.get_filename_list()
            }
            result = target_filename in filenames
            setattr(self, has_attr, result)
        except Exception:
            logger.exception("Error checking for metadata file in %s", self._path)
            setattr(self, has_attr, False)
            return False
        else:
            return result

    def _has_comicinfo(self) -> bool:
        """Checks if the archive contains ComicInfo metadata."""
        return self._has_metadata_file("_has_ci", "_ci_xml_filename")

    def _has_metroninfo(self) -> bool:
        """Checks if the archive contains MetronInfo metadata."""
        return self._has_metadata_file("_has_mi", "_mi_xml_filename")

    def has_metadata(self, fmt: MetadataFormat) -> bool:
        """
        Checks if the archive contains metadata based on the specified format.

        Args:
            fmt: The format of the metadata to check for.

        Returns:
            True if the archive has the specified metadata, False otherwise.
        """
        match fmt:
            case MetadataFormat.COMIC_RACK:
                return self._has_comicinfo()
            case MetadataFormat.METRON_INFO:
                return self._has_metroninfo()
            case _:
                return False

    def apply_archive_info_to_metadata(
        self,
        metadata: Metadata,
        calc_page_sizes: bool = False,
    ) -> None:
        """
        Apply page information from the archive to the metadata.

        Args:
            metadata: The metadata object to update.
            calc_page_sizes: Indicates whether to calculate page sizes. Default is False.
        """
        metadata.page_count = self.get_number_of_pages()

        if not calc_page_sizes:
            return

        for page in metadata.pages:
            if self._should_calculate_page_info(page):
                try:
                    self._calculate_page_info(page)
                except Exception:
                    logger.exception(
                        "Error calculating page info for page %s", page.get("Image", "unknown")
                    )
                    continue

    @staticmethod
    def _should_calculate_page_info(page: ImageMetadata) -> bool:
        """Determines if page information should be calculated."""
        required_keys = {"ImageSize", "ImageHeight", "ImageWidth"}
        return any(key not in page for key in required_keys)

    def _calculate_page_info(self, page: ImageMetadata) -> None:
        """Calculates and sets page information."""
        try:
            idx = int(page["Image"])
        except (KeyError, ValueError, TypeError):
            logger.warning("Invalid page index in metadata: %s", page.get("Image"))
            return

        data = self.get_page(idx)
        if data is None:
            return

        # Always set the image size
        page["ImageSize"] = str(len(data))

        try:
            # Try to get image dimensions
            with Image.open(io.BytesIO(data)) as page_image:
                width, height = page_image.size
                page["ImageHeight"] = str(height)
                page["ImageWidth"] = str(width)
        except (OSError, Image.DecompressionBombError):
            # If we can't get dimensions, at least we have the size
            logger.debug("Could not get image dimensions for page %d", idx)

    def export_as_zip(self, zip_filename: Path) -> bool:
        """
        Export comic archive to CBZ format.

        Args:
            zip_filename: The filename for the zip archive.

        Returns:
            True if the export operation was successful, False otherwise.
        """
        if self.is_zip():
            logger.info("Archive %s is already in ZIP format", self._path)
            return True

        try:
            zip_archiver = ZipArchiver(zip_filename)
            return zip_archiver.copy_from_archive(self._archiver)
        except Exception:
            logger.exception("Error exporting %s to ZIP format", self._path)
            return False

    def get_metadata_formats(self) -> set[MetadataFormat]:
        """
        Returns the set of metadata formats present in the archive.

        Returns:
            A set of MetadataFormat enums representing the available metadata.
        """
        formats = set()

        if self.has_metadata(MetadataFormat.COMIC_RACK):
            formats.add(MetadataFormat.COMIC_RACK)

        if self.has_metadata(MetadataFormat.METRON_INFO):
            formats.add(MetadataFormat.METRON_INFO)

        return formats

    def is_valid_comic(self) -> bool:
        """
        Performs a comprehensive validation of the comic archive.

        Returns:
            True if the comic archive is valid, False otherwise.
        """
        try:
            return (
                self._path.exists()
                and self.is_archive_valid()
                and self.seems_to_be_a_comic_archive()
            )
        except Exception:
            logger.exception("Error validating comic %s", self._path)
            return False
