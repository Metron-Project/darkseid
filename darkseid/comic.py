"""A class to represent a single comic archive with comprehensive metadata support.

This module provides the Comic class for reading, writing, and manipulating comic book archives
(CBZ/ZIP, CBR/RAR, CBT, and CB7 (optional) formats) along with their associated metadata in ComicInfo and MetronInfo
formats.

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
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

if TYPE_CHECKING:
    from collections.abc import Callable

from natsort import natsorted, ns

try:
    from PIL import Image

    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False
    Image = None


from darkseid.archivers import ArchiverFactory, ArchiverReadError
from darkseid.archivers.sevenzip import PY7ZR_AVAILABLE
from darkseid.archivers.zip import ZipArchiver
from darkseid.metadata.comicinfo import ComicInfo
from darkseid.metadata.data_classes import ImageMetadata, Metadata
from darkseid.metadata.metroninfo import MetronInfo
from darkseid.validate import SchemaVersion, ValidateMetadata, ValidationError

if PY7ZR_AVAILABLE:
    from darkseid.archivers.sevenzip import SevenZipArchiver

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


@dataclass
class ComicCache:
    """Cache holder for comic archive data to improve performance.

    This class centralizes all cached data for a comic, making it easier to
    manage cache invalidation and state.
    """

    has_ci: bool | None = None
    has_mi: bool | None = None
    page_count: int | None = None
    page_list: list[str] | None = None
    metadata: Metadata | None = None

    def reset(self) -> None:
        """Clear all cached data to ensure fresh reads."""
        self.has_ci = None
        self.has_mi = None
        self.page_count = None
        self.page_list = None
        self.metadata = None


class MetadataFormatRegistry:
    """Registry for metadata format handlers to consolidate format-specific operations.

    This class centralizes all metadata format mappings, reducing duplication
    and making it easier to add new metadata formats in the future.
    """

    def __init__(self, comic: Comic) -> None:
        """Initialize registry with references to comic instance methods.

        Args:
            comic: The Comic instance this registry belongs to.

        """
        self._comic = comic
        self._registry: dict[MetadataFormat, dict[str, Any]] = {
            MetadataFormat.COMIC_INFO: {
                "filename": COMIC_RACK_FILENAME,
                "reader": comic._read_comicinfo,  # noqa: SLF001
                "writer": comic._write_ci,  # noqa: SLF001
                "checker": comic._has_comicinfo,  # noqa: SLF001
                "calc_page_sizes": True,
            },
            MetadataFormat.METRON_INFO: {
                "filename": METRON_INFO_FILENAME,
                "reader": comic._read_metroninfo,  # noqa: SLF001
                "writer": comic._write_mi,  # noqa: SLF001
                "checker": comic._has_metroninfo,  # noqa: SLF001
                "calc_page_sizes": False,
            },
        }

    def get_filename(self, fmt: MetadataFormat) -> str | None:
        """Get the filename for a metadata format."""
        entry = self._registry.get(fmt)
        return entry["filename"] if entry else None

    def get_reader(self, fmt: MetadataFormat) -> Callable[[], Metadata] | None:
        """Get the reader function for a metadata format."""
        entry = self._registry.get(fmt)
        return entry["reader"] if entry else None

    def get_writer(self, fmt: MetadataFormat) -> Callable[[Metadata | None], bool] | None:
        """Get the writer function for a metadata format."""
        entry = self._registry.get(fmt)
        return entry["writer"] if entry else None

    def get_checker(self, fmt: MetadataFormat) -> Callable[[], bool] | None:
        """Get the checker function for a metadata format."""
        entry = self._registry.get(fmt)
        return entry["checker"] if entry else None

    def get_calc_page_sizes(self, fmt: MetadataFormat) -> bool:
        """Get whether to calculate page sizes for a metadata format."""
        entry = self._registry.get(fmt)
        return entry.get("calc_page_sizes", False) if entry else False

    def is_supported(self, fmt: MetadataFormat) -> bool:
        """Check if a metadata format is supported."""
        return fmt in self._registry


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
    in CBZ (ZIP) CBR (RAR), CBT (TAR) and CB7 (7ZIP) formats. It supports reading and writing metadata in
    ComicInfo and MetronInfo formats, page manipulation, and archive validation.

    Key Features:
        - Support for CBZ/ZIP, CBR/RAR, CBT/TAR, and CB7/7ZIP (optional) comic archives
        - Read/write ComicInfo and MetronInfo metadata
        - Page extraction and manipulation
        - Archive validation and format detection
        - Metadata validation with schema version detection
        - Export capabilities (e.g., CBR to CBZ conversion / CBT to CBZ conversion)

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
        # This needs to be initialized *before* the archivers
        self._supported_extensions: set[str] = set()
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
        if PY7ZR_AVAILABLE:
            ArchiverFactory.register_archiver(".cb7", SevenZipArchiver)
        try:
            self._archiver: Archiver = ArchiverFactory.create_archiver(self._path)
        except Exception as e:
            msg = f"Failed to create archiver for {self._path}: {e}"
            raise ComicArchiveError(msg) from e
        # Set the supported archive extensions
        self._supported_extensions = set(ArchiverFactory.get_supported_extensions())

    def _initialize_attributes(self) -> None:
        """Initialize instance attributes and set up caching system."""
        # Use constants for filenames
        self._ci_xml_filename: str = COMIC_RACK_FILENAME
        self._mi_xml_filename: str = METRON_INFO_FILENAME

        # Initialize cache and metadata format registry
        self._cache = ComicCache()
        self._metadata_registry = MetadataFormatRegistry(self)

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
        self._cache.reset()

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

        1. It's a supported archive based on it's extension
        2. It contains at least one image file

        Returns:
            bool: True if the file appears to be a comic archive, False otherwise.

        Note:
            This is a heuristic check and may not catch all edge cases.
            Use is_valid_comic() for a more comprehensive validation.

        """
        return (self._path.suffix.lower() in self._supported_extensions) and (
            self.get_number_of_pages() > 0
        )

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
        if self._cache.page_list is not None:
            return self._cache.page_list

        try:
            # Get the list of file names in the archive
            files = self._archiver.get_filename_list()

            # Sort files if requested (case-insensitive natural sort)
            if sort_list:
                files = natsorted(files, alg=ns.IGNORECASE)

            # Filter for image files only
            self._cache.page_list = [str(name) for name in files if self.is_image(Path(str(name)))]

        except Exception:
            logger.exception("Error getting page list from %s", self._path)
            self._cache.page_list = []

        return self._cache.page_list

    def get_number_of_pages(self) -> int:
        """Get the total number of pages (images) in the archive.

        Returns:
            int: The number of image files in the archive.

        Note:
            This count includes only supported image formats and excludes hidden files.
            The result is cached for performance.

        """
        if self._cache.page_count is None:
            self._cache.page_count = len(self.get_page_name_list())
        return self._cache.page_count

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
        reader = self._metadata_registry.get_reader(metadata_format)
        if reader is None:
            logger.warning("Unknown metadata format: %s", metadata_format)
            return Metadata()

        return reader()

    def _read_comicinfo(self) -> Metadata:
        """Read and parse ComicInfo metadata from the archive.

        Returns:
            Metadata: The parsed ComicInfo metadata.

        """
        if self._cache.metadata is not None:
            return self._cache.metadata

        self._cache.metadata = self._parse_metadata(self.read_raw_ci_metadata(), ComicInfo())
        self._validate_and_fix_page_list()
        return self._cache.metadata

    def _read_metroninfo(self) -> Metadata:
        """Read and parse MetronInfo metadata from the archive.

        Returns:
            Metadata: The parsed MetronInfo metadata.

        """
        if self._cache.metadata is not None:
            return self._cache.metadata

        self._cache.metadata = self._parse_metadata(self.read_raw_mi_metadata(), MetronInfo())
        self._validate_and_fix_page_list()
        return self._cache.metadata

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
        if self._cache.metadata is None:
            return

        actual_page_count = self.get_number_of_pages()
        metadata_page_count = len(self._cache.metadata.pages)

        # If page counts don't match, reset the page list
        if metadata_page_count not in (0, actual_page_count):
            logger.warning(
                "Page count mismatch in %s: metadata has %d pages, archive has %d",
                self._path,
                metadata_page_count,
                actual_page_count,
            )
            self._cache.metadata.pages = []

        # Set default page list if empty
        if not self._cache.metadata.pages:
            self._cache.metadata.set_default_page_list(actual_page_count)

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
        return self._metadata_registry.get_filename(metadata_format)

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

        Serializes metadata to XML and writes it to the archive. ComicInfo format includes
        detailed page information (slower), while MetronInfo format is faster but less detailed.

        Args:
            metadata: Metadata object to write.
            metadata_format: Format to use (COMIC_INFO or METRON_INFO).

        Returns:
            bool: True if successful, False if failed (read-only archive, I/O errors).

        Raises:
            ComicMetadataError: If metadata format is not supported.

        Examples:
            >>> comic = Comic("example.cbz")
            >>> metadata = Metadata()
            >>> metadata.series = "Amazing Spider-Man"
            >>> comic.write_metadata(metadata, MetadataFormat.COMIC_INFO)

        """
        if not self.is_writable():
            logger.warning("Cannot write metadata to read-only archive: %s", self._path)
            return False

        writer = self._metadata_registry.get_writer(metadata_format)
        if writer is None:
            msg = f"Unsupported metadata format: {metadata_format}"
            raise ComicMetadataError(msg)

        return writer(metadata)

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
                    self._cache.has_ci = True
                elif filename == self._mi_xml_filename:
                    self._cache.has_mi = True

            return self._successful_write(write_success, metadata)

        except Exception:
            logger.exception("Error writing metadata to %s", self._path)
            return False

    def remove_metadata(self, metadata_format_list: list[MetadataFormat]) -> bool:
        """Remove metadata from the comic archive.

        Args:
            metadata_format_list: A list of metadata formats to remove.

        Returns:
            bool: True if any metadata was successfully removed or didn't exist,
                 False if an error occurred.

        Examples:
            >>> comic = Comic(Path("example.cbz"))
            >>> success = comic.remove_metadata([MetadataFormat.COMIC_INFO])
            >>> if success:
            ...     print("ComicInfo metadata removed")

        Note:
            - If the metadata doesn't exist, this method returns True
            - The archive must be writable
            - All metadata files matching the format are removed (case-insensitive)

        """
        supported_formats = {MetadataFormat.COMIC_INFO, MetadataFormat.METRON_INFO}

        if not any(fmt in supported_formats for fmt in metadata_format_list):
            logger.warning("Unsupported metadata formats for removal: %s", metadata_format_list)
            return False

        if not any(self.has_metadata(fmt) for fmt in metadata_format_list):
            logger.info("No metadata found in %s", self._path)
            return True  # Already removed, consider it success

        return self._remove_metadata_files(metadata_format_list)

    def _metadata_present(self, metadata_format_filenames: list[str]) -> list[str]:
        """Find all metadata files present in the archive (case-insensitive).

        Args:
            metadata_format_filenames: List of metadata filenames to search for.

        Returns:
            List of actual file paths found in the archive matching the filenames.

        """
        archive_files_lower = {
            Path(str(p)).name.lower(): str(p) for p in self._archiver.get_filename_list()
        }
        return [
            archive_files_lower[filename.lower()]
            for filename in metadata_format_filenames
            if filename.lower() in archive_files_lower
        ]

    def _remove_metadata_files(self, metadata_format_list: list[MetadataFormat]) -> bool:
        """Remove metadata files from the archive.

        Args:
            metadata_format_list: A list of metadata formats to remove.

        Returns:
            bool: True if successful, False otherwise.

        """
        # Build list of filenames to remove and track formats being processed
        formats_to_remove = set()
        metadata_format_filenames = []

        for fmt in metadata_format_list:
            filename = self._get_metadata_filename(fmt)
            if filename is not None:
                metadata_format_filenames.append(filename)
                formats_to_remove.add(fmt)

        all_metadata_present = self._metadata_present(metadata_format_filenames)

        if not all_metadata_present:
            return True  # No files to remove

        try:
            write_success = self._archiver.remove_files(all_metadata_present)
        except Exception:
            logger.exception("Error removing metadata from %s", self._path)
            return False

        # Update cache flags for successfully removed formats
        if write_success:
            if MetadataFormat.METRON_INFO in formats_to_remove:
                self._cache.has_mi = False
            if MetadataFormat.COMIC_INFO in formats_to_remove:
                self._cache.has_ci = False

        return self._successful_write(write_success, None)

    def remove_pages(self, pages_index: list[int]) -> bool:
        """Remove pages from the comic archive by their indices (0-based).

        This is a destructive operation that cannot be undone. Metadata caches are
        invalidated after successful removal.

        Args:
            pages_index: List of zero-based page indices to remove.

        Returns:
            bool: True if successful, False if failed.

        Raises:
            ValueError: If any page index is negative or out of range.

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
                self._cache.has_mi = False
                self._cache.has_ci = False

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
            self._cache.metadata = metadata
        self._reset_cache()
        return write_success

    def _has_metadata_file(self, cache_attr: str, filename_attr: str) -> bool:
        """Check if a metadata file exists in the archive.

        Args:
            cache_attr: The cache attribute name for the cached result (e.g., 'has_ci').
            filename_attr: The attribute name for the filename.

        Returns:
            True if the metadata file exists, False otherwise.

        """
        cached_result = getattr(self._cache, cache_attr)
        if cached_result is not None:
            return cached_result

        if not self.seems_to_be_a_comic_archive():
            setattr(self._cache, cache_attr, False)
            return False

        return self._check_metadata_file_exists(cache_attr, filename_attr)

    def _check_metadata_file_exists(self, cache_attr: str, filename_attr: str) -> bool:
        """Check if metadata file exists in archive.

        Args:
            cache_attr: The cache attribute name for caching the result.
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
            setattr(self._cache, cache_attr, result)
        except Exception:
            logger.exception("Error checking for metadata file in %s", self._path)
            setattr(self._cache, cache_attr, False)
            return False
        else:
            return result

    def _has_comicinfo(self) -> bool:
        """Check if the archive contains ComicInfo metadata."""
        return self._has_metadata_file("has_ci", "_ci_xml_filename")

    def _has_metroninfo(self) -> bool:
        """Check if the archive contains MetronInfo metadata."""
        return self._has_metadata_file("has_mi", "_mi_xml_filename")

    def has_metadata(self, fmt: MetadataFormat) -> bool:
        """Check if the archive contains metadata in the specified format.

        Performs case-insensitive search for metadata files. Results are cached.

        Args:
            fmt: Metadata format to check (COMIC_INFO or METRON_INFO).

        Returns:
            bool: True if metadata exists, False otherwise.

        """
        checker = self._metadata_registry.get_checker(fmt)
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

        if not PILLOW_AVAILABLE:
            logger.warning(
                "Unable to calculate page sizes since Pillow is not available: %s", self._path.name
            )
            return

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
        if not PILLOW_AVAILABLE:
            return
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

        Converts RAR/CBR, CBT, or CB7 archives to ZIP/CBZ format. Returns True immediately
        if already ZIP. Preserves all pages, metadata, and directory structure.

        Args:
            zip_filename: Path where the ZIP archive will be created (overwrites if exists).

        Returns:
            bool: True if successful or already ZIP, False if failed.

        Note:
            Large archives may require significant time and disk space for conversion.

        """
        if self._path.suffix.lower() in {".cbz", ".zip"}:
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
        """Validate metadata XML and return its schema version.

        Args:
            metadata_format: Format to validate (COMIC_INFO or METRON_INFO).

        Returns:
            SchemaVersion: Detected schema version, or SchemaVersion.Unknown if invalid/not found.

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
        """Perform comprehensive validation of the comic archive.

        Checks file existence, archive validity, and comic content (at least one image).

        Returns:
            bool: True if valid comic archive, False otherwise.

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
