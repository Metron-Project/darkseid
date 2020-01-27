""" Tests for comic archive files """
import tempfile
from pathlib import Path
from shutil import make_archive
from unittest import TestCase, main

from darkseid.comicarchive import ComicArchive
from darkseid.genericmetadata import GenericMetadata


class TestComicArchive(TestCase):
    """ Collection of test of the comic archive library """

    def setUp(self):
        self.tmp_archive_dir = tempfile.TemporaryDirectory()
        self.tmp_image_dir = tempfile.TemporaryDirectory()
        # Create 3 fake jpgs
        img_1 = tempfile.NamedTemporaryFile(
            suffix=".jpg", dir=self.tmp_image_dir.name, mode="wb"
        )
        img_1.write(b"test data")
        img_2 = tempfile.NamedTemporaryFile(
            suffix=".jpg", dir=self.tmp_image_dir.name, mode="wb"
        )
        img_2.write(b"more data")
        img_3 = tempfile.NamedTemporaryFile(
            suffix=".jpg", dir=self.tmp_image_dir.name, mode="wb"
        )
        img_3.write(b"yet more data")

        zip_file = (
            Path(self.tmp_archive_dir.name) / "Aquaman v1 #001 (of 08) (1994)"
        )

        # Create zipfile
        open(make_archive(zip_file, "zip", self.tmp_image_dir.name), "rb").read()

        # Append .zip to pathlib
        new_path = zip_file.parent / (zip_file.stem + ".zip")
        self.comic_archive = ComicArchive(new_path)

        # Setup test metadata
        self.meta_data = GenericMetadata()
        self.meta_data.series = "Aquaman"
        self.meta_data.issue = "0"
        self.meta_data.title = "A Crash of Symbols"
        self.meta_data.notes = "Test comment"
        self.meta_data.volume = "1"

    def tearDown(self):
        self.tmp_archive_dir.cleanup()
        self.tmp_image_dir.cleanup()

    def test_zip_file_exists(self):
        """ Test function that determines if a file is a zip file """
        res = self.comic_archive.is_zip()
        self.assertTrue(res)

    def test_whether_text_file_is_comic_archive(self):
        """
        Test that a text file produces a false result
        when determining whether it's a comic archive
        """
        test_file = tempfile.NamedTemporaryFile(suffix=".txt", mode="wb")
        test_file.write(b"Blah Blah Blah")

        comic_archive = ComicArchive(test_file)
        res = comic_archive.seems_to_be_a_comic_archive()
        # Clean up tmp file
        test_file.close()
        self.assertFalse(res)

    def test_archive_number_of_pages(self):
        """ Test to determine number of pages in a comic archive """
        res = self.comic_archive.get_number_of_pages()
        self.assertEqual(res, 3)

    def test_archive_is_writable(self):
        """ Test to determine if a comic archive is writable """
        res = self.comic_archive.is_writable()
        self.assertTrue(res)

    def test_archive_test_metadata(self):
        """ Test to determine if a comic archive has metadata """
        # verify archive has no metadata
        res = self.comic_archive.has_metadata()
        self.assertFalse(res)

        # now let's test that we can write some
        write_result = self.comic_archive.write_metadata(self.meta_data)
        self.assertTrue(write_result)
        has_md = self.comic_archive.has_metadata()

        self.assertTrue(has_md)
        self.assertFalse(res)

        # Verify what was written
        new_md = self.comic_archive.read_metadata()
        self.assertEqual(new_md.series, self.meta_data.series)
        self.assertEqual(new_md.issue, self.meta_data.issue)
        self.assertEqual(new_md.title, self.meta_data.title)
        self.assertEqual(new_md.notes, self.meta_data.notes)
        self.assertEqual(new_md.volume, self.meta_data.volume)

        # now remove what was just written
        self.comic_archive.remove_metadata()
        remove_md = self.comic_archive.has_metadata()
        self.assertFalse(remove_md)

    def test_archive_writing_with_no_metadata(self):
        """Make sure writing no metadata to comic returns False"""
        res = self.comic_archive.write_metadata(None)
        self.assertFalse(res)

    def test_removing_metadata_on_comic_wo_metadata(self):
        """
        Make sure trying to remove metadata from
        comic w/o any returns True
        """
        res = self.comic_archive.write_metadata(None)
        remove_result = self.comic_archive.remove_metadata()
        self.assertFalse(res)
        self.assertTrue(remove_result)

    def test_archive_get_page(self):
        """ Test to set if a page from a comic archive can be retrieved """
        # Get page 2
        img = self.comic_archive.get_page(1)
        self.assertIsNotNone(img)

    def test_archive_metadata_from_filename(self):
        """ Test to get metadata from comic archives filename """
        test_md = self.comic_archive.metadata_from_filename()
        self.assertEqual(test_md.series, "Aquaman")
        self.assertEqual(test_md.issue, "1")
        self.assertEqual(test_md.volume, "1")
        self.assertEqual(test_md.year, "1994")

    def test_archive_apply_file_info_to_metadata(self):
        """ Test to apply archive info to the generic metadata """
        test_md = GenericMetadata()
        self.comic_archive.apply_archive_info_to_metadata(test_md)
        # TODO: Need to test calculate page sizes
        self.assertEqual(test_md.page_count, 3)


if __name__ == "__main__":
    main()
