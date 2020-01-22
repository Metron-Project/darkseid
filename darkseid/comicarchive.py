"""A class to represent a single comic"""

# Copyright 2012-2014 Anthony Beville
# Copyright 2019 Brian Pepple

import io
import os
import sys
import tempfile
import zipfile

from natsort import natsorted
from PIL import Image

from .comicinfoxml import ComicInfoXml
from .filenameparser import FileNameParser
from .genericmetadata import GenericMetadata

sys.path.insert(0, os.path.abspath("."))


class ZipArchiver:

    """ZIP implementation"""

    def __init__(self, path):
        self.path = path

    def read_archive_file(self, archive_file):
        """Read the contents of a comic archive"""

        data = ""
        zip_file = zipfile.ZipFile(self.path, "r")

        try:
            data = zip_file.read(archive_file)
        except zipfile.BadZipfile as bad_zip_error:
            print(
                f"bad zipfile [{bad_zip_error}]: {self.path} :: {archive_file}",
                file=sys.stderr,
            )
            zip_file.close()
            raise IOError
        except Exception as exception_error:
            zip_file.close()
            print(
                f"bad zipfile [{exception_error}]: {self.path} :: {archive_file}",
                file=sys.stderr,
            )
            raise IOError
        finally:
            zip_file.close()
        return data

    def remove_archive_file(self, archive_file):
        """Returns a boolean when attempting to remove a file from an archive"""

        try:
            self.rebuild_zipfile([archive_file])
        except zipfile.BadZipfile:
            return False
        else:
            return True

    def write_archive_file(self, archive_file, data):
        #  At the moment, no other option but to rebuild the whole
        #  zip archive w/o the indicated file. Very sucky, but maybe
        # another solution can be found
        try:
            self.rebuild_zipfile([archive_file])

            # now just add the archive file as a new one
            zip_file = zipfile.ZipFile(
                self.path, mode="a", allowZip64=True, compression=zipfile.ZIP_DEFLATED
            )
            zip_file.writestr(archive_file, data)
            zip_file.close()
            return True
        except (zipfile.BadZipfile, zipfile.LargeZipFile) as exception_error:
            print(f"Error writing zipfile: {exception_error}.")
            return False

    def get_archive_filename_list(self):
        """Returns a list of the filenames in an archive"""

        try:
            zip_file = zipfile.ZipFile(self.path, "r")
            namelist = zip_file.namelist()
            zip_file.close()
            return namelist
        except Exception as exception_error:
            print(
                f"Unable to get zipfile list [{exception_error}]: {self.path}",
                file=sys.stderr,
            )
            return []

    def rebuild_zipfile(self, exclude_list):
        """Zip helper func

        This recompresses the zip archive, without the files in the exclude_list
        """

        # print ">> sys.stderr, Rebuilding zip {0} without {1}".format(
        #                                            self.path, exclude_list )

        # generate temp file
        tmp_fd, tmp_name = tempfile.mkstemp(dir=os.path.dirname(self.path))
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
        os.remove(self.path)
        os.rename(tmp_name, self.path)


# ------------------------------------------


class UnknownArchiver:

    """Unknown implementation"""

    def __init__(self, path):
        self.path = path

    @classmethod
    def read_archive_file(cls):
        return ""

    @classmethod
    def write_archive_file(cls, archive_file, data):
        return False

    @classmethod
    def remove_archive_file(cls, archive_file):
        return False

    @classmethod
    def get_archive_filename_list(cls):
        return []


# ------------------------------------------------------------------


class ComicArchive:

    """Comic Archive implementation"""

    class ArchiveType:
        """Types of archives supported. Currently only .cbz"""

        Zip, Unknown = list(range(2))

    def __init__(self, path):
        self.path = path

        self.ci_xml_filename = "ComicInfo.xml"
        self.has_md = None
        self.page_count = None
        self.page_list = None
        self.metadata = None

        self.archive_type = self.ArchiveType.Unknown
        self.archiver = UnknownArchiver(self.path)

        if self.zip_test():
            self.archive_type = self.ArchiveType.Zip
            self.archiver = ZipArchiver(self.path)

    def reset_cache(self):
        """Clears the cached data"""
        self.has_md = None
        self.page_count = None
        self.page_list = None
        self.metadata = None

    def zip_test(self):
        """Tests whether an archive is a zipfile"""

        return zipfile.is_zipfile(self.path)

    def is_zip(self):
        """Returns a boolean as to whether an archive is a zipfile"""

        return self.archive_type == self.ArchiveType.Zip

    def is_writable(self):
        """Returns a boolean as to whether an archive is writable"""

        if self.archive_type == self.ArchiveType.Unknown:
            return False

        if not os.access(self.path, os.W_OK):
            return False

        return True

    def seems_to_be_a_comic_archive(self):
        """Returns a boolean as to whether the file is a comic archive"""

        if (self.is_zip()) and (self.get_number_of_pages() > 0):
            return True
        else:
            return False

    def get_page(self, index):
        """Returns an image(page) from an archive"""

        image_data = None

        filename = self.get_page_name(index)

        if filename is not None:
            try:
                image_data = self.archiver.read_archive_file(filename)
            except IOError:
                print("Error reading in page.", file=sys.stderr)

        return image_data

    def get_page_name(self, index):
        """Returns the page name from an index"""

        if index is None:
            return None

        page_list = self.get_page_name_list()

        num_pages = len(page_list)
        if num_pages == 0 or index >= num_pages:
            return None

        return page_list[index]

    def get_page_name_list(self, sort_list=True):
        """Returns a list of page names from an archive"""

        if self.page_list is None:
            # get the list file names in the archive, and sort
            files = self.archiver.get_archive_filename_list()

            # seems like some archive creators are on  Windows, and don't know
            # about case-sensitivity!
            if sort_list:

                def keyfunc(k):
                    # hack to account for some weird scanner ID pages
                    # basename=os.path.split(k)[1]
                    # if basename < '0':
                    #    k = os.path.join(os.path.split(k)[0], "z" + basename)
                    return k.lower()

                files = natsorted(files, key=keyfunc)

            # make a sub-list of image files
            self.page_list = []
            for name in files:
                if (
                    name[-4:].lower() in [".jpg", "jpeg", ".png", ".gif", "webp"]
                    and os.path.basename(name)[0] != "."
                ):
                    self.page_list.append(name)

        return self.page_list

    def get_number_of_pages(self):
        """Returns the number of pages in an archive"""

        if self.page_count is None:
            self.page_count = len(self.get_page_name_list())
        return self.page_count

    def read_metadata(self):
        """Reads the metadata from an archive if present"""

        if self.metadata is None:
            raw_metadata = self.read_raw_metadata()
            if raw_metadata is None or raw_metadata == "":
                self.metadata = GenericMetadata()
            else:
                self.metadata = ComicInfoXml().metadata_from_string(raw_metadata)

            # validate the existing page list (make sure count is correct)
            if len(self.metadata.pages) != 0:
                if len(self.metadata.pages) != self.get_number_of_pages():
                    # pages array doesn't match the actual number of images we're seeing
                    # in the archive, so discard the data
                    self.metadata.pages = []

            if len(self.metadata.pages) == 0:
                self.metadata.set_default_page_list(self.get_number_of_pages())

        return self.metadata

    def read_raw_metadata(self):
        if not self.has_metadata():
            return None
        try:
            raw_metadata = self.archiver.read_archive_file(self.ci_xml_filename)
        except IOError:
            print("Error reading in raw CIX!")
            raw_metadata = ""
        return raw_metadata

    def write_metadata(self, metadata):
        """Write the metadata to the archive"""

        if metadata is not None:
            self.apply_archive_info_to_metadata(metadata, calc_page_sizes=True)
            md_string = ComicInfoXml().string_from_metadata(metadata)
            write_success = self.archiver.write_archive_file(
                self.ci_xml_filename, md_string
            )
            if write_success:
                self.has_md = True
                self.metadata = metadata
            self.reset_cache()
            return write_success
        else:
            return False

    def remove_metadata(self):
        """Remove the metadata from the archive if present"""

        if self.has_metadata():
            write_success = self.archiver.remove_archive_file(self.ci_xml_filename)
            if write_success:
                self.has_md = False
                self.metadata = None
            self.reset_cache()
            return write_success
        return True

    def has_metadata(self):
        """Checks to see if the archive has metadata"""

        if self.has_md is None:

            if not self.seems_to_be_a_comic_archive():
                self.has_md = False
            elif self.ci_xml_filename in self.archiver.get_archive_filename_list():
                self.has_md = True
            else:
                self.has_md = False
        return self.has_md

    def apply_archive_info_to_metadata(self, metadata, calc_page_sizes=False):
        """Apply page information from the archive to the metadata"""

        metadata.page_count = self.get_number_of_pages()

        if calc_page_sizes:
            for page in metadata.pages:
                idx = int(page["Image"])
                if (
                    "ImageSize" not in page
                    or "ImageHeight" not in page
                    or "ImageWidth" not in page
                ):
                    data = self.get_page(idx)
                    if data is not None:
                        try:
                            page_image = Image.open(io.BytesIO(data))
                            width, height = page_image.size

                            page["ImageSize"] = str(len(data))
                            page["ImageHeight"] = str(height)
                            page["ImageWidth"] = str(width)
                        except IOError:
                            page["ImageSize"] = str(len(data))

                else:
                    if "ImageSize" not in page:
                        data = self.get_page(idx)
                        page["ImageSize"] = str(len(data))

    def metadata_from_filename(self, parse_scan_info=True):
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
            metadata.issueCount = fnp.issue_count
        if parse_scan_info:
            if fnp.remainder != "":
                metadata.scanInfo = fnp.remainder

        metadata.isEmpty = False

        return metadata
