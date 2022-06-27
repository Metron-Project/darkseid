"""
Exceptions module.

This module provides the following classes:

- RarError
"""


class RarError(Exception):
    """Class for a Rar error."""

    def __init__(self, *args, **kwargs):
        """Initialize an RarError."""
        Exception.__init__(self, *args, **kwargs)
