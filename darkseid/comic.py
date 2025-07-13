"""A class to represent a single comic archive with comprehensive metadata support.

This module provides the Comic class for reading, writing, and manipulating comic book archives
(CBZ/ZIP and CBR/RAR formats) along with their associated metadata in ComicInfo and MetronInfo formats.

Examples:
    Basic usage of the Comic class:

    >>> from pathlib import Path
    >>> comic = Comic(Path("example.cbz"))
    >>> print(f"Comic has {comic.get_number_of_pages()} pages")
    >>> metadata = comic.read_metadata(MetadataFormat.COMIC_INFO)
    >>> print(f"Issue: {metadata.series.name} #{metadata.issue}")

"""

# Copyright 2012-2014 Anthony Beville
# Copyright 2019 Brian Pepple
from __future__ import annotations

__all__ = ["Comic", "ComicArchiveError", "ComicError", "ComicMetadataError", "MetadataFormat"]

import io
import logging
import os
from contextlib import suppress
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Final

from natsort import natsorted, ns
from PIL import Image

from darkseid.archivers import ArchiverFactory, ArchiverReadError
from darkseid.archivers.zip import ZipArchiver
from darkseid.metadata.comicinfo import ComicInfo
from darkseid.metadata.data_classes import ImageMetadata, Metadata
from darkseid.metadata.metroninfo import MetronInfo
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
    """An enumeration of supported metadata formats for comic books.

    This enum defines the different metadata formats that can be stored within
    comic book archives. Each format has specific characteristics and use cases.

    Attributes:
        METRON_INFO: MetronInfo format - A comprehensive metadata format that includes
                    detailed bibliographic information and is designed for library
                    and collection management systems.
        COMIC_INFO: ComicInfo format - The standard metadata format used by ComicRack
                   and other comic reading applications.
        UNKNOWN: Unknown or unsupported metadata format.

    Examples:
        >>> fmt = MetadataFormat.COMIC_INFO
        >>> print(fmt)  # Output: ComicInfo
        >>> comic = Comic(Path("example.cbz"))
        >>> comic.has_metadata(MetadataFormat.METRON_INFO)

    """

    METRON_INFO = auto()
    COMIC_INFO = auto()
    UNKNOWN = auto()

    def __str__(self) -> str:
        """Return a human-readable string representation of the metadata format.

        Returns:
            str: A capitalized string representation (e.g., "ComicInfo", "MetronInfo").

        Examples:
            >>> str(MetadataFormat.COMIC_INFO)
            'ComicInfo'

        """
        return "".join(word.capitalize() for word in self.name.split("_"))


class ComicError(Exception):
    """Base exception for all comic-related errors.

    This is the parent class for all exceptions raised by the Comic class
    and related functionality. Use this for general exception handling.
    """


class ComicArchiveError(ComicError):
    """Exception raised when there are issues with the comic archive file.

    This exception is raised when:

    - The comic file doesn't exist
    - The archive is corrupted or unreadable
    - Archive format is not supported
    - File system permissions prevent access
    """


class ComicMetadataError(ComicError):
    """Exception raised when there are issues with comic metadata operations.

    This exception is raised when:

    - Metadata format is not supported
    - Metadata parsing fails
    - Metadata validation errors occur
    """


class Comic:
    """A comprehensive comic book archive handler with metadata support.

    The Comic class provides a high-level interface for working with comic book archives
    in CBZ (ZIP) and CBR (RAR) formats. It supports reading and writing metadata in
    ComicInfo and MetronInfo formats, page manipulation, and archive validation.

    Key Features:
        - Support for CBZ/ZIP and CBR/RAR comic archives
        - Read/write ComicInfo and MetronInfo metadata
        - Page extraction and manipulation
        - Archive validation and format detection
        - Metadata validation with schema version detection
        - Export capabilities (e.g., CBR to CBZ conversion)

    Thread Safety:
        This class is not thread-safe. Each thread should use its own Comic instance.

    Performance Considerations:
        - Page lists and metadata are cached after first access
        - Large archives may consume significant memory when processing all pages
        - RAR archives are read-only due to library limitations

    Examples:
        Basic usage:

        >>> from pathlib import Path
        >>> comic = Comic(Path("my_comic.cbz"))
        >>>
        >>> # Check if it's a valid comic
        >>> if comic.is_valid_comic():
        ...     print(f"Comic '{comic.name}' has {comic.get_number_of_pages()} pages")
        >>>
        >>> # Read metadata
        >>> if comic.has_metadata(MetadataFormat.COMIC_INFO):
        ...     metadata = comic.read_metadata(MetadataFormat.COMIC_INFO)
        ...     print(f"Series: {metadata.series.name}")
        >>>
        >>> # Get a page
        >>> page_data = comic.get_page(0)  # First page
        >>> if page_data:
        ...     with open("cover.jpg", "wb") as f:
        ...         f.write(page_data)

    Attributes:
        path (Path): The file system path to the comic archive.
        name (str): The filename of the comic archive.
        size (int): The size of the comic archive in bytes.

    """

    # Class-level constants for better maintainability
    _RAR_EXTENSIONS: Final[frozenset[str]] = frozenset([".cbr", ".rar"])
    _ZIP_EXTENSIONS: Final[frozenset[str]] = frozenset([".cbz", ".zip"])

    def __init__(self, path: Path | str) -> None:
        """Initialize a Comic object with the provided path.

        Args:
            path: The file system path to the comic archive. Can be a string or Path object.
                 The file must exist and be a valid ZIP or RAR archive.

        Raises:
            ComicArchiveError: If the path doesn't exist, isn't accessible, or can't be
                             opened as a valid archive format.

        Examples:
            >>> comic = Comic("my_comic.cbz")
            >>> comic_ = Comic(Path("/path/to/comic.cbr"))
            >>> print(comic.name)
            >>> print(comic_.name)

        """
        self._path: Path = Path(path) if isinstance(path, str) else path
        self._validate_path()
        self._initialize_archiver()
        self._initialize_attributes()

    def _validate_path(self) -> None:
        """Validate that the comic file path exists and is accessible.

        Raises:
            ComicArchiveError: If the path doesn't exist or isn't accessible.

        """
        if not self._path.exists():
            msg = f"Comic file does not exist: {self._path}"
            raise ComicArchiveError(msg)

    def _initialize_archiver(self) -> None:
        """Initialize the appropriate archiver for the comic file format.

        Raises:
            ComicArchiveError: If no suitable archiver can be created for the file.

        """
        try:
            self._archiver: Archiver = ArchiverFactory.create_archiver(self._path)
        except Exception as e:
            msg = f"Failed to create archiver for {self._path}: {e}"
            raise ComicArchiveError(msg) from e

    def _initialize_attributes(self) -> None:
        """Initialize instance attributes and set up caching system."""
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
        """Return the name of the comic file.

        Returns:
            str: The filename of the comic archive.

        """
        return self._path.name

    def __repr__(self) -> str:
        """Return a detailed string representation of the Comic object.

        Returns:
            str: A string representation showing the path and page count.

        Examples:
            >>> comic = Comic(Path("example.cbz"))
            >>> repr(comic)
            "Comic(path=PosixPath('/comics/example.cbz'), pages=24)"

        """
        return f"Comic(path={self._path!r}, pages={self.get_number_of_pages()})"

    def __eq__(self, other: object) -> bool:
        """Check if two Comic objects are equal based on their file paths.

        Args:
            other: Another object to compare with.

        Returns:
            bool: True if both objects are Comic instances with the same path.

        """
        if not isinstance(other, Comic):
            return NotImplemented
        return self._path == other._path

    def __hash__(self) -> int:
        """Make Comic objects hashable based on their file path.

        Returns:
            int: Hash value based on the file path.

        Note:
            This allows Comic objects to be used in sets and as dictionary keys.

        """
        return hash(self._path)

    @property
    def path(self) -> Path:
        """Get the file system path of the comic archive.

        Returns:
            Path: The path to the comic archive file.

        """
        return self._path

    @property
    def name(self) -> str:
        """Get the filename of the comic archive.

        Returns:
            str: The filename without the directory path.

        """
        return self._path.name

    @property
    def size(self) -> int:
        """Get the size of the comic archive file in bytes.

        Returns:
            int: The file size in bytes.

        Raises:
            OSError: If the file cannot be accessed or doesn't exist.

        """
        return self._path.stat().st_size

    def _reset_cache(self) -> None:
        """Clear all cached data to ensure fresh reads.

        This method is called after write operations to ensure that cached
        data doesn't become stale after the archive is modified.
        """
        self._has_ci = None
        self._has_mi = None
        self._page_count = None
        self._page_list = None
        self._metadata = None

    def _validate_page_index(self, index: int) -> None:
        """Validate that a page index is within the valid range.

        Args:
            index: The page index to validate (0-based).

        Raises:
            ValueError: If the index is negative or exceeds the available pages.

        Note:
            Page indices are 0-based, so valid indices range from 0 to page_count-1.

        """
        if index < 0:
            msg = f"Page index cannot be negative: {index}"
            raise ValueError(msg)

        page_count = self.get_number_of_pages()
        if index >= page_count:
            msg = f"Page index {index} is out of range (0-{page_count - 1})"
            raise ValueError(msg)

    def is_archive_valid(self) -> bool:
        """Test whether the archive file is valid and readable.

        This method performs a comprehensive check to determine if the archive
        can be opened and read as either a ZIP or RAR file.

        Returns:
            bool: True if the archive is valid and readable, False otherwise.

        Note:
            This method is more thorough than just checking file extensions,
            as it actually attempts to open and validate the archive structure.

        """
        with suppress(Exception):
            return self._archiver.test()
        return False

    def is_rar(self) -> bool:
        """Check if the archive is a RAR file based on its extension.

        Returns:
            bool: True if the file has a RAR extension (.cbr or .rar).

        Note:
            This method only checks the file extension, not the actual file format.
            Use archiver.test() for a more thorough validation.

        """
        return self._path.suffix.lower() in self._RAR_EXTENSIONS

    def is_zip(self) -> bool:
        """Check if the archive is a ZIP file based on its extension.

        Returns:
            bool: True if the file has a ZIP extension (.cbz or .zip).

        Note:
            This method only checks the file extension, not the actual file format.
            Use archiver.test() for a more thorough validation.

        """
        return self._path.suffix.lower() in self._ZIP_EXTENSIONS

    def is_writable(self) -> bool:
        """Check if the archive supports write operations.

        Returns:
            bool: True if the archive can be modified, False otherwise.

        Note:
            RAR archives are typically read-only due to library limitations.
            ZIP archives can be written to if the file system permissions allow it.

        """
        return self._archiver.is_write_operation_expected() and os.access(self._path, os.W_OK)

    def seems_to_be_a_comic_archive(self) -> bool:
        """Determine if the file appears to be a comic book archive.

        A file is considered a comic archive if it meets the following criteria:

        1. It's either a ZIP or RAR archive
        2. It contains at least one image file

        Returns:
            bool: True if the file appears to be a comic archive, False otherwise.

        Note:
            This is a heuristic check and may not catch all edge cases.
            Use is_valid_comic() for a more comprehensive validation.

        """
        return (self.is_zip() or self.is_rar()) and (self.get_number_of_pages() > 0)

    def get_page(self, index: int) -> bytes | None:
        """Retrieve the raw image data for a specific page.

        Args:
            index: The 0-based index of the page to retrieve.

        Returns:
            bytes | None: The raw image data of the page, or None if the page
                         cannot be retrieved (invalid index or read error).

        Examples:
            >>> comic = Comic(Path("example.cbz"))
            >>> page_data = comic.get_page(0)  # Get first page
            >>> if page_data:
            ...     with open("page_1.jpg", "wb") as f:
            ...         f.write(page_data)

        Note:
            The returned data is the raw image file content and can be written
            directly to a file or processed with image libraries like PIL.

        """
        try:
            self._validate_page_index(index)
        except ValueError:
            logger.warning("Invalid page index %d for comic %s", index, self._path)
            return None

        filename = self.get_page_name(index)
        return None if filename is None else self._read_file_safely(filename)

    def _read_file_safely(self, filename: str) -> bytes | None:
        """Safely read a file from the archive with error handling.

        Args:
            filename: The name of the file to read from the archive.

        Returns:
            bytes | None: The file data, or None if an error occurs.

        """
        try:
            return self._archiver.read_file(filename)
        except (OSError, ArchiverReadError):
            logger.exception("Error reading '%s' from '%s'", filename, self._path)
            return None

    def get_page_name(self, index: int) -> str | None:
        """Get the filename of a page by its index.

        Args:
            index: The 0-based index of the page.

        Returns:
            str | None: The filename of the page within the archive, or None if
                       the index is invalid or out of range.

        Examples:
            >>> comic = Comic(Path("example.cbz"))
            >>> filename = comic.get_page_name(0)
            >>> print(filename)  # Output: "page_01.jpg"

        """
        if index < 0:
            return None

        page_list = self.get_page_name_list()
        return page_list[index] if index < len(page_list) else None

    @staticmethod
    def is_image(name_path: Path) -> bool:
        """Check if a file is a supported image format.

        Args:
            name_path: The path to check (can be filename or full path).

        Returns:
            bool: True if the file has a supported image extension and isn't
                 a hidden file (doesn't start with '.').

        Note:
            Supported formats: .jpg, .jpeg, .png, .gif, .webp
            Hidden files (starting with '.') are excluded.

        """
        return (
            name_path.suffix.lower() in SUPPORTED_IMAGE_EXTENSIONS
            and not name_path.name.startswith(".")
        )

    def get_page_name_list(self, sort_list: bool = True) -> list[str]:  # noqa: FBT001, FBT002
        """Get a list of all page filenames in the archive.

        Args:
            sort_list: Whether to sort the list using natural sorting. Default is True.

        Returns:
            list[str]: A list of page filenames, filtered to include only image files.

        Note:
            - Only image files are included in the list
            - Hidden files (starting with '.') are excluded
            - Natural sorting ensures proper ordering (e.g., page10.jpg comes after page2.jpg)
            - Results are cached for performance

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
        """Get the total number of pages (images) in the archive.

        Returns:
            int: The number of image files in the archive.

        Note:
            This count includes only supported image formats and excludes hidden files.
            The result is cached for performance.

        """
        if self._page_count is None:
            self._page_count = len(self.get_page_name_list())
        return self._page_count

    def read_metadata(self, metadata_format: MetadataFormat) -> Metadata:
        """Read metadata from the archive in the specified format.

        Args:
            metadata_format: The format of metadata to read (COMIC_INFO or METRON_INFO).

        Returns:
            Metadata: The parsed metadata object, or an empty Metadata instance
                     if the format is not recognized or parsing fails.

        Examples:
            >>> comic = Comic(Path("example.cbz"))
            >>> if comic.has_metadata(MetadataFormat.COMIC_INFO):
            ...     metadata = comic.read_metadata(MetadataFormat.COMIC_INFO)
            ...     print(f"Series: {metadata.series.name}")
            ...     print(f"Issue: {metadata.issue}")

        Note:
            - The result is cached after first read
            - Page list validation is performed to ensure consistency
            - Returns empty Metadata object if format is unsupported

        """
        metadata_readers = {
            MetadataFormat.COMIC_INFO: self._read_comicinfo,
            MetadataFormat.METRON_INFO: self._read_metroninfo,
        }

        reader = metadata_readers.get(metadata_format)
        if reader is None:
            logger.warning("Unknown metadata format: %s", metadata_format)
            return Metadata()

        return reader()

    def _read_comicinfo(self) -> Metadata:
        """Read and parse ComicInfo metadata from the archive.

        Returns:
            Metadata: The parsed ComicInfo metadata.

        """
        if self._metadata is not None:
            return self._metadata

        self._metadata = self._parse_metadata(self.read_raw_ci_metadata(), ComicInfo())
        self._validate_and_fix_page_list()
        return self._metadata

    def _read_metroninfo(self) -> Metadata:
        """Read and parse MetronInfo metadata from the archive.

        Returns:
            Metadata: The parsed MetronInfo metadata.

        """
        if self._metadata is not None:
            return self._metadata

        self._metadata = self._parse_metadata(self.read_raw_mi_metadata(), MetronInfo())
        self._validate_and_fix_page_list()
        return self._metadata

    def _parse_metadata(self, raw_metadata: str | None, parser: MetronInfo | ComicInfo) -> Metadata:
        """Parse raw metadata XML using the appropriate parser.

        Args:
            raw_metadata: The raw XML metadata string.
            parser: The metadata parser instance (ComicInfo or MetronInfo).

        Returns:
            Metadata: Parsed metadata object or empty Metadata if parsing fails.

        """
        if not raw_metadata:
            return Metadata()

        try:
            return parser.metadata_from_string(raw_metadata)
        except Exception:
            logger.exception("Error parsing metadata from %s", self._path)
            return Metadata()

    def _validate_and_fix_page_list(self) -> None:
        """Validate and fix inconsistencies in the metadata page list.

        This method ensures that the page count in metadata matches the actual
        number of image files in the archive. If there's a mismatch, it resets
        the page list to default values.
        """
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
        """Read raw metadata XML from the archive.

        Args:
            metadata_format: The format of metadata to read.

        Returns:
            str | None: The raw XML metadata as a string, or None if not found or error.

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
        """Get the standard filename for the specified metadata format.

        Args:
            metadata_format: The metadata format.

        Returns:
            str | None: The filename for the metadata format, or None if unknown.

        """
        filename_map = {
            MetadataFormat.COMIC_INFO: self._ci_xml_filename,
            MetadataFormat.METRON_INFO: self._mi_xml_filename,
        }
        return filename_map.get(metadata_format)

    def read_raw_ci_metadata(self) -> str | None:
        """Read raw ComicInfo metadata XML from the archive.

        Returns:
            str | None: The raw ComicInfo XML as a string, or None if not found.

        Note:
            This method returns the raw XML content without any parsing or validation.
            Use read_metadata() for parsed metadata objects.

        """
        return self._read_raw_metadata(MetadataFormat.COMIC_INFO)

    def read_raw_mi_metadata(self) -> str | None:
        """Read raw MetronInfo metadata XML from the archive.

        Returns:
            str | None: The raw MetronInfo XML as a string, or None if not found.

        Note:
            This method returns the raw XML content without any parsing or validation.
            Use read_metadata() for parsed metadata objects.

        """
        return self._read_raw_metadata(MetadataFormat.METRON_INFO)

    def write_metadata(self, metadata: Metadata, metadata_format: MetadataFormat) -> bool:
        """Write metadata to the comic archive in the specified format.

        This method serializes the provided metadata object and writes it to the comic archive
        as an XML file. The metadata is automatically synchronized with the current archive
        state before writing to ensure consistency. The operation modifies the archive file
        directly and may overwrite existing metadata in the same format.

        Args:
            metadata: The metadata object containing the information to write. Must be a valid
                     Metadata instance with appropriate fields populated. The object is not
                     modified during the write operation.
            metadata_format: The format in which to write the metadata. Supported formats:

                - MetadataFormat.COMIC_INFO: Writes as ComicInfo.xml (ComicInfo format)
                - MetadataFormat.METRON_INFO: Writes as MetronInfo.xml (MetronInfo format)
                - MetadataFormat.UNKNOWN: Not supported, raises ComicMetadataError

        Returns:
            bool: True if the metadata was successfully written to the archive,
                  False if the operation failed due to read-only archive, I/O errors,
                  or other issues.

        Raises:
            ComicMetadataError: If the specified metadata format is not supported or
                               if the metadata format is MetadataFormat.UNKNOWN.

        Side Effects:
            - Creates or overwrites the metadata file in the archive (ComicInfo.xml or MetronInfo.xml)
            - Updates internal cache flags to reflect the presence of the new metadata
            - Automatically applies archive information to metadata before writing
            - Clears internal metadata cache after successful write
            - For ComicInfo format: calculates and includes page sizes and dimensions
            - For MetronInfo format: writes metadata without detailed page calculations

        Prerequisites:
            - The archive must be writable (not read-only)
            - The archive must be a valid comic archive format (ZIP or RAR)
            - The metadata object must be properly initialized

        Automatic Processing:
            The method automatically performs several operations before writing:

            1. Validates archive write permissions
            2. Applies current archive information to metadata via apply_archive_info_to_metadata()
            3. For ComicInfo: calculates page sizes, dimensions, and other detailed information
            4. For MetronInfo: synchronizes page count without expensive calculations
            5. Serializes metadata to appropriate XML format
            6. Updates internal cache state upon successful write

        Examples:
            >>> comic = Comic("example.cbz")
            >>>
            >>> # Basic metadata writing
            >>> metadata = Metadata()
            >>> metadata.series = "Amazing Spider-Man"
            >>> metadata.issue = "1"
            >>> success = comic.write_metadata(metadata, MetadataFormat.COMIC_INFO)
            >>> if success:
            ...     print("Metadata written successfully")
            ... else:
            ...     print("Failed to write metadata")

            >>> # Read, modify, and write back metadata
            >>> if comic.has_metadata(MetadataFormat.COMIC_INFO):
            ...     metadata = comic.read_metadata(MetadataFormat.COMIC_INFO)
            ...     metadata.title = "Updated Title"
            ...     comic.write_metadata(metadata, MetadataFormat.COMIC_INFO)

            >>> # Write metadata in multiple formats
            >>> metadata = Metadata()
            >>> metadata.series = "Batman"
            >>> metadata.issue = "42"
            >>>
            >>> # Write as ComicInfo (with detailed page information)
            >>> comic.write_metadata(metadata, MetadataFormat.COMIC_INFO)
            >>>
            >>> # Write as MetronInfo (faster, less detailed)
            >>> comic.write_metadata(metadata, MetadataFormat.METRON_INFO)

            >>> # Error handling example
            >>> try:
            ...     success = comic.write_metadata(metadata, MetadataFormat.UNKNOWN)
            ... except ComicMetadataError as e:
            ...     print(f"Unsupported format: {e}")

            >>> # Conditional writing based on archive type
            >>> if comic.is_writable():
            ...     success = comic.write_metadata(metadata, MetadataFormat.COMIC_INFO)
            ...     if not success:
            ...         print("Write failed despite writable archive")
            ... else:
            ...     print("Archive is read-only, cannot write metadata")

        Format-Specific Behavior:
            ComicInfo Format:

            - Calculates and includes detailed page information (sizes, dimensions)
            - Preserves existing ComicInfo structure when possible
            - Includes page list with complete image metadata
            - Slower due to page analysis but more complete

            MetronInfo Format:

            - Focuses on bibliographic information
            - Skips expensive page size calculations
            - Faster processing for large archives
            - Suitable for metadata-only operations

        Performance Considerations:
            - ComicInfo writing is slower due to page analysis (calc_page_sizes=True)
            - MetronInfo writing is faster (calc_page_sizes=False)
            - Large archives may take significant time with ComicInfo format
            - Consider format choice based on use case and performance requirements

        Error Scenarios:
            - Returns False if archive is read-only or write-protected
            - Returns False if I/O errors occur during writing
            - Returns False if XML serialization fails
            - Raises ComicMetadataError for unsupported formats
            - Logs detailed error information for debugging

        Best Practices:
            - Always check return value to verify successful write
            - Use is_writable() to check permissions before writing
            - Consider MetronInfo format for better performance on large archives
            - Handle ComicMetadataError exceptions for unsupported formats
            - Verify metadata completeness before writing

        See Also:
            - read_metadata(): Read existing metadata from archive
            - has_metadata(): Check if metadata exists in specified format
            - remove_metadata(): Remove metadata from archive
            - apply_archive_info_to_metadata(): Synchronize metadata with archive
            - is_writable(): Check if archive supports write operations

        """
        if not self.is_writable():
            logger.warning("Cannot write metadata to read-only archive: %s", self._path)
            return False

        writers = {
            MetadataFormat.COMIC_INFO: self._write_ci,
            MetadataFormat.METRON_INFO: self._write_mi,
        }

        writer = writers.get(metadata_format)
        if writer is None:
            msg = f"Unsupported metadata format: {metadata_format}"
            raise ComicMetadataError(msg)

        return writer(metadata)  # type: ignore

    def _write_ci(self, metadata: Metadata | None) -> bool:
        """Write ComicInfo metadata to the archive.

        Args:
            metadata: The metadata to write.

        Returns:
            bool: True if successful, False otherwise.

        """
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
        """Write MetronInfo metadata to the archive.

        Args:
            metadata: The metadata to write.

        Returns:
            bool: True if successful, False otherwise.

        """
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
        formatter: MetronInfo | ComicInfo,
        filename: str,
        raw_metadata: str | None,
        calc_page_sizes: bool = False,  # noqa: FBT002, FBT001
    ) -> bool:
        """Write metadata in a specific format to the archive.

        Args:
            metadata: The metadata to write.
            formatter: The metadata formatter instance.
            filename: The filename to write to in the archive.
            raw_metadata: Existing raw metadata string for preservation.
            calc_page_sizes: Whether to calculate page sizes and dimensions.

        Returns:
            bool: True if successful, False otherwise.

        """
        try:
            self._apply_archive_info_to_metadata(metadata, calc_page_sizes=calc_page_sizes)

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
        """Remove metadata from the comic archive.

        Args:
            metadata_format: The format of metadata to remove.

        Returns:
            bool: True if the metadata was successfully removed or didn't exist,
                 False if an error occurred.

        Examples:
            >>> comic = Comic(Path("example.cbz"))
            >>> success = comic.remove_metadata(MetadataFormat.COMIC_INFO)
            >>> if success:
            ...     print("ComicInfo metadata removed")

        Note:
            - If the metadata doesn't exist, this method returns True
            - The archive must be writable
            - All metadata files matching the format are removed (case-insensitive)

        """
        supported_formats = {MetadataFormat.COMIC_INFO, MetadataFormat.METRON_INFO}

        if metadata_format not in supported_formats:
            logger.warning("Unsupported metadata format for removal: %s", metadata_format)
            return False

        if not self.has_metadata(metadata_format):
            logger.info("No %s metadata found in %s", metadata_format, self._path)
            return True  # Already removed, consider it success

        return self._remove_metadata_files(metadata_format)

    def _remove_metadata_files(self, metadata_format: MetadataFormat) -> bool:
        """Remove metadata files from the archive.

        Args:
            metadata_format: The format of metadata to remove.

        Returns:
            bool: True if successful, False otherwise.

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
                elif metadata_format == MetadataFormat.COMIC_INFO:
                    self._has_ci = False

            return self._successful_write(write_success, None)

        except Exception:
            logger.exception("Error removing %s metadata from %s", metadata_format, self._path)
            return False

    def remove_pages(self, pages_index: list[int]) -> bool:
        """Remove pages from the comic archive.

        This method removes specified pages from the comic archive by their index positions.
        The operation modifies the archive file directly and cannot be undone. Page indices
        are zero-based, where 0 represents the first page.

        Args:
            pages_index: A list of zero-based page indices to remove from the archive.
                        Indices must be valid (0 <= index < total_pages). Duplicate
                        indices are allowed but will only remove the page once.

        Returns:
            bool: True if all specified pages were successfully removed from the archive,
                  False if the operation failed due to read-only archive, invalid indices,
                  or other errors.

        Raises:
            ValueError: If any page index is negative or exceeds the total number of pages.

        Warning:
            This operation is destructive and cannot be undone. It will:

            - Permanently remove the specified pages from the archive
            - Invalidate any existing metadata cache
            - Reset ComicInfo and MetronInfo metadata flags
            - Require the archive to be writable

        Examples:
            >>> comic = Comic("example.cbz")
            >>> comic.get_number_of_pages()
            10
            >>> # Remove the first and last pages
            >>> success = comic.remove_pages([0, 9])
            >>> if success:
            ...     print(f"Pages removed. New page count: {comic.get_number_of_pages()}")
            ... else:
            ...     print("Failed to remove pages")

            >>> # Remove multiple pages (pages 2, 3, and 5 from original numbering)
            >>> comic.remove_pages([2, 3, 5])

        Note:
            - The archive must be writable for this operation to succeed
            - Page indices are validated before removal begins
            - If any index is invalid, the entire operation fails
            - After successful removal, page indices of remaining pages may change
            - Metadata caches are automatically cleared after successful removal

        """
        if not pages_index:
            logger.warning("No pages specified for removal")
            return False

        if not self.is_writable():
            logger.warning("Cannot remove pages from read-only archive: %s", self._path)
            return False

        return self._remove_pages_by_index(pages_index)

    def _remove_pages_by_index(self, pages_index: list[int]) -> bool:
        """Remove pages by their indices.

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

    def _successful_write(self, write_success: bool, metadata: Metadata | None) -> bool:  # noqa: FBT001
        """Update the state based on the success of a write operation.

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
        """Check if a metadata file exists in the archive.

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
        """Check if metadata file exists in archive.

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
        """Check if the archive contains ComicInfo metadata."""
        return self._has_metadata_file("_has_ci", "_ci_xml_filename")

    def _has_metroninfo(self) -> bool:
        """Check if the archive contains MetronInfo metadata."""
        return self._has_metadata_file("_has_mi", "_mi_xml_filename")

    def has_metadata(self, fmt: MetadataFormat) -> bool:
        """Check if the archive contains metadata in the specified format.

        This method determines whether the comic archive contains metadata files
        corresponding to the requested format. It performs a case-insensitive search
        for the appropriate metadata file within the archive and caches the result
        for improved performance on subsequent calls.

        Args:
            fmt: The metadata format to check for. Must be one of:
                - MetadataFormat.COMIC_INFO: Checks for ComicInfo.xml (ComicInfo format)
                - MetadataFormat.METRON_INFO: Checks for MetronInfo.xml (MetronInfo format)
                - MetadataFormat.UNKNOWN: Always returns False

        Returns:
            bool: True if the archive contains metadata in the specified format,
                  False if no metadata is found, the format is unsupported, or
                  the archive is not a valid comic archive.

        Note:
            - The method uses case-insensitive filename matching (e.g., "comicinfo.xml",
              "COMICINFO.XML", and "ComicInfo.xml" are all considered matches)
            - Results are cached internally to avoid repeated file system operations
            - The archive must be a valid comic archive (ZIP or RAR with pages) for
              metadata detection to work properly
            - Returns False immediately if the archive doesn't seem to be a comic

        Performance:
            - First call performs file system lookup and caches result
            - Subsequent calls return cached result for improved performance
            - Cache is automatically cleared when archive contents are modified

        Examples:
            >>> comic = Comic("example.cbz")
            >>>
            >>> # Check for ComicInfo.xml metadata
            >>> if comic.has_metadata(MetadataFormat.COMIC_INFO):
            ...     print("Comic has ComicInfo metadata")
            ...     metadata = comic.read_metadata(MetadataFormat.COMIC_INFO)
            ... else:
            ...     print("No ComicInfo metadata found")

            >>> # Check for MetronInfo.xml metadata
            >>> if comic.has_metadata(MetadataFormat.METRON_INFO):
            ...     print("Comic has MetronInfo metadata")

            >>> # Check what metadata formats are available
            >>> formats = comic.get_metadata_formats()
            >>> for fmt in formats:
            ...     print(f"Found metadata: {fmt}")

            >>> # Conditional metadata reading
            >>> preferred_formats = [MetadataFormat.METRON_INFO, MetadataFormat.COMIC_INFO]
            >>> for fmt in preferred_formats:
            ...     if comic.has_metadata(fmt):
            ...         metadata = comic.read_metadata(fmt)
            ...         print(f"Using {fmt} metadata")
            ...         break
            ... else:
            ...     print("No supported metadata found")

        See Also:
            - read_metadata(): Read metadata content from the archive
            - get_metadata_formats(): Get all available metadata formats
            - write_metadata(): Write metadata to the archive
            - remove_metadata(): Remove metadata from the archive

        """
        metadata_checkers = {
            MetadataFormat.COMIC_INFO: self._has_comicinfo,
            MetadataFormat.METRON_INFO: self._has_metroninfo,
        }

        checker = metadata_checkers.get(fmt)
        return checker() if checker else False

    def _apply_archive_info_to_metadata(
        self,
        metadata: Metadata,
        calc_page_sizes: bool = False,  # noqa: FBT002, FBT001
    ) -> None:
        """Apply page information from the archive to the metadata.

        Args:
            metadata: The metadata object to update.
            calc_page_sizes: Whether to calculate page sizes. Default is False.

        """
        metadata.page_count = self.get_number_of_pages()

        if calc_page_sizes:
            self._calculate_all_page_info(metadata)

    def _calculate_all_page_info(self, metadata: Metadata) -> None:
        """Calculate page information for all pages in metadata.

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
        """Determine if page information should be calculated."""
        required_keys = {"ImageSize", "ImageHeight", "ImageWidth"}
        return any(key not in page for key in required_keys)

    def _calculate_page_info(self, page: ImageMetadata) -> None:
        """Calculate and set page information.

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
        """Set image dimensions for a page.

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
        """Export the comic archive to CBZ (ZIP) format.

        This method creates a new ZIP-format comic archive containing all files from the
        current comic archive. If the source is already in ZIP format, the method returns
        True immediately without creating a duplicate. The operation preserves all content
        including pages, metadata files, and any other files present in the original archive.

        Args:
            zip_filename: The path where the new ZIP archive will be created. Must be a
                         valid Path object pointing to the desired output location.
                         - Parent directory must exist and be writable
                         - File extension typically should be .cbz or .zip
                         - Existing files at this path will be overwritten

        Returns:
            bool: True if the export operation was successful or if the source archive
                  is already in ZIP format, False if the operation failed due to I/O
                  errors, permission issues, or other problems.

        Side Effects:
            - Creates a new ZIP file at the specified path
            - Overwrites any existing file at the target location
            - Does not modify the original archive in any way
            - May create temporary files during the conversion process

        File Preservation:
            The export operation preserves:

            - All page images in their original format and quality
            - All metadata files (ComicInfo.xml, MetronInfo.xml, etc.)
            - Directory structure within the archive
            - File timestamps and attributes where possible
            - Any additional files present in the original archive

        Format Conversion:
            - RAR/CBR → ZIP/CBZ: Full conversion with file extraction and re-compression
            - ZIP/CBZ → ZIP/CBZ: Returns True immediately (no-op)
            - Maintains compatibility with all comic reading applications
            - Preserves metadata across format conversion

        Examples:
            >>> comic = Comic("example.cbr")  # RAR format
            >>> output_path = Path("converted/example.cbz")
            >>>
            >>> # Basic export operation
            >>> success = comic.export_as_zip(output_path)
            >>> if success:
            ...     print(f"Successfully exported to {output_path}")
            ... else:
            ...     print("Export failed")

            >>> # Export with directory creation
            >>> output_path = Path("exports/comics/my_comic.cbz")
            >>> output_path.parent.mkdir(parents=True, exist_ok=True)
            >>> success = comic.export_as_zip(output_path)

            >>> # Batch conversion example
            >>> for rar_file in Path("comics").glob("*.cbr"):
            ...     comic = Comic(rar_file)
            ...     zip_path = rar_file.with_suffix(".cbz")
            ...     if comic.export_as_zip(zip_path):
            ...         print(f"Converted: {rar_file.name} → {zip_path.name}")

            >>> # Handle already-ZIP archives
            >>> zip_comic = Comic("already_zip.cbz")
            >>> result = zip_comic.export_as_zip(Path("copy.cbz"))
            >>> # Returns True immediately, no actual copying occurs

            >>> # Export with error handling
            >>> try:
            ...     output_path = Path("/readonly/location/comic.cbz")
            ...     success = comic.export_as_zip(output_path)
            ...     if not success:
            ...         print("Export failed - check permissions and disk space")
            ... except Exception as e:
            ...     print(f"Unexpected error during export: {e}")

        Performance Considerations:
            - RAR to ZIP conversion requires extracting and re-compressing all files
            - Processing time depends on archive size and compression settings
            - Memory usage scales with the size of individual files being processed
            - Large archives (>1GB) may require significant time and disk space
            - ZIP to ZIP operations are nearly instantaneous (early return)

        Error Scenarios:
            Common reasons for failure (returns False):

            - Insufficient disk space for the output file
            - Permission denied on target directory or file
            - Corrupted or unreadable source archive
            - Invalid or inaccessible zip_filename path
            - I/O errors during file extraction or compression
            - Interrupted operation due to system issues

        Disk Space Requirements:
            - Temporary space: Up to 2x the size of the original archive
            - Final space: Similar to original archive size (may vary due to compression)
            - Ensure adequate free space before starting large conversions

        Use Cases:
            - Converting RAR/CBR archives to more widely supported ZIP/CBZ format
            - Creating backup copies in standardized format
            - Preparing archives for systems that don't support RAR format
            - Batch processing comic collections for format standardization
            - Migrating archives to ZIP for better write support

        Limitations:
            - Cannot export archives that are corrupted or unreadable
            - Requires sufficient disk space for temporary files
            - May not preserve all extended file attributes or metadata
            - Does not validate the integrity of the output archive
            - Performance depends on compression algorithms and hardware

        Best Practices:
            - Verify sufficient disk space before conversion
            - Test with small archives first when batch processing
            - Keep backups of original archives until conversion is verified
            - Use descriptive filenames to avoid confusion
            - Consider the target audience's software compatibility

        See Also:
            - is_zip(): Check if the current archive is already in ZIP format
            - is_rar(): Check if the current archive is in RAR format
            - is_writable(): Check if the archive supports write operations
            - seems_to_be_a_comic_archive(): Validate archive as comic format

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
        """Return the set of metadata formats present in the archive.

        Returns:
            A set of MetadataFormat enums representing the available metadata.

        """
        format_checkers = [
            (MetadataFormat.COMIC_INFO, self.has_metadata),
            (MetadataFormat.METRON_INFO, self.has_metadata),
        ]

        return {fmt for fmt, checker in format_checkers if checker(fmt)}

    def validate_metadata(self, metadata_format: MetadataFormat) -> SchemaVersion:
        """Validate the metadata in the archive for the specified format and return its schema version.

        This method performs XML validation on the metadata contained within the comic archive.
        It first checks if the archive contains metadata in the requested format, then validates
        the XML structure against the appropriate schema, and finally returns the detected
        schema version.

        The validation process includes:

        1. Checking if the archive contains the specified metadata format
        2. Reading the metadata XML file from the archive
        3. Validating the XML structure and content
        4. Determining the schema version used

        Args:
            metadata_format (MetadataFormat): The format of the metadata to validate.
                Must be one of:
                - MetadataFormat.COMIC_INFO: For ComicInfo.xml validation
                - MetadataFormat.METRON_INFO: For MetronInfo.xml validation

        Returns:
            SchemaVersion: The schema version of the validated metadata. Possible values:

                - SchemaVersion.Unknown: If the metadata format is not supported,
                  the archive doesn't contain the specified metadata format,
                  the XML is invalid, or validation fails for any reason
                - SchemaVersion.METRON_INFO_V1: If valid MetronInfo v1.0 schema is detected
                - SchemaVersion.COMIC_INFO_V1: If valid ComicInfo v1.0 schema is detected
                - SchemaVersion.COMIC_INFO_V2: If valid ComicInfo v2.0 schema is detected
                - (Other schema versions as defined in SchemaVersion enum)

        Examples:
            >>> comic = Comic("example.cbz")
            >>> schema_version = comic.validate_metadata(MetadataFormat.COMIC_INFO)
            >>> if schema_version != SchemaVersion.Unknown:
            ...     print(f"Valid ComicInfo metadata found with schema version: {schema_version}")
            ... else:
            ...     print("No valid ComicInfo metadata found")

        Note:
            - This method does not modify the archive or its metadata
            - The validation is performed on the raw XML content
            - If multiple metadata formats are present, each must be validated separately
            - The method is safe to call multiple times as it doesn't cache results

        See Also:
            - has_metadata(): Check if metadata exists without validation
            - read_metadata(): Read and parse metadata content
            - get_metadata_formats(): Get all available metadata formats
            - ValidateMetadata: The underlying validation class

        """
        metadata_handlers = {
            MetadataFormat.METRON_INFO: (self._has_metroninfo, self._mi_xml_filename),
            MetadataFormat.COMIC_INFO: (self._has_comicinfo, self._ci_xml_filename),
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
        """Validate metadata XML and return schema version.

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
        """Perform a comprehensive validation of the comic archive.

        This method conducts a thorough validation to determine if the file represents
        a valid comic book archive. It performs multiple checks to ensure the archive
        is accessible, properly formatted, and contains comic book content.

        The validation process includes three essential checks:

        1. **File Existence**: Verifies the comic file exists on the filesystem
        2. **Archive Validity**: Confirms the file is a valid ZIP or RAR archive
        3. **Comic Content**: Ensures the archive contains at least one readable page/image

        This method is particularly useful for:

        - Batch processing comic libraries to identify corrupted files
        - Validating comic files before performing operations
        - Quality assurance in comic management applications
        - Filtering out non-comic files from mixed directories

        Returns:
            bool: True if the comic archive passes all validation checks, False otherwise.
                Returns False if any of the following conditions are met:

                - The file path doesn't exist on the filesystem
                - The file is not a valid ZIP or RAR archive
                - The archive is valid but contains no readable image pages
                - An exception occurs during validation (e.g., permission errors, corruption)

        Examples:
            >>> comic = Comic("my_comic.cbz")
            >>> if comic.is_valid_comic():
            ...     print(f"'{comic.name}' is a valid comic with {comic.get_number_of_pages()} pages")
            ...     # Safe to perform operations like reading pages or metadata
            ...     first_page = comic.get_page(0)
            ... else:
            ...     print(f"'{comic.name}' is not a valid comic archive")
            ...     # Handle invalid comic (skip, log error, etc.)

        Performance Notes:
            - This method may be slower for large archives as it needs to scan for images
            - Results are not cached, so repeated calls will re-validate
            - Consider calling this method once and storing the result if needed multiple times
            - The method performs minimal I/O operations but may access the archive contents

        Common Failure Scenarios:
            - **File not found**: The specified path doesn't exist
            - **Corrupted archive**: The ZIP/RAR file is damaged or incomplete
            - **Wrong file type**: The file has a comic extension but isn't actually an archive
            - **Empty archive**: The archive exists but contains no image files
            - **Permission issues**: Insufficient permissions to read the file
            - **Unsupported format**: Archive uses unsupported compression methods

        Note:
            - This method does not validate metadata (use validate_metadata() for that)
            - It only checks for the presence of image files, not their validity
            - The method is safe to call and will not modify the archive
            - Archive format detection is based on file content, not just file extension

        See Also:
            - is_archive_valid(): Check only archive format validity
            - seems_to_be_a_comic_archive(): Check if archive contains comic content
            - get_number_of_pages(): Get the count of readable pages
            - validate_metadata(): Validate metadata content and schema

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
