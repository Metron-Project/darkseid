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
    """ZIP implementation."""

    def __init__(self: ZipArchiver, path: Path) -> None:
        super().__init__(path)

    def read_file(self: ZipArchiver, archive_file: str) -> bytes:
        """Read the contents of a comic archive."""
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
        """Returns a boolean when attempting to remove a file from an archive."""
        return self._rebuild([archive_file])

    def remove_files(self: ZipArchiver, filename_lst: list[str]) -> bool:
        """Returns a boolean when attempting to remove a list of files from an archive."""
        return self._rebuild(filename_lst)

    def write_file(self: ZipArchiver, archive_file: str, data: str) -> bool:
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
        """Returns a list of the filenames in an archive."""
        try:
            with zipfile.ZipFile(self.path, mode="r") as zf:
                return zf.namelist()
        except (zipfile.BadZipfile, OSError):
            logger.exception("Error listing files in zip archive: %s", self.path)
            return []

    def _rebuild(self: ZipArchiver, exclude_list: list[str]) -> bool:
        """Zip helper func.

        This recompresses the zip archive, without the files in the exclude_list
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
        """Replace the current zip with one copied from another archive."""
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
