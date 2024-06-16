from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class Archiver:
    """Unknown implementation."""

    def __init__(self: Archiver, path: Path) -> None:
        self.path = path

    def read_file(self: Archiver, archive_file: str) -> bytes:
        raise NotImplementedError

    def write_file(
        self: Archiver,
        archive_file: str,  # noqa: ARG002
        data: str,  # noqa: ARG002
    ) -> bool:
        return False

    def remove_file(self: Archiver, archive_file: str) -> bool:  # noqa: ARG002
        return False

    def remove_files(
        self: Archiver,
        filename_lst: list[str],  # noqa: ARG002
    ) -> bool:
        return False

    def get_filename_list(self: Archiver) -> list[str]:
        return []

    def copy_from_archive(
        self: Archiver,
        other_archive: Archiver,  # noqa: ARG002
    ) -> bool:
        return False
