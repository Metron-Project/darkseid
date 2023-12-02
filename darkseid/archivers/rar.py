import io
from pathlib import Path

import rarfile

from darkseid.archivers import Archiver
from darkseid.exceptions import RarError


class RarArchiver(Archiver):
    """Rar implementation."""

    def __init__(self: "RarArchiver", path: Path) -> None:
        super().__init__(path)

    def read_file(self: "RarArchiver", archive_file: str) -> bytes:
        """Read the contents of a comic archive."""
        try:
            with rarfile.RarFile(self.path) as rf:
                data: bytes = rf.read(archive_file)
            return data
        except rarfile.RarCannotExec as e:
            raise RarError(e) from e
        except io.UnsupportedOperation:
            """If rar directory doesn't contain any data, return None."""
            return b""

    def remove_file(self: "RarArchiver", archive_file: str) -> bool:  # noqa: ARG002
        """Rar files are read-only, so we return False."""
        return False

    def remove_files(self: "RarArchiver", filename_lst: list[str]) -> bool:  # noqa: ARG002
        """Rar files are read-only, so we return False."""
        return False

    def write_file(self: "RarArchiver", archive_file: str, data: str) -> bool:  # noqa: ARG002
        """Rar files are read-only, so we return False."""
        return False

    def get_filename_list(self: "RarArchiver") -> list[str]:
        """Returns a list of the filenames in an archive."""
        try:
            with rarfile.RarFile(self.path) as rf:
                return sorted(rf.namelist())
        except rarfile.RarCannotExec as e:
            raise RarError(e) from e

    def copy_from_archive(
        self: "RarArchiver",
        other_archive: "Archiver",  # noqa: ARG002
    ) -> bool:
        """Rar files are read-only, so we return False."""
        return False
