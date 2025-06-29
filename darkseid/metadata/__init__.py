"""Metadata modules for different XML formats."""

from darkseid.metadata.base_handler import BaseMetadataHandler, XmlError
from darkseid.metadata.comicinfo import ComicInfo
from darkseid.metadata.data_classes import (
    GTIN,
    AgeRatings,
    AlternativeNames,
    Arc,
    Basic,
    Credit,
    ImageMetadata,
    InfoSources,
    Links,
    Metadata,
    Notes,
    PageType,
    Price,
    Publisher,
    Role,
    Series,
    Universe,
)
from darkseid.metadata.metroninfo import MetronInfo

__all__ = [
    "GTIN",
    "AgeRatings",
    "AlternativeNames",
    "Arc",
    "BaseMetadataHandler",
    "Basic",
    "ComicInfo",
    "Credit",
    "ImageMetadata",
    "InfoSources",
    "Links",
    "Metadata",
    "MetronInfo",
    "Notes",
    "PageType",
    "Price",
    "Publisher",
    "Role",
    "Series",
    "Universe",
    "XmlError",
]
