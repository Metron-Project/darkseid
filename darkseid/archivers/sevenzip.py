"""7-Zip archiver implementation using py7zr library.

This module provides 7-Zip archive support for the darkseid archiver system.
It implements the Archiver abstract base class to provide consistent interface
for 7-Zip archive operations.

Requirements:
    py7zr < 1.0.0

Examples:
    Basic usage:

    >>> from pathlib import Path
    >>> from darkseid.archivers.sevenzip import SevenZipArchiver
    >>>
    >>> # Create a new 7z archive
    >>> with SevenZipArchiver(Path("example.cb7")) as archive:
    ...     archive.write_file("hello.txt", "Hello, World!")
    ...     archive.write_file("data.json", '{"key": "value"}')
    ...
    ...     # Read files from the archive
    ...     content = archive.read_file("hello.txt")
    ...     print(content.decode())  # Output: Hello, World!
    ...
    ...     # List all files
    ...     files = archive.get_filename_list()
    ...     print(files)  # Output: ['hello.txt', 'data.json']

    Reading existing archives:

    >>> with SevenZipArchiver(Path("existing.cb7")) as archive:
    ...     if archive.exists("config.txt"):
    ...         config = archive.read_file("config.txt").decode()
    ...         print(f"Config: {config}")

"""

from __future__ import annotations

import logging
from contextlib import suppress

try:
    import py7zr

    PY7ZR_AVAILABLE = True
except ImportError:
    PY7ZR_AVAILABLE = False
    py7zr = None

from typing import TYPE_CHECKING

from typing_extensions import Self

from darkseid.archivers import Archiver, ArchiverReadError, ArchiverWriteError

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class SevenZipArchiver(Archiver):
    """7-Zip archiver implementation using py7zr library.

    This class provides 7-Zip archive support following the Archiver interface.
    It handles reading, writing, and management of 7-Zip archives using the
    py7zr library.

    Features:
        - Full read/write support for 7-Zip archives
        - Compression with LZMA algorithm
        - Efficient batch operations
        - Memory-efficient file operations

    Limitations:
        - Requires py7zr < 1.0.0 to be installed
        - Some advanced 7-Zip features may not be supported
        - Performance may be slower than native 7-Zip for very large archives
        - No password protection support

    Thread Safety:
        This class is not thread-safe. Use separate instances for concurrent access.

    Examples:
        Creating and writing to a 7z archive:

        >>> archive = SevenZipArchiver(Path("test.cb7"))
        >>> with archive:
        ...     archive.write_file("readme.txt", "This is a readme file")
        ...     archive.write_file("data/page1.jpg", b'bogus data')

        Reading from an existing 7z archive:

        >>> with SevenZipArchiver(Path("existing.cb7")) as archive:
        ...     files = archive.get_filename_list()
        ...     for filename in files:
        ...         content = archive.read_file(filename)
        ...         print(f"{filename}: {len(content)} bytes")

    """

    def __init__(self, path: Path) -> None:
        """Initialize SevenZipArchiver.

        Args:
            path: Path to the 7-Zip archive file.

        """
        super().__init__(path)
        self._archive: py7zr.SevenZipFile | None = None
        self._file_cache: dict[str, bytes] = {}
        self._filename_list_cache: list[str] | None = None

    def __enter__(self) -> Self:
        """Context manager entry for 7-Zip archive operations."""
        return self

    def __exit__(self, *_: object) -> None:
        """Context manager exit with proper cleanup."""
        if self._archive is not None:
            try:
                self._archive.close()
            except Exception as e:
                logger.warning("Error closing 7z archive: %s", e)
            finally:
                self._archive = None

        # Clear caches
        self._file_cache.clear()
        self._filename_list_cache = None

    def _get_archive_for_reading(self) -> py7zr.SevenZipFile:
        """Get archive instance for reading operations."""
        if not self._path.exists():
            msg = f"Archive file does not exist: {self._path}"
            raise ArchiverReadError(msg)

        try:
            return py7zr.SevenZipFile(self._path, mode="r")
        except Exception as e:
            self._handle_error("open_for_read", str(self._path), e)
            msg = f"Failed to open archive for reading: {self._path}"
            raise ArchiverReadError(msg) from e

    def _get_archive_for_writing(self) -> py7zr.SevenZipFile:
        """Get archive instance for writing operations."""
        try:
            # Create parent directories if they don't exist
            self._path.parent.mkdir(parents=True, exist_ok=True)
            return py7zr.SevenZipFile(self._path, mode="w")
        except Exception as e:
            self._handle_error("open_for_write", str(self._path), e)
            msg = f"Failed to open archive for writing: {self._path}"
            raise ArchiverWriteError(msg) from e

    def _load_file_cache(self) -> None:
        """Load all files into memory cache for efficient access."""
        if self._file_cache:
            return  # Already loaded

        try:
            with self._get_archive_for_reading() as archive:
                # Read all files to memory
                extracted = archive.readall()
                for filename, file_info in extracted.items():
                    if hasattr(file_info, "read"):
                        # file_info is a file-like object
                        self._file_cache[filename] = file_info.read()
                    else:
                        # file_info might be bytes directly, tho this shouldn't happen
                        self._file_cache[filename] = file_info  # Do we need to cast this?
        except Exception as e:
            self._handle_error("load_cache", str(self._path), e)
            # Continue without cache - individual operations will handle errors

    def read_file(self, archive_file: str) -> bytes:
        """Read a file from the 7z archive.

        Args:
            archive_file: Path of the file within the archive.

        Returns:
            The file contents as bytes.

        Raises:
            ArchiverReadError: If the file cannot be read.

        """
        # Try cache first
        if archive_file in self._file_cache:
            return self._file_cache[archive_file]

        try:
            with self._get_archive_for_reading() as archive:
                # read specific file
                extracted = archive.read(targets=[archive_file])

                if archive_file not in extracted:
                    msg = f"File not found in archive: {archive_file}"
                    raise ArchiverReadError(msg)  # noqa: TRY301

                file_data = extracted[archive_file]

                # Handle different return types from py7zr
                if hasattr(file_data, "read"):
                    content = file_data.read()
                elif isinstance(file_data, bytes):
                    content = file_data
                else:
                    # Convert to bytes if needed
                    content = bytes(file_data)

                # Cache the result
                self._file_cache[archive_file] = content
                return content

        except ArchiverReadError:
            raise
        except Exception as e:
            self._handle_error("read", archive_file, e)
            msg = f"Failed to read file {archive_file}"
            raise ArchiverReadError(msg) from e

    def write_file(self, archive_file: str, data: str | bytes) -> bool:
        """Write a file to the 7z archive.

        Args:
            archive_file: Path of the file within the archive.
            data: Data to write (string or bytes).

        Returns:
            True if successful, False otherwise.

        Raises:
            ArchiverWriteError: If the write operation fails.

        """
        try:
            # Convert string to bytes if needed
            file_data = data.encode("utf-8") if isinstance(data, str) else data

            # For 7z, we need to rewrite the entire archive
            # First, read existing files if the archive exists
            existing_files: dict[str, bytes] = {}

            if self._path.exists():
                try:
                    with self._get_archive_for_reading():
                        for filename in self.get_filename_list():
                            if filename != archive_file:  # Skip the file we're replacing
                                existing_files[filename] = self.read_file(filename)
                except Exception as e:
                    logger.warning("Could not read existing archive contents: %s", e)

            # Write new archive with all files
            with self._get_archive_for_writing() as write_archive:
                # Add existing files
                for filename, content in existing_files.items():
                    write_archive.writestr(content, filename)

                # Add new file
                write_archive.writestr(file_data, archive_file)

            # Update cache
            self._file_cache[archive_file] = file_data
            self._filename_list_cache = None  # Invalidate filename cache
        except Exception as e:
            self._handle_error("write", archive_file, e)
            msg = f"Failed to write file {archive_file}"
            raise ArchiverWriteError(msg) from e
        else:
            return True

    def remove_file(self, archive_file: str) -> bool:
        """Remove a file from the 7z archive.

        Args:
            archive_file: Path of the file to remove.

        Returns:
            True if successful, False otherwise.

        """
        try:
            if not self._path.exists():
                return True  # File doesn't exist, so removal is successful

            # Get current file list
            current_files = self.get_filename_list()

            if archive_file not in current_files:
                return True  # File doesn't exist, so removal is successful

            # Read all files except the one to remove
            remaining_files: dict[str, bytes] = {}

            for filename in current_files:
                if filename != archive_file:
                    remaining_files[filename] = self.read_file(filename)

            # Rewrite archive without the removed file
            with self._get_archive_for_writing() as write_archive:
                for filename, content in remaining_files.items():
                    write_archive.writestr(content, filename)

            # Update cache
            self._file_cache.pop(archive_file, None)
            self._filename_list_cache = None  # Invalidate filename cache
        except Exception as e:
            self._handle_error("remove", archive_file, e)
            return False
        else:
            return True

    def remove_files(self, filename_list: list[str]) -> bool:
        """Remove multiple files from the 7z archive.

        Args:
            filename_list: List of file paths to remove.

        Returns:
            True if all files were removed successfully, False otherwise.

        """
        try:
            if not self._path.exists():
                return True  # Archive doesn't exist, so removal is successful

            # Get current file list
            current_files = self.get_filename_list()
            files_to_remove = set(filename_list)

            # Read all files except those to remove
            remaining_files: dict[str, bytes] = {}

            for filename in current_files:
                if filename not in files_to_remove:
                    remaining_files[filename] = self.read_file(filename)

            # Rewrite archive without the removed files
            with self._get_archive_for_writing() as write_archive:
                for filename, content in remaining_files.items():
                    write_archive.writestr(content, filename)

            # Update cache
            for filename in filename_list:
                self._file_cache.pop(filename, None)
            self._filename_list_cache = None  # Invalidate filename cache
        except Exception as e:
            self._handle_error("remove_files", str(filename_list), e)
            return False
        else:
            return True

    def get_filename_list(self) -> list[str]:
        """Get list of all files in the 7z archive.

        Returns:
            List of file paths in the archive.

        """
        if self._filename_list_cache is not None:
            return self._filename_list_cache

        if not self._path.exists():
            self._filename_list_cache = []
            return self._filename_list_cache

        try:
            with self._get_archive_for_reading() as archive:
                # Get file list from archive
                file_list = archive.getnames()
                self._filename_list_cache = sorted(file_list)
                return self._filename_list_cache
        except Exception as e:
            self._handle_error("get_filename_list", str(self._path), e)
            self._filename_list_cache = []
            return self._filename_list_cache

    def test(self) -> bool:
        """Test whether the 7z archive is valid.

        Returns:
            True if the archive is valid, False otherwise.

        """
        with suppress(Exception):
            return py7zr.is_7zfile(self._path)
        return False

    def copy_from_archive(self, other_archive: Archiver) -> bool:
        """Attempt to copy files from another archive to the 7ZIP archive.

        Args:
            other_archive: The source archive to copy files from.

        Returns:
            False: 7ZIP support is not implemented, so this operation always fails.

        Note:
            This method logs a warning and returns False immediately.
            No actual copy operation is attempted since converting to
            7ZIP format does not make sense. If the user wants to reduce file size, they are better off using an image
            format with better compression.

        Warning:
            A warning will be logged indicating that the copy operation was attempted on a 7ZIP archive,
            including the path of the source archive.

        Examples:
            >>> seven_zip_archive = SevenZipArchiver(Path("target.rar"))
            >>> zip_archive = ZipArchiver(Path("source.zip"))
            >>> result = seven_zip_archive.copy_from_archive(zip_archive)
            >>> print(f"Copy successful: {result}")  # Will print: Copy successful: False

        """
        logger.warning("Cannot copy to 7ZIP archive from: %s", other_archive.path)
        return False
