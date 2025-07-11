# Darkseid

[![PyPI - Version](https://img.shields.io/pypi/v/darkseid.svg)](https://pypi.org/project/darkseid/)
[![PyPI - Python](https://img.shields.io/pypi/pyversions/darkseid.svg)](https://pypi.org/project/darkseid/)
[![Ruff](https://img.shields.io/badge/Linter-Ruff-informational)](https://github.com/charliermarsh/ruff)
[![Pre-Commit](https://img.shields.io/badge/Pre--Commit-Enabled-informational?logo=pre-commit)](https://github.com/pre-commit/pre-commit)

A [Python](https://www.python.org/) library to interact with comic archives.

## Installation

```bash
pip install darkseid
```

## Example

```python
from pathlib import Path
from darkseid.comic import Comic, MetadataFormat

comic = Comic(Path("my_comic.cbz"))

# Check if it's a valid comic
if comic.is_valid_comic():
    print(f"Comic '{comic.name}' has {comic.get_number_of_pages()} pages")

# Read metadata
if comic.has_metadata(MetadataFormat.COMIC_INFO):
    metadata = comic.read_metadata(MetadataFormat.COMIC_INFO)
    print(f"Series: {metadata.series.name}")

# Get a page
page_data = comic.get_page(0)  # First page
if page_data:
    with open("cover.jpg", "wb") as f:
        f.write(page_data)
```

## Documentation

[Read the project documentation](https://darkseid.readthedocs.io/en/stable/?badge=latest)

## Bugs/Requests

Please use the
[GitHub issue tracker](https://github.com/Metron-Project/darkseid/issues) to
submit bugs or request features.
