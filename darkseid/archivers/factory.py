"""Factory for creating appropriate archiver instances.

This module provides a factory pattern implementation for creating archiver instances
based on file extensions. It supports automatic detection of archive types and provides
a fallback for unknown formats.

Examples:
    Basic usage of the factory:

    >>> from pathlib import Path
    >>> from darkseid.archivers.factory import ArchiverFactory
    >>>
    >>> # Create archiver for a ZIP file
    >>> zip_path = Path("comics/issue_001.cbz")
    >>> archiver = ArchiverFactory.create_archiver(zip_path)
    >>> print(archiver.name())  # "Zip"
    >>>
    >>> # Get list of files in the archive
    >>> files = archiver.get_filename_list()
    >>> print(files)  # ['page_01.jpg', 'page_02.jpg', ...]

Supported Formats:
    - ZIP files (.zip, .cbz)
    - RAR files (.rar, .cbr)
    - Unknown formats (fallback handling)

Note:
    Comic book formats (.cbz, .cbr) are treated as their underlying archive formats
    (ZIP and RAR respectively).

"""

from pathlib import Path
from typing import ClassVar, Protocol, runtime_checkable

from darkseid.archivers.archiver import Archiver
from darkseid.archivers.rar import RarArchiver
from darkseid.archivers.tar import TarArchiver
from darkseid.archivers.zip import ZipArchiver


@runtime_checkable
class ArchiverProtocol(Protocol):
    """Protocol defining the interface for archiver classes."""

    def __init__(self, path: Path) -> None:
        """Initialize the archiver with a path."""
        ...

    @staticmethod
    def name() -> str:
        """Return the name of the archiver."""
        ...


class UnknownArchiver(Archiver):
    """Fallback archiver for unsupported file types.

    This archiver is used when the file extension is not recognized by the factory.
    All operations return failure states or raise NotImplementedError to indicate
    that the archive format is not supported.

    Examples:
        >>> from pathlib import Path
        >>> archiver = UnknownArchiver(Path("file.unknown"))
        >>> archiver.name()
        'Unknown'
        >>> archiver.get_filename_list()
        []

    """

    def read_file(self, archive_file: str) -> bytes:
        """Read a file from the archive.

        This method is not implemented for unknown archive types and always raises NotImplementedError.

        Args:
            archive_file: The filename to read from the archive.

        Raises:
            NotImplementedError: Always raised for unknown archive types, indicating
                that the archive format is not supported.

        Returns:
            bytes: This method does not return; it always raises an exception.

        Examples:
            >>> archiver = UnknownArchiver(Path("file.unknown"))
            >>> archiver.read_file("some_file.txt")
            Traceback (most recent call last):
                ...
            NotImplementedError: Unknown archive format

        """
        msg = "Unknown archive format"
        raise NotImplementedError(msg)

    def write_file(self, archive_file: str, data: str | bytes) -> bool:  # noqa: ARG002
        """Write a file to the archive.

        This method is not implemented for unknown archive types and always returns False.

        Args:
            archive_file: The filename to write to the archive.
            data: The data to write to the file. Can be either string or bytes.

        Returns:
            bool: Always False, indicating that writing is not supported for unknown archive types.

        Examples:
            >>> archiver = UnknownArchiver(Path("file.unknown"))
            >>> archiver.write_file("new_file.txt", "content")
            False

        """
        return False

    def remove_file(self, archive_file: str) -> bool:  # noqa: ARG002
        """Remove a single file from the archive.

        This method is not implemented for unknown archive types and always returns False.

        Args:
            archive_file: The filename to remove from the archive.

        Returns:
            bool: Always False, indicating that file removal is not supported for unknown archive types.

        Examples:
            >>> archiver = UnknownArchiver(Path("file.unknown"))
            >>> archiver.remove_file("file_to_remove.txt")
            False

        """
        return False

    def remove_files(self, filename_list: list[str]) -> bool:  # noqa: ARG002
        """Remove multiple files from the archive.

        This method is not implemented for unknown archive types and always returns False.

        Args:
            filename_list: List of filenames to remove from the archive.

        Returns:
            bool: Always False, indicating that file removal is not supported for unknown archive types.

        Examples:
            >>> archiver = UnknownArchiver(Path("file.unknown"))
            >>> archiver.remove_files(["file1.txt", "file2.txt"])
            False

        """
        return False

    def get_filename_list(self) -> list[str]:
        """Return a list of filenames in the archive.

        For unknown archive types, this always returns an empty list since the
        archive format cannot be parsed.

        Returns:
            list[str]: Always an empty list, as filenames cannot be determined for unknown archive types.

        Examples:
            >>> archiver = UnknownArchiver(Path("file.unknown"))
            >>> archiver.get_filename_list()
            []

        """
        return []

    def test(self) -> bool:
        """Test whether the file is a RAR archive.

        Returns:
            bool: Returns False, as validity test for archive is unavailable.

        """
        return False

    def copy_from_archive(self, other_archive: Archiver) -> bool:  # noqa: ARG002
        """Copy files from another archive.

        This method is not implemented for unknown archive types and always returns False.

        Args:
            other_archive: The source archive to copy files from.

        Returns:
            bool: Always False, indicating that copying is not supported for unknown archive types.

        Examples:
            >>> source = ZipArchiver(Path("source.zip"))
            >>> target = UnknownArchiver(Path("target.unknown"))
            >>> target.copy_from_archive(source)
            False

        """
        return False

    @staticmethod
    def name() -> str:
        """Return the name of the archiver.

        Returns:
            str: Always returns "Unknown" to identify this as the fallback archiver.

        """
        return "Unknown"


class ArchiverFactory:
    """Factory for creating appropriate archiver instances based on file type.

    This factory uses the file extension to determine the appropriate archiver class
    and returns an instance configured for the given file. It supports registration
    of new archiver types and provides a fallback for unknown formats.

    The factory maintains a mapping of file extensions to archiver classes and can
    be extended at runtime by registering new archiver types.

    Attributes:
        _ARCHIVER_MAP: Class variable mapping file extensions to archiver classes.

    Examples:
        Creating archivers for different file types:

        >>> from pathlib import Path
        >>>
        >>> # Create archiver for ZIP file
        >>> zip_archiver = ArchiverFactory.create_archiver(Path("archive.zip"))
        >>> print(zip_archiver.name())  # "Zip"
        >>>
        >>> # Create archiver for RAR file
        >>> rar_archiver = ArchiverFactory.create_archiver(Path("archive.rar"))
        >>> print(rar_archiver.name())  # "Rar"
        >>>
        >>> # Create archiver for unknown format
        >>> unknown_archiver = ArchiverFactory.create_archiver(Path("archive.7z"))
        >>> print(unknown_archiver.name())  # "Unknown"

        Registering a new archiver type:

        >>> from darkseid.archivers.seven_zip import SevenZipArchiver
        >>> ArchiverFactory.register_archiver(".7z", SevenZipArchiver)
        >>> archiver = ArchiverFactory.create_archiver(Path("archive.7z"))
        >>> print(archiver.name())  # "SevenZip"

    """

    _ARCHIVER_MAP: ClassVar[dict[str, type[Archiver]]] = {
        ".zip": ZipArchiver,
        ".cbz": ZipArchiver,  # Comic book ZIP format
        ".rar": RarArchiver,
        ".cbr": RarArchiver,  # Comic book RAR format
        ".cbt": TarArchiver,  # Comic book TAR format
    }

    @classmethod
    def create_archiver(cls, path: Path) -> Archiver:
        """Create an appropriate archiver for the given file.

        Analyzes the file extension and returns an archiver instance capable of
        handling that file type. If the extension is not recognized, returns
        an UnknownArchiver instance.

        Args:
            path: Path to the archive file. The file extension is used to determine
                the appropriate archiver type.

        Returns:
            Archiver: An archiver instance appropriate for the file type. This will be
                a specific archiver (ZipArchiver, RarArchiver, etc.) for known formats,
                or UnknownArchiver for unsupported formats.

        Examples:
            >>> from pathlib import Path
            >>>
            >>> # Create archiver for different file types
            >>> zip_archiver = ArchiverFactory.create_archiver(Path("comics/issue.cbz"))
            >>> rar_archiver = ArchiverFactory.create_archiver(Path("archive.rar"))
            >>> unknown_archiver = ArchiverFactory.create_archiver(Path("data.tar.gz"))
            >>>
            >>> print(zip_archiver.name())      # "Zip"
            >>> print(rar_archiver.name())      # "Rar"
            >>> print(unknown_archiver.name())  # "Unknown"

        """
        suffix = path.suffix.lower()
        archiver_class = cls._ARCHIVER_MAP.get(suffix, UnknownArchiver)
        return archiver_class(path)

    @classmethod
    def register_archiver(cls, extension: str, archiver_class: type[Archiver]) -> None:
        """Register a new archiver for a file extension.

        Adds a new archiver class to the factory's mapping, allowing it to handle
        additional file types. The extension is automatically converted to lowercase
        for consistent matching.

        Args:
            extension: File extension including the dot (e.g., '.7z', '.tar.gz').
                The extension will be converted to lowercase for storage.
            archiver_class: Archiver class that should handle files with this extension.
                Must be a subclass of Archiver and implement the required interface.

        Raises:
            TypeError: If archiver_class is not a subclass of Archiver.

        Examples:
            >>> from darkseid.archivers.seven_zip import SevenZipArchiver
            >>> from darkseid.archivers.tar import TarArchiver
            >>>
            >>> # Register new archiver types
            >>> ArchiverFactory.register_archiver(".7z", SevenZipArchiver)
            >>> ArchiverFactory.register_archiver(".tar.gz", TarArchiver)
            >>>
            >>> # Now these extensions are supported
            >>> archiver = ArchiverFactory.create_archiver(Path("archive.7z"))
            >>> print(archiver.name())  # "SevenZip"

            >>> # Case insensitive registration
            >>> ArchiverFactory.register_archiver(".TAR", TarArchiver)
            >>> archiver = ArchiverFactory.create_archiver(Path("archive.tar"))
            >>> print(archiver.name())  # "Tar"

        """
        if not issubclass(archiver_class, Archiver):
            msg = f"archiver_class must be a subclass of Archiver, got {archiver_class}"
            raise TypeError(msg)

        cls._ARCHIVER_MAP[extension.lower()] = archiver_class

    @classmethod
    def get_supported_extensions(cls) -> list[str]:
        """Get list of supported file extensions.

        Returns a list of all file extensions that the factory can handle.
        This includes both built-in extensions and any extensions registered
        via register_archiver().

        Returns:
            list[str]: Sorted list of supported file extensions, including the dot
                (e.g., ['.cbr', '.cbz', '.rar', '.zip']).

        Examples:
            >>> extensions = ArchiverFactory.get_supported_extensions()
            >>> print(extensions)  # ['.cbr', '.cbz', '.rar', '.zip']
            >>>
            >>> # After registering new types
            >>> ArchiverFactory.register_archiver(".7z", SevenZipArchiver)
            >>> extensions = ArchiverFactory.get_supported_extensions()
            >>> print(extensions)  # ['.7z', '.cbr', '.cbz', '.rar', '.zip']

        """
        return sorted(cls._ARCHIVER_MAP.keys())

    @classmethod
    def is_supported(cls, path: Path) -> bool:
        """Check if a file extension is supported by the factory.

        Args:
            path: Path to check for support.

        Returns:
            bool: True if the file extension is supported, False otherwise.

        Examples:
            >>> from pathlib import Path
            >>>
            >>> ArchiverFactory.is_supported(Path("archive.zip"))  # True
            >>> ArchiverFactory.is_supported(Path("archive.7z"))   # False
            >>>
            >>> # After registering .7z support
            >>> ArchiverFactory.register_archiver(".7z", SevenZipArchiver)
            >>> ArchiverFactory.is_supported(Path("archive.7z"))   # True

        """
        suffix = path.suffix.lower()
        return suffix in cls._ARCHIVER_MAP

    @classmethod
    def clear_registry(cls) -> None:
        """Clear all registered archivers and restore defaults.

        This method removes all archiver registrations and restores the factory
        to its default state with only built-in archiver types.

        Warning:
            This method will remove all custom archiver registrations. Use with caution.

        Examples:
            >>> # After registering custom archivers
            >>> ArchiverFactory.register_archiver(".7z", SevenZipArchiver)
            >>> len(ArchiverFactory.get_supported_extensions())  # 5
            >>>
            >>> # Clear and restore defaults
            >>> ArchiverFactory.clear_registry()
            >>> len(ArchiverFactory.get_supported_extensions())  # 4

        """
        cls._ARCHIVER_MAP = {
            ".zip": ZipArchiver,
            ".cbz": ZipArchiver,
            ".rar": RarArchiver,
            ".cbr": RarArchiver,
        }
