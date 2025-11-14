"""PDF document implementation.

This module provides a read-only interface for working with PDF documents.
PDF files are treated as archives where each page is rendered as a PNG image.
The implementation uses pymupdf (fitz) for PDF processing.

Examples:
    >>> from pathlib import Path
    >>> archiver = PdfArchiver(Path("example.pdf"))
    >>> files = archiver.get_filename_list()
    >>> # Returns: ['page_001.png', 'page_002.png', ...]
    >>> page_data = archiver.read_file("page_001.png")
    >>> # Returns PNG image data for first page

Note:
    All write operations (write_file, remove_files, copy_from_archive) will
    return False and log warnings since PDF archives are read-only.

"""

from __future__ import annotations

import logging
from contextlib import suppress
from typing import TYPE_CHECKING

try:
    import fitz  # pymupdf

    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    fitz = None

if TYPE_CHECKING:
    from pathlib import Path

from darkseid.archivers.archiver import Archiver, ArchiverReadError

logger = logging.getLogger(__name__)


class PdfArchiver(Archiver):
    """A read-only archiver for PDF files.

    This class provides an interface for reading pages from PDF documents.
    Each page is treated as a separate PNG image file within the archive.
    Pages are numbered sequentially with zero-padding (page_001.png, page_002.png, etc.).

    The implementation uses pymupdf (fitz) for PDF rendering and processing.
    Write operations are not supported - PDFs are treated as read-only archives.

    Attributes:
        path (Path): The filesystem path to the PDF file.

    Note:
        PDF files are read-only in this implementation. Each page is rendered
        to PNG format at 150 DPI by default when read.

    """

    def __init__(self, path: Path) -> None:
        """Initialize a PdfArchiver with the provided path.

        Args:
            path: The filesystem path to the PDF file.

        Note:
            This constructor does not validate that the file exists or is
            a valid PDF document. Validation occurs when operations are
            performed on the document.

        """
        super().__init__(path)

    def is_write_operation_expected(self) -> bool:
        """Check if write operations are supported.

        Returns:
            False: PDF files are always read-only in this implementation.

        Note:
            This method is used by the parent class to determine if write
            operations should be attempted. For PDF files, this always
            returns False to prevent unnecessary operation attempts.

        """
        return False

    def read_file(self, archive_file: str) -> bytes:
        """Read a page from the PDF as PNG image data.

        Args:
            archive_file: The virtual filename within the archive. Expected format
                         is 'page_NNN.png' where NNN is a zero-padded page number.
                         Page numbers start from 001.

        Returns:
            PNG image data for the requested page as bytes.

        Raises:
            ArchiverReadError: If the page cannot be read due to:

                - Invalid page filename format
                - Page number out of range
                - Corrupt or invalid PDF file
                - PDF processing errors
                - Other I/O errors

        Examples:
            >>> archiver = PdfArchiver(Path("document.pdf"))
            >>> image_data = archiver.read_file("page_001.png")
            >>> with open("page1.png", "wb") as f:
            ...     f.write(image_data)

        """
        # Extract page number from filename (e.g., "page_001.png" -> 0)
        try:
            if not archive_file.startswith("page_") or not archive_file.endswith(".png"):
                msg = f"Invalid page filename format: {archive_file}"
                raise ArchiverReadError(msg)

            page_str = archive_file[5:-4]  # Extract number from "page_NNN.png"
            page_index = int(page_str) - 1  # Convert to 0-based index

            if page_index < 0:
                msg = f"Invalid page number: {page_str}"
                raise ArchiverReadError(msg)

        except ValueError as e:
            msg = f"Invalid page filename format: {archive_file}"
            raise ArchiverReadError(msg) from e

        try:
            doc = fitz.open(self.path)
            try:
                if page_index >= len(doc):
                    msg = f"Page {page_index + 1} not found (document has {len(doc)} pages)"
                    raise ArchiverReadError(msg)

                page = doc[page_index]
                # Render page to PNG at 150 DPI (zoom factor of 2.0)
                # mat = fitz.Matrix(2.0, 2.0) produces 150 DPI for typical 72 DPI PDFs
                mat = fitz.Matrix(2.0, 2.0)
                pix = page.get_pixmap(matrix=mat)
                return pix.tobytes("png")
            finally:
                doc.close()

        except fitz.FileDataError as e:
            self._handle_error("read", archive_file, e)
            msg = f"Corrupt or invalid PDF file: {e}"
            raise ArchiverReadError(msg) from e
        except Exception as e:
            self._handle_error("read", archive_file, e)
            msg = f"Failed to read page from PDF: {e}"
            raise ArchiverReadError(msg) from e

    def write_file(self, archive_file: str, data: str | bytes) -> bool:  # noqa: ARG002
        """Attempt to write data to the PDF.

        Args:
            archive_file: The virtual filename within the archive.
            data: The data to write (string or bytes).

        Returns:
            False: PDF files are read-only, so this operation always fails.

        Note:
            This method logs a warning and returns False immediately.
            No actual write operation is attempted since PDFs are treated
            as read-only archives in this implementation.

        Warning:
            A warning will be logged indicating that the write operation
            was attempted on a read-only PDF archive.

        """
        logger.warning("Cannot write to PDF archive: %s", archive_file)
        return False

    def remove_files(self, filename_list: list[str]) -> bool:
        """Attempt to remove files from the PDF.

        Args:
            filename_list: A list of filenames to remove from the archive.

        Returns:
            False: PDF files are read-only, so this operation always fails.

        Note:
            This method logs a warning and returns False immediately.
            No actual removal operations are attempted since PDFs are treated
            as read-only archives in this implementation.

        Warning:
            A warning will be logged indicating that the bulk remove operation
            was attempted on a read-only PDF archive, including the list of
            files that were requested to be removed.

        """
        logger.warning("Cannot remove files from PDF archive: %s", filename_list)
        return False

    def get_filename_list(self) -> list[str]:
        """Get a list of all pages in the PDF as virtual filenames.

        Returns:
            A list of virtual filenames representing each page in the PDF.
                Filenames follow the format 'page_NNN.png' where NNN is a
                zero-padded page number starting from 001.

        Raises:
            ArchiverReadError: If the PDF cannot be read due to:

                - Corrupt or invalid PDF file
                - File system or permission errors
                - PDF processing errors

        Examples:
            >>> archiver = PdfArchiver(Path("document.pdf"))
            >>> pages = archiver.get_filename_list()
            >>> print(f"PDF contains {len(pages)} pages:")
            >>> # Output: ['page_001.png', 'page_002.png', 'page_003.png']

        Note:
            The returned list represents virtual files - the PNG images are
            generated on-demand when read_file() is called.

        """
        try:
            doc = fitz.open(self.path)
            try:
                page_count = len(doc)
                # Generate page filenames with zero-padding (page_001.png, page_002.png, etc.)
                return [f"page_{i + 1:03d}.png" for i in range(page_count)]
            finally:
                doc.close()

        except fitz.FileDataError as e:
            self._handle_error("list", "", e)
            msg = f"Corrupt or invalid PDF file: {e}"
            raise ArchiverReadError(msg) from e
        except Exception as e:
            self._handle_error("list", "", e)
            msg = f"Cannot read PDF file: {e}"
            raise ArchiverReadError(msg) from e

    def test(self) -> bool:
        """Test whether the file is a valid PDF document.

        Returns:
            bool: True if the file is a valid PDF, False otherwise.

        Note:
            This method attempts to open the PDF with pymupdf to validate
            its structure, not just checking the file extension.

        """
        with suppress(Exception):
            doc = fitz.open(self._path)
            doc.close()
            return True
        return False

    def copy_from_archive(self, other_archive: Archiver) -> bool:
        """Attempt to copy files from another archive to the PDF.

        Args:
            other_archive: The source archive to copy files from.

        Returns:
            False: PDF files are read-only, so this operation always fails.

        Note:
            This method logs a warning and returns False immediately.
            No actual copy operation is attempted since PDFs are treated
            as read-only archives in this implementation.

        Warning:
            A warning will be logged indicating that the copy operation
            was attempted on a read-only PDF archive, including the path
            of the source archive.

        Examples:
            >>> pdf_archive = PdfArchiver(Path("target.pdf"))
            >>> zip_archive = ZipArchiver(Path("source.zip"))
            >>> success = pdf_archive.copy_from_archive(zip_archive)
            >>> print(f"Copy successful: {success}")  # Will print: Copy successful: False

        """
        logger.warning("Cannot copy to PDF archive from: %s", other_archive.path)
        return False
