"""A class to represent a single comic"""

# Copyright 2012-2014 Anthony Beville
# Copyright 2019 Brian Pepple

import io
import logging
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import List, Optional, cast

import py7zr
import rarfile
from natsort import natsorted, ns
from PIL import Image

from darkseid.comicinfo import ComicInfoXml
from darkseid.exceptions import RarError
from darkseid.filename import FileNameParser
from darkseid.metadata import ComicMetadata

logger = logging.getLogger(__name__)


class UnknownArchiver:

    """Unknown implementation"""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read_file(self, archive_file: str) -> bytes:
        raise NotImplementedError

    def write_file(self, archive_file: str, data: str) -> bool:
        return False

    def remove_file(self, archive_file: str) -> bool:
        return False

    def get_filename_list(self) -> List[str]:
        return []

    def copy_from_archive(self, other_archive: "UnknownArchiver") -> bool:
        return False


# ------------------------------------------------------------------
class RarArchiver(UnknownArchiver):
    """Rar implementation"""

    def __init__(self, path: Path) -> None:
        super().__init__(path)

    def read_file(self, archive_file: str) -> bytes:
        """Read the contents of a comic archive"""
        try:
            with rarfile.RarFile(self.path) as rf:
                data: bytes = rf.read(archive_file)
            return data
        except rarfile.RarCannotExec as e:
            raise RarError(e) from e
        except io.UnsupportedOperation:
            """If rar directory doesn't contain any data, return None."""
            return b""

    def remove_file(self) -> bool:
        """Rar files are read-only, so we return False."""
        return False

    def write_file(self) -> bool:
        """Rar files are read-only, so we return False."""
        return False

    def get_filename_list(self) -> List[str]:
        """Returns a list of the filenames in an archive"""
        try:
            fn_list = []
            with rarfile.RarFile(self.path) as rf:
                fn_list = sorted(rf.namelist())
            return fn_list
        except rarfile.RarCannotExec as e:
            raise RarError(e) from e

    def copy_from_archive(self) -> bool:
        """Rar files are read-only, so we return False."""
        return False


# ------------------------------------------------------------------


class ZipArchiver(UnknownArchiver):

    """ZIP implementation"""

    def __init__(self, path: Path) -> None:
        super().__init__(path)

    def read_file(self, archive_file: str) -> bytes:
        """Read the contents of a comic archive"""
        try:
            data = bytes()
            with zipfile.ZipFile(self.path, mode="r") as zf:
                data = zf.read(archive_file)
            return data
        except (zipfile.BadZipfile, OSError) as e:
            logger.error(f"Error reading zip archive [{e}]: {self.path} :: {archive_file}")
            raise OSError from e

    def remove_file(self, archive_file: str) -> bool:
        """Returns a boolean when attempting to remove a file from an archive"""
        return self._rebuild([archive_file])

    def write_file(self, archive_file: str, data: str) -> bool:
        #  At the moment, no other option but to rebuild the whole
        #  zip archive w/o the indicated file. Very sucky, but maybe
        # another solution can be found
        files = self.get_filename_list()
        if archive_file in files:
            self._rebuild([archive_file])

        try:
            # now just add the archive file as a new one
            with zipfile.ZipFile(
                self.path, mode="a", allowZip64=True, compression=zipfile.ZIP_DEFLATED
            ) as zf:
                zf.writestr(archive_file, data)
            return True
        except (zipfile.BadZipfile, OSError) as e:
            logger.error(f"Error writing zip archive [{e}]: {self.path} :: {archive_file}")
            return False

    def get_filename_list(self) -> List[str]:
        """Returns a list of the filenames in an archive"""
        try:
            with zipfile.ZipFile(self.path, mode="r") as zf:
                namelist = zf.namelist()
            return namelist
        except (zipfile.BadZipfile, OSError) as e:
            logger.error(f"Error listing files in zip archive [{e}]: {self.path}")
            return []

    def _rebuild(self, exclude_list: List[str]) -> bool:
        """
        Zip helper func

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
                self.path.unlink()
                shutil.move(cast(str, zout.filename), self.path)
            return True
        except (zipfile.BadZipfile, OSError) as e:
            logger.error(f"Error rebuilding zip file [{e}]: {self.path}")
            return False

    def copy_from_archive(self, other_archive: UnknownArchiver) -> bool:
        """Replace the current zip with one copied from another archive"""
        try:
            with zipfile.ZipFile(self.path, mode="w", allowZip64=True) as zout:
                for filename in other_archive.get_filename_list():
                    data = other_archive.read_file(filename)
                    if data is not None:
                        zout.writestr(filename, data)
            return True
        except Exception as e:
            # Remove any partial files created
            if self.path.exists():
                self.path.unlink()
            logger.warning(f"Error while copying to {self.path}: {e}")
            return False


# ------------------------------------------------------------------
class SevenZipArchiver(UnknownArchiver):

    """7Z implementation"""

    def __init__(self, path: Path) -> None:
        super().__init__(path)

    def read_file(self, archive_file: str) -> bytes:
        """Read the contents of a comic archive"""
        try:
            data = bytes()
            with py7zr.SevenZipFile(self.path, "r") as zf:
                data = zf.read(archive_file)[archive_file].read()
            return data
        except (py7zr.Bad7zFile, OSError) as e:
            logger.warning(f"bad 7zip file [{e}]: {self.path} :: {archive_file}")
            raise OSError from e

    def remove_file(self, archive_file: str) -> bool:
        """Returns a boolean when attempting to remove a file from an archive"""
        return self._rebuild([archive_file])

    def write_file(self, archive_file: str, data: str) -> bool:
        files = self.get_filename_list()
        if archive_file in files:
            self._rebuild([archive_file])

        try:
            # now just add the archive file as a new one
            with py7zr.SevenZipFile(self.path, "a") as zf:
                zf.writestr(data, archive_file)
            return True
        except (py7zr.Bad7zFile, OSError) as e:
            logger.error(f"Error writing 7zip archive [{e}]: {self.path} :: {archive_file}")
            return False

    def get_filename_list(self) -> List[str]:
        """Returns a list of the filenames in an archive"""
        try:
            with py7zr.SevenZipFile(self.path, "r") as zf:
                namelist = zf.getnames()
            return namelist
        except (py7zr.Bad7zFile, OSError) as e:
            logger.warning(f"Unable to get 7zip file list [{e}]: {self.path}")
            return []

    def _rebuild(self, exclude_list: List[str]) -> bool:
        """Zip helper func

        This recompresses the zip archive, without the files in the exclude_list
        """
        try:
            with py7zr.SevenZipFile(self.path, "r") as zip:
                targets = [f for f in zip.getnames() if f not in exclude_list]
            with tempfile.NamedTemporaryFile(dir=self.path.parent, delete=False) as tmp_file:
                with py7zr.SevenZipFile(tmp_file.file, mode="w") as zout:
                    with py7zr.SevenZipFile(self.path, mode="r") as zin:
                        for filename, buffer in zin.read(targets).items():
                            zout.writef(buffer, filename)
                self.path.unlink()
                shutil.move(tmp_file.name, self.path)
            return True
        except Exception as e:
            logger.warning("Exception[%s]: %s", e, self.path)
            return False

    def copy_from_archive(self, other_archive: UnknownArchiver) -> bool:
        """Replace the current zip with one copied from another archive"""
        try:
            with py7zr.SevenZipFile(self.path, "w") as zout:
                for fname in other_archive.get_filename_list():
                    if data := other_archive.read_file(fname):
                        zout.writestr(data, fname)
            return True
        except Exception as e:
            # Remove any partial files created
            if self.path.exists():
                self.path.unlink()
            logger.warning(f"Error while copying to {self.path}: {e}")
            return False


# ------------------------------------------------------------------


class Comic:

    """Comic implementation"""

    class ArchiveType:
        """Types of archives supported. Currently .cbr, .cbz, and .cb7"""

        zip, sevenzip, rar, unknown = list(range(4))

    def __init__(self, path: Path) -> None:
        self.path = path

        self.ci_xml_filename = "ComicInfo.xml"
        self.has_md: Optional[bool] = None
        self.page_count: Optional[int] = None
        self.page_list: Optional[List[str]] = None
        self.metadata: Optional[ComicMetadata] = None

        if self.zip_test():
            self.archive_type: int = self.ArchiveType.zip
            self.archiver = ZipArchiver(self.path)
        elif self.rar_test():
            self.archive_type: int = self.ArchiveType.rar
            self.archiver = RarArchiver(self.path)
        elif self.sevenzip_test():
            self.archive_type: int = self.ArchiveType.sevenzip
            self.archiver = SevenZipArchiver(self.path)
        else:
            self.archive_type = self.ArchiveType.unknown
            self.archiver = UnknownArchiver(self.path)

    def reset_cache(self) -> None:
        """Clears the cached data"""
        self.has_md = None
        self.page_count = None
        self.page_list = None
        self.metadata = None

    def rar_test(self) -> bool:
        """Test whether an archive is a rar file"""
        return rarfile.is_rarfile(self.path)

    def sevenzip_test(self) -> bool:
        """Tests whether an archive is a sevenzipfile"""
        return py7zr.is_7zfile(self.path)

    def zip_test(self) -> bool:
        """Tests whether an archive is a zipfile"""
        return zipfile.is_zipfile(self.path)

    def is_rar(self) -> bool:
        """Returns a boolean as to whether an archive is a rarfile."""
        return self.archive_type == self.ArchiveType.rar

    def is_sevenzip(self) -> bool:
        """Returns a boolean as to whether an archive is a sevenzipfile"""
        return self.archive_type == self.ArchiveType.sevenzip

    def is_zip(self) -> bool:
        """Returns a boolean as to whether an archive is a zipfile"""
        return self.archive_type == self.ArchiveType.zip

    def is_writable(self) -> bool:
        """Returns a boolean as to whether an archive is writable"""
        if self.archive_type in [self.ArchiveType.unknown, self.ArchiveType.rar]:
            return False

        return bool(os.access(self.path, os.W_OK))

    def seems_to_be_a_comic_archive(self) -> bool:
        """Returns a boolean as to whether the file is a comic archive"""
        return bool(
            (self.is_zip() or self.is_sevenzip() or self.is_rar())
            and (self.get_number_of_pages() > 0)
        )

    def get_page(self, index: int) -> Optional[bytes]:
        """Returns an image(page) from an archive"""
        image_data = None

        filename = self.get_page_name(index)

        if filename is not None:
            try:
                image_data = self.archiver.read_file(filename)
            except OSError:
                logger.exception(f"Error reading '{filename}' from '{self.path}'")

        return image_data

    def get_page_name(self, index: int) -> Optional[str]:
        """Returns the page name from an index"""
        if index is None:
            return None

        page_list = self.get_page_name_list()

        num_pages = len(page_list)
        return None if num_pages == 0 or index >= num_pages else page_list[index]

    def is_image(self, name_path: Path) -> bool:
        suffix_list = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        return name_path.suffix.casefold() in suffix_list and name_path.name[0] != "."

    def get_page_name_list(self, sort_list: bool = True) -> List[str]:
        """Returns a list of page names from an archive"""
        if self.page_list is None:
            # get the list file names in the archive, and sort
            files = self.archiver.get_filename_list()

            # seems like some archive creators are on  Windows, and don't know
            # about case-sensitivity!
            if sort_list:
                files = natsorted(files, alg=ns.IGNORECASE)

            # make a sub-list of image files
            self.page_list = []
            for name in files:
                name_str = str(name)
                if self.is_image(Path(name_str)):
                    self.page_list.append(name_str)

        return self.page_list

    def get_number_of_pages(self) -> int:
        """Returns the number of pages in an archive"""
        if self.page_count is None:
            self.page_count = len(self.get_page_name_list())
        return self.page_count

    def read_metadata(self) -> ComicMetadata:
        """Reads the metadata from an archive if present"""
        if self.metadata is None:
            raw_metadata = self.read_raw_metadata()
            if raw_metadata is None or raw_metadata == "":
                self.metadata = ComicMetadata()
            else:
                self.metadata = ComicInfoXml().metadata_from_string(raw_metadata)

            # validate the existing page list (make sure count is correct)
            if len(self.metadata.pages) not in [0, self.get_number_of_pages()]:
                # pages array doesn't match the actual number of images we're seeing
                # in the archive, so discard the data
                self.metadata.pages = []

            if len(self.metadata.pages) == 0:
                self.metadata.set_default_page_list(self.get_number_of_pages())

        return self.metadata

    def read_raw_metadata(self) -> Optional[str]:
        if not self.has_metadata():
            return None
        try:
            tmp_raw_metadata = self.archiver.read_file(self.ci_xml_filename)
            # Convert bytes to str. Is it safe to decode with utf-8?
            raw_metadata = tmp_raw_metadata.decode("utf-8")
        except OSError:
            logger.error("Error reading in raw CIX!")
            raw_metadata = None
        return raw_metadata

    def write_metadata(self, metadata: Optional[ComicMetadata]) -> bool:
        """Write the metadata to the archive"""
        if metadata is None or not self.is_writable():
            return False
        self.apply_archive_info_to_metadata(metadata, calc_page_sizes=True)
        if raw_cix := self.read_raw_metadata():
            md_string = ComicInfoXml().string_from_metadata(metadata, raw_cix.encode("utf-8"))
        else:
            md_string = ComicInfoXml().string_from_metadata(metadata)
        write_success = self.archiver.write_file(self.ci_xml_filename, md_string)
        return self._successful_write(write_success, True, metadata)

    def remove_metadata(self) -> bool:
        """Remove the metadata from the archive if present"""
        if self.has_metadata():
            write_success = self.archiver.remove_file(self.ci_xml_filename)
            return self._successful_write(write_success, False, None)
        return True

    def _successful_write(
        self, write_success: bool, has_md: bool, metadata: Optional[ComicMetadata]
    ) -> bool:
        if write_success:
            self.has_md = has_md
            self.metadata = metadata
        self.reset_cache()
        return write_success

    def has_metadata(self) -> bool:
        """Checks to see if the archive has metadata"""
        if self.has_md is None:
            self.has_md = bool(
                self.seems_to_be_a_comic_archive()
                and (
                    not self.seems_to_be_a_comic_archive()
                    or self.ci_xml_filename in self.archiver.get_filename_list()
                )
            )

        return self.has_md

    def apply_archive_info_to_metadata(
        self, metadata: ComicMetadata, calc_page_sizes: bool = False
    ) -> None:
        """Apply page information from the archive to the metadata"""
        metadata.page_count = str(self.get_number_of_pages())

        if calc_page_sizes:
            for page in metadata.pages:
                if (
                    "ImageSize" not in page
                    or "ImageHeight" not in page
                    or "ImageWidth" not in page
                ):
                    idx = int(page["Image"])
                    data = self.get_page(idx)
                    if data is not None:
                        try:
                            page_image = Image.open(io.BytesIO(data))
                            width, height = page_image.size

                            page["ImageSize"] = str(len(data))
                            page["ImageHeight"] = str(height)
                            page["ImageWidth"] = str(width)
                        except OSError:
                            page["ImageSize"] = str(len(data))

    def metadata_from_filename(self, parse_scan_info: bool = True) -> ComicMetadata:
        """Attempts to get the metadata from the filename"""
        metadata = ComicMetadata()

        fnp = FileNameParser()
        fnp.parse_filename(self.path)

        if fnp.issue != "":
            metadata.issue = fnp.issue
        if fnp.series != "":
            metadata.series = fnp.series
        if fnp.volume != "":
            metadata.volume = fnp.volume
        if fnp.year != "":
            metadata.year = fnp.year
        if fnp.issue_count != "":
            metadata.issue_count = fnp.issue_count
        if parse_scan_info and fnp.remainder != "":
            metadata.scan_info = fnp.remainder

        metadata.is_empty = False

        return metadata

    def export_as_cb7(self, new_7zip_filename: Path) -> bool:
        """Export CBZ or CBR archives to CB7 format."""
        if self.archive_type == self.ArchiveType.sevenzip:
            # nothing to do, we're already a 7zip
            return True

        zip_archiver = SevenZipArchiver(new_7zip_filename)

        return zip_archiver.copy_from_archive(self.archiver)

    def export_as_zip(self, zipfilename: Path) -> bool:
        """Export CBR or CB7 archives to CBZ format."""
        if self.archive_type == self.ArchiveType.zip:
            # nothing to do, we're already a zip
            return True

        zip_archiver = ZipArchiver(zipfilename)

        return zip_archiver.copy_from_archive(self.archiver)
