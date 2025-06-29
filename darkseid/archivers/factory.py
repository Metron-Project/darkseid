"""Factory for creating appropriate archiver instances."""

from pathlib import Path
from typing import ClassVar

from darkseid.archivers.archiver import Archiver
from darkseid.archivers.rar import RarArchiver
from darkseid.archivers.zip import ZipArchiver


class UnknownArchiver(Archiver):
    """Archiver for unknown file types."""

    def read_file(self, archive_file: str) -> bytes:
        """Read a file from the archive.

        This method is not implemented for unknown archive types and always raises NotImplementedError.

        Args:
            archive_file: The filename to read.

        Raises:
            NotImplementedError: Always raised for unknown archive types.

        Returns:
            bytes: This method does not return; it always raises an exception.

        """
        msg = "Unknown archive format"
        raise NotImplementedError(msg)

    def write_file(self, archive_file: str, data: str | bytes) -> bool:  # noqa: ARG002
        """Write a file to the archive.

        This method is not implemented for unknown archive types and always returns False.

        Args:
            archive_file: The filename to write.
            data: The data to write to the file.

        Returns:
            bool: False, as writing is not supported for unknown archive types.

        """
        return False

    def remove_file(self, archive_file: str) -> bool:  # noqa: ARG002
        """Remove a single file from the archive.

        This method is not implemented for unknown archive types and always returns False.

        Args:
            archive_file: The filename to remove.

        Returns:
            bool: False, as file removal is not supported for unknown archive types.

        """
        return False

    def remove_files(self, filename_list: list[str]) -> bool:  # noqa: ARG002
        """Remove multiple files from the archive.

        This method is not implemented for unknown archive types and always returns False.

        Args:
            filename_list: List of filenames to remove.

        Returns:
            bool: False, as file removal is not supported for unknown archive types.

        """
        return False

    def get_filename_list(self) -> list[str]:
        """Return a list of filenames in the archive.

        For unknown archive types, this always returns an empty list.

        Returns:
            list[str]: An empty list, as filenames cannot be determined for unknown archive types.

        """
        return []

    def copy_from_archive(self, other_archive: Archiver) -> bool:  # noqa: ARG002
        """Copy files from another archive.

        This method is not implemented for unknown archive types and always returns False.

        Args:
            other_archive: The source archive to copy from.

        Returns:
            bool: False, as copying is not supported for unknown archive types.

        """
        return False

    @staticmethod
    def name() -> str:
        """Return the name of the archiver."""
        return "Unknown"


class ArchiverFactory:
    """Factory for creating appropriate archiver instances based on file type."""

    _ARCHIVER_MAP: ClassVar[dict[str, type[Archiver]]] = {
        ".zip": ZipArchiver,
        ".cbz": ZipArchiver,  # Comic book ZIP
        ".rar": RarArchiver,
        ".cbr": RarArchiver,  # Comic book RAR
    }

    @classmethod
    def create_archiver(cls, path: Path) -> Archiver:
        """Create an appropriate archiver for the given file.

        Args:
            path: Path to the archive file.

        Returns:
            Appropriate archiver instance for the file type.

        """
        suffix = path.suffix.lower()
        archiver_class = cls._ARCHIVER_MAP.get(suffix, UnknownArchiver)
        return archiver_class(path)

    @classmethod
    def register_archiver(cls, extension: str, archiver_class: type[Archiver]) -> None:
        """Register a new archiver for a file extension.

        Args:
            extension: File extension (including dot, e.g., '.7z').
            archiver_class: Archiver class to handle this extension.

        """
        cls._ARCHIVER_MAP[extension.lower()] = archiver_class

    @classmethod
    def get_supported_extensions(cls) -> list[str]:
        """Get list of supported file extensions."""
        return list(cls._ARCHIVER_MAP.keys())
