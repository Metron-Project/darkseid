"""ZIP archive implementation."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import rarfile
from zipremove import ZIP_DEFLATED, ZIP_STORED, BadZipfile, ZipFile

from darkseid.archivers.archiver import Archiver, ArchiverReadError

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class ZipArchiver(Archiver):
    """Handles archiving operations specific to ZIP files."""

    def __init__(self, path: Path) -> None:
        """Initialize a ZipArchiver with the provided path."""
        super().__init__(path)
        self._temp_files: list[Path] = []

    def read_file(self, archive_file: str) -> bytes:
        """Read the contents of a file from the ZIP archive.

        Args:
            archive_file: Path of the file within the archive.

        Returns:
            File contents as bytes.

        Raises:
            ArchiverReadError: If the file cannot be read.

        """
        try:
            with ZipFile(self.path, mode="r") as zf:
                return zf.read(archive_file)
        except BadZipfile as e:
            self._handle_error("read", archive_file, e)
            msg = f"Corrupt ZIP file: {e}"
            raise ArchiverReadError(msg) from e
        except OSError as e:
            self._handle_error("read", archive_file, e)
            msg = f"Cannot read ZIP file: {e}"
            raise ArchiverReadError(msg) from e
        except KeyError as e:
            msg = f"File not found in archive: {archive_file}"
            raise ArchiverReadError(msg) from e

    def write_file(self, archive_file: str, data: str | bytes) -> bool:
        """Write data to a file in the ZIP archive.

        Args:
            archive_file: Path of the file within the archive.
            data: Data to write (string or bytes).

        Returns:
            True if successful, False otherwise.

        """
        # Convert data to bytes if it's a string
        if isinstance(data, str):
            data = data.encode("utf-8")

        # Choose compression based on file type
        compress_type = ZIP_STORED if self.IMAGE_EXT_RE.search(archive_file) else ZIP_DEFLATED

        try:
            with ZipFile(self.path, "a") as zf:
                # Remove existing file if present
                if archive_file in set(zf.namelist()):
                    zf_infos = [zf.remove(archive_file)]
                    zf.repack(zf_infos)
                zf.writestr(archive_file, data, compress_type=compress_type, compresslevel=9)
        except (BadZipfile, OSError) as e:
            self._handle_error("write", archive_file, e)
            return False
        else:
            return True

    def remove_file(self, archive_file: str) -> bool:
        """Remove a file from the ZIP archive.

        Args:
            archive_file: Path of the file to remove.

        Returns:
            True if successful, False otherwise.

        """
        try:
            with ZipFile(self.path, "a") as zf:
                zf_infos = [zf.remove(archive_file)]
                zf.repack(zf_infos)
        except KeyError:
            logger.warning("File not found for removal: %s", archive_file)
            return False
        except (BadZipfile, OSError) as e:
            self._handle_error("remove", archive_file, e)
            return False
        else:
            return True

    def remove_files(self, filename_list: list[str]) -> bool:
        """Remove multiple files from the ZIP archive.

        Args:
            filename_list: List of file paths to remove.

        Returns:
            True if all files were successfully removed, False otherwise.

        """
        if not filename_list:
            return True

        existing_files = set(self.get_filename_list())
        files_to_remove = [f for f in filename_list if f in existing_files]

        if not files_to_remove:
            return True

        try:
            with ZipFile(self.path, "a") as zf:
                zf_infos = [zf.remove(filename) for filename in files_to_remove]
                zf.repack(zf_infos)
        except (BadZipfile, OSError) as e:
            self._handle_error("remove_multiple", str(files_to_remove), e)
            return False
        else:
            return True

    def get_filename_list(self) -> list[str]:
        """Get a list of all files in the ZIP archive.

        Returns:
            List of file paths within the archive.

        """
        try:
            with ZipFile(self.path, mode="r") as zf:
                return zf.namelist()
        except (BadZipfile, OSError) as e:
            self._handle_error("list", "", e)
            return []

    def copy_from_archive(self, other_archive: Archiver) -> bool:
        """Copy files from another archive to the ZIP archive.

        Args:
            other_archive: Source archive to copy from.

        Returns:
            True if successful, False otherwise.

        """
        try:
            with ZipFile(self.path, mode="w", allowZip64=True) as zout:
                for filename in other_archive.get_filename_list():
                    try:
                        data = other_archive.read_file(filename)
                        if data is not None:
                            compress_type = (
                                ZIP_STORED if self.IMAGE_EXT_RE.search(filename) else ZIP_DEFLATED
                            )
                            zout.writestr(
                                filename, data, compress_type=compress_type, compresslevel=9
                            )
                    except (ArchiverReadError, rarfile.BadRarFile) as e:
                        logger.warning("Skipping bad file %s: %s", filename, e)
                        self._cleanup_partial_file()
                        return False
        except (BadZipfile, OSError) as e:
            self._cleanup_partial_file()
            self._handle_error("copy", str(other_archive.path), e)
            return False
        else:
            return True

    def _cleanup_partial_file(self) -> None:
        """Remove partially created archive file."""
        if self.path.exists():
            try:
                self.path.unlink()
            except OSError as e:
                logger.warning("Could not remove partial file %s: %s", self.path, e)

    def _cleanup_temp_files(self) -> None:
        """Clean up any temporary files."""
        for temp_file in self._temp_files:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError as e:
                    logger.warning("Could not remove temp file %s: %s", temp_file, e)
        self._temp_files.clear()

    def __del__(self) -> None:
        """Clean up resources when archiver is destroyed."""
        self._cleanup_temp_files()
