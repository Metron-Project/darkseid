"""Base archiver class providing common interface for archive operations.

This module defines the abstract base class for archive operations, providing
a unified interface for reading, writing, and managing files within different
archive formats such as ZIP, RAR, 7Z, etc.

The Archiver class serves as the foundation for implementing specific archive
format handlers while maintaining consistent behavior across all implementations.

Examples:
    Basic usage with a concrete implementation:

    >>> from pathlib import Path
    >>> from darkseid.archivers.zip import ZipArchiver
    >>>
    >>> # Create or open an archive
    >>> with ZipArchiver(Path("example.zip")) as archive:
    ...     # Write files to the archive
    ...     archive.write_file("hello.txt", "Hello, World!")
    ...     archive.write_file("data.json", '{"key": "value"}')
    ...
    ...     # Read files from the archive
    ...     content = archive.read_file("hello.txt")
    ...     print(content.decode())  # Output: Hello, World!
    ...
    ...     # List all files
    ...     files = archive.get_filename_list()
    ...     print(files)  # Output: ['hello.txt', 'data.json']

    Copying between archives:

    >>> with ZipArchiver(Path("source.zip")) as source:
    ...     with ZipArchiver(Path("destination.zip")) as dest:
    ...         dest.copy_from_archive(source)

Attributes:
    IMAGE_EXT_RE: A compiled regular expression pattern for matching common
        image file extensions (jpeg, jpg, png, webp, gif). Case-insensitive.

"""

from __future__ import annotations

import logging
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

logger = logging.getLogger(__name__)


class ArchiverError(Exception):
    """Base exception for archiver operations.

    This is the parent class for all archiver-related exceptions.
    Concrete implementations should raise more specific exceptions
    that inherit from this base class.

    Examples:
        >>> try:
        ...     archive.read_file("nonexistent.txt")
        ... except ArchiverError as e:
        ...     print(f"Archive operation failed: {e}")

    """


class ArchiverReadError(ArchiverError):
    """Raised when reading from archive fails.

    This exception is raised when:

    - A file doesn't exist in the archive
    - The archive is corrupted or unreadable
    - Permission issues prevent reading
    - The archive format is unsupported

    Examples:
        >>> try:
        ...     content = archive.read_file("missing.txt")
        ... except ArchiverReadError as e:
        ...     print(f"Failed to read file: {e}")

    """


class ArchiverWriteError(ArchiverError):
    """Raised when writing to archive fails.

    This exception is raised when:

    - The archive is read-only
    - Disk space is insufficient
    - Permission issues prevent writing
    - The archive format doesn't support the operation

    Examples:
        >>> try:
        ...     archive.write_file("new.txt", "content")
        ... except ArchiverWriteError as e:
        ...     print(f"Failed to write file: {e}")

    """


class Archiver(ABC):
    """Abstract base class for archive operations.

    Provides a common interface for reading, writing, and managing files
    within different archive formats. This class defines the contract that
    all concrete archive implementations must follow.

    The class is designed to work with various archive formats including
    but not limited to ZIP, RAR, 7Z, TAR, etc. Each concrete implementation
    should handle the specifics of its archive format while maintaining
    the same public interface.

    Features:
        - Context manager support for automatic resource cleanup
        - Unified error handling with specific exception types
        - Support for both text and binary data
        - Batch operations for multiple files
        - Archive-to-archive copying functionality
        - Built-in file existence checking

    Thread Safety:
        The base class does not provide thread safety guarantees.
        Concrete implementations should document their thread safety
        characteristics and implement appropriate locking if needed.

    Performance Considerations:
        - File operations are performed individually; batch operations
          may be more efficient for large numbers of files
        - The get_filename_list() method may be expensive for large archives
        - Consider caching file lists in concrete implementations

    Attributes:
        IMAGE_EXT_RE: Compiled regex for matching image file extensions.
            Matches: .jpg, .jpeg, .png, .webp, .gif (case-insensitive)

    Examples:
        Implementing a concrete archiver:

        >>> class MyArchiver(Archiver):
        ...     def read_file(self, archive_file: str) -> bytes:
        ...         # Implementation specific to your archive format
        ...         pass
        ...
        ...     def write_file(self, archive_file: str, data: str | bytes) -> bool:
        ...         # Implementation specific to your archive format
        ...         pass
        ...
        ...     # ... implement other abstract methods

    """

    IMAGE_EXT_RE = re.compile(r"\.(jpe?g|png|webp|gif)$", re.IGNORECASE)

    def __init__(self, path: Path) -> None:
        """Initialize an Archiver with the specified path.

        Creates a new archiver instance that will operate on the specified
        archive file. The path validation is performed during initialization,
        but the actual archive operations are deferred until method calls.

        Args:
            path: Path to the archive file. Can be an existing file or a path
                where a new archive will be created. The path should include
                the appropriate file extension for the archive format.

        Raises:
            FileNotFoundError: If the archive file doesn't exist and the
                archiver is expected to perform read operations on an existing
                archive. This is determined by the is_write_operation_expected()
                method.

        Note:
            The constructor does not immediately open or create the archive.
            The actual file operations are performed when methods are called.
            This allows for lazy initialization and better error handling.

        Examples:
            >>> from pathlib import Path
            >>>
            >>> # For existing archives
            >>> archiver = MyArchiver(Path("existing.zip"))
            >>>
            >>> # For new archives to be created
            >>> archiver = MyArchiver(Path("new_archive.zip"))

        """
        self._path = path
        self._validate_path()

    def _validate_path(self) -> None:
        """Validate the archive path.

        Performs basic validation of the archive path, including checking
        if the file exists when read operations are expected. This method
        is called during initialization and logs warnings for potential issues.

        The validation is non-blocking - warnings are logged but exceptions
        are not raised unless the archive is actually accessed.

        Note:
            This method can be overridden by subclasses to provide format-specific
            validation logic.

        """
        if not self._path.exists() and not self.is_write_operation_expected():
            logger.warning("Archive file does not exist: %s", self._path)

    def is_write_operation_expected(self) -> bool:
        """Check if this archiver is expected to be used for write operations.

        This method helps determine whether the archiver will be used primarily
        for writing (creating new archives) or reading (accessing existing archives).
        It's used during path validation to determine if a missing file should
        trigger a warning.

        Returns:
            True if write operations are expected (default), False if the archiver
            is read-only or primarily intended for reading existing archives.

        Note:
            Override this method in read-only implementations to return False.
            This will change the validation behavior to expect existing files.

        Examples:
            >>> class ReadOnlyArchiver(Archiver):
            ...     def is_write_operation_expected(self) -> bool:
            ...         return False  # This archiver only reads existing archives

        """
        return True  # Override in read-only implementations

    @property
    def path(self) -> Path:
        """Get the path associated with this archiver.

        Returns:
            The Path object representing the archive file location.

        Examples:
            >>> archiver = MyArchiver(Path("example.zip"))
            >>> print(archiver.path)  # Output: example.zip

        """
        return self._path

    @abstractmethod
    def read_file(self, archive_file: str) -> bytes:
        """Read the contents of a file from the archive.

        Extracts and returns the complete contents of the specified file
        from the archive. The file path should use forward slashes as
        separators regardless of the operating system.

        Args:
            archive_file: Path of the file within the archive. Should use
                forward slashes as path separators (e.g., "folder/file.txt").
                The path is relative to the archive root.

        Returns:
            The complete file contents as bytes. For text files, you'll need to decode the bytes using the
                appropriate encoding.

        Raises:
            ArchiverReadError: If the file cannot be read. This includes cases
                where the file doesn't exist, the archive is corrupted, or
                there are permission issues.

        Examples:
            >>> # Reading a text file
            >>> content = archive.read_file("config.txt")
            >>> config_text = content.decode('utf-8')
            >>>
            >>> # Reading a binary file
            >>> image_data = archive.read_file("images/photo.jpg")
            >>> with open("extracted_photo.jpg", "wb") as f:
            ...     f.write(image_data)

        Note:
            The entire file is loaded into memory. For very large files,
            consider implementing streaming read methods in concrete classes.

        """

    @abstractmethod
    def write_file(self, archive_file: str, data: str | bytes) -> bool:
        """Write data to a file in the archive.

        Creates or overwrites a file in the archive with the provided data.
        If the file already exists, it will be replaced. Directory structure
        within the archive is created automatically as needed.

        Args:
            archive_file: Path of the file within the archive. Should use
                forward slashes as path separators (e.g., "folder/file.txt").
                The path is relative to the archive root.
            data: Data to write to the file. Can be either a string (which
                will be encoded as UTF-8) or bytes for binary data.

        Returns:
            True if the write operation was successful, False otherwise.
            Note that returning False doesn't necessarily mean an error
            occurred - check the logs for detailed error information.

        Raises:
            ArchiverWriteError: If the write operation fails due to serious
                errors such as disk full, permission denied, or archive
                format limitations.

        Examples:
            >>> # Writing text content
            >>> success = archive.write_file("config.txt", "setting=value")
            >>>
            >>> # Writing binary content
            >>> with open("image.jpg", "rb") as f:
            ...     image_data = f.read()
            >>> success = archive.write_file("images/photo.jpg", image_data)
            >>>
            >>> # Writing JSON data
            >>> import json
            >>> data = {"name": "example", "version": "1.0"}
            >>> success = archive.write_file("data.json", json.dumps(data))

        Note:
            String data is automatically encoded as UTF-8 bytes. For other
            encodings, encode the string manually before passing it to this method.

        """

    @abstractmethod
    def remove_file(self, archive_file: str) -> bool:
        """Remove a file from the archive.

        Deletes the specified file from the archive. The operation is
        permanent and cannot be undone. If the file doesn't exist,
        the behavior depends on the implementation but should not raise
        an exception.

        Args:
            archive_file: Path of the file to remove from the archive.
                Should use forward slashes as path separators.

        Returns:
            True if the file was successfully removed or didn't exist,
            False if the removal failed for other reasons.

        Examples:
            >>> # Remove a single file
            >>> success = archive.remove_file("old_config.txt")
            >>> if success:
            ...     print("File removed successfully")
            >>> else:
            ...     print("Failed to remove file")

        Note:
            This method only removes files, not directories. Empty directories
            may remain in the archive depending on the format and implementation.

        """

    @abstractmethod
    def remove_files(self, filename_list: list[str]) -> bool:
        """Remove multiple files from the archive.

        Batch operation to remove multiple files from the archive in a single
        call. This is more efficient than calling remove_file() multiple times
        for large numbers of files.

        Args:
            filename_list: List of file paths to remove from the archive.
                Each path should use forward slashes as separators.

        Returns:
            True if ALL files were successfully removed (or didn't exist),
            False if ANY file removal failed. The operation may be partially
            successful - some files may be removed even if the method returns False.

        Examples:
            >>> # Remove multiple files at once
            >>> files_to_remove = ["old1.txt", "old2.txt", "temp/cache.dat"]
            >>> success = archive.remove_files(files_to_remove)
            >>> if success:
            ...     print("All files removed successfully")
            >>> else:
            ...     print("Some files may not have been removed")

        Note:
            The atomic nature of this operation depends on the archive format
            and implementation. Some formats may support atomic batch operations
            while others may process files individually.

        """

    @abstractmethod
    def get_filename_list(self) -> list[str]:
        """Get a list of all files in the archive.

        Returns a complete list of all files contained in the archive.
        The returned paths use forward slashes as separators and are
        relative to the archive root.

        Returns:
            List of file paths within the archive. The list is sorted
            alphabetically by most implementations. Returns an empty list
            if the archive is empty or doesn't exist.

        Examples:
            >>> files = archive.get_filename_list()
            >>> print(files)
            >>> # Output: ['config.txt', 'data/users.json', 'images/logo.png']
            >>>
            >>> # Check if archive is empty
            >>> if not files:
            ...     print("Archive is empty")
            >>>
            >>> # Filter for specific file types
            >>> text_files = [f for f in files if f.endswith('.txt')]
            >>> image_files = [f for f in files if archive.IMAGE_EXT_RE.search(f)]

        Performance Note:
            This method may be expensive for large archives as it typically
            requires reading the archive's central directory. Consider caching
            the result if you need to call this method multiple times.

        """

    @abstractmethod
    def test(self) -> bool:
        """Test whether the archive is valid.

        Returns:
            bool: True if the file is a valid archive, False otherwise.

        """

    @abstractmethod
    def copy_from_archive(self, other_archive: Archiver) -> bool:
        """Copy files from another archive to this archive.

        Copies all files from the source archive to this archive. This is
        useful for converting between archive formats, merging archives,
        or creating backups.

        Args:
            other_archive: Source archive to copy files from. Must be a
                valid Archiver instance that can read files.

        Returns:
            True if all files were successfully copied, False if any
            copy operation failed. The operation may be partially successful.

        Examples:
            >>> # Copy from ZIP to 7Z
            >>> with ZipArchiver(Path("source.zip")) as source:
            ...     with SevenZipArchiver(Path("destination.7z")) as dest:
            ...         success = dest.copy_from_archive(source)
            >>>
            >>> # Merge two archives
            >>> with ZipArchiver(Path("archive1.zip")) as arch1:
            ...     with ZipArchiver(Path("archive2.zip")) as arch2:
            ...         success = arch2.copy_from_archive(arch1)

        Note:
            - Files with the same name will be overwritten in the destination
            - The source archive must be readable and the destination writable
            - Large archives may take significant time to copy
            - Consider implementing progress callbacks in concrete classes

        """

    def __enter__(self):  # noqa: ANN204
        """Context manager entry.

        Enables the archiver to be used in a 'with' statement for automatic
        resource management. The archiver will be properly initialized and
        any necessary resources will be acquired.

        Examples:
            >>> with MyArchiver(Path("archive.zip")) as archive:
            ...     content = archive.read_file("file.txt")
            ...     # Archive is automatically closed when exiting the block

        """
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:  # noqa: B027
        """Context manager exit.

        Performs cleanup when exiting a 'with' statement. This method should
        be overridden by concrete implementations to release any resources
        such as file handles, network connections, or temporary files.

        Args:
            exc_type: The exception type if an exception was raised, None otherwise.
            exc_val: The exception value if an exception was raised, None otherwise.
            exc_tb: The exception traceback if an exception was raised, None otherwise.

        Note:
            This base implementation does nothing. Concrete implementations
            should override this method to perform proper cleanup.

        """

    def _handle_error(self, operation: str, filename: str, error: Exception) -> None:  # noqa: ARG002
        """Centralized error handling and logging.

        Provides consistent error handling across all archiver operations.
        This method logs exceptions with detailed context information and
        can be extended by subclasses to provide additional error handling
        such as retry logic or error recovery.

        Args:
            operation: Description of the operation that failed (e.g., "read", "write").
            filename: Name of the file involved in the operation.
            error: The exception that occurred during the operation.

        Examples:
            >>> try:
            ...     self._perform_operation()
            ... except Exception as e:
            ...     self._handle_error("read", "example.txt", e)
            ...     raise ArchiverReadError(f"Failed to read {filename}") from e

        Note:
            This method only logs the error and does not raise exceptions.
            Concrete implementations should raise appropriate exceptions
            after calling this method.

        """
        logger.exception("Error during %s operation on %s :: %s", operation, self.path, filename)

    def exists(self, archive_file: str) -> bool:
        """Check if a file exists in the archive.

        Determines whether a specific file exists within the archive without
        actually reading its contents. This is useful for conditional operations
        and avoiding exceptions when checking for file presence.

        Args:
            archive_file: Path of the file to check within the archive.
                Should use forward slashes as path separators.

        Returns:
            True if the file exists in the archive, False otherwise.

        Examples:
            >>> # Check before reading
            >>> if archive.exists("config.txt"):
            ...     content = archive.read_file("config.txt")
            ... else:
            ...     print("Config file not found")
            >>>
            >>> # Conditional writing
            >>> if not archive.exists("backup.txt"):
            ...     archive.write_file("backup.txt", "backup data")

        Performance Note:
            This method calls get_filename_list() internally, which may be
            expensive for large archives. Consider caching the file list
            if you need to check existence of multiple files.

        """
        return archive_file in self.get_filename_list()
