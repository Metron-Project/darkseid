"""ZIP archive implementation with comprehensive file manipulation capabilities.

This module provides a ZipArchiver class that extends the base Archiver interface
to handle ZIP file operations including reading, writing, removing files, and
copying between archives. It supports both compressed and uncompressed storage
based on file type optimization.

Examples:
    Basic usage of the ZipArchiver:

    >>> from pathlib import Path
    >>> archiver = ZipArchiver(Path("example.cbz"))
    >>> content = archiver.read_file("readme.txt")
    >>> archiver.write_file("new_file.txt", "Hello, World!")
    >>> files = archiver.get_filename_list()
    >>> archiver.remove_files(["old_file.txt"])

"""

from __future__ import annotations

import logging
import lzma
import zlib
from contextlib import suppress
from pathlib import Path
from zipfile import is_zipfile

import rarfile
from zipremove import ZIP_DEFLATED, ZIP_STORED, BadZipfile, ZipFile

from darkseid.archivers.archiver import Archiver, ArchiverReadError
from darkseid.constants import IMAGE_EXTENSIONS

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
    - Automatic cleanup of  partial operations

    Attributes:
        path (Path): Path to the ZIP archive file

    Thread Safety:
        See darkseid.archivers.archiver.Archiver for the full contract.

    Examples:
        >>> archiver = ZipArchiver(Path("my_archive.cbz"))
        >>> archiver.write_file("config.json", '{"version": "1.0"}')
        >>> data = archiver.read_file("config.json")
        >>> archiver.remove_files(["old_config.json"])

    """

    def __init__(self, path: Path) -> None:
        """Initialize a ZipArchiver with the provided path.

        Args:
            path: Path to the ZIP archive file. The file doesn't need to exist
                  yet - it will be created when first written to.


        """
        super().__init__(path)

    @staticmethod
    def _compress_type(archive_file: str) -> int:
        """Store page images uncompressed, since they're already compressed; deflate the rest."""
        is_image = Path(archive_file).suffix.lower() in IMAGE_EXTENSIONS
        return ZIP_STORED if is_image else ZIP_DEFLATED

    def read_file(self, archive_file: str, max_size: int | None = None) -> bytes:
        """Read the contents of a file from the ZIP archive.

        Opens the ZIP archive in read mode and extracts the specified file's
        contents. The file path should use forward slashes as separators,
        following ZIP archive conventions.

        Args:
            archive_file: Path of the file within the archive. Should use
                         forward slashes (/) as path separators regardless
                         of the host operating system.
            max_size: Maximum uncompressed size in bytes to read. Defaults to
                     MAX_READ_SIZE when None.

        Returns:
            File contents as bytes. For text files, you may need to decode
                using the appropriate encoding (e.g., .decode('utf-8')).

        Raises:
            ArchiverFileTooLargeError: If the file's uncompressed size exceeds max_size.
            ArchiverReadError: If the file cannot be read due to:

                - Corrupt ZIP file (BadZipfile)
                - File system errors (OSError)
                - File not found in archive (KeyError)
                - Encrypted member, unsupported compression method, or corrupt
                  compressed data

        Examples:
            >>> archiver = ZipArchiver(Path("docs.cbz"))
            >>> content = archiver.read_file("readme.txt")
            >>> text = content.decode('utf-8')

        """
        try:
            with ZipFile(self.path, mode="r") as zf:
                info = zf.getinfo(archive_file)
                # zipfile never decompresses past the recorded file_size.
                self._check_size(archive_file, info.file_size, self._resolve_max_size(max_size))
                return zf.read(info)
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
        except (RuntimeError, NotImplementedError, EOFError, zlib.error, lzma.LZMAError) as e:
            # zipfile reports encrypted members as RuntimeError and unsupported compression
            # as NotImplementedError; corrupt compressed data surfaces as the codec's error.
            self._handle_error("read", archive_file, e)
            msg = f"Cannot read '{archive_file}' from ZIP file: {e}"
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
            - Image files (extensions in IMAGE_EXTENSIONS) are stored uncompressed
            - Other files are compressed with deflate at maximum compression level
            - Existing files are replaced, not appended to

        Examples:
            >>> archiver = ZipArchiver(Path("data.cbz"))
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
        compress_type = self._compress_type(archive_file)

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
        finally:
            # ZIP files are edited in place, so even a failed write may have changed them.
            self.invalidate_cache()

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
            - The archive is edited in place and repacked once after all removals,
              so a failure part way through can leave some files removed

        Examples:
            >>> archiver = ZipArchiver(Path("batch_cleanup.cbz"))
            >>> files_to_remove = ["temp1.txt", "temp2.txt", "cache.dat"]
            >>> success = archiver.remove_files(files_to_remove)
            >>> if success:
            ...     print(f"Removed {len(files_to_remove)} files")

        """
        if not filename_list:
            return True

        # Only attempt to remove files that actually exist
        try:
            existing_files = set(self.get_filename_list())
        except ArchiverReadError as e:
            self._handle_error("remove_multiple", str(filename_list), e)
            return False
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
        finally:
            # ZIP files are edited in place, so even a failed removal may have changed them.
            self.invalidate_cache()

    def _list_files(self) -> list[str]:
        """List all entries in the ZIP archive, including any directory entries.

        Returns:
            The member names, using forward slashes regardless of host OS.

        """
        with ZipFile(self.path, mode="r") as zf:
            return zf.namelist()

    def test(self) -> bool:
        """Test whether the file is a valid ZIP archive.

        Returns:
            bool: True if the file is a valid ZIP archive, False otherwise.

        Note:
            This method uses the zipfile library to validate the archive structure,
            not just the file extension.

        """
        with suppress(Exception):
            return is_zipfile(self._path)
        return False

    def copy_from_archive(self, other_archive: Archiver) -> bool:
        """Copy files from another archive to the ZIP archive.

        Creates a new ZIP archive containing all files from the source archive.
        This completely replaces the current ZIP file's contents. If the source
        can't be listed, the ZIP file is left untouched; if copying fails after
        that, the incomplete ZIP file is deleted.

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
            - Skips files with unsafe names (absolute paths, drive letters or
              '..' components) with warnings
            - Performs cleanup on partial failures
            - Uses ZIP64 format for large archives

        Examples:
            >>> source = RarArchiver(Path("source.rar"))
            >>> target = ZipArchiver(Path("target.cbz"))
            >>> success = target.copy_from_archive(source)
            >>> if success:
            ...     print("Archive converted successfully")

        """
        try:
            source_files = self._safe_source_files(other_archive)
        except ArchiverReadError as e:
            self._handle_error("copy", str(other_archive.path), e)
            return False

        try:
            with ZipFile(self.path, mode="w", allowZip64=True) as zout:
                try:
                    for filename in source_files:
                        data = other_archive.read_file(filename)
                        if data is not None:
                            compress_type = self._compress_type(filename)
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
        finally:
            # The ZIP file was replaced or deleted, so its old listing no longer applies.
            self.invalidate_cache()

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
