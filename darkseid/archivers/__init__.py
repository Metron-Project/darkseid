from typing import ClassVar

from darkseid.archivers.archiver import Archiver
from darkseid.archivers.rar import RarArchiver
from darkseid.archivers.zip import ZipArchiver


class UnknownArchiver(Archiver):
    """
    Represents an unknown archiver.

    This class provides functionality for an unknown archiver type.
    """

    @staticmethod
    def name() -> str:
        """
        Returns the name of the archiver as "Unknown".

        Returns:
            str: The name of the archiver.
        """

        return "Unknown"

    __all__: ClassVar[list] = [Archiver, RarArchiver, "UnknownArchiver", ZipArchiver]
