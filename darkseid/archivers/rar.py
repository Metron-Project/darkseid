from __future__ import annotations

import io
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

import rarfile

from darkseid.archivers import Archiver
from darkseid.exceptions import RarError


class RarArchiver(Archiver):
    """
    Handles archiving operations specific to RAR files.

    This class provides methods for reading, writing, and removing files within a RAR archive.
    """

    def __init__(self: RarArchiver, path: Path) -> None:
        """
        Initializes a RarArchiver object with the provided path.

        Args:
            path (Path): The path associated with the RAR file.

        Returns:
            None
        """

        super().__init__(path)

    def read_file(self: RarArchiver, archive_file: str) -> bytes:
        """
        Reads the contents of a file from the RAR archive.

        Args:
            archive_file (str): The file to read from the archive.

        Returns:
            bytes: The content of the file as bytes.

        Raises:
            RarError: If an error occurs during reading.
        """

        try:
            with rarfile.RarFile(self.path) as rf:
                data: bytes = rf.read(archive_file)
        except rarfile.RarCannotExec as e:
            raise RarError(e) from e
        except io.UnsupportedOperation:
            """If rar directory doesn't contain any data, return None."""
            return b""
        else:
            return data

    def remove_file(self: RarArchiver, archive_file: str) -> bool:  # noqa: ARG002
        """
        Removes a file from the RAR archive.

        Args:
            archive_file (str): The file to remove from the archive.
        Returns:
            bool: False, as RAR files are read-only.
        """

        return False

    def remove_files(self: RarArchiver, filename_lst: list[str]) -> bool:  # noqa: ARG002
        """
        Removes multiple files from the RAR archive.

        Args:
            filename_lst (list[str]): The list of files to remove from the archive.

        Returns:
            bool: False, as RAR files are read-only.
        """

        return False

    def write_file(self: RarArchiver, archive_file: str, data: str) -> bool:  # noqa: ARG002
        """
        Writes data to a file in the RAR archive.

        Args:
            archive_file (str): The file to write to in the archive.
            data (str): The data to write to the file.

        Returns:
            bool: False, as RAR files are read-only.
        """
        return False

    def get_filename_list(self: RarArchiver) -> list[str]:
        """
        Returns a list of filenames in the RAR archive.

        Returns:
            list[str]: A sorted list of filenames in the archive.

        Raises:
            RarError: If an error occurs during retrieval.
        """

        try:
            with rarfile.RarFile(self.path) as rf:
                return sorted(rf.namelist())
        except rarfile.RarCannotExec as e:
            raise RarError(e) from e

    def copy_from_archive(
        self: RarArchiver,
        other_archive: Archiver,  # noqa: ARG002
    ) -> bool:
        """
        Copies files from another archive to the RAR archive.

        Args:
            other_archive (Archiver): The archive to copy files from.

        Returns:
            bool: False, as RAR files are read-only.
        """

        return False
