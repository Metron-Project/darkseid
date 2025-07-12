"""7zip archiver implementation for the Archiver base class.

This module provides a concrete implementation of the Archiver interface
for working with 7zip archives (.cb7 files). It uses the py7zr library
for 7zip operations.

The SevenZipArchiver class supports all standard archiver operations
including reading, writing, and managing files within 7zip archives.

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
    ...     # Read files from the archive
    ...     content = archive.read_file("hello.txt")
    ...     print(content.decode())  # Output: Hello, World!
    ...
    ...     # List all files
    ...     files = archive.get_filename_list()
    ...     print(files)  # Output: ['hello.txt', 'data.json']

    Reading from an existing archive:

    >>> with SevenZipArchiver(Path("existing.cb7")) as archive:
    ...     if archive.exists("config.txt"):
    ...         config = archive.read_file("config.txt").decode()
    ...         print(config)

Requirements:
    - py7zr: Install with `pip install py7zr`

"""

from __future__ import annotations

import io
import logging
from contextlib import suppress
from typing import TYPE_CHECKING

from darkseid.archivers.archiver import Archiver, ArchiverReadError, ArchiverWriteError

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import py7zr

    PY7ZR_AVAILABLE = True
except ImportError:
    PY7ZR_AVAILABLE = False
    logger.warning("py7zr library not available. SevenZipArchiver will not function.")


class SevenZipArchiver(Archiver):
    """7zip archiver implementation.

    Provides read and write operations for 7zip archives using the py7zr library.
    Supports all standard archiver operations including file reading, writing,
    removal, and batch operations.

    Features:
        - Full 7zip format support through py7zr
        - Efficient batch operations for multiple files
        - Automatic directory structure creation
        - Context manager support for resource management
        - Comprehensive error handling with specific exceptions

    Limitations:
        - Requires py7zr library to be installed
        - May not support all 7zip compression methods
        - Large archives may consume significant memory

    Thread Safety:
        This class is not thread-safe. External synchronization is required
        for concurrent access to the same archive file.

    Examples:
        Creating and writing to a 7zip archive:

        >>> with SevenZipArchiver(Path("documents.cb7")) as archive:
        ...     archive.write_file("readme.txt", "This is a readme file")
        ...     archive.write_file("data/config.json", '{"version": "1.0"}')
        ...
        ...     # Verify the files were written
        ...     files = archive.get_filename_list()
        ...     print(f"Files in archive: {files}")

        Reading from an existing 7zip archive:

        >>> with SevenZipArchiver(Path("existing.cb7")) as archive:
        ...     files = archive.get_filename_list()
        ...     for filename in files:
        ...         if filename.endswith('.txt'):
        ...             content = archive.read_file(filename)
        ...             print(f"{filename}: {content.decode()}")

    """

    def __init__(self, path: Path) -> None:
        """Initialize a SevenZipArchiver with the specified path.

        Args:
            path: Path to the 7zip archive file. Should have a .cb7 extension.

        Raises:
            ImportError: If py7zr library is not installed.
            ValueError: If the file extension is not .cb7.

        """
        if not PY7ZR_AVAILABLE:
            msg = (
                "py7zr library is required for SevenZipArchiver. Install it with: pip install py7zr"
            )
            raise ImportError(msg)

        if not path.name.lower().endswith(".cb7"):
            logger.warning("File does not have .cb7 extension: %s", path)

        super().__init__(path)
        self._file_list_cache: list[str] | None = None

    def _clear_cache(self) -> None:
        """Clear the internal file list cache."""
        self._file_list_cache = None

    def read_file(self, archive_file: str) -> bytes:
        """Read the contents of a file from the 7zip archive.

        Args:
            archive_file: Path of the file within the archive.

        Returns:
            The complete file contents as bytes.

        Raises:
            ArchiverReadError: If the file cannot be read or doesn't exist.

        """
        if not self.path.exists():
            msg = f"Archive file does not exist: {self.path}"
            raise ArchiverReadError(msg)

        try:
            with py7zr.SevenZipFile(self.path, mode="r") as archive:
                # Extract the specific file to memory
                extracted = archive.read([archive_file])

                if archive_file not in extracted:
                    msg = f"File not found in archive: {archive_file}"
                    raise ArchiverReadError(msg)  # noqa: TRY301

                file_data = extracted[archive_file]
                if hasattr(file_data, "read"):
                    return file_data.read()
                return file_data

        except py7zr.exceptions.Bad7zFile as e:
            self._handle_error("read", archive_file, e)
            msg = f"Invalid 7zip file: {self.path}"
            raise ArchiverReadError(msg) from e
        except Exception as e:
            self._handle_error("read", archive_file, e)
            msg = f"Failed to read {archive_file} from {self.path}"
            raise ArchiverReadError(msg) from e

    def write_file(self, archive_file: str, data: str | bytes) -> bool:
        """Write data to a file in the 7zip archive.

        Args:
            archive_file: Path of the file within the archive.
            data: Data to write to the file.

        Returns:
            True if the write operation was successful, False otherwise.

        Raises:
            ArchiverWriteError: If the write operation fails.

        """
        try:
            # Convert string to bytes if necessary
            if isinstance(data, str):
                data = data.encode("utf-8")

            # Read existing archive contents if it exists
            existing_files = {}
            if self.path.exists():
                try:
                    with py7zr.SevenZipFile(self.path, mode="r") as archive:
                        existing_files = archive.readall()
                except Exception as e:
                    logger.warning("Could not read existing archive contents: %s", e)

            # Add or update the file
            existing_files[archive_file] = io.BytesIO(data)

            # Write the updated archive
            with py7zr.SevenZipFile(self.path, mode="w") as archive:
                for filename, file_data in existing_files.items():
                    if hasattr(file_data, "read"):
                        # Reset stream position if it's a file-like object
                        if hasattr(file_data, "seek"):
                            file_data.seek(0)
                        archive.writestr(file_data.read(), filename)
                    else:
                        archive.writestr(file_data, filename)

            self._clear_cache()
        except Exception as e:
            self._handle_error("write", archive_file, e)
            msg = f"Failed to write {archive_file} to {self.path}"
            raise ArchiverWriteError(msg) from e
        else:
            return True

    def remove_file(self, archive_file: str) -> bool:
        """Remove a file from the 7zip archive.

        Args:
            archive_file: Path of the file to remove from the archive.

        Returns:
            True if the file was successfully removed or didn't exist, False otherwise.

        """
        try:
            if not self.path.exists():
                return True  # File doesn't exist, consider it "removed"

            # Read all files except the one to remove
            with py7zr.SevenZipFile(self.path, mode="r") as archive:
                all_files = archive.readall()

            # Remove the target file if it exists
            if archive_file in all_files:
                del all_files[archive_file]

            # Write the updated archive
            with py7zr.SevenZipFile(self.path, mode="w") as archive:
                for filename, file_data in all_files.items():
                    if hasattr(file_data, "read"):
                        if hasattr(file_data, "seek"):
                            file_data.seek(0)
                        archive.writestr(file_data.read(), filename)
                    else:
                        archive.writestr(file_data, filename)

            self._clear_cache()
        except Exception as e:
            self._handle_error("remove", archive_file, e)
            return False
        else:
            return True

    def remove_files(self, filename_list: list[str]) -> bool:
        """Remove multiple files from the 7zip archive.

        Args:
            filename_list: List of file paths to remove from the archive.

        Returns:
            True if ALL files were successfully removed, False otherwise.

        """
        try:
            if not self.path.exists():
                return True  # Archive doesn't exist, consider files "removed"

            # Read all files
            with py7zr.SevenZipFile(self.path, mode="r") as archive:
                all_files = archive.readall()

            # Remove the target files
            files_to_remove = set(filename_list)
            for filename in files_to_remove:
                all_files.pop(filename, None)

            # Write the updated archive
            with py7zr.SevenZipFile(self.path, mode="w") as archive:
                for filename, file_data in all_files.items():
                    if hasattr(file_data, "read"):
                        if hasattr(file_data, "seek"):
                            file_data.seek(0)
                        archive.writestr(file_data.read(), filename)
                    else:
                        archive.writestr(file_data, filename)

            self._clear_cache()
        except Exception as e:
            self._handle_error("remove_files", str(filename_list), e)
            return False
        else:
            return True

    def get_filename_list(self) -> list[str]:
        """Get a list of all files in the 7zip archive.

        Returns:
            List of file paths within the archive, sorted alphabetically.

        """
        if self._file_list_cache is not None:
            return self._file_list_cache

        if not self.path.exists():
            self._file_list_cache = []
            return self._file_list_cache

        try:
            with py7zr.SevenZipFile(self.path, mode="r") as archive:
                # Get list of files from archive
                filenames = archive.getnames()
                # Filter out directories (they usually end with '/')
                files = [f for f in filenames if not f.endswith("/")]
                files.sort()
                self._file_list_cache = files
                return files

        except Exception as e:
            self._handle_error("get_filename_list", str(self.path), e)
            return []

    def file_test(self) -> bool:
        """Test whether the file is a valid CB7 archive.

        Returns:
            bool: True if the file is a valid CB7 archive, False otherwise.

        Note:
            This method uses the py7zr library to validate the archive structure,
            not just the file extension.

        """
        with suppress(Exception):
            return py7zr.is_7zfile(self.path)
        return False

    def copy_from_archive(self, other_archive: Archiver) -> bool:  # noqa: C901
        """Copy files from another archive to this 7zip archive.

        Args:
            other_archive: Source archive to copy files from.

        Returns:
            True if all files were successfully copied, False otherwise.

        """
        try:
            # Get list of files to copy
            files_to_copy = other_archive.get_filename_list()

            if not files_to_copy:
                return True  # Nothing to copy

            # Read existing files from this archive
            existing_files = {}
            if self.path.exists():
                try:
                    with py7zr.SevenZipFile(self.path, mode="r") as archive:
                        existing_files = archive.readall()
                except Exception as e:
                    logger.warning("Could not read existing archive contents: %s", e)

            # Copy files from source archive
            success = True
            try:
                for filename in files_to_copy:
                    file_data = other_archive.read_file(filename)
                    existing_files[filename] = io.BytesIO(file_data)
            except Exception:
                logger.exception("Failed to copy file")
                success = False

            # Write the updated archive
            with py7zr.SevenZipFile(self.path, mode="w") as archive:
                for filename, file_data in existing_files.items():
                    if hasattr(file_data, "read"):
                        if hasattr(file_data, "seek"):
                            file_data.seek(0)
                        archive.writestr(file_data.read(), filename)
                    else:
                        archive.writestr(file_data, filename)

            self._clear_cache()
        except Exception as e:
            self._handle_error("copy_from_archive", str(other_archive.path), e)
            return False
        else:
            return success

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        """Context manager exit with cleanup."""
        self._clear_cache()
        super().__exit__(exc_type, exc_val, exc_tb)
