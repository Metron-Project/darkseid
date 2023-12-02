from typing import ClassVar

from darkseid.archivers.archiver import Archiver
from darkseid.archivers.rar import RarArchiver
from darkseid.archivers.zip import ZipArchiver


class UnknownArchiver(Archiver):
    @staticmethod
    def name() -> str:
        return "Unknown"

    __all__: ClassVar[list] = [Archiver, RarArchiver, "UnknownArchiver", ZipArchiver]
