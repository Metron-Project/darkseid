"""RAR archive implementation."""

from __future__ import annotations

import io
import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import rarfile

from darkseid.archivers.archiver import Archiver, ArchiverReadError

logger = logging.getLogger(__name__)


class RarArchiver(Archiver):
    """Handles archiving operations specific to RAR files.

    Note: RAR files are read-only due to format limitations.
    """

    def __init__(self, path: Path) -> None:
        """Initialize a RarArchiver with the provided path."""
        super().__init__(path)

    def is_write_operation_expected(self) -> bool:
        """RAR files are read-only."""
        return False

    def read_file(self, archive_file: str) -> bytes:
        """Read the contents of a file from the RAR archive.

        Args:
            archive_file: Path of the file within the archive.

        Returns:
            File contents as bytes.

        Raises:
            ArchiverReadError: If the file cannot be read.

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
            # Handle empty directories
            return b""

    def write_file(self, archive_file: str, data: str | bytes) -> bool:  # noqa: ARG002
        """Write data to a file in the RAR archive.

        Args:
            archive_file: Path of the file within the archive.
            data: Data to write.

        Returns:
            False, as RAR files are read-only.

        """
        logger.warning("Cannot write to RAR archive: %s", archive_file)
        return False

    def remove_file(self, archive_file: str) -> bool:
        """Remove a file from the RAR archive.

        Args:
            archive_file: Path of the file to remove.

        Returns:
            False, as RAR files are read-only.

        """
        logger.warning("Cannot remove file from RAR archive: %s", archive_file)
        return False

    def remove_files(self, filename_list: list[str]) -> bool:
        """Remove multiple files from the RAR archive.

        Args:
            filename_list: List of files to remove.

        Returns:
            False, as RAR files are read-only.

        """
        logger.warning("Cannot remove files from RAR archive: %s", filename_list)
        return False

    def get_filename_list(self) -> list[str]:
        """Get a list of all files in the RAR archive.

        Returns:
            Sorted list of file paths within the archive.

        Raises:
            ArchiverReadError: If the archive cannot be read.

        """
        try:
            with rarfile.RarFile(self.path) as rf:
                return sorted(rf.namelist())
        except (rarfile.RarCannotExec, rarfile.BadRarFile) as e:
            self._handle_error("list", "", e)
            msg = f"Cannot read RAR archive: {e}"
            raise ArchiverReadError(msg) from e

    def copy_from_archive(self, other_archive: Archiver) -> bool:
        """Copy files from another archive to the RAR archive.

        Args:
            other_archive: Source archive to copy from.

        Returns:
            False, as RAR files are read-only.

        """
        logger.warning("Cannot copy to RAR archive from: %s", other_archive.path)
        return False
