"""ZIP archive implementation with comprehensive file manipulation capabilities.

This module provides a ZipArchiver class that extends the base Archiver interface
to handle ZIP file operations including reading, writing, removing files, and
copying between archives. It supports both compressed and uncompressed storage
based on file type optimization.

Examples:
    Basic usage of the ZipArchiver:

    >>> from pathlib import Path
    >>> archiver = ZipArchiver(Path("example.zip"))
    >>> content = archiver.read_file("readme.txt")
    >>> archiver.write_file("new_file.txt", "Hello, World!")
    >>> files = archiver.get_filename_list()
    >>> archiver.remove_files(["old_file.txt"])

"""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

import rarfile
from zipremove import ZIP_DEFLATED, ZIP_STORED, BadZipfile, ZipFile

from darkseid.archivers.archiver import Archiver, ArchiverReadError

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class ZipArchiver(Archiver):
    """Handles archiving operations specific to ZIP files.

    This class provides a complete interface for manipulating ZIP archives,
    including reading and writing files, removing entries, and copying content
    between archives. It automatically selects appropriate compression methods
    based on file types (images are stored uncompressed, other files are deflated).

    The archiver supports:

    - Reading individual files from ZIP archives
    - Writing new files or updating existing ones
    - Removing single files or multiple files in batch
    - Copying entire archive contents to a new ZIP file
    - Automatic cleanup of temporary files and partial operations

    Attributes:
        path (Path): Path to the ZIP archive file
        _temp_files (list[Path]): List of temporary files created during operations

    Examples:
        >>> archiver = ZipArchiver(Path("my_archive.zip"))
        >>> archiver.write_file("config.json", '{"version": "1.0"}')
        >>> data = archiver.read_file("config.json")
        >>> archiver.remove_files(["old_config.json"])

    """

    def __init__(self, path: Path) -> None:
        """Initialize a ZipArchiver with the provided path.

        Args:
            path: Path to the ZIP archive file. The file doesn't need to exist
                  yet - it will be created when first written to.

        Note:
            The archiver maintains a list of temporary files that will be
            automatically cleaned up when the object is destroyed.

        """
        super().__init__(path)
        self._temp_files: list[Path] = []

    def read_file(self, archive_file: str) -> bytes:
        """Read the contents of a file from the ZIP archive.

        Opens the ZIP archive in read mode and extracts the specified file's
        contents. The file path should use forward slashes as separators,
        following ZIP archive conventions.

        Args:
            archive_file: Path of the file within the archive. Should use
                         forward slashes (/) as path separators regardless
                         of the host operating system.

        Returns:
            File contents as bytes. For text files, you may need to decode
                using the appropriate encoding (e.g., .decode('utf-8')).

        Raises:
            ArchiverReadError: If the file cannot be read due to:

                - Corrupt ZIP file (BadZipfile)
                - File system errors (OSError)
                - File not found in archive (KeyError)

        Examples:
            >>> archiver = ZipArchiver(Path("docs.zip"))
            >>> content = archiver.read_file("readme.txt")
            >>> text = content.decode('utf-8')

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

        Creates a new file or updates an existing file in the ZIP archive.
        The compression method is automatically selected based on the file
        extension: image files are stored uncompressed (ZIP_STORED) while
        other files are compressed using deflate (ZIP_DEFLATED).

        If the file already exists in the archive, it will be removed and
        replaced with the new content using the zipremove library's repack
        functionality.

        Args:
            archive_file: Path of the file within the archive. Should use
                         forward slashes (/) as path separators.
            data: Data to write. Can be either a string (will be UTF-8 encoded)
                 or bytes. Binary data should be passed as bytes.

        Returns:
            True if the file was successfully written, False if an error
                occurred during the write operation.

        Note:
            - String data is automatically encoded as UTF-8
            - Image files (matched by IMAGE_EXT_RE) are stored uncompressed
            - Other files are compressed with deflate at maximum compression level
            - Existing files are replaced, not appended to

        Examples:
            >>> archiver = ZipArchiver(Path("data.zip"))
            >>> # Write text content
            >>> archiver.write_file("note.txt", "Hello, World!")
            >>> # Write binary content
            >>> with open("image.jpg", "rb") as f:
            ...     archiver.write_file("image.jpg", f.read())

        """
        # Convert data to bytes if it's a string
        if isinstance(data, str):
            data = data.encode("utf-8")

        # Choose compression based on file type
        # Images are stored uncompressed to avoid double compression
        compress_type = ZIP_STORED if self.IMAGE_EXT_RE.search(archive_file) else ZIP_DEFLATED

        try:
            with ZipFile(self.path, "a") as zf:
                # Remove existing file if present to avoid duplicates
                if archive_file in set(zf.namelist()):
                    zf_infos = [zf.remove(archive_file)]
                    zf.repack(zf_infos)
                zf.writestr(archive_file, data, compress_type=compress_type, compresslevel=9)
        except (BadZipfile, OSError) as e:
            self._handle_error("write", archive_file, e)
            return False
        else:
            return True

    def remove_files(self, filename_list: list[str]) -> bool:
        """Remove multiple files from the ZIP archive in a single operation.

        Efficiently removes multiple files from the ZIP archive by performing
        all removals in a single transaction and repacking once.

        Only files that actually exist in the archive will be removed. Files
        that don't exist are silently skipped.

        Args:
            filename_list: List of file paths to remove from the archive.
                          Each path should use forward slashes (/) as separators.

        Returns:
            True if all existing files were successfully removed, False if
                an error occurred during the removal process. Returns True if
                the filename_list is empty or contains no existing files.

        Note:
            - Non-existent files are silently ignored
            - All removals are performed in a single transaction
            - If any error occurs, no files are removed
            - The archive is repacked once after all removals

        Examples:
            >>> archiver = ZipArchiver(Path("batch_cleanup.zip"))
            >>> files_to_remove = ["temp1.txt", "temp2.txt", "cache.dat"]
            >>> success = archiver.remove_files(files_to_remove)
            >>> if success:
            ...     print(f"Removed {len(files_to_remove)} files")

        """
        if not filename_list:
            return True

        # Only attempt to remove files that actually exist
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

        Retrieves the complete list of files contained in the ZIP archive.
        This includes all files and directories, with paths using forward
        slashes as separators.

        Returns:
            List of file paths within the archive. Returns an empty list
                if the archive cannot be read or is empty. Directory entries
                (if any) are included in the list.

        Note:
            - Paths use forward slashes regardless of host OS
            - Directory entries may be included depending on how the ZIP was created
            - Returns empty list on any error (corrupt archive, file not found, etc.)

        Examples:
            >>> archiver = ZipArchiver(Path("project.zip"))
            >>> files = archiver.get_filename_list()
            >>> for file in files:
            ...     print(f"Found: {file}")

        """
        try:
            with ZipFile(self.path, mode="r") as zf:
                return zf.namelist()
        except (BadZipfile, OSError) as e:
            self._handle_error("list", "", e)
            return []

    def test(self) -> bool:
        """Test whether the file is a valid ZIP archive.

        Returns:
            bool: True if the file is a valid ZIP archive, False otherwise.

        Note:
            This method uses the zipfile library to validate the archive structure,
            not just the file extension.

        """
        with suppress(Exception):
            return ZipFile.is_zipfile(self._path)
        return False

    def copy_from_archive(self, other_archive: Archiver) -> bool:
        """Copy files from another archive to the ZIP archive.

        Creates a new ZIP archive containing all files from the source archive.
        This completely replaces the current ZIP file's contents. The operation
        is atomic - if any error occurs, the original archive is left unchanged.

        Files are copied with appropriate compression: image files are stored
        uncompressed while other files are compressed using deflate. Bad or
        corrupted files in the source archive are skipped with a warning.

        Args:
            other_archive: Source archive to copy from. Can be any Archiver
                          implementation (ZIP, RAR, etc.) that supports the
                          read_file() and get_filename_list() methods.

        Returns:
            True if all files were successfully copied, False if any error
                occurred during the copy operation. Partial failures result in
                cleanup of the incomplete archive.

        Note:
            - Creates a new ZIP file, replacing any existing content
            - Automatically selects compression based on file type
            - Skips corrupted files with warnings
            - Performs cleanup on partial failures
            - Uses ZIP64 format for large archives

        Examples:
            >>> source = RarArchiver(Path("source.rar"))
            >>> target = ZipArchiver(Path("target.zip"))
            >>> success = target.copy_from_archive(source)
            >>> if success:
            ...     print("Archive converted successfully")

        """
        try:
            with ZipFile(self.path, mode="w", allowZip64=True) as zout:
                try:
                    for filename in other_archive.get_filename_list():
                        data = other_archive.read_file(filename)
                        if data is not None:
                            # Apply same compression logic as write_file
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
        """Remove partially created archive file.

        Removes the archive file if it exists, typically called when an
        operation fails partway through to prevent leaving corrupted or
        incomplete archives.

        Note:
            - Silently continues if the file doesn't exist
            - Logs warnings for removal failures
            - Used internally for error recovery

        """
        if self.path.exists():
            try:
                self.path.unlink()
            except OSError as e:
                logger.warning("Could not remove partial file %s: %s", self.path, e)

    def _cleanup_temp_files(self) -> None:
        """Clean up any temporary files created during operations.

        Removes all temporary files tracked in _temp_files and clears the list.
        This is automatically called when the archiver is destroyed, but can
        also be called manually for immediate cleanup.

        Note:
            - Silently continues if temp files don't exist
            - Logs warnings for removal failures
            - Clears the temp files list after cleanup attempt

        """
        for temp_file in self._temp_files:
            if temp_file.exists():
                try:
                    temp_file.unlink()
                except OSError as e:
                    logger.warning("Could not remove temp file %s: %s", temp_file, e)
        self._temp_files.clear()

    def __del__(self) -> None:
        """Clean up resources when archiver is destroyed.

        Ensures all temporary files are cleaned up when the archiver object
        is garbage collected. This provides a safety net for resource cleanup
        even if explicit cleanup is not performed.

        Note:
            - Automatically called by Python's garbage collector
            - Provides fail-safe cleanup of temporary resources
            - Should not be called directly - use _cleanup_temp_files() instead

        """
        self._cleanup_temp_files()
