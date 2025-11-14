"""PDF document implementation.

This module provides an interface for working with PDF documents as archives.
PDF files are treated as archives where:
- Each page is rendered as a PNG image (page_001.png, page_002.png, etc.)
- Metadata files (ComicInfo.xml, MetronInfo.xml) can be embedded as attachments

The implementation uses pymupdf (fitz) for PDF processing.

Examples:
    >>> from pathlib import Path
    >>> archiver = PdfArchiver(Path("example.pdf"))
    >>> files = archiver.get_filename_list()
    >>> # Returns: ['page_001.png', 'page_002.png', ..., 'ComicInfo.xml']
    >>> page_data = archiver.read_file("page_001.png")
    >>> # Returns PNG image data for first page
    >>> metadata = archiver.read_file("ComicInfo.xml")
    >>> # Returns ComicInfo XML data
    >>> archiver.write_file("MetronInfo.xml", xml_data)
    >>> # Embeds MetronInfo XML as attachment

Note:
    Pages are read-only (virtual PNG files rendered from PDF pages).
    Only embedded files (like ComicInfo.xml, MetronInfo.xml) can be written/removed.
    copy_from_archive() is not supported for PDFs.

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
    """An archiver for PDF files with support for embedded metadata.

    This class provides an interface for reading pages from PDF documents
    and managing embedded metadata files. Each page is treated as a separate
    PNG image file within the archive, and metadata files (like ComicInfo.xml
    and MetronInfo.xml) can be embedded as PDF attachments.

    Pages are numbered sequentially with zero-padding (page_001.png, page_002.png, etc.).

    The implementation uses pymupdf (fitz) for PDF rendering and processing.

    Attributes:
        path (Path): The filesystem path to the PDF file.

    Note:
        - PDF pages are read-only virtual files rendered at 150 DPI
        - Metadata files can be embedded, read, and removed as PDF attachments
        - copy_from_archive() is not supported for PDFs

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
            True: PDF files support writing embedded files (metadata).

        Note:
            This method is used by the parent class to determine if write
            operations should be attempted. For PDF files, this returns True
            to allow embedding metadata files like ComicInfo.xml and MetronInfo.xml.
            Note that PDF pages themselves remain read-only virtual files.

        """
        return True

    def read_file(self, archive_file: str) -> bytes:  # noqa: PLR0915
        """Read a file from the PDF (page or embedded file).

        Args:
            archive_file: The filename within the archive. Can be:
                         - Page file: 'page_NNN.png' (zero-padded page number, starts at 001)
                         - Embedded file: e.g., 'ComicInfo.xml', 'MetronInfo.xml'

        Returns:
            File data as bytes:
                - For page files: PNG image data rendered at 150 DPI
                - For embedded files: Raw file content

        Raises:
            ArchiverReadError: If the file cannot be read due to:

                - Invalid page filename format
                - Page number out of range
                - File not found in archive
                - Corrupt or invalid PDF file
                - PDF processing errors
                - Other I/O errors

        Examples:
            >>> archiver = PdfArchiver(Path("document.pdf"))
            >>> # Read a page
            >>> image_data = archiver.read_file("page_001.png")
            >>> # Read embedded metadata
            >>> metadata = archiver.read_file("ComicInfo.xml")

        """
        # Check if this is a page file (virtual PNG) or an embedded file
        if archive_file.startswith("page_") and archive_file.endswith(".png"):
            # Handle page rendering
            try:
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
        else:
            # Handle embedded file reading
            try:
                doc = fitz.open(self.path)
                try:
                    # Check if the embedded file exists
                    if archive_file not in doc.embfile_names():
                        msg = f"Embedded file not found: {archive_file}"
                        raise ArchiverReadError(msg)

                    # Get the embedded file content
                    return doc.embfile_get(archive_file)
                finally:
                    doc.close()

            except fitz.FileDataError as e:
                self._handle_error("read", archive_file, e)
                msg = f"Corrupt or invalid PDF file: {e}"
                raise ArchiverReadError(msg) from e
            except Exception as e:
                self._handle_error("read", archive_file, e)
                msg = f"Failed to read embedded file from PDF: {e}"
                raise ArchiverReadError(msg) from e

    def write_file(self, archive_file: str, data: str | bytes) -> bool:
        """Write an embedded file to the PDF.

        Args:
            archive_file: The filename for the embedded file (e.g., 'ComicInfo.xml').
                         Cannot be a page file (page_NNN.png) as pages are read-only.
            data: The data to embed (string or bytes).

        Returns:
            True if the file was successfully embedded, False otherwise.

        Note:
            - Only embedded files can be written (not PDF pages)
            - If the embedded file already exists, it will be replaced
            - String data is automatically encoded as UTF-8
            - Commonly used for ComicInfo.xml and MetronInfo.xml metadata

        Warning:
            Attempting to write to a page file (page_NNN.png) will fail
            and log a warning, as pages are read-only virtual files.

        Examples:
            >>> archiver = PdfArchiver(Path("comic.pdf"))
            >>> xml_data = '<?xml version="1.0"?><ComicInfo>...</ComicInfo>'
            >>> success = archiver.write_file("ComicInfo.xml", xml_data)

        """
        # Prevent writing to page files (they are virtual/read-only)
        if archive_file.startswith("page_") and archive_file.endswith(".png"):
            logger.warning("Cannot write to virtual page file: %s", archive_file)
            return False

        # Convert string data to bytes if needed
        if isinstance(data, str):
            data = data.encode("utf-8")

        try:
            doc = fitz.open(self.path)
            try:
                # Remove existing embedded file if present
                if archive_file in doc.embfile_names():
                    doc.embfile_del(archive_file)

                # Add the new embedded file
                doc.embfile_add(archive_file, data)

                # Save the document (incremental save to preserve existing content)
                doc.save(doc.name, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
            finally:
                doc.close()

            return True  # noqa: TRY300

        except Exception as e:
            self._handle_error("write", archive_file, e)
            logger.warning("Failed to write embedded file to PDF: %s", e)
            return False

    def remove_files(self, filename_list: list[str]) -> bool:
        """Remove embedded files from the PDF.

        Args:
            filename_list: A list of filenames to remove. Only embedded files
                          can be removed (not page files like page_NNN.png).

        Returns:
            True if all existing embedded files were successfully removed,
                False if any error occurred. Returns True if the list is empty
                or contains only non-existent files.

        Note:
            - Only embedded files can be removed (page files are read-only)
            - Non-existent files are silently ignored
            - Page files (page_NNN.png) are skipped with a warning
            - All removals are performed in a single transaction

        Examples:
            >>> archiver = PdfArchiver(Path("comic.pdf"))
            >>> archiver.remove_files(["ComicInfo.xml", "MetronInfo.xml"])
            >>> # Removes both metadata files if they exist

        """
        if not filename_list:
            return True

        # Filter out page files (they can't be removed)
        embedded_files_to_remove = [
            f for f in filename_list if not (f.startswith("page_") and f.endswith(".png"))
        ]

        # Warn about any page files
        page_files = [f for f in filename_list if f.startswith("page_") and f.endswith(".png")]
        if page_files:
            logger.warning("Cannot remove virtual page files: %s", page_files)

        if not embedded_files_to_remove:
            return True

        try:
            doc = fitz.open(self.path)
            try:
                # Get list of existing embedded files
                existing_embedded = set(doc.embfile_names())

                # Only remove files that actually exist
                files_to_remove = [f for f in embedded_files_to_remove if f in existing_embedded]

                if not files_to_remove:
                    return True

                # Remove each embedded file
                for filename in files_to_remove:
                    doc.embfile_del(filename)

                # Save the document (incremental save to preserve existing content)
                doc.save(doc.name, incremental=True, encryption=fitz.PDF_ENCRYPT_KEEP)
            finally:
                doc.close()

            return True  # noqa: TRY300

        except Exception as e:
            self._handle_error("remove_multiple", str(embedded_files_to_remove), e)
            logger.warning("Failed to remove embedded files from PDF: %s", e)
            return False

    def get_filename_list(self) -> list[str]:
        """Get a list of all files in the PDF (pages and embedded files).

        Returns:
            A list of filenames including:
                - Virtual page files: 'page_NNN.png' (zero-padded, starting from 001)
                - Embedded files: e.g., 'ComicInfo.xml', 'MetronInfo.xml'

        Raises:
            ArchiverReadError: If the PDF cannot be read due to:

                - Corrupt or invalid PDF file
                - File system or permission errors
                - PDF processing errors

        Examples:
            >>> archiver = PdfArchiver(Path("document.pdf"))
            >>> files = archiver.get_filename_list()
            >>> print(files)
            >>> # Output: ['page_001.png', 'page_002.png', 'ComicInfo.xml']

        Note:
            - Page PNG files are virtual and generated on-demand when read
            - Embedded files are actual PDF attachments
            - The list is sorted with pages first, then embedded files alphabetically

        """
        try:
            doc = fitz.open(self.path)
            try:
                page_count = len(doc)
                # Generate page filenames with zero-padding (page_001.png, page_002.png, etc.)
                page_files = [f"page_{i + 1:03d}.png" for i in range(page_count)]

                # Get embedded file names
                embedded_files = sorted(doc.embfile_names())

                # Return pages first, then embedded files
                return page_files + embedded_files
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
            False: This operation is not supported for PDF archives.

        Note:
            This method logs a warning and returns False immediately.
            Copying entire archives to PDF is not supported because:
            - PDF pages cannot be replaced with image files
            - PDFs maintain their original page structure
            - Only embedded metadata files can be written individually

            To add metadata to a PDF, use write_file() instead:
                >>> pdf.write_file("ComicInfo.xml", xml_data)

        Warning:
            A warning will be logged indicating that the copy operation
            was attempted on a PDF archive.

        Examples:
            >>> pdf_archive = PdfArchiver(Path("target.pdf"))
            >>> zip_archive = ZipArchiver(Path("source.cbz"))
            >>> success = pdf_archive.copy_from_archive(zip_archive)
            >>> print(f"Copy successful: {success}")  # Will print: Copy successful: False

        """
        logger.warning("Cannot copy to PDF archive from: %s", other_archive.path)
        return False
