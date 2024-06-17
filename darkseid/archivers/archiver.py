from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class Archiver:
    """
    Handles archiving operations for files.

    This class provides methods for reading, writing, and removing files within an archive.
    """

    def __init__(self: Archiver, path: Path) -> None:
        """
        Initializes an Archiver object with a specified path.

        Args:
            path (Path): The path associated with the Archiver.

        Returns:
            None
        """

        self.path = path

    def read_file(self: Archiver, archive_file: str) -> bytes:
        """
        Reads the content of a file from the archive.

        Args:
            archive_file (str): The file to read from the archive.

        Returns:
            bytes: The content of the file as bytes.

        Raises:
            NotImplementedError: Method or function hasn't been implemented yet.
        """

        raise NotImplementedError

    def write_file(
        self: Archiver,
        archive_file: str,  # noqa: ARG002
        data: str,  # noqa: ARG002
    ) -> bool:
        """
        Writes data to a file in the archive.

        Args:
            archive_file (str): The file to write to in the archive.
            data (str): The data to write to the file.

        Returns:
            bool: True if the write operation was successful, False otherwise.
        """

        return False

    def remove_file(self: Archiver, archive_file: str) -> bool:  # noqa: ARG002
        """
        Removes a file from the archive.

        Args:
            archive_file (str): The file to remove from the archive.

        Returns:
            bool: True if the file was successfully removed, False otherwise.
        """

        return False

    def remove_files(
        self: Archiver,
        filename_lst: list[str],  # noqa: ARG002
    ) -> bool:
        """
        Removes multiple files from the archive.

        Args:
            filename_lst (list[str]): The list of files to remove from the archive.

        Returns:
            bool: True if all files were successfully removed, False otherwise.
        """

        return False

    def get_filename_list(self: Archiver) -> list[str]:
        """
        Returns an empty list of filenames from the archive.

        Returns:
            list[str]: An empty list of filenames.
        """

        return []

    def copy_from_archive(
        self: Archiver,
        other_archive: Archiver,  # noqa: ARG002
    ) -> bool:
        """
        Copies files from another archive.

        Args:
            other_archive (Archiver): The archive to copy files from.

        Returns:
            bool: True if the copy operation was successful, False otherwise.
        """

        return False
