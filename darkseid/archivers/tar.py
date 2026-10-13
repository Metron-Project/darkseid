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
import time
from typing import TYPE_CHECKING

from darkseid.archivers.archiver import Archiver, ArchiverReadError, ArchiverWriteError

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable
    from pathlib import Path
    from typing import Self

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

    - Automatic compression format detection
    - Efficient batch operations
    - Proper resource cleanup via context manager

    Thread Safety:
        See darkseid.archivers.archiver.Archiver for the full contract.

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

    def read_file(self, archive_file: str, max_size: int | None = None) -> bytes:
        """Read the contents of a file from the TAR archive.

        Args:
            archive_file: Path of the file within the archive.
            max_size: Maximum uncompressed size in bytes to read. Defaults to
                MAX_READ_SIZE when None.

        Returns:
            The complete file contents as bytes.

        Raises:
            ArchiverFileTooLargeError: If the file's size exceeds max_size.
            ArchiverReadError: If the file cannot be read from the archive.

        """
        try:
            try:
                with tarfile.open(self._path, mode=self._read_mode()) as tar:
                    member = tar.getmember(archive_file)
                    if not member.isfile():
                        msg = f"'{archive_file}' is not a regular file"
                        raise ArchiverReadError(msg)

                    self._check_size(archive_file, member.size, self._resolve_max_size(max_size))
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

    @staticmethod
    def _check_reached_end(tar: tarfile.TarFile) -> None:
        """Raise if iterating the archive stopped before its end-of-archive marker.

        tarfile silently stops iterating when it hits an invalid header after the
        first member, which would drop every member after it from a rewrite.

        Args:
            tar: An archive opened for reading that has been fully iterated.

        Raises:
            tarfile.ReadError: If the block where iteration stopped isn't the end marker.

        """
        if tar.fileobj is None:
            return
        tar.fileobj.seek(tar.offset)
        if tar.fileobj.read(tarfile.BLOCKSIZE).strip(b"\0"):
            msg = f"Invalid header at offset {tar.offset}"
            raise tarfile.ReadError(msg)

    def _rewrite(self, exclude: Collection[str], new_files: Iterable[tuple[str, bytes]]) -> None:
        """Rebuild the archive, keeping existing members and adding new files.

        Existing regular files whose names aren't in exclude are streamed from the
        current archive into a temporary file, followed by new_files. The temporary
        file then atomically replaces the original, so members are never all held in
        memory and a failure part way through leaves the original archive untouched.

        Args:
            exclude: Names of existing members to leave out of the new archive.
            new_files: (name, data) pairs to append to the new archive.

        Raises:
            tarfile.TarError: If the existing archive can't be read in full or the new
                one written.
            OSError: If a file system operation fails.

        """
        has_existing = self._path.exists() and self._path.stat().st_size > 0
        with (
            self._atomic_replace() as out_path,
            tarfile.open(out_path, mode=self._write_mode()) as out,
        ):
            if has_existing:
                with tarfile.open(self._path, mode=self._read_mode()) as src:
                    for member in src:
                        if member.isfile() and member.name not in exclude:
                            out.addfile(member, src.extractfile(member))
                    self._check_reached_end(src)

            for name, data in new_files:
                tarinfo = tarfile.TarInfo(name=name)
                tarinfo.size = len(data)
                tarinfo.mtime = int(time.time())
                out.addfile(tarinfo, io.BytesIO(data))

        # Invalidate filename cache since the archive contents changed
        self._filename_list_cache = None

    def write_file(self, archive_file: str, data: str | bytes) -> bool:
        """Write data to a file in the TAR archive.

        The archive is rebuilt in a temporary file that replaces the original only
        once it is complete, so the original is left untouched if the write fails.

        Args:
            archive_file: Path of the file within the archive.
            data: Data to write to the file.

        Returns:
            True if the write operation was successful.

        Raises:
            ArchiverWriteError: If the existing archive can't be read or the write fails.

        """
        # Convert string to bytes if necessary
        if isinstance(data, str):
            data = data.encode("utf-8")

        try:
            self._rewrite({archive_file}, [(archive_file, data)])
        except (tarfile.TarError, OSError) as e:
            self._handle_error("write", archive_file, e)
            msg = f"Failed to write file '{archive_file}': {e}"
            raise ArchiverWriteError(msg) from e
        else:
            return True

    def remove_files(self, filename_list: list[str]) -> bool:
        """Remove multiple files from the TAR archive.

        Args:
            filename_list: List of file paths to remove from the archive.

        Returns:
            True if all files were successfully removed, False otherwise. The
                original archive is left untouched on failure.

        """
        if not self._path.exists():
            return True  # No files to remove

        try:
            self._rewrite(set(filename_list), [])
        except (tarfile.TarError, OSError) as e:
            self._handle_error("remove_files", str(filename_list), e)
            return False
        else:
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

    def copy_from_archive(self, other_archive: Archiver) -> bool:
        """Copy files from another archive to this TAR archive.

        Existing files in this archive are kept unless the source archive has a
        file with the same name. Nothing is written if any file can't be copied.
        Files with unsafe names (absolute paths, drive letters or '..' components)
        are skipped with a warning.

        Args:
            other_archive: Source archive to copy files from.

        Returns:
            True if all files were successfully copied, False otherwise.

        """
        try:
            source_files = self._safe_source_files(other_archive)
            if not source_files:
                return True  # Nothing to copy

            # Read source files lazily so only one is held in memory at a time
            new_files = ((filename, other_archive.read_file(filename)) for filename in source_files)
            self._rewrite(set(source_files), new_files)
        except Exception as e:  # noqa: BLE001 - convert any source or TAR failure to a bool result
            self._handle_error("copy_from_archive", str(other_archive.path), e)
            return False
        else:
            return True
