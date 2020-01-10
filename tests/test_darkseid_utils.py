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
        new_txt = utils.remove_articles(txt)
        self.assertEqual(new_txt, "champions inhumans")

    def test_list_to_string(self):
        thislist = ["apple", "banana", "cherry"]
        expected_result = "apple; banana; cherry"

        list_string = utils.list_to_string(thislist)
        self.assertEqual(list_string, expected_result)

    def test_unique_name(self):
        new_file = self.tmp_file_1.name
        new_name = utils.unique_file(new_file)
        # Now let's create our expected result
        path = Path(self.tmp_file_1.name)
        result = Path(path.parent).joinpath(f"{path.stem} (1){path.suffix}")

        self.assertEqual(new_name, result)

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
