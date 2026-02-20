"""Tar archiver implementation for handling TAR files.

This module provides the TarArchiver class which implements the Archiver interface
for working with TAR archives, including compressed variants like .tar.gz, .tar.bz2,
and .tar.xz.

The TarArchiver supports:
- Reading from and writing to TAR archives
- Automatic compression detection based on file extension
- Support for gzip, bzip2, and xz compression
- Context manager support for proper resource cleanup
- Batch operations for multiple files

Examples:
    Basic usage with uncompressed TAR:

    >>> from pathlib import Path
    >>> from darkseid.archivers.tar import TarArchiver
    >>>
    >>> with TarArchiver(Path("archive.cbt")) as archive:
    ...     archive.write_file("hello.txt", "Hello, World!")
    ...     content = archive.read_file("hello.txt")
    ...     print(content.decode())  # Output: Hello, World!

    Working with compressed TAR files:

    >>> # Gzip compressed
    >>> with TarArchiver(Path("archive.tar.gz")) as archive:
    ...     archive.write_file("data.json", '{"key": "value"}')
    ...     files = archive.get_filename_list()
    ...     print(files)  # Output: ['data.json']

    >>> # Bzip2 compressed
    >>> with TarArchiver(Path("archive.tar.bz2")) as archive:
    ...     archive.write_file("metadata.txt", "blah blah")

"""

from __future__ import annotations

import io
import logging
import tarfile
from typing import TYPE_CHECKING

from darkseid.archivers.archiver import Archiver, ArchiverReadError, ArchiverWriteError

if TYPE_CHECKING:
    from pathlib import Path

    from typing_extensions import Self

logger = logging.getLogger(__name__)


class TarArchiver(Archiver):
    """Tar archiver implementation for handling TAR files.

    This class provides support for TAR archives including compressed variants.
    It automatically detects the compression format based on the file extension
    and handles the appropriate compression/decompression transparently.

    Supported formats:

    - .cbt: Uncompressed TAR
    - .tar: Uncompressed TAR
    - .tar.gz, .tgz: Gzip compressed TAR
    - .tar.bz2, .tbz2: Bzip2 compressed TAR
    - .tar.xz, .txz: XZ compressed TAR

    Features:

    - Thread-safe for reading operations (multiple readers)
    - Write operations should be performed by a single thread
    - Automatic compression format detection
    - Efficient batch operations
    - Proper resource cleanup via context manager

    Performance Notes:
        - Filename lists are cached to avoid repeated archive parsing

    Note:
        TAR files are append-only by nature. When removing files, the entire
        archive is reconstructed without the specified files. This can be
        expensive for large archives.

    """

    def __init__(self, path: Path) -> None:
        """Initialize TarArchiver with the specified path.

        Args:
            path: Path to the TAR file. The compression format is determined
                automatically based on the file extension.

        """
        super().__init__(path)
        self._mode = self._determine_mode()
        self._filename_list_cache: list[str] | None = None

    def __enter__(self) -> Self:
        """Context manager entry for Tar archive operations.

        Returns:
            Self: The archiver instance for use in the context.

        Examples:
            >>> with TarArchiver(Path("archive.cbt")) as archive:
            ...     # Use archive here
            ...     files = archive.get_filename_list()

        """
        return self

    def __exit__(self, *_: object) -> None:
        """Context manager exit with proper cleanup.

        Ensures the archive is properly closed and caches are cleared
        to prevent memory leaks and resource issues.

        Args:
            *_: Exception information (ignored)

        Note:
            This method is called automatically when exiting a 'with' block.
            It handles exceptions gracefully and always cleans up resources.

        """
        # Clear filename cache to free memory
        self._filename_list_cache = None

    def _determine_mode(self) -> str:  # noqa: PLR0911
        """Determine the appropriate tarfile mode based on file extension.

        Returns:
            String mode suitable for tarfile.open() calls.

        """
        suffix = self._path.suffix.lower()
        stem_suffix = self._path.stem.split(".")[-1].lower() if "." in self._path.stem else ""

        # Handle double extensions like .tar.gz
        if suffix == ".gz" and stem_suffix == "tar":
            return "gz"
        if suffix == ".bz2" and stem_suffix == "tar":
            return "bz2"
        if suffix == ".xz" and stem_suffix == "tar":
            return "xz"
        if suffix == ".tgz":
            return "gz"
        if suffix == ".tbz2":
            return "bz2"
        if suffix == ".txz":
            return "xz"
        return ""  # Uncompressed TAR & .cbt

    def _write_mode(self) -> str:
        return f"w:{self._mode}" if self._mode else "w"

    def _read_mode(self) -> str:
        return f"r:{self._mode}" if self._mode else "r"

    def read_file(self, archive_file: str) -> bytes:
        """Read the contents of a file from the TAR archive.

        Args:
            archive_file: Path of the file within the archive.

        Returns:
            The complete file contents as bytes.

        Raises:
            ArchiverReadError: If the file cannot be read from the archive.

        """
        try:
            try:
                with tarfile.open(self._path, mode=self._read_mode()) as tar:
                    member = tar.getmember(archive_file)
                    if not member.isfile():
                        msg = f"'{archive_file}' is not a regular file"
                        raise ArchiverReadError(msg)

                    file_obj = tar.extractfile(member)
                    if file_obj is None:
                        msg = f"Cannot extract file: {archive_file}"
                        raise ArchiverReadError(msg)

                    return file_obj.read()
            except KeyError as err:
                msg = f"File not found in archive: {archive_file}"
                raise ArchiverReadError(msg) from err
        except (tarfile.TarError, OSError) as e:
            self._handle_error("read", archive_file, e)
            msg = f"Failed to read file '{archive_file}': {e}"
            raise ArchiverReadError(msg) from e

    def write_file(self, archive_file: str, data: str | bytes) -> bool:
        """Write data to a file in the TAR archive.

        Args:
            archive_file: Path of the file within the archive.
            data: Data to write to the file.

        Returns:
            True if the write operation was successful, False otherwise.

        Raises:
            ArchiverWriteError: If the write operation fails.

        """
        try:
            # Convert string to bytes if necessary
            if isinstance(data, str):
                data = data.encode("utf-8")

            # For TAR files, we need to read existing files and rewrite the entire archive
            existing_files = {}

            # Read existing files if the archive exists
            if self._path.exists():
                try:
                    with tarfile.open(self._path, mode=self._read_mode()) as tar:
                        for member in tar.getmembers():
                            if member.isfile() and member.name != archive_file:
                                file_obj = tar.extractfile(member)
                                if file_obj:
                                    existing_files[member.name] = file_obj.read()
                except (tarfile.TarError, OSError):
                    # If we can't read existing files, start fresh
                    existing_files = {}

            # Create new archive with existing files plus the new one
            with tarfile.open(self._path, mode=self._write_mode()) as tar:
                # Add existing files
                for filename, file_data in existing_files.items():
                    tarinfo = tarfile.TarInfo(name=filename)
                    tarinfo.size = len(file_data)
                    tar.addfile(tarinfo, io.BytesIO(file_data))

                # Add the new file
                tarinfo = tarfile.TarInfo(name=archive_file)
                tarinfo.size = len(data)
                tar.addfile(tarinfo, io.BytesIO(data))
        except (tarfile.TarError, OSError) as e:
            self._handle_error("write", archive_file, e)
            msg = f"Failed to write file '{archive_file}': {e}"
            raise ArchiverWriteError(msg) from e
        else:
            # Invalidate filename cache since the archive contents changed
            self._filename_list_cache = None
            return True

    def remove_files(self, filename_list: list[str]) -> bool:
        """Remove multiple files from the TAR archive.

        Args:
            filename_list: List of file paths to remove from the archive.

        Returns:
            True if all files were successfully removed, False otherwise.

        """
        try:
            if not self._path.exists():
                return True  # No files to remove

            files_to_remove = set(filename_list)
            remaining_files = {}

            # Read all files except those to remove
            with tarfile.open(self._path, mode=self._read_mode()) as tar:
                for member in tar.getmembers():
                    if member.isfile() and member.name not in files_to_remove:
                        file_obj = tar.extractfile(member)
                        if file_obj:
                            remaining_files[member.name] = file_obj.read()

            # Recreate archive without the removed files
            with tarfile.open(self._path, mode=self._write_mode()) as tar:
                for filename, file_data in remaining_files.items():
                    tarinfo = tarfile.TarInfo(name=filename)
                    tarinfo.size = len(file_data)
                    tar.addfile(tarinfo, io.BytesIO(file_data))
        except (tarfile.TarError, OSError) as e:
            self._handle_error("remove_files", str(filename_list), e)
            return False
        else:
            # Invalidate filename cache since the archive contents changed
            self._filename_list_cache = None
            return True

    def get_filename_list(self) -> list[str]:
        """Get list of all files in the Tar archive.

        Returns a sorted list of all file paths contained in the archive.
        The list is cached for performance and updated when files are
        added or removed.

        Returns:
            List of file paths in the archive, sorted alphabetically.
                Returns empty list if archive doesn't exist or is empty.

        Examples:
            >>> with TarArchiver(Path("archive.cbt")) as archive:
            ...     files = archive.get_filename_list()
            ...     print(f"Archive contains {len(files)} files:")
            ...     for file in files:
            ...         print(f"  - {file}")
            ...
            ...     # Check if specific file exists
            ...     if "config.txt" in files:
            ...         print("Config file found")

        Performance:
            The filename list is cached after first access, so subsequent
            calls are very fast. Cache is invalidated when files are added
            or removed.

        Note:
            File paths use forward slashes regardless of platform.

        """
        if self._filename_list_cache is not None:
            return self._filename_list_cache

        if not self._path.exists():
            self._filename_list_cache = []
            return self._filename_list_cache

        try:
            with tarfile.open(self._path, mode=self._read_mode()) as tar:
                # Only return regular files, not directories
                filenames = [member.name for member in tar.getmembers() if member.isfile()]
                self._filename_list_cache = sorted(filenames)
        except (tarfile.TarError, OSError, ArchiverReadError) as e:
            self._handle_error("get_filename_list", str(self._path), e)
            return []
        else:
            return self._filename_list_cache

    def test(self) -> bool:
        """Test whether the TAR archive is valid.

        Returns:
            True if the file is a valid TAR archive, False otherwise.

        """
        if not self._path.exists():
            return False

        try:
            with tarfile.open(self._path, mode=self._read_mode()) as tar:
                # Try to read the member list to validate the archive
                list(tar.getmembers())
        except (tarfile.TarError, OSError) as e:
            logger.debug("TAR test failed for %s: %s", self._path, e)
            return False
        else:
            return True

    def copy_from_archive(self, other_archive: Archiver) -> bool:  # noqa: C901
        """Copy files from another archive to this TAR archive.

        Args:
            other_archive: Source archive to copy files from.

        Returns:
            True if all files were successfully copied, False otherwise.

        """
        try:
            # Get list of files from source archive
            source_files = other_archive.get_filename_list()
            if not source_files:
                return True  # Nothing to copy

            # Read existing files from this archive
            existing_files = {}
            if self._path.exists():
                try:
                    with tarfile.open(self._path, mode=self._read_mode()) as tar:
                        for member in tar.getmembers():
                            if member.isfile():
                                file_obj = tar.extractfile(member)
                                if file_obj:
                                    existing_files[member.name] = file_obj.read()
                except (tarfile.TarError, OSError):
                    # If we can't read existing files, start fresh
                    existing_files = {}

            # Create new archive with existing files plus copied files
            with tarfile.open(self._path, mode=self._write_mode()) as tar:
                # Add existing files first
                for filename, file_data in existing_files.items():
                    if filename not in source_files:  # Don't duplicate files
                        tarinfo = tarfile.TarInfo(name=filename)
                        tarinfo.size = len(file_data)
                        tar.addfile(tarinfo, io.BytesIO(file_data))

                # Add files from source archive
                try:
                    for filename in source_files:
                        file_data = other_archive.read_file(filename)
                        tarinfo = tarfile.TarInfo(name=filename)
                        tarinfo.size = len(file_data)
                        tar.addfile(tarinfo, io.BytesIO(file_data))
                except Exception:
                    logger.exception("Failed to copy file %s", filename)
                    return False
        except (tarfile.TarError, OSError) as e:
            self._handle_error("copy_from_archive", str(other_archive.path), e)
            return False
        else:
            return True
