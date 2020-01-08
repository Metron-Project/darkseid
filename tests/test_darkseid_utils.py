import os
import tempfile
import unittest
from pathlib import Path

from darkseid import utils


class TestUtils(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.TemporaryDirectory()
        self.tmp_file_1 = tempfile.NamedTemporaryFile(
            suffix=".cbz", dir=self.tmp_dir.name
        )
        self.tmp_file_2 = tempfile.NamedTemporaryFile(
            suffix=".cbz", dir=self.tmp_dir.name
        )

    def tearDown(self):
        self.tmp_file_1.close()
        self.tmp_file_2.close()
        self.tmp_dir.cleanup()

    def test_remove_articles(self):
        txt = "The Champions & Inhumans"
        new_txt = utils.removearticles(txt)
        self.assertEqual(new_txt, "champions inhumans")

    def test_list_to_string(self):
        thislist = ["apple", "banana", "cherry"]
        expected_result = "apple; banana; cherry"

        list_string = utils.listToString(thislist)
        self.assertEqual(list_string, expected_result)

    def test_unique_name(self):
        new_file = self.tmp_file_1.name
        new_name = utils.unique_file(new_file)
        # Now let's create our expected result
        result_split = os.path.splitext(self.tmp_file_1.name)
        correct_result = result_split[0] + " (1)" + result_split[1]
        self.assertEqual(new_name, correct_result)

    def test_recursive_list_with_file(self):
        expected_result = []
        expected_result.append(Path(self.tmp_file_1.name))

        file_list = []
        file_list.append(self.tmp_file_1.name)
        result = utils.get_recursive_filelist(file_list)

        self.assertEqual(result, expected_result)

    def test_recursive_list_with_directory(self):
        expected_result = []
        expected_result.append(Path(self.tmp_file_2.name))
        expected_result.append(Path(self.tmp_file_1.name))
        expected_result = sorted(expected_result)

        file_list = []
        file_list.append(self.tmp_dir.name)
        result = utils.get_recursive_filelist(file_list)

        self.assertEqual(result, expected_result)


if __name__ == "__main__":
    unittest.main()
