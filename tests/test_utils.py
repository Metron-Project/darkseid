"""Comprehensive tests for darkseid utils module."""

from pathlib import Path
from tempfile import TemporaryDirectory

from darkseid.utils import (
    DataSources,
    get_issue_id_from_note,
    get_recursive_filelist,
    list_to_string,
    remove_articles,
    unique_file,
)


# DataSources enum tests
def test_data_sources_enum_values():
    """Test that DataSources enum has correct string values."""
    assert DataSources.COMIC_VINE == "Comic Vine"
    assert DataSources.METRON == "Metron"
    assert DataSources.GCD == "Grand Comics Database"
    assert DataSources.KITSU == "Kitsu"
    assert DataSources.MANGADEX == "MangaDex"
    assert DataSources.MANGAUPDATES == "MangaUpdates"


def test_data_sources_enum_is_string():
    """Test that DataSources enum values are strings."""
    for source in DataSources:
        assert isinstance(source.value, str)


# get_issue_id_from_note tests
def test_get_issue_id_from_note_empty_input():
    """Test with empty or None input."""
    assert get_issue_id_from_note("") is None
    assert get_issue_id_from_note(None) is None


def test_get_issue_id_from_note_metrontagger():
    """Test MetronTagger format extraction."""
    note = "metrontagger issue_id:12345"
    result = get_issue_id_from_note(note)
    assert result == {"source": "Metron", "id": "12345"}


def test_get_issue_id_from_note_metrontagger_case_insensitive():
    """Test MetronTagger format with different cases."""
    note = "METRONTAGGER Issue_ID:67890"
    result = get_issue_id_from_note(note)
    assert result == {"source": "Metron", "id": "67890"}


def test_get_issue_id_from_note_metrontagger_no_match():
    """Test MetronTagger format without valid issue_id."""
    note = "metrontagger something else"
    result = get_issue_id_from_note(note)
    assert result is None


def test_get_issue_id_from_note_comictagger_comic_vine():
    """Test ComicTagger format with Comic Vine."""
    note = "comictagger comic vine issue id 54321"
    result = get_issue_id_from_note(note)
    assert result == {"source": "Comic Vine", "id": "54321"}


def test_get_issue_id_from_note_comictagger_cvdb():
    """Test ComicTagger format with cvdb notation."""
    note = "ComicTagger Comic Vine [CVDB806681]"
    result = get_issue_id_from_note(note)
    assert result == {"source": "Comic Vine", "id": "806681"}


def test_get_issue_id_from_note_comictagger_metron():
    """Test ComicTagger format with Metron source."""
    note = "comictagger metron issue id 11111"
    result = get_issue_id_from_note(note)
    assert result == {"source": "Metron", "id": "11111"}


def test_get_issue_id_from_note_comictagger_gcd():
    """Test ComicTagger format with Grand Comics Database."""
    note = "comictagger grand comics database issue id 22222"
    result = get_issue_id_from_note(note)
    assert result == {"source": "Grand Comics Database", "id": "22222"}


def test_get_issue_id_from_note_comictagger_no_source():
    """Test ComicTagger format without recognized source."""
    note = "comictagger unknown source issue id 33333"
    result = get_issue_id_from_note(note)
    assert result is None


def test_get_issue_id_from_note_no_match():
    """Test with text that doesn't match any pattern."""
    note = "random text without ids"
    result = get_issue_id_from_note(note)
    assert result is None


# get_recursive_filelist tests
def test_get_recursive_filelist_empty_list():
    """Test with empty path list."""
    result = get_recursive_filelist([])
    assert result == []


def test_get_recursive_filelist_with_files():
    """Test with actual files in temporary directory."""
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create test files
        (temp_path / "comic1.cbz").touch()
        (temp_path / "comic2.cbr").touch()
        (temp_path / "not_comic.txt").touch()
        (temp_path / "comic4.cbt").touch()

        # Create subdirectory with more comics
        subdir = temp_path / "subdir"
        subdir.mkdir()
        (subdir / "comic3.cbz").touch()

        result = get_recursive_filelist([temp_path])

        # Should find 4 comic files, sorted
        assert len(result) == 4
        assert all(path.suffix in [".cbz", ".cbr", ".cbt"] for path in result)
        assert result == sorted(result)


def test_get_recursive_filelist_with_single_file():
    """Test with single file path."""
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        comic_file = temp_path / "single.cbz"
        comic_file.touch()

        result = get_recursive_filelist([comic_file])
        assert len(result) == 1
        assert result[0] == comic_file


def test_get_recursive_filelist_nonexistent_file():
    """Test with non-existent file path."""
    nonexistent = Path("/nonexistent/file.cbz")
    result = get_recursive_filelist([nonexistent])
    assert result == []


def test_get_recursive_filelist_mixed_paths():
    """Test with mix of directories and files."""
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create directory with comics
        (temp_path / "dir_comic.cbz").touch()

        # Create standalone file
        standalone = temp_path / "standalone.cbr"
        standalone.touch()

        result = get_recursive_filelist([temp_path, standalone])

        # Should find both comics, but standalone should appear twice
        # (once from directory scan, once from direct file)
        assert len(result) >= 2


# list_to_string tests
def test_list_to_string_empty_list():
    """Test with empty list."""
    assert list_to_string([]) == ""


def test_list_to_string_simple_items():
    """Test with simple string items."""
    items = ["apple", "banana", "cherry"]
    result = list_to_string(items)
    assert result == "apple, banana, cherry"


def test_list_to_string_items_with_commas():
    """Test with items containing commas."""
    items = ["apple", "banana, yellow", "cherry"]
    result = list_to_string(items)
    assert result == 'apple, "banana, yellow", cherry'


def test_list_to_string_all_items_with_commas():
    """Test with all items containing commas."""
    items = ["red, apple", "yellow, banana"]
    result = list_to_string(items)
    assert result == '"red, apple", "yellow, banana"'


def test_list_to_string_single_item():
    """Test with single item."""
    assert list_to_string(["single"]) == "single"
    assert list_to_string(["single, item"]) == '"single, item"'


# remove_articles tests
def test_remove_articles_empty_string():
    """Test with empty string."""
    assert remove_articles("") == ""


def test_remove_articles_basic():
    """Test removing common articles."""
    assert remove_articles("The Amazing Spider-Man") == "Amazing Spider-Man"
    assert remove_articles("A tale of two cities") == "tale two cities"


def test_remove_articles_multiple_articles():
    """Test removing multiple articles."""
    text = "The quick brown fox and the lazy dog"
    result = remove_articles(text)
    assert result == "quick brown fox lazy dog"


def test_remove_articles_case_insensitive():
    """Test case insensitive article removal."""
    assert remove_articles("THE amazing SPIDER-MAN") == "amazing SPIDER-MAN"
    assert remove_articles("An Issue Of Great Importance") == "Great Importance"


def test_remove_articles_no_articles():
    """Test with text containing no articles."""
    text = "Superman Batman Wonder Woman"
    assert remove_articles(text) == text


def test_remove_articles_only_articles():
    """Test with text containing only articles."""
    assert remove_articles("the and or but") == ""


def test_remove_articles_preserve_contractions():
    """Test that contractions are handled properly."""
    text = "It's a wonderful life"
    result = remove_articles(text)
    assert "wonderful" in result
    assert "life" in result


# unique_file tests
def test_unique_file_nonexistent():
    """Test with non-existent file."""
    with TemporaryDirectory() as temp_dir:
        file_path = Path(temp_dir) / "nonexistent.txt"
        result = unique_file(file_path)
        assert result == file_path


def test_unique_file_existing():
    """Test with existing file."""
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        original = temp_path / "existing.txt"
        original.touch()

        result = unique_file(original)
        expected = temp_path / "existing (1).txt"
        assert result == expected


def test_unique_file_multiple_existing():
    """Test with multiple existing files."""
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        original = temp_path / "existing.txt"
        original.touch()
        (temp_path / "existing (1).txt").touch()
        (temp_path / "existing (2).txt").touch()

        result = unique_file(original)
        expected = temp_path / "existing (3).txt"
        assert result == expected


def test_unique_file_preserves_extension():
    """Test that file extension is preserved."""
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        original = temp_path / "test.cbz"
        original.touch()

        result = unique_file(original)
        assert result.suffix == ".cbz"
        assert "test (1)" in result.stem


# Integration tests
def test_integration_comic_file_processing():
    """Integration test simulating comic file processing workflow."""
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create comic files
        comics = ["Amazing Spider-Man #1.cbz", "The X-Men Vol 2.cbr"]
        for comic in comics:
            (temp_path / comic).touch()

        # Get file list
        files = get_recursive_filelist([temp_path])
        assert len(files) == 2

        # Process file names (remove articles)
        processed_names = [remove_articles(f.stem) for f in files]
        assert any("Amazing Spider-Man" in name for name in processed_names)
        assert any("X-Men Vol 2" in name for name in processed_names)


def test_integration_note_processing():
    """Integration test for note processing workflow."""
    notes = [
        "metrontagger metron issue_id:12345",
        "comictagger comic vine issue id 67890",
        "comictagger comic vine cvdb54321",
    ]

    results = [get_issue_id_from_note(note) for note in notes]

    # Should extract 3 valid IDs
    valid_results = [r for r in results if r is not None]
    assert len(valid_results) == 3

    # Convert IDs to strings
    string_ids = [str(r["id"]) for r in valid_results]
    assert all(isinstance(id_str, str) for id_str in string_ids)


def test_integration_file_uniqueness():
    """Integration test for file uniqueness workflow."""
    with TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Create original file
        original = temp_path / "comic.cbz"
        original.touch()

        # Create unique versions
        unique1 = unique_file(original)
        unique1.touch()

        unique2 = unique_file(original)

        # All should be different
        assert original != unique1 != unique2
        assert all(f.suffix == ".cbz" for f in [original, unique1, unique2])


# Performance tests (basic)
def test_performance_large_file_list():
    """Test performance with large file list."""
    # Create a large list of paths
    large_path_list = [Path(f"/fake/path{i}.cbz") for i in range(1000)]

    # This should complete quickly even with many paths
    result = get_recursive_filelist(large_path_list)
    assert isinstance(result, list)
    # Files don't exist, so result should be empty
    assert len(result) == 0


def test_performance_long_string_processing():
    """Test performance with long strings."""
    long_text = " ".join(["the"] * 1000 + ["important", "content"])
    result = remove_articles(long_text)

    # Should remove all "the" articles but keep important content
    assert "important content" in result
    assert "the" not in result.split()


# Edge case tests
def test_edge_case_special_characters():
    """Test with special characters and unicode."""
    # Unicode in file names
    unicode_text = "Café München #1"
    processed = remove_articles(unicode_text)
    assert "Café München" in processed

    # Special characters in note extraction
    note_with_special = "metrontagger issue_id:123 (special-chars_here)"
    result = get_issue_id_from_note(note_with_special)
    assert result["id"] == "123"
