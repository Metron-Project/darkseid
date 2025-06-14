"""Exceptions module.

This module provides the following classes:

- ArchiverError
- ArchiverReadError
- ArchiverWriteError
- RarError
"""


class ArchiverError(Exception):
    """Base exception for archiver operations."""


class ArchiverReadError(ArchiverError):
    """Raised when reading from archive fails."""


class ArchiverWriteError(ArchiverError):
    """Raised when writing to archive fails."""


class XmlError(Exception):
    """Class for an XML error."""
