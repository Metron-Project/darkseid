"""A class to represent a single comic"""

# Copyright 2012-2014 Anthony Beville
# Copyright 2019 Brian Pepple

import io
import logging
import os
import tempfile
import zipfile
from pathlib import Path
from typing import Any, List, Optional

import py7zr
from natsort import natsorted, ns
from PIL import Image

from .comicinfoxml import ComicInfoXml
from .filenameparser import FileNameParser
from .genericmetadata import GenericMetadata

logger = logging.getLogger(__name__)


class ZipArchiver:

    """ZIP implementation"""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read_archive_file(self, archive_file: str) -> bytes:
        """Read the contents of a comic archive"""

        data = ""
        zip_file = zipfile.ZipFile(self.path, "r")

        try:
            data = zip_file.read(archive_file)
        except zipfile.BadZipfile as bad_zip_error:
            logger.exception(f"bad zipfile [{bad_zip_error}]: {self.path} :: {archive_file}")
            zip_file.close()
            raise OSError from bad_zip_error
        except Exception as exception_error:
            logger.exception(f"bad zipfile [{exception_error}]: {self.path} :: {archive_file}")
            zip_file.close()
            raise OSError from exception_error
        finally:
            zip_file.close()
        return data

    def remove_archive_file(self, archive_file: str) -> bool:
        """Returns a boolean when attempting to remove a file from an archive"""

        try:
            self._rebuild_zipfile([archive_file])
        except zipfile.BadZipfile:
            return False
        else:
            return True

    def write_archive_file(self, archive_file: str, data: str) -> bool:
        #  At the moment, no other option but to rebuild the whole
        #  zip archive w/o the indicated file. Very sucky, but maybe
        # another solution can be found
        try:
            self._rebuild_zipfile([archive_file])

            # now just add the archive file as a new one
            zip_file = zipfile.ZipFile(
                self.path, mode="a", allowZip64=True, compression=zipfile.ZIP_DEFLATED
            )
            zip_file.writestr(archive_file, data)
            zip_file.close()
            return True
        except (zipfile.BadZipfile, zipfile.LargeZipFile) as exception_error:
            logger.exception(f"Error writing zipfile: {exception_error}.")
            return False

    def get_archive_filename_list(self) -> List[str]:
        """Returns a list of the filenames in an archive"""

        try:
            zip_file = zipfile.ZipFile(self.path, "r")
            namelist = zip_file.namelist()
            zip_file.close()
            return namelist
        except Exception as exception_error:
            logger.exception(f"Unable to get zipfile list [{exception_error}]: {self.path}")
            return []

    def _rebuild_zipfile(self, exclude_list: List[str]) -> None:
        """Zip helper func

        This recompresses the zip archive, without the files in the exclude_list
        """
        # generate temp file
        tmp_fd, tmp_name = tempfile.mkstemp(dir=self.path.parent)
        os.close(tmp_fd)

        zin = zipfile.ZipFile(self.path, "r")
        zout = zipfile.ZipFile(tmp_name, "w", allowZip64=True)
        for item in zin.infolist():
            buffer = zin.read(item.filename)
            if item.filename not in exclude_list:
                zout.writestr(item, buffer)

        zout.close()
        zin.close()

        # replace with the new file
        self.path.unlink()
        os.rename(tmp_name, self.path)


# ------------------------------------------------------------------
class SevenZipArchiver:

    """7Z implementation"""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read_archive_file(self, archive_file: str):
        """Read the contents of a comic archive"""
        data = ""
        try:
            with py7zr.SevenZipFile(self.path, "r") as zf:
                if r := zf.read([archive_file]):
                    data = r[archive_file].read()
                else:
                    logger.warning(f"No data in 7zipfile: {self.path} :: {archive_file}")
                    raise OSError
        except py7zr.Bad7zFile as e:
            logger.warning(f"bad 7zip file [{e}]: {self.path} :: {archive_file}")
            raise OSError from e
        except Exception as e:
            logger.warning(f"bad 7zip file [{e}]: {self.path} :: {archive_file}")
            raise OSError from e

        return data

    def remove_archive_file(self, archive_file: str) -> bool:
        """Returns a boolean when attempting to remove a file from an archive"""
        try:
            self._rebuild_seven_zipfile([archive_file])
        except py7zr.Bad7zFile:
            return False
        else:
            return True

    def write_archive_file(self, archive_file: str, data: str) -> bool:
        try:
            files = self.get_archive_filename_list()
            if archive_file in files:
                self._rebuild_seven_zipfile([archive_file])

            # now just add the archive file as a new one
            with py7zr.SevenZipFile(self.path, "a") as zf:
                zf.writestr(data, archive_file)
            return True
        except py7zr.Bad7zFile:
            return False

    def get_archive_filename_list(self) -> List[str]:
        """Returns a list of the filenames in an archive"""
        try:
            with py7zr.SevenZipFile(self.path, "r") as zf:
                namelist = zf.getnames()

            return namelist
        except Exception as e:
            logger.warning("Unable to get 7zip file list [%s]: %s", e, self.path)
            return []

    def _rebuild_seven_zipfile(self, exclude_list: List[str]) -> None:
        """Zip helper func

        This recompresses the zip archive, without the files in the exclude_list
        """
        tmp_fd, tmp_name = tempfile.mkstemp(dir=self.path.parent)
        os.close(tmp_fd)

        try:
            with py7zr.SevenZipFile(self.path, "r") as zip:
                targets = [f for f in zip.getnames() if f not in exclude_list]
            with py7zr.SevenZipFile(self.path, "r") as zin:
                with py7zr.SevenZipFile(tmp_name, "w") as zout:
                    if r := zin.read(targets):
                        for fname, bio in r.items():
                            zout.writef(bio, fname)
        except Exception as e:
            logger.warning("Exception[%s]: %s", e, self.path)
            return

        # replace with the new file
        self.path.unlink()
        os.rename(tmp_name, self.path)

    def copy_from_archive(self, other_archive) -> bool:
        """Replace the current zip with one copied from another archive"""
        try:
            with py7zr.SevenZipFile(self.path, "w") as zout:
                for fname in other_archive.get_archive_filename_list():
                    if data := other_archive.read_archive_file(fname):
                        zout.writestr(data, fname)
        except Exception as e:
            logger.warning("Error while copying to %s: %s", self.path, e)
            return False
        else:
            return True


# ------------------------------------------------------------------
class UnknownArchiver:

    """Unknown implementation"""

    def __init__(self, path: Path) -> None:
        self.path = path

    def read_archive_file(self, archive_file: str) -> Any:
        return Any

    def write_archive_file(self, archive_file: str, data: str) -> bool:
        return False

    def remove_archive_file(self, archive_file: str) -> bool:
        return False

    def get_archive_filename_list(self) -> List[str]:
        return []

    def copy_from_archive(self) -> bool:
        return False


# ------------------------------------------------------------------


class ComicArchive:

    """Comic Archive implementation"""

    class ArchiveType:
        """Types of archives supported. Currently only .cbz and .cb7"""

        zip, sevenzip, unknown = list(range(3))

    def __init__(self, path: Path) -> None:
        self.path = path

        self.ci_xml_filename = "ComicInfo.xml"
        self.has_md: Optional[bool] = None
        self.page_count: Optional[int] = None
        self.page_list: Optional[List[str]] = None
        self.metadata: Optional[GenericMetadata] = None

        if self.sevenzip_test():
            self.archive_type: int = self.ArchiveType.sevenzip
            self.archiver = SevenZipArchiver(self.path)
        elif self.zip_test():
            self.archive_type: int = self.ArchiveType.zip
            self.archiver = ZipArchiver(self.path)
        else:
            self.archive_type = self.ArchiveType.unknown
            self.archiver = UnknownArchiver(self.path)

    def reset_cache(self) -> None:
        """Clears the cached data"""
        self.has_md = None
        self.page_count = None
        self.page_list = None
        self.metadata = None

    def sevenzip_test(self) -> bool:
        """Tests whether an archive is a sevenzipfile"""
        return py7zr.is_7zfile(self.path)

    def zip_test(self) -> bool:
        """Tests whether an archive is a zipfile"""

        return zipfile.is_zipfile(self.path)

    def is_sevenzip(self) -> bool:
        """Returns a boolean as to whether an archive is a sevenzipfile"""
        return self.archive_type == self.ArchiveType.sevenzip

    def is_zip(self) -> bool:
        """Returns a boolean as to whether an archive is a zipfile"""

        return self.archive_type == self.ArchiveType.zip

    def is_writable(self) -> bool:
        """Returns a boolean as to whether an archive is writable"""

        if self.archive_type == self.ArchiveType.unknown:
            return False

        return bool(os.access(self.path, os.W_OK))

    def seems_to_be_a_comic_archive(self) -> bool:
        """Returns a boolean as to whether the file is a comic archive"""

        return bool((self.is_zip() or self.is_sevenzip()) and (self.get_number_of_pages() > 0))

    def get_page(self, index: int) -> Optional[bytes]:
        """Returns an image(page) from an archive"""

        image_data = None

        filename = self.get_page_name(index)

        if filename is not None:
            try:
                image_data = self.archiver.read_archive_file(filename)
            except OSError:
                logger.exception("Error reading in page.")

        return image_data

    def get_page_name(self, index: int) -> Optional[str]:
        """Returns the page name from an index"""

        if index is None:
            return None

        page_list = self.get_page_name_list()

        num_pages = len(page_list)
        if num_pages == 0 or index >= num_pages:
            return None

        return page_list[index]

    def is_image(self, name_path: Path) -> bool:
        suffix_list = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
        return name_path.suffix.lower() in suffix_list and name_path.name[0] != "."

    def get_page_name_list(self, sort_list: bool = True) -> List[str]:
        """Returns a list of page names from an archive"""

        if self.page_list is None:
            # get the list file names in the archive, and sort
            files = self.archiver.get_archive_filename_list()

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

    def read_metadata(self) -> GenericMetadata:
        """Reads the metadata from an archive if present"""

        if self.metadata is None:
            raw_metadata = self.read_raw_metadata()
            if raw_metadata is None or raw_metadata == "":
                self.metadata = GenericMetadata()
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
            tmp_raw_metadata = self.archiver.read_archive_file(self.ci_xml_filename)
            # Convert bytes to str. Is it safe to decode with utf-8?
            raw_metadata = tmp_raw_metadata.decode("utf-8")
        except OSError:
            print("Error reading in raw CIX!")
            raw_metadata = None
        return raw_metadata

    def write_metadata(self, metadata: Optional[GenericMetadata]) -> bool:
        """Write the metadata to the archive"""
        if metadata is None:
            return False
        self.apply_archive_info_to_metadata(metadata, calc_page_sizes=True)
        if raw_cix := self.read_raw_metadata():
            md_string = ComicInfoXml().string_from_metadata(metadata, raw_cix.encode("utf-8"))
        else:
            md_string = ComicInfoXml().string_from_metadata(metadata)
        write_success = self.archiver.write_archive_file(self.ci_xml_filename, md_string)
        return self._successful_write(write_success, True, metadata)

    def remove_metadata(self) -> bool:
        """Remove the metadata from the archive if present"""

        if self.has_metadata():
            write_success = self.archiver.remove_archive_file(self.ci_xml_filename)
            return self._successful_write(write_success, False, None)
        return True

    def _successful_write(
        self, write_success: bool, has_md: bool, metadata: Optional[GenericMetadata]
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
                    or self.ci_xml_filename in self.archiver.get_archive_filename_list()
                )
            )

        return self.has_md

    def apply_archive_info_to_metadata(
        self, metadata: GenericMetadata, calc_page_sizes: bool = False
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

    def metadata_from_filename(self, parse_scan_info: bool = True) -> GenericMetadata:
        """Attempts to get the metadata from the filename"""

        metadata = GenericMetadata()

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
        """Export CBZ archive to CB7 format."""
        if self.archive_type == self.ArchiveType.zip:
            zip_archiver = SevenZipArchiver(new_7zip_filename)
        else:
            return False

        return zip_archiver.copy_from_archive(self.archiver)
