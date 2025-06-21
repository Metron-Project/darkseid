"""A class to represent a single comic."""

# Copyright 2012-2014 Anthony Beville
# Copyright 2019 Brian Pepple
from __future__ import annotations

__all__ = ["Comic", "ComicArchiveError", "ComicError", "ComicMetadataError", "MetadataFormat"]

import io
import logging
import os
import zipfile
from contextlib import suppress
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Final

import rarfile
from natsort import natsorted, ns
from PIL import Image

from darkseid.archivers import ArchiverFactory, ArchiverReadError
from darkseid.archivers.zip import ZipArchiver
from darkseid.comicinfo import ComicInfo
from darkseid.metadata import ImageMetadata, Metadata
from darkseid.metroninfo import MetronInfo
from darkseid.validate import SchemaVersion, ValidateMetadata, ValidationError

if TYPE_CHECKING:
    from darkseid.archivers.archiver import Archiver

logger = logging.getLogger(__name__)

# Constants
SUPPORTED_IMAGE_EXTENSIONS: Final[frozenset[str]] = frozenset(
    [".jpg", ".jpeg", ".png", ".gif", ".webp"]
)
COMIC_RACK_FILENAME: Final[str] = "ComicInfo.xml"
METRON_INFO_FILENAME: Final[str] = "MetronInfo.xml"


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
    _RAR_EXTENSIONS: Final[frozenset[str]] = frozenset([".cbr", ".rar"])
    _ZIP_EXTENSIONS: Final[frozenset[str]] = frozenset([".cbz", ".zip"])

    def __init__(self, path: Path | str) -> None:
        """
        Initializes a Comic object with the provided path.

        Args:
            path: The path to the comic file.

        Raises:
            ComicArchiveError: If the path doesn't exist or isn't a valid archive.
        """
        self._path: Path = Path(path) if isinstance(path, str) else path
        self._validate_path()
        self._initialize_archiver()
        self._initialize_attributes()

    def _validate_path(self) -> None:
        """Validate that the comic file path exists."""
        if not self._path.exists():
            msg = f"Comic file does not exist: {self._path}"
            raise ComicArchiveError(msg)

    def _initialize_archiver(self) -> None:
        """Initialize the archiver for the comic file."""
        try:
            self._archiver: Archiver = ArchiverFactory.create_archiver(self._path)
        except Exception as e:
            msg = f"Failed to create archiver for {self._path}: {e}"
            raise ComicArchiveError(msg) from e

    def _initialize_attributes(self) -> None:
        """Initialize instance attributes."""
        # Use constants for filenames
        self._ci_xml_filename: str = COMIC_RACK_FILENAME
        self._mi_xml_filename: str = METRON_INFO_FILENAME

        # Cache attributes - Initialize as None for lazy loading
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

    def __eq__(self, other: object) -> bool:
        """Check if two Comic objects are equal based on their paths."""
        if not isinstance(other, Comic):
            return NotImplemented
        return self._path == other._path

    def __hash__(self) -> int:
        """Make Comic objects hashable based on their path."""
        return hash(self._path)

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
        with suppress(Exception):
            return self.rar_test() or self.zip_test()
        return False

    def rar_test(self) -> bool:
        """
        Tests whether the provided path is a rar file.

        Returns:
            True if the path is a rar file, False otherwise.
        """
        with suppress(Exception):
            return rarfile.is_rarfile(self._path)
        return False

    def zip_test(self) -> bool:
        """
        Tests whether the provided path is a zipfile.

        Returns:
            True if the path is a zipfile, False otherwise.
        """
        with suppress(Exception):
            return zipfile.is_zipfile(self._path)
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
        return self._archiver.is_write_operation_expected() and os.access(self._path, os.W_OK)

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
        """
        try:
            self._validate_page_index(index)
        except ValueError:
            logger.warning("Invalid page index %d for comic %s", index, self._path)
            return None

        filename = self.get_page_name(index)
        return None if filename is None else self._read_file_safely(filename)

    def _read_file_safely(self, filename: str) -> bytes | None:
        """
        Safely read a file from the archive.

        Args:
            filename: The name of the file to read.

        Returns:
            The file data, or None if an error occurs.
        """
        try:
            return self._archiver.read_file(filename)
        except (OSError, ArchiverReadError):
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
        Read metadata based on the specified format.

        Args:
            metadata_format: The format of the metadata to read.

        Returns:
            The metadata retrieved from the comic, or an empty Metadata
            instance if the format is not recognized.
        """
        metadata_readers = {
            MetadataFormat.COMIC_RACK: self._read_comicinfo,
            MetadataFormat.METRON_INFO: self._read_metroninfo,
        }

        reader = metadata_readers.get(metadata_format)
        if reader is None:
            logger.warning("Unknown metadata format: %s", metadata_format)
            return Metadata()

        return reader()

    def _read_comicinfo(self) -> Metadata:
        """Read ComicInfo metadata from the archive."""
        if self._metadata is not None:
            return self._metadata

        self._metadata = self._parse_metadata(self.read_raw_ci_metadata(), ComicInfo())
        self._validate_and_fix_page_list()
        return self._metadata

    def _read_metroninfo(self) -> Metadata:
        """Read MetronInfo metadata from the archive."""
        if self._metadata is not None:
            return self._metadata

        self._metadata = self._parse_metadata(self.read_raw_mi_metadata(), MetronInfo())
        self._validate_and_fix_page_list()
        return self._metadata

    def _parse_metadata(self, raw_metadata: str | None, parser) -> Metadata:
        """
        Parse raw metadata using the provided parser.

        Args:
            raw_metadata: The raw metadata string.
            parser: The metadata parser instance.

        Returns:
            Parsed Metadata object or empty Metadata if parsing fails.
        """
        if not raw_metadata:
            return Metadata()

        try:
            return parser.metadata_from_string(raw_metadata)
        except Exception:
            logger.exception("Error parsing metadata from %s", self._path)
            return Metadata()

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
        except ArchiverReadError:
            logger.exception("Error reading raw metadata from %s", self._path)
            return None
        except UnicodeDecodeError:
            logger.exception("Error decoding metadata from %s", self._path)
            return None

    def _get_metadata_filename(self, metadata_format: MetadataFormat) -> str | None:
        """Get the filename for the specified metadata format."""
        filename_map = {
            MetadataFormat.COMIC_RACK: self._ci_xml_filename,
            MetadataFormat.METRON_INFO: self._mi_xml_filename,
        }
        return filename_map.get(metadata_format)

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
        Write metadata to a comic based on the specified format.

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

        writers = {
            MetadataFormat.COMIC_RACK: self._write_ci,
            MetadataFormat.METRON_INFO: self._write_mi,
        }

        writer = writers.get(metadata_format)
        if writer is None:
            msg = f"Unsupported metadata format: {metadata_format}"
            raise ComicMetadataError(msg)

        return writer(metadata)  # type: ignore

    def _write_ci(self, metadata: Metadata | None) -> bool:
        """Write ComicInfo metadata to the archive."""
        if metadata is None:
            return False

        return self._write_metadata_format(
            metadata,
            ComicInfo(),
            self._ci_xml_filename,
            self.read_raw_ci_metadata(),
            calc_page_sizes=True,
        )

    def _write_mi(self, metadata: Metadata | None) -> bool:
        """Write MetronInfo metadata to the archive."""
        if metadata is None:
            return False

        return self._write_metadata_format(
            metadata,
            MetronInfo(),
            self._mi_xml_filename,
            self.read_raw_mi_metadata(),
            calc_page_sizes=False,
        )

    def _write_metadata_format(
        self,
        metadata: Metadata,
        formatter,
        filename: str,
        raw_metadata: str | None,
        calc_page_sizes: bool = False,
    ) -> bool:
        """
        Write metadata in a specific format.

        Args:
            metadata: The metadata to write.
            formatter: The metadata formatter instance.
            filename: The filename to write to.
            raw_metadata: Existing raw metadata string.
            calc_page_sizes: Whether to calculate page sizes.

        Returns:
            True if successful, False otherwise.
        """
        try:
            self.apply_archive_info_to_metadata(metadata, calc_page_sizes=calc_page_sizes)

            raw_bytes = raw_metadata.encode("utf-8") if raw_metadata else None
            md_string = formatter.string_from_metadata(metadata, raw_bytes)
            write_success = self._archiver.write_file(filename, md_string)

            if write_success:
                # Update appropriate cache flag
                if filename == self._ci_xml_filename:
                    self._has_ci = True
                elif filename == self._mi_xml_filename:
                    self._has_mi = True

            return self._successful_write(write_success, metadata)

        except Exception:
            logger.exception("Error writing metadata to %s", self._path)
            return False

    def remove_metadata(self, metadata_format: MetadataFormat) -> bool:
        """
        Remove metadata from a comic based on the specified format.

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

        return self._remove_metadata_files(metadata_format)

    def _remove_metadata_files(self, metadata_format: MetadataFormat) -> bool:
        """
        Remove metadata files from the archive.

        Args:
            metadata_format: The format of metadata to remove.

        Returns:
            True if successful, False otherwise.
        """
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

        return self._remove_pages_by_index(pages_index)

    def _remove_pages_by_index(self, pages_index: list[int]) -> bool:
        """
        Remove pages by their indices.

        Args:
            pages_index: List of page indices to remove.

        Returns:
            True if successful, False otherwise.
        """
        try:
            # Validate all indices first
            for idx in pages_index:
                self._validate_page_index(idx)

            # Get page names to remove
            pages_to_remove = [
                page_name
                for idx in pages_index
                if (page_name := self.get_page_name(idx)) is not None
            ]

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
        Check if a metadata file exists in the archive.

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

        return self._check_metadata_file_exists(has_attr, filename_attr)

    def _check_metadata_file_exists(self, has_attr: str, filename_attr: str) -> bool:
        """
        Check if metadata file exists in archive.

        Args:
            has_attr: The attribute name for caching the result.
            filename_attr: The attribute name for the filename.

        Returns:
            True if file exists, False otherwise.
        """
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
        Check if the archive contains metadata based on the specified format.

        Args:
            fmt: The format of the metadata to check for.

        Returns:
            True if the archive has the specified metadata, False otherwise.
        """
        metadata_checkers = {
            MetadataFormat.COMIC_RACK: self._has_comicinfo,
            MetadataFormat.METRON_INFO: self._has_metroninfo,
        }

        checker = metadata_checkers.get(fmt)
        return checker() if checker else False

    def apply_archive_info_to_metadata(
        self,
        metadata: Metadata,
        calc_page_sizes: bool = False,
    ) -> None:
        """
        Apply page information from the archive to the metadata.

        Args:
            metadata: The metadata object to update.
            calc_page_sizes: Whether to calculate page sizes. Default is False.
        """
        metadata.page_count = self.get_number_of_pages()

        if calc_page_sizes:
            self._calculate_all_page_info(metadata)

    def _calculate_all_page_info(self, metadata: Metadata) -> None:
        """
        Calculate page information for all pages in metadata.

        Args:
            metadata: The metadata object containing pages.
        """
        for page in metadata.pages:
            if self._should_calculate_page_info(page):
                try:
                    self._calculate_page_info(page)
                except Exception:
                    logger.exception(
                        "Error calculating page info for page %s", page.get("Image", "unknown")
                    )

    @staticmethod
    def _should_calculate_page_info(page: ImageMetadata) -> bool:
        """Determines if page information should be calculated."""
        required_keys = {"ImageSize", "ImageHeight", "ImageWidth"}
        return any(key not in page for key in required_keys)

    def _calculate_page_info(self, page: ImageMetadata) -> None:
        """
        Calculate and set page information.

        Args:
            page: The page metadata to update.
        """
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

        # Try to get image dimensions
        self._set_image_dimensions(page, data, idx)

    @staticmethod
    def _set_image_dimensions(page: ImageMetadata, data: bytes, idx: int) -> None:
        """
        Set image dimensions for a page.

        Args:
            page: The page metadata to update.
            data: The image data.
            idx: The page index for logging.
        """
        try:
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
        Return the set of metadata formats present in the archive.

        Returns:
            A set of MetadataFormat enums representing the available metadata.
        """
        format_checkers = [
            (MetadataFormat.COMIC_RACK, self.has_metadata),
            (MetadataFormat.METRON_INFO, self.has_metadata),
        ]

        return {fmt for fmt, checker in format_checkers if checker(fmt)}

    def validate_metadata(self, metadata_format: MetadataFormat) -> SchemaVersion:
        """
        Validates the metadata in the archive for the specified format and returns its schema version.

        This method checks if the archive contains metadata in the given format, validates the XML,
        and returns the detected schema version.

        Args:
            metadata_format: The format of the metadata to validate.

        Returns:
            SchemaVersion: The schema version of the validated metadata,
                          or SchemaVersion.Unknown if not found or invalid.
        """
        metadata_handlers = {
            MetadataFormat.METRON_INFO: (self._has_metroninfo, self._mi_xml_filename),
            MetadataFormat.COMIC_RACK: (self._has_comicinfo, self._ci_xml_filename),
        }

        if metadata_format not in metadata_handlers:
            return SchemaVersion.Unknown

        has_metadata_func, filename = metadata_handlers[metadata_format]

        if not has_metadata_func():
            return SchemaVersion.Unknown

        return self._validate_metadata_xml(metadata_format, filename)

    def _validate_metadata_xml(
        self, metadata_format: MetadataFormat, filename: str
    ) -> SchemaVersion:
        """
        Validate metadata XML and return schema version.

        Args:
            metadata_format: The metadata format being validated.
            filename: The filename of the metadata file.

        Returns:
            The schema version of the metadata.
        """
        try:
            xml_bytes = self._archiver.read_file(filename)
            vm = ValidateMetadata(xml_bytes)
            return vm.validate()
        except (ArchiverReadError, ValidationError):
            logger.exception("Error validating %s XML archive from %s", metadata_format, self._path)
            return SchemaVersion.Unknown

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
