"""Archive handling modules for different file formats."""

from darkseid.archivers.archiver import (
    Archiver,
    ArchiverError,
    ArchiverReadError,
    ArchiverWriteError,
)
from darkseid.archivers.factory import ArchiverFactory, UnknownArchiver
from darkseid.archivers.rar import RarArchiver
from darkseid.archivers.sevenzip import PY7ZR_AVAILABLE
from darkseid.archivers.tar import TarArchiver
from darkseid.archivers.zip import ZipArchiver

__all__ = [
    "Archiver",
    "ArchiverError",
    "ArchiverFactory",
    "ArchiverReadError",
    "ArchiverWriteError",
    "RarArchiver",
    "TarArchiver",
    "UnknownArchiver",
    "ZipArchiver",
]

# Optional dependencies - only export if py7zr installed
if PY7ZR_AVAILABLE:
    from darkseid.archivers.sevenzip import SevenZipArchiver

    __all__ += ["SevenZipArchiver"]
