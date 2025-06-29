"""Base archiver class providing common interface for archive operations."""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class ArchiverError(Exception):
    """Base exception for archiver operations."""


class ArchiverReadError(ArchiverError):
    """Raised when reading from archive fails."""


class ArchiverWriteError(ArchiverError):
    """Raised when writing to archive fails."""


class Archiver(ABC):
    """Abstract base class for archive operations.

    Provides a common interface for reading, writing, and managing files
    within different archive formats.
    """

    IMAGE_EXT_RE = re.compile(r"\.(jpe?g|png|webp|gif)$", re.IGNORECASE)

    def __init__(self, path: Path) -> None:
        """Initialize an Archiver with the specified path.

        Args:
            path: Path to the archive file.

        Raises:
            FileNotFoundError: If the archive file doesn't exist for read operations.

        """
        self._path = path
        self._validate_path()

    def _validate_path(self) -> None:
        """Validate the archive path."""
        if not self._path.exists() and not self.is_write_operation_expected():
            logger.warning("Archive file does not exist: %s", self._path)

    def is_write_operation_expected(self) -> bool:
        """Check if this archiver is expected to be used for write operations."""
        return True  # Override in read-only implementations

    @property
    def path(self) -> Path:
        """Get the path associated with this archiver."""
        return self._path

    @abstractmethod
    def read_file(self, archive_file: str) -> bytes:
        """Read the contents of a file from the archive.

        Args:
            archive_file: Path of the file within the archive.

        Returns:
            The file contents as bytes.

        Raises:
            ArchiverReadError: If the file cannot be read or doesn't exist.

        """

    @abstractmethod
    def write_file(self, archive_file: str, data: str | bytes) -> bool:
        """Write data to a file in the archive.

        Args:
            archive_file: Path of the file within the archive.
            data: Data to write (string or bytes).

        Returns:
            True if successful, False otherwise.

        Raises:
            ArchiverWriteError: If the write operation fails.

        """

    @abstractmethod
    def remove_file(self, archive_file: str) -> bool:
        """Remove a file from the archive.

        Args:
            archive_file: Path of the file to remove.

        Returns:
            True if successful, False otherwise.

        """

    @abstractmethod
    def remove_files(self, filename_list: list[str]) -> bool:
        """Remove multiple files from the archive.

        Args:
            filename_list: List of file paths to remove.

        Returns:
            True if all files were successfully removed, False otherwise.

        """

    @abstractmethod
    def get_filename_list(self) -> list[str]:
        """Get a list of all files in the archive.

        Returns:
            List of file paths within the archive.

        """

    @abstractmethod
    def copy_from_archive(self, other_archive: Archiver) -> bool:
        """Copy files from another archive to this archive.

        Args:
            other_archive: Source archive to copy from.

        Returns:
            True if successful, False otherwise.

        """

    def __enter__(self):  # noqa: ANN204
        """Context manager entry."""
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:  # noqa: B027
        """Context manager exit."""

    def _handle_error(self, operation: str, filename: str, error: Exception) -> None:  # noqa: ARG002
        """Centralized error handling and logging.

        Args:
            operation: Description of the operation that failed.
            filename: Name of the file involved in the operation.
            error: The exception that occurred.

        """
        logger.exception("Error during %s operation on %s :: %s", operation, self.path, filename)

    def exists(self, archive_file: str) -> bool:
        """Check if a file exists in the archive.

        Args:
            archive_file: Path of the file to check.

        Returns:
            True if file exists, False otherwise.

        """
        return archive_file in self.get_filename_list()
