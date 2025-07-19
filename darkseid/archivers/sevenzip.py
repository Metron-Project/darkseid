"""7-Zip archiver implementation using py7zr library.

This module provides 7-Zip archive support for the darkseid archiver system.
It implements the Archiver abstract base class to provide consistent interface
for 7-Zip archive operations.

Requirements:
    py7zr < 1.0.0

Examples:
    Basic usage:

    >>> from pathlib import Path
    >>> from darkseid.archivers.sevenzip import SevenZipArchiver
    >>>
    >>> # Create a new 7z archive
    >>> with SevenZipArchiver(Path("example.cb7")) as archive:
    ...     archive.write_file("hello.txt", "Hello, World!")
    ...     archive.write_file("page1.jpg", b'bogus image')
    ...
    ...     # Read files from the archive
    ...     content = archive.read_file("hello.txt")
    ...     print(content.decode())  # Output: Hello, World!
    ...
    ...     # List all files
    ...     files = archive.get_filename_list()
    ...     print(files)  # Output: ['hello.txt', 'data.json']

    Reading existing archives:

    >>> with SevenZipArchiver(Path("existing.cb7")) as archive:
    ...     if archive.exists("config.txt"):
    ...         config = archive.read_file("config.txt").decode()
    ...         print(f"Config: {config}")

"""

from __future__ import annotations

import logging
from contextlib import suppress

try:
    import py7zr

    PY7ZR_AVAILABLE = True
except ImportError:
    PY7ZR_AVAILABLE = False
    py7zr = None

from typing import TYPE_CHECKING

from typing_extensions import Self

from darkseid.archivers import Archiver, ArchiverReadError, ArchiverWriteError

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class SevenZipArchiver(Archiver):
    """7-Zip archiver implementation using py7zr library.

    This class provides comprehensive 7-Zip archive support following the Archiver interface.
    It handles reading, writing, and management of 7-Zip archives (.cb7) using the
    py7zr library with efficient caching and batch operations.

    Features:
        - Full read/write support for 7-Zip archives
        - LZMA compression for optimal file size reduction
        - Intelligent file caching for improved performance
        - Batch operations for multiple files
        - Memory-efficient streaming operations
        - Context manager support for proper resource cleanup
        - Automatic parent directory creation

    Limitations:
        - Requires py7zr < 1.0.0 to be installed
        - Write operations require full archive reconstruction
        - No password protection support
        - Some advanced 7-Zip features may not be available
        - Performance may be slower than native 7-Zip for very large archives

    Performance Notes:
        - Files are cached in memory after first read for faster subsequent access
        - Filename lists are cached to avoid repeated archive parsing
        - Write operations rewrite the entire archive (7-Zip format limitation)
        - Use batch operations (write_files, remove_files) when possible

    Thread Safety:
        This class is NOT thread-safe. Use separate instances for concurrent access
        or implement external synchronization.

    Error Handling:
        All operations can raise ArchiverReadError or ArchiverWriteError exceptions.
        The class includes comprehensive error handling and logging for troubleshooting.

    Examples:
        Creating and writing to a 7z archive:

        >>> from pathlib import Path
        >>> from darkseid.archivers.sevenzip import SevenZipArchiver
        >>>
        >>> # Create new archive and add files
        >>> archive = SevenZipArchiver(Path("comic.cb7"))
        >>> with archive:
        ...     # Add text file
        ...     archive.write_file("metadata.txt", "Comic metadata here")
        ...
        ...     # Add binary file (e.g., image)
        ...     with open("page1.jpg", "rb") as f:
        ...         archive.write_file("pages/page1.jpg", f.read())
        ...
        ...     # Verify files were added
        ...     files = archive.get_filename_list()
        ...     print(f"Archive contains: {files}")

        Reading from an existing 7z archive:

        >>> # Read from existing archive
        >>> with SevenZipArchiver(Path("existing.cb7")) as archive:
        ...     # Check if archive is valid
        ...     if archive.test():
        ...         # List all files
        ...         files = archive.get_filename_list()
        ...         print(f"Found {len(files)} files")
        ...
        ...         # Read specific file
        ...         if "metadata.txt" in files:
        ...             content = archive.read_file("metadata.txt")
        ...             print(f"Metadata: {content.decode()}")
        ...
        ...         # Process all files
        ...         for filename in files:
        ...             if filename.endswith('.jpg'):
        ...                 image_data = archive.read_file(filename)
        ...                 print(f"Image {filename}: {len(image_data)} bytes")

        Batch operations for better performance:

        >>> with SevenZipArchiver(Path("batch.cb7")) as archive:
        ...     # Remove multiple files at once
        ...     files_to_remove = ["temp1.txt", "temp2.txt", "old_data.json"]
        ...     success = archive.remove_files(files_to_remove)
        ...
        ...     if success:
        ...         print("Batch removal successful")
        ...     else:
        ...         print("Some files could not be removed")

        Error handling:

        >>> from darkseid.archivers import ArchiverReadError, ArchiverWriteError
        >>>
        >>> try:
        ...     with SevenZipArchiver(Path("nonexistent.cb7")) as archive:
        ...         content = archive.read_file("missing.txt")
        ... except ArchiverReadError as e:
        ...     print(f"Read error: {e}")
        ... except ArchiverWriteError as e:
        ...     print(f"Write error: {e}")

    Attributes:
        path (Path): Path to the 7-Zip archive file
        _archive (py7zr.SevenZipFile | None): Current archive instance
        _file_cache (dict[str, bytes]): In-memory cache of read files
        _filename_list_cache (list[str] | None): Cached list of filenames

    """

    def __init__(self, path: Path) -> None:
        """Initialize SevenZipArchiver.

        Creates a new SevenZipArchiver instance for the specified archive file.
        The archive file doesn't need to exist yet - it will be created when
        first written to.

        Args:
            path: Path to the 7-Zip archive file. Can be any extension,
                  but typically .cb7 for comic book archives.

        Note:
            The parent directory will be created automatically when writing
            if it doesn't exist.

        Examples:
            >>> from pathlib import Path
            >>> archiver1 = SevenZipArchiver(Path("my_archive.cb7"))
            >>> archiver2 = SevenZipArchiver(Path("comics/issue1.cb7"))

        """
        super().__init__(path)
        self._archive: py7zr.SevenZipFile | None = None
        self._file_cache: dict[str, bytes] = {}
        self._filename_list_cache: list[str] | None = None

    def __enter__(self) -> Self:
        """Context manager entry for 7-Zip archive operations.

        Returns:
            Self: The archiver instance for use in the context.

        Examples:
            >>> with SevenZipArchiver(Path("archive.cb7")) as archive:
            ...     # Use archive here
            ...     files = archive.get_filename_list()

        """
        return self

    def __exit__(self, *_: object) -> None:
        """Context manager exit with proper cleanup.

        Ensures the archive is properly closed and all caches are cleared
        to prevent memory leaks and resource issues.

        Args:
            *_: Exception information (ignored)

        Note:
            This method is called automatically when exiting a 'with' block.
            It handles exceptions gracefully and always cleans up resources.

        """
        if self._archive is not None:
            try:
                self._archive.close()
            except Exception as e:
                logger.warning("Error closing 7z archive: %s", e)
            finally:
                self._archive = None

        # Clear caches to free memory
        self._file_cache.clear()
        self._filename_list_cache = None

    def _get_archive_for_reading(self) -> py7zr.SevenZipFile:
        """Get archive instance for reading operations.

        Opens the archive file in read mode and returns a py7zr.SevenZipFile
        instance. This is used internally by read operations.

        Returns:
            py7zr.SevenZipFile: Opened archive in read mode.

        Raises:
            ArchiverReadError: If the archive file doesn't exist or cannot be opened.

        Note:
            This method is for internal use. The returned archive should be
            used in a context manager to ensure proper cleanup.

        """
        if not self._path.exists():
            msg = f"Archive file does not exist: {self._path}"
            raise ArchiverReadError(msg)

        try:
            return py7zr.SevenZipFile(self._path, mode="r")
        except Exception as e:
            self._handle_error("open_for_read", str(self._path), e)
            msg = f"Failed to open archive for reading: {self._path}"
            raise ArchiverReadError(msg) from e

    def _get_archive_for_writing(self) -> py7zr.SevenZipFile:
        """Get archive instance for writing operations.

        Opens the archive file in write mode and returns a py7zr.SevenZipFile
        instance. Creates parent directories if they don't exist.

        Returns:
            py7zr.SevenZipFile: Opened archive in write mode.

        Raises:
            ArchiverWriteError: If the archive cannot be opened for writing.

        Note:
            This method is for internal use. Write mode creates a new archive,
            so existing content will be overwritten.

        """
        try:
            # Create parent directories if they don't exist
            self._path.parent.mkdir(parents=True, exist_ok=True)
            return py7zr.SevenZipFile(self._path, mode="w")
        except Exception as e:
            self._handle_error("open_for_write", str(self._path), e)
            msg = f"Failed to open archive for writing: {self._path}"
            raise ArchiverWriteError(msg) from e

    def _load_file_cache(self) -> None:
        """Load all files into memory cache for efficient access.

        Reads all files from the archive into memory to enable faster
        subsequent access. This is particularly useful when multiple
        files will be read from the same archive.

        Note:
            This method is called automatically when needed. It's safe to
            call multiple times - subsequent calls are ignored if cache
            is already loaded.

        Warning:
            Large archives may consume significant memory when cached.
            The cache is cleared when the context manager exits.

        """
        if self._file_cache:
            return  # Already loaded

        try:
            with self._get_archive_for_reading() as archive:
                # Read all files to memory
                extracted = archive.readall()
                for filename, file_info in extracted.items():
                    if hasattr(file_info, "read"):
                        # file_info is a file-like object
                        self._file_cache[filename] = file_info.read()
                    else:
                        # file_info might be bytes directly, tho this shouldn't happen
                        self._file_cache[filename] = file_info  # Do we need to cast this?
        except Exception as e:
            self._handle_error("load_cache", str(self._path), e)
            # Continue without cache - individual operations will handle errors

    def read_file(self, archive_file: str) -> bytes:
        """Read a file from the 7z archive.

        Reads the specified file from the archive and returns its contents as bytes.
        Files are automatically cached in memory for faster subsequent access.

        Args:
            archive_file: Path of the file within the archive. Use forward slashes
                         for directory separators regardless of platform.

        Returns:
            The file contents as bytes. For text files, use .decode() to convert
                to string.

        Raises:
            ArchiverReadError: If the file cannot be read, doesn't exist, or
                             the archive is corrupted.

        Examples:
            >>> with SevenZipArchiver(Path("archive.cb7")) as archive:
            ...     # Read text file
            ...     text_data = archive.read_file("config.txt")
            ...     config = text_data.decode('utf-8')
            ...
            ...     # Read binary file
            ...     image_data = archive.read_file("images/photo.jpg")
            ...     print(f"Image size: {len(image_data)} bytes")
            ...
            ...     # Read file in subdirectory
            ...     data = archive.read_file("data/records/file.json")

        Performance:
            Files are cached after first read, so subsequent reads of the same
            file are very fast. Cache is cleared when context manager exits.

        """
        # Try cache first
        if archive_file in self._file_cache:
            return self._file_cache[archive_file]

        try:
            with self._get_archive_for_reading() as archive:
                # read specific file
                extracted = archive.read(targets=[archive_file])

                if archive_file not in extracted:
                    msg = f"File not found in archive: {archive_file}"
                    raise ArchiverReadError(msg)  # noqa: TRY301

                file_data = extracted[archive_file]

                # Handle different return types from py7zr
                if hasattr(file_data, "read"):
                    content = file_data.read()
                elif isinstance(file_data, bytes):
                    content = file_data
                else:
                    # Convert to bytes if needed
                    content = bytes(file_data)

                # Cache the result
                self._file_cache[archive_file] = content
                return content

        except ArchiverReadError:
            raise
        except Exception as e:
            self._handle_error("read", archive_file, e)
            msg = f"Failed to read file {archive_file}"
            raise ArchiverReadError(msg) from e

    def write_file(self, archive_file: str, data: str | bytes) -> bool:
        """Write a file to the 7z archive.

        Writes the specified data to a file in the archive. If the archive already
        exists, it will be completely reconstructed with the new file added or
        replaced. This is a limitation of the 7-Zip format.

        Args:
            archive_file: Path of the file within the archive. Use forward slashes
                         for directory separators. Parent directories will be
                         created automatically.
            data: Data to write. Can be a string (will be UTF-8 encoded) or bytes.

        Returns:
            True if the write operation was successful.

        Raises:
            ArchiverWriteError: If the write operation fails due to permissions,
                               disk space, or other I/O errors.

        Examples:
            >>> with SevenZipArchiver(Path("archive.cb7")) as archive:
            ...     # Write text file
            ...     archive.write_file("readme.txt", "This is a readme file")
            ...
            ...     # Write binary data
            ...     with open("image.jpg", "rb") as f:
            ...         archive.write_file("images/photo.jpg", f.read())
            ...
            ...     # Write to subdirectory
            ...     archive.write_file("data/config.json", '{"setting": "value"}')

        Performance:
            This operation rewrites the entire archive, so it can be slow for
            large archives. Consider batching multiple writes when possible.

        Note:
            The parent directory of the archive file will be created if it
            doesn't exist.

        """
        try:
            # Convert string to bytes if needed
            file_data = data.encode("utf-8") if isinstance(data, str) else data

            # For 7z, we need to rewrite the entire archive
            # First, read existing files if the archive exists
            existing_files: dict[str, bytes] = {}

            if self._path.exists():
                try:
                    with self._get_archive_for_reading():
                        for filename in self.get_filename_list():
                            if filename != archive_file:  # Skip the file we're replacing
                                existing_files[filename] = self.read_file(filename)
                except Exception as e:
                    logger.warning("Could not read existing archive contents: %s", e)

            # Write new archive with all files
            with self._get_archive_for_writing() as write_archive:
                # Add existing files
                for filename, content in existing_files.items():
                    write_archive.writestr(content, filename)

                # Add new file
                write_archive.writestr(file_data, archive_file)

            # Update cache
            self._file_cache[archive_file] = file_data
            self._filename_list_cache = None  # Invalidate filename cache
        except Exception as e:
            self._handle_error("write", archive_file, e)
            msg = f"Failed to write file {archive_file}"
            raise ArchiverWriteError(msg) from e
        else:
            return True

    def remove_files(self, filename_list: list[str]) -> bool:
        """Remove multiple files from the 7z archive.

        Removes all specified files from the archive in a single operation.

        Args:
            filename_list: List of file paths to remove from the archive.

        Returns:
            True if all files were removed successfully (or didn't exist),
                False if the operation failed.

        Examples:
            >>> with SevenZipArchiver(Path("archive.cb7")) as archive:
            ...     # Remove multiple files at once
            ...     files_to_remove = ["temp1.txt", "temp2.txt", "old/data.json"]
            ...     success = archive.remove_files(files_to_remove)
            ...
            ...     if success:
            ...         print("All files removed successfully")
            ...     else:
            ...         print("Some files could not be removed")

        Note:
            The operation is atomic - either all files are removed or none are.
            Files that don't exist are ignored (not treated as errors).

        """
        try:
            if not self._path.exists():
                return True  # Archive doesn't exist, so removal is successful

            # Get current file list
            current_files = self.get_filename_list()
            files_to_remove = set(filename_list)

            # If none of the files to remove are in the archive, return True
            current_files_set = set(current_files)
            if not any(filename in current_files_set for filename in filename_list):
                return True

            # Read all files except those to remove
            remaining_files: dict[str, bytes] = {}

            for filename in current_files:
                if filename not in files_to_remove:
                    remaining_files[filename] = self.read_file(filename)

            # Rewrite archive without the removed files
            with self._get_archive_for_writing() as write_archive:
                for filename, content in remaining_files.items():
                    write_archive.writestr(content, filename)

            # Update cache
            for filename in filename_list:
                self._file_cache.pop(filename, None)
            self._filename_list_cache = None  # Invalidate filename cache
        except Exception as e:
            self._handle_error("remove_files", str(filename_list), e)
            return False
        else:
            return True

    def get_filename_list(self) -> list[str]:
        """Get list of all files in the 7z archive.

        Returns a sorted list of all file paths contained in the archive.
        The list is cached for performance and updated when files are
        added or removed.

        Returns:
            List of file paths in the archive, sorted alphabetically.
                Returns empty list if archive doesn't exist or is empty.

        Examples:
            >>> with SevenZipArchiver(Path("archive.cb7")) as archive:
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
            with self._get_archive_for_reading() as archive:
                # Get file list from archive
                file_list = [file_.filename for file_ in archive.list() if not file_.is_directory]
                self._filename_list_cache = sorted(file_list)
                return self._filename_list_cache
        except Exception as e:
            self._handle_error("get_filename_list", str(self._path), e)
            self._filename_list_cache = []
            return self._filename_list_cache

    def test(self) -> bool:
        """Test whether the 7z archive is valid.

        Checks if the archive file exists and is a valid 7-Zip archive
        that can be read. This is useful for validating archives before
        attempting to read from them.

        Returns:
            True if the archive is valid and can be read, False otherwise.

        Examples:
            >>> archive = SevenZipArchiver(Path("archive.cb7"))
            >>> if archive.test():
            ...     print("Archive is valid")
            ...     with archive:
            ...         files = archive.get_filename_list()
            ... else:
            ...     print("Archive is invalid or corrupted")

        Note:
            This method does not require the archive to be opened with
            a context manager - it can be called on any instance.

        """
        with suppress(Exception):
            return py7zr.is_7zfile(self._path)
        return False

    def copy_from_archive(self, other_archive: Archiver) -> bool:
        """Copy files from another archive to this 7z archive.

        Note:
            This operation is not supported for 7-Zip archives and will
            always return False. Converting other archive formats to 7-Zip
            is not recommended as it may not provide meaningful benefits
            and could reduce compatibility.

        Args:
            other_archive: The source archive to copy files from.

        Returns:
            False: This operation is not supported for 7-Zip archives.

        Warning:
            A warning will be logged when this method is called, indicating
            that the copy operation was attempted on a 7-Zip archive.

        Examples:
            >>> seven_zip_archive = SevenZipArchiver(Path("target.cb7"))
            >>> zip_archive = ZipArchiver(Path("source.zip"))
            >>> result = seven_zip_archive.copy_from_archive(zip_archive)
            >>> print(f"Copy successful: {result}")  # Will print: Copy successful: False

        """
        logger.warning("Cannot copy to 7ZIP archive from: %s", other_archive.path)
        return False
