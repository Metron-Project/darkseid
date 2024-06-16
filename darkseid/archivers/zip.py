from __future__ import annotations

import logging
import shutil
import tempfile
import zipfile
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path
from typing import cast

import rarfile

from darkseid.archivers import Archiver

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

        return self._rebuild([archive_file])

    def remove_files(self: ZipArchiver, filename_lst: list[str]) -> bool:
        """
        Removes multiple files from the ZIP archive.

        Args:
            filename_lst (list[str]): The list of files to remove from the archive.

        Returns:
            bool: True if all files were successfully removed, False otherwise.
        """

        return self._rebuild(filename_lst)

    def write_file(self: ZipArchiver, archive_file: str, data: str) -> bool:
        """
        Writes data to a file in the ZIP archive.

        Args:
            archive_file (str): The file to write to in the archive.
            data (str): The data to write to the file.

        Returns:
            bool: True if the write operation was successful, False otherwise.
        """

        #  At the moment, no other option but to rebuild the whole
        #  zip archive w/o the indicated file. Very sucky, but maybe
        # another solution can be found
        files = self.get_filename_list()
        if archive_file in files:
            self._rebuild([archive_file])

        try:
            # now just add the archive file as a new one
            with zipfile.ZipFile(
                self.path,
                mode="a",
                allowZip64=True,
                compression=zipfile.ZIP_DEFLATED,
            ) as zf:
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

    def _rebuild(self: ZipArchiver, exclude_list: list[str]) -> bool:
        """
        Rebuilds the ZIP archive excluding specified files.

        Args:
            exclude_list (list[str]): The list of files to exclude from the rebuild.

        Returns:
            bool: True if the rebuild was successful, False otherwise.
        """

        try:
            with zipfile.ZipFile(
                tempfile.NamedTemporaryFile(dir=self.path.parent, delete=False),
                "w",
                allowZip64=True,
            ) as zout:
                with zipfile.ZipFile(self.path, mode="r") as zin:
                    for item in zin.infolist():
                        buffer = zin.read(item.filename)
                        if item.filename not in exclude_list:
                            zout.writestr(item, buffer)

                # replace with the new file
                self.path.unlink(missing_ok=True)
                zout.close()  # Required on Windows
                shutil.move(cast(str, zout.filename), self.path)
        except (zipfile.BadZipfile, OSError):
            logger.exception("Error rebuilding zip file: %s", self.path)
            return False
        else:
            return True

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
