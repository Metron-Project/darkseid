"""Constants for comic archive and page image file extensions."""

from __future__ import annotations

from typing import Final

CB7 = ".cb7"
CBR = ".cbr"
CBT = ".cbt"
CBZ = ".cbz"
PDF = ".pdf"

# Lowercase file extensions treated as comic page images.
IMAGE_EXTENSIONS: Final[frozenset[str]] = frozenset(
    {".jpg", ".jpeg", ".png", ".gif", ".webp", ".jxl"}
)
