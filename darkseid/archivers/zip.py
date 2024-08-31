from __future__ import annotations

import logging
import zipfile
from typing import TYPE_CHECKING

from darkseid.zipfile_remove import ZipFileWithRemove

if TYPE_CHECKING:
    from pathlib import Path

import rarfile

from darkseid.archivers.archiver import Archiver

logger = logging.getLogger(__name__)


class ZipArchiver(Archiver):
    """
    Handles archiving operations specific to ZIP files.

    This class provides methods for reading, writing, and removing files within a ZIP archive.
    """

    def __init__(self: ZipArchiver, path: Path) -> None:
        """
        Initializes a ZipArchiver object with the provided path.

        Args:
            path (Path): The path associated with the Zip file.

        Returns:
            None
        """
        super().__init__(path)

    def read_file(self: ZipArchiver, archive_file: str) -> bytes:
        """
        Reads the contents of a file from the ZIP archive.

        Args:
            archive_file (str): The file to read from the archive.

        Returns:
            bytes: The content of the file as bytes.

        Raises:
            OSError: If an error occurs during reading.
        """

        try:
            with zipfile.ZipFile(self.path, mode="r") as zf:
                return zf.read(archive_file)
        except (zipfile.BadZipfile, OSError) as e:
            logger.exception(
                "Error reading zip archive %s :: %s",
                self.path,
                archive_file,
            )
            raise OSError from e

    def remove_file(self: ZipArchiver, archive_file: str) -> bool:
        """
        Removes a file from the ZIP archive.

        Args:
            archive_file (str): The file to remove from the archive.

        Returns:
            bool: True if the file was successfully removed, False otherwise.
        """
        try:
            with ZipFileWithRemove(self.path, "a") as zf:
                zf.remove(archive_file)
        except KeyError:
            return False
        except (zipfile.BadZipfile, OSError):
            logger.exception(
                "Error writing zip archive %s :: %s",
                self.path,
                archive_file,
            )
            return False
        else:
            return True

    def remove_files(self: ZipArchiver, filename_lst: list[str]) -> bool:
        """
        Removes multiple files from the ZIP archive.

        Args:
            filename_lst (list[str]): The list of files to remove from the archive.

        Returns:
            bool: True if all files were successfully removed, False otherwise.
        """
        files = set(self.get_filename_list())
        if filenames_to_remove := [filename for filename in filename_lst if filename in files]:
            try:
                with ZipFileWithRemove(self.path, "a") as zf:
                    for filename in filenames_to_remove:
                        zf.remove(filename)
            except (zipfile.BadZipfile, OSError):
                logger.exception(
                    "Error writing zip archive %s :: %s",
                    self.path,
                    filename,
                )
                return False
        return True

    def write_file(self: ZipArchiver, archive_file: str, data: str) -> bool:
        """
        Writes data to a file in the ZIP archive.

        Args:
            archive_file (str): The file to write to in the archive.
            data (str): The data to write to the file.

        Returns:
            bool: True if the write operation was successful, False otherwise.
        """
        try:
            with ZipFileWithRemove(self.path, "a") as zf:
                if archive_file in set(zf.namelist()):
                    zf.remove(archive_file)
                zf.writestr(archive_file, data)
        except (zipfile.BadZipfile, OSError):
            logger.exception(
                "Error writing zip archive %s :: %s",
                self.path,
                archive_file,
            )
            return False
        else:
            return True

    def get_filename_list(self: ZipArchiver) -> list[str]:
        """
        Returns a list of filenames in the ZIP archive.

        Returns:
            list[str]: A list of filenames in the archive.

        Raises:
            OSError: If an error occurs during retrieval.
        """

        try:
            with zipfile.ZipFile(self.path, mode="r") as zf:
                return zf.namelist()
        except (zipfile.BadZipfile, OSError):
            logger.exception("Error listing files in zip archive: %s", self.path)
            return []

    def copy_from_archive(self: ZipArchiver, other_archive: Archiver) -> bool:
        """
        Copies files from another archive to the ZIP archive.

        Args:
            other_archive (Archiver): The archive to copy files from.

        Returns:
            bool: True if the copy operation was successful, False otherwise.
        """

        try:
            with zipfile.ZipFile(self.path, mode="w", allowZip64=True) as zout:
                for filename in other_archive.get_filename_list():
                    try:
                        data = other_archive.read_file(filename)
                    except rarfile.BadRarFile:
                        # Skip any bad images in the file.
                        continue
                    if data is not None:
                        zout.writestr(filename, data)
        except (zipfile.BadZipfile, OSError) as e:
            # Remove any partial files created
            if self.path.exists():
                self.path.unlink()
            logger.warning("Error while copying to %s: %s", self.path, e)
            return False
        else:
            return True
