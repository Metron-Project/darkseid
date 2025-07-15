"""7zip archiver implementation using py7zr library.

This module provides a concrete implementation of the Archiver base class
for handling 7zip archives using the py7zr library. It supports reading,
writing, and managing files within 7zip archives.

Requirements:
    py7zr >= 1.0

Examples:
    Basic usage:

    >>> from pathlib import Path
    >>> from darkseid.archivers.sevenzip import SevenZipArchiver
    >>>
    >>> # Create a new 7zip archive
    >>> with SevenZipArchiver(Path("example.cb7")) as archive:
    ...     archive.write_file("hello.txt", "Hello, World!")
    ...     archive.write_file("data.json", '{"key": "value"}')
    ...
    >>> # Read from existing archive
    >>> with SevenZipArchiver(Path("example.cb7")) as archive:
    ...     content = archive.read_file("hello.txt")
    ...     print(content.decode())  # Output: Hello, World!
    ...     files = archive.get_filename_list()
    ...     print(files)  # Output: ['hello.txt', 'data.json']

    Converting from other archive formats:

    >>> with ZipArchiver(Path("source.zip")) as source:
    ...     with SevenZipArchiver(Path("converted.cb7")) as dest:
    ...         dest.copy_from_archive(source)

"""

from __future__ import annotations

import io
import logging
from sys import maxsize
from typing import TYPE_CHECKING

from darkseid.archivers.archiver import Archiver, ArchiverReadError, ArchiverWriteError

# Optional dependency handling
try:
    import py7zr

    PY7ZR_AVAILABLE = True
except ImportError:
    PY7ZR_AVAILABLE = False
    py7zr = None

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class SevenZipArchiver(Archiver):
    """7zip archiver implementation using py7zr library.

    This class provides a concrete implementation of the Archiver interface
    for working with 7zip archives. It uses the py7zr library for all
    archive operations.

    Features:
        - Full read/write support for 7zip archives
        - Automatic compression using LZMA2 algorithm
        - Efficient batch operations
        - Context manager support for automatic cleanup

    Limitations:
        - Requires py7zr >= 1.0 to be installed
        - Some 7zip features may not be supported depending on py7zr version
        - Large archives may consume significant memory during operations

    Thread Safety:
        This class is not thread-safe. Do not use the same instance from
        multiple threads simultaneously.

    Examples:
        Creating and writing to a 7zip archive:

        >>> with SevenZipArchiver(Path("documents.cb7")) as archive:
        ...     archive.write_file("readme.txt", "This is a readme file")
        ...     archive.write_file("config/settings.json", '{"debug": true}')
        ...
        >>> # Archive is automatically closed and finalized

        Reading from an existing 7zip archive:

        >>> with SevenZipArchiver(Path("documents.cb7")) as archive:
        ...     if archive.exists("readme.txt"):
        ...         content = archive.read_file("readme.txt")
        ...         print(content.decode())
        ...
        ...     all_files = archive.get_filename_list()
        ...     for filename in all_files:
        ...         print(f"Found file: {filename}")

    """

    def __init__(self, path: Path) -> None:
        """Initialize a SevenZipArchiver instance.

        Args:
            path: Path to the 7zip archive file.

        Raises:
            ImportError: If py7zr library is not installed.
            ValueError: If the path doesn't have a .cb7 extension.

        """
        if not PY7ZR_AVAILABLE:
            msg = (
                "py7zr library is required for 7zip support. "
                "Install it with: pip install py7zr>=1.0"
            )
            raise ImportError(msg)

        if path.suffix.lower() != ".cb7":
            msg = f"SevenZipArchiver requires .cb7 extension, got: {path.suffix}"
            raise ValueError(msg)

        super().__init__(path)
        self._archive: py7zr.SevenZipFile | None = None

    def _ensure_archive_open(self, mode: str = "r") -> py7zr.SevenZipFile:
        """Ensure the archive is open in the specified mode.

        Args:
            mode: Open mode - 'r' for read, 'w' for write, 'a' for append.

        Returns:
            The opened py7zr.SevenZipFile instance.

        Raises:
            ArchiverReadError: If opening for read fails.
            ArchiverWriteError: If opening for write fails.

        """
        if self._archive is None or self._archive.mode != mode:
            self._close_archive()
            try:
                if mode == "r":
                    if not self._path.exists():
                        msg = f"Archive file does not exist: {self._path}"
                        raise ArchiverReadError(msg)  # noqa: TRY301
                    self._archive = py7zr.SevenZipFile(self._path, mode=mode)
                else:
                    # For write mode, create parent directories if needed
                    self._path.parent.mkdir(parents=True, exist_ok=True)
                    self._archive = py7zr.SevenZipFile(self._path, mode=mode)
            except Exception as e:
                error_msg = f"Failed to open 7zip archive in mode '{mode}': {e}"
                if mode == "r":
                    raise ArchiverReadError(error_msg) from e
                raise ArchiverWriteError(error_msg) from e

        return self._archive

    def _close_archive(self) -> None:
        """Close the current archive if it's open."""
        if self._archive is not None:
            try:
                self._archive.close()
            except Exception as e:
                logger.warning("Error closing 7zip archive: %s", e)
            finally:
                self._archive = None

    def read_file(self, archive_file: str) -> bytes:
        """Read the contents of a file from the 7zip archive.

        Args:
            archive_file: Path of the file within the archive.

        Returns:
            The complete file contents as bytes.

        Raises:
            ArchiverReadError: If the file cannot be read.

        """
        try:
            archive = self._ensure_archive_open("r")

            # py7zr expects consistent path separators
            normalized_path = archive_file.replace("\\", "/")

            seven_zip_factory = py7zr.io.BytesIOFactory(maxsize)

            # Read the specific file
            archive.extract(targets=[normalized_path], factory=seven_zip_factory)
            file_obj = seven_zip_factory.products.get(normalized_path)
            if file_obj is None:
                msg = f"File not found in archive: {archive_file}"
                raise ArchiverReadError(msg)  # noqa: TRY301
            return file_obj.read()
        except ArchiverReadError:
            raise
        except Exception as e:
            self._handle_error("read", archive_file, e)
            msg = f"Failed to read file '{archive_file}': {e}"
            raise ArchiverReadError(msg) from e

    def write_file(self, archive_file: str, data: str | bytes) -> bool:
        """Write data to a file in the 7zip archive.

        Args:
            archive_file: Path of the file within the archive.
            data: Data to write to the file.

        Returns:
            True if successful, False otherwise.

        Raises:
            ArchiverWriteError: If the write operation fails.

        """
        try:
            # Convert string to bytes if necessary
            if isinstance(data, str):
                data = data.encode("utf-8")

            archive = self._ensure_archive_open("w")

            # py7zr expects consistent path separators
            normalized_path = archive_file.replace("\\", "/")

            # Create a file-like object from the data
            file_obj = io.BytesIO(data)

            # Write the file to the archive
            archive.writestr(file_obj.getvalue(), normalized_path)
        except Exception as e:
            self._handle_error("write", archive_file, e)
            msg = f"Failed to write file '{archive_file}': {e}"
            raise ArchiverWriteError(msg) from e
        else:
            return True

    def remove_file(self, archive_file: str) -> bool:
        """Remove a file from the 7zip archive.

        Note: py7zr doesn't support direct file removal from existing archives.
        This method will recreate the archive without the specified file.

        Args:
            archive_file: Path of the file to remove.

        Returns:
            True if successful, False otherwise.

        """
        try:
            # Get list of all files except the one to remove
            all_files = self.get_filename_list()
            normalized_path = archive_file.replace("\\", "/")

            if normalized_path not in all_files:
                # File doesn't exist, consider it successfully "removed"
                return True

            # Read all files except the one to remove
            archive = self._ensure_archive_open("r")
            files_to_keep = [f for f in all_files if f != normalized_path]

            if not files_to_keep:
                # If no files to keep, just close and recreate empty archive
                self._close_archive()
                self._path.unlink(missing_ok=True)
                return True

            factory = py7zr.io.BytesIOFactory(maxsize)
            archive.extract(targets=files_to_keep, factory=factory)

            # Read data for files to keep
            file_data = factory.products
            self._close_archive()

            # Recreate archive with remaining files
            archive = self._ensure_archive_open("w")
            for filename, data in file_data.items():
                content = data.read() if hasattr(data, "read") else data
                archive.writestr(content, filename)
        except Exception as e:
            self._handle_error("remove", archive_file, e)
            return False
        else:
            return True

    def remove_files(self, filename_list: list[str]) -> bool:
        """Remove multiple files from the 7zip archive.

        Args:
            filename_list: List of file paths to remove.

        Returns:
            True if all files were successfully removed, False otherwise.

        """
        try:
            # Get list of all files
            all_files = self.get_filename_list()
            normalized_files_to_remove = {f.replace("\\", "/") for f in filename_list}

            # Filter out files that don't exist
            files_to_keep = [f for f in all_files if f not in normalized_files_to_remove]

            if len(files_to_keep) == len(all_files):
                # No files to remove (all files in filename_list don't exist)
                return True

            if not files_to_keep:
                # If no files to keep, just close and recreate empty archive
                self._close_archive()
                self._path.unlink(missing_ok=True)
                return True

            # Read data for files to keep
            archive = self._ensure_archive_open("r")
            factory = py7zr.io.BytesIOFactory(maxsize)
            archive.extract(targets=files_to_keep, factory=factory)
            file_data = factory.products
            self._close_archive()

            # Recreate archive with remaining files
            archive = self._ensure_archive_open("w")
            for filename, data in file_data.items():
                content = data.read() if hasattr(data, "read") else data
                archive.writestr(content, filename)
        except Exception as e:
            self._handle_error("remove_files", str(filename_list), e)
            return False
        else:
            return True

    def get_filename_list(self) -> list[str]:
        """Get a list of all files in the 7zip archive.

        Returns:
            List of file paths within the archive.

        """
        try:
            if not self._path.exists():
                return []

            archive = self._ensure_archive_open("r")
            return sorted(archive.getnames())

        except Exception as e:
            self._handle_error("get_filename_list", str(self._path), e)
            return []

    def test(self) -> bool:
        """Test the integrity of the 7zip archive.

        Performs a test operation on the archive to verify its integrity
        and ensure it can be read without errors. This is useful for
        validating archive files before performing operations on them.

        Returns:
            True if the archive passes integrity tests, False otherwise.

        Examples:
            >>> archive = SevenZipArchiver(Path("test.cb7"))
            >>> if archive.test():
            ...     print("Archive is valid")
            ...     # Safe to proceed with operations
            ... else:
            ...     print("Archive is corrupted or invalid")

            >>> # Test before copying
            >>> if source_archive.test() and dest_archive.test():
            ...     dest_archive.copy_from_archive(source_archive)

        Note:
            This method will return False if the archive file doesn't exist
            or if py7zr encounters any errors while testing the archive.
            The test operation reads the archive's metadata and verifies
            the integrity of compressed data without extracting files.

        """
        try:
            if not self._path.exists():
                return False

            archive = self._ensure_archive_open("r")

            # py7zr's test method verifies archive integrity
            result = archive.testzip()
        except Exception as e:
            self._handle_error("test", str(self._path), e)
            return False
        else:
            # testzip() returns None if archive is OK, or the name of the first bad file
            return result is None

    def copy_from_archive(self, other_archive: Archiver) -> bool:  # noqa: ARG002
        """Copy files from another archive to this 7zip archive.

        Args:
            other_archive: Source archive to copy files from.

        Returns:
            False since this functionality is not present.

        Note:
            If the user wants to decrease comic size, they are better off optimizing the images within comic that creating a 7zip archive.

        """
        return False

    def __exit__(self, *_: object) -> None:
        """Context manager exit - close the archive."""
        self._close_archive()
