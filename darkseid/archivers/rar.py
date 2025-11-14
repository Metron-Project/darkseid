"""RAR archive implementation.

This module provides a read-only interface for working with RAR archives.
RAR format is proprietary and only supports read operations through the
rarfile library, which requires external RAR tools to be installed.

Examples:
    >>> from pathlib import Path
    >>> archiver = RarArchiver(Path("example.cbr"))
    >>> files = archiver.get_filename_list()
    >>> content = archiver.read_file("file.txt")
    >>> print(content.decode('utf-8'))

Note:
    All write operations (write_file, remove_files, copy_from_archive) will
    return False and log warnings since RAR archives are read-only.

"""

from __future__ import annotations

import io
import logging
from contextlib import suppress
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import rarfile

from darkseid.archivers.archiver import Archiver, ArchiverReadError

logger = logging.getLogger(__name__)


class RarArchiver(Archiver):
    """A read-only archiver for RAR files.

    This class provides an interface for reading files from RAR archives.
    Due to the proprietary nature of the RAR format, write operations are
    not supported. All modification attempts will fail gracefully with
    appropriate warnings.

    The implementation depends on the rarfile library, which in turn requires
    external RAR tools (like unrar) to be installed on the system.

    Attributes:
        path (Path): The filesystem path to the RAR archive.

    Note:
        RAR files are read-only due to format limitations and licensing
        restrictions of the RAR compression algorithm.

    """

    def __init__(self, path: Path) -> None:
        """Initialize a RarArchiver with the provided path.

        Args:
            path: The filesystem path to the RAR archive file.

        Note:
            This constructor does not validate that the file exists or is
            a valid RAR archive. Validation occurs when operations are
            performed on the archive.

        """
        super().__init__(path)

    def is_write_operation_expected(self) -> bool:
        """Check if write operations are supported.

        Returns:
            False: RAR files are always read-only.

        Note:
            This method is used by the parent class to determine if write
            operations should be attempted. For RAR files, this always
            returns False to prevent unnecessary operation attempts.

        """
        return False

    def read_file(self, archive_file: str) -> bytes:
        """Read the contents of a file from the RAR archive.

        Args:
            archive_file: The path of the file within the archive.
                         Should use forward slashes as path separators
                         regardless of the operating system.

        Returns:
            The file contents as bytes. For text files, decode using
                the appropriate encoding (e.g., content.decode('utf-8')).

        Raises:
            ArchiverReadError: If the file cannot be read due to:

                - RAR command execution failure (missing unrar tool)
                - Corrupt or invalid RAR file
                - File not found in the archive
                - Other I/O errors

        Examples:
            >>> archiver = RarArchiver(Path("comics.rar"))
            >>> image_data = archiver.read_file("page01.jpg")
            >>> with open("extracted_page.jpg", "wb") as f:
            ...     f.write(image_data)

        """
        try:
            with rarfile.RarFile(self.path) as rf:
                return rf.read(archive_file)
        except rarfile.RarCannotExec as e:
            self._handle_error("read", archive_file, e)
            msg = f"Cannot execute RAR command: {e}"
            raise ArchiverReadError(msg) from e
        except rarfile.BadRarFile as e:
            self._handle_error("read", archive_file, e)
            msg = f"Corrupt RAR file: {e}"
            raise ArchiverReadError(msg) from e
        except KeyError as e:
            msg = f"File not found in archive: {archive_file}"
            raise ArchiverReadError(msg) from e
        except io.UnsupportedOperation:
            # Handle empty directories - return empty bytes
            return b""

    def write_file(self, archive_file: str, data: str | bytes) -> bool:  # noqa: ARG002
        """Attempt to write data to a file in the RAR archive.

        Args:
            archive_file: The path of the file within the archive.
            data: The data to write (string or bytes).

        Returns:
            False: RAR files are read-only, so this operation always fails.

        Note:
            This method logs a warning and returns False immediately.
            No actual write operation is attempted since RAR format
            does not support modification of existing archives.

        Warning:
            A warning will be logged indicating that the write operation
            was attempted on a read-only RAR archive.

        """
        logger.warning("Cannot write to RAR archive: %s", archive_file)
        return False

    def remove_files(self, filename_list: list[str]) -> bool:
        """Attempt to remove multiple files from the RAR archive.

        Args:
            filename_list: A list of file paths to remove from the archive.

        Returns:
            False: RAR files are read-only, so this operation always fails.

        Note:
            This method logs a warning and returns False immediately.
            No actual removal operations are attempted since RAR format
            does not support modification of existing archives.

        Warning:
            A warning will be logged indicating that the bulk remove operation
            was attempted on a read-only RAR archive, including the list of
            files that were requested to be removed.

        """
        logger.warning("Cannot remove files from RAR archive: %s", filename_list)
        return False

    def get_filename_list(self) -> list[str]:
        """Get a list of all files in the RAR archive.

        Returns:
            A sorted list of file paths within the archive. Paths use
                forward slashes as separators and are relative to the archive root.
                Empty directories may or may not be included depending on how
                the archive was created.

        Raises:
            ArchiverReadError: If the archive cannot be read due to:

                - RAR command execution failure (missing unrar tool)
                - Corrupt or invalid RAR file
                - File system or permission errors

        Examples:
            >>> archiver = RarArchiver(Path("documents.rar"))
            >>> files = archiver.get_filename_list()
            >>> print(f"Archive contains {len(files)} files:")
            >>> for file in files:
            ...     print(f"  {file}")

        Note:
            The returned list is sorted alphabetically for consistent ordering.
            This may differ from the order in which files were added to the archive.

        """
        try:
            with rarfile.RarFile(self.path) as rf:
                return sorted(rf.namelist())
        except (rarfile.RarCannotExec, rarfile.BadRarFile) as e:
            self._handle_error("list", "", e)
            msg = f"Cannot read RAR archive: {e}"
            raise ArchiverReadError(msg) from e

    def test(self) -> bool:
        """Test whether the file is a valid RAR archive.

        Returns:
            bool: True if the file is a valid RAR archive, False otherwise.

        Note:
            This method uses the rarfile library to validate the archive structure,
            not just the file extension.

        """
        with suppress(Exception):
            return rarfile.is_rarfile(self._path)
        return False

    def copy_from_archive(self, other_archive: Archiver) -> bool:
        """Attempt to copy files from another archive to the RAR archive.

        Args:
            other_archive: The source archive to copy files from.

        Returns:
            False: RAR files are read-only, so this operation always fails.

        Note:
            This method logs a warning and returns False immediately.
            No actual copy operation is attempted since RAR format
            does not support modification of existing archives.

        Warning:
            A warning will be logged indicating that the copy operation
            was attempted on a read-only RAR archive, including the path
            of the source archive.

        Examples:
            >>> rar_archive = RarArchiver(Path("target.rar"))
            >>> zip_archive = ZipArchiver(Path("source.cbz"))
            >>> success = rar_archive.copy_from_archive(zip_archive)
            >>> print(f"Copy successful: {success}")  # Will print: Copy successful: False

        """
        logger.warning("Cannot copy to RAR archive from: %s", other_archive.path)
        return False
