"""Some generic utilities."""
# Copyright 2012-2014 Anthony Beville
# Copyright 2019 Brian Pepple

import re
from enum import Enum
from pathlib import Path


# TODO: Change to StrEnum when Python-3.10 support dropped
class DataSources(str, Enum):
    """Enumeration for various comic data sources.

    This class defines a set of constants representing different sources of comic data.
    Each constant is a string that corresponds to a specific data source name.

    Attributes:
        COMIC_VINE: Represents the Comic Vine data source.
        METRON: Represents the Metron data source.
        GCD: Represents the Grand Comics Database data source.
        KITSU: Represents the Kitsu data source.
        MANGADEX: Represents the MangaDex data source.
        MANGAUPDATES: Represents the MangaUpdates data source.
    """

    COMIC_VINE = "Comic Vine"
    METRON = "Metron"
    GCD = "Grand Comics Database"
    KITSU = "Kitsu"
    MANGADEX = "MangaDex"
    MANGAUPDATES = "MangaUpdates"


def get_issue_id_from_note(note_txt: str) -> dict[str, str] | None:
    """Extract the issue ID from a given note text based on specific keywords and formats.

    This function identifies the source of the issue ID and returns it along with the ID itself.

    Args:
        note_txt: The text from which to extract the issue ID.

    Returns:
        A dictionary containing the source and the issue ID if found, otherwise None.

    Examples:
        >>> get_issue_id_from_note("metrontagger issue_id:12345")
        {'source': 'Metron', 'id': '12345'}

        >>> get_issue_id_from_note("comictagger comic vine issue id 67890")
        {'source': 'Comic Vine', 'id': '67890'}
    """
    if not note_txt:
        return None

    note_lower = note_txt.lower()

    # Handle MetronTagger format
    if "metrontagger" in note_lower:
        if match := re.search(r"issue_id:(\d+)", note_lower):
            return {"source": DataSources.METRON.value, "id": match.group(1)}
    elif "comictagger" in note_lower:
        source_map = {
            "comic vine": DataSources.COMIC_VINE,
            "metron": DataSources.METRON,
            "grand comics database": DataSources.GCD,
            "mangadx": DataSources.MANGADEX,
            "mangaupdates": DataSources.MANGAUPDATES,
            "kitsu": DataSources.KITSU,
        }

        if match := re.search(r"issue id (\d+)|cvdb(\d+)", note_lower):
            issue_id = match.group(1) or match.group(2)
            for website, src_enum in source_map.items():
                if website in note_lower:
                    return {"source": src_enum.value, "id": issue_id}

    return None


def cast_id_as_str(id_: str | int) -> str:
    """Convert an ID to a string.

    This function takes an ID that can be either a string or an integer and returns it as a string.
    If the input is an integer, it will be converted to a string; if it is already a string,
    it will be returned unchanged.

    Args:
        id_: The ID to be converted.

    Returns:
        The ID represented as a string.

    Examples:
        >>> cast_id_as_str(123)
        '123'

        >>> cast_id_as_str("456")
        '456'
    """
    return str(id_)


def get_recursive_filelist(path_list: list[Path]) -> list[Path]:
    """Retrieve a list of comic files recursively from the provided paths.

    Args:
        path_list: List of paths to search for files.

    Returns:
        A sorted list of comic files found in the provided paths.

    Examples:
        >>> paths = [Path("/comics"), Path("/manga/series.cbz")]
        >>> files = get_recursive_filelist(paths)
        >>> len(files) > 0  # Returns True if comic files are found
        True
    """
    comic_extensions = ["*.cbz", "*.cbr"]
    filelist: list[Path] = []

    for path_item in path_list:
        path = Path(path_item)
        if path.is_dir():
            for extension in comic_extensions:
                filelist.extend(path.rglob(extension))
        elif path.exists():  # Only add existing files
            filelist.append(path)

    return sorted(filelist)


def list_to_string(list_of_strings: list[str]) -> str:
    """Convert a list of strings into a single comma-separated string.

    Strings containing commas are wrapped in double quotes to preserve structure.

    Args:
        list_of_strings: The list of strings to convert.

    Returns:
        The comma-separated string.

    Examples:
        >>> list_to_string(["apple", "banana", "cherry"])
        'apple, banana, cherry'

        >>> list_to_string(["item, with comma", "normal item"])
        '"item, with comma", normal item'
    """
    if not list_of_strings:
        return ""

    formatted_items = []
    for item in list_of_strings:
        if "," in item:
            formatted_items.append(f'"{item}"')
        else:
            formatted_items.append(item)

    return ", ".join(formatted_items)


def remove_articles(text: str) -> str:
    """Remove common articles and stop words from the input text.

    Args:
        text: The text from which articles are to be removed.

    Returns:
        The text with articles removed.

    Examples:
        >>> remove_articles("The Amazing Spider-Man")
        'Amazing Spider-Man'

        >>> remove_articles("A tale of two cities")
        'tale two cities'
    """
    if not text:
        return ""

    # Common articles and stop words
    articles = frozenset(
        {
            "&",
            "a",
            "am",
            "an",
            "and",
            "as",
            "at",
            "be",
            "but",
            "by",
            "for",
            "if",
            "is",
            "issue",
            "it",
            "it's",
            "its",
            "itself",
            "of",
            "or",
            "so",
            "the",
            "with",
        }
    )

    words = text.split()
    filtered_words = [word for word in words if word.casefold() not in articles]

    return " ".join(filtered_words)


def unique_file(file_name: Path) -> Path:
    """Generate a unique file name by appending a number in parentheses if the original exists.

    Args:
        file_name: The original file name to make unique.

    Returns:
        The unique file name.

    Examples:
        >>> original = Path("document.txt")
        >>> unique = unique_file(original)  # Returns "document (1).txt" if original exists
        >>> isinstance(unique, Path)
        True
    """
    if not file_name.exists():
        return file_name

    original_stem = file_name.stem
    counter = 1

    while True:
        new_name = file_name.parent / f"{original_stem} ({counter}){file_name.suffix}"
        if not new_name.exists():
            return new_name
        counter += 1


def xlate(data: int | str | None, is_int: bool = False) -> int | str | None:
    """Translate data to an integer or string based on the provided flag.

    This function handles data conversion with special handling for numeric extraction
    when converting to integers.

    Args:
        data: The data to translate.
        is_int: A flag indicating whether to translate to an integer.

    Returns:
        The translated data as int, str, or None.

    Examples:
        >>> xlate("123", is_int=True)
        123

        >>> xlate("abc123def", is_int=True)
        123

        >>> xlate("hello", is_int=False)
        'hello'

        >>> xlate(None)
        None
    """
    if data is None or data == "":
        return None

    if is_int:
        if numeric_chars := "".join(char for char in str(data) if char.isdigit()):
            # Handle special case of "0"
            return 0 if numeric_chars == "0" else int(numeric_chars)
        return None

    return str(data)
