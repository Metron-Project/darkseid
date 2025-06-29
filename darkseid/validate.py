"""Class to validate a comic archive ComicInfo.xml."""

from __future__ import annotations

__all__ = ["SchemaVersion", "ValidateMetadata", "ValidationError"]

import logging
from contextlib import contextmanager
from enum import Enum, auto, unique
from importlib.resources import as_file, files
from io import BytesIO
from typing import TYPE_CHECKING, ClassVar

from xmlschema import XMLSchema10, XMLSchema11, XMLSchemaValidationError

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path

    from xmlschema import XMLSchemaBase

logger = logging.getLogger(__name__)


class ValidationError(Exception):
    """Exception raised for errors encountered during XML metadata validation.

    This exception is used to signal validation failures, optionally including the schema version involved.
    """

    def __init__(self, message: str, schema_version: SchemaVersion | None = None) -> None:
        """Initialize ValidationError with a message and optional schema version.

        Args:
            message: The error message describing the validation failure.
            schema_version: The schema version related to the validation error, if applicable.

        """
        super().__init__(message)
        self.schema_version = schema_version


@unique
class SchemaVersion(Enum):
    """Enum representing supported schema versions for comic metadata.

    This enumeration defines the possible schema versions that can be detected
    or validated for comic archive metadata, ordered from newest to oldest
    for validation priority.
    """

    METRON_INFO_V1 = auto()
    COMIC_INFO_V2 = auto()
    COMIC_INFO_V1 = auto()
    UNKNOWN = auto()

    def __str__(self) -> str:
        """Return a human-readable string representation."""
        return self.name.replace("_", " ").title()


class ValidateMetadata:
    """Validates XML metadata against comic archive schemas.

    This class provides functionality to validate XML data against various
    comic metadata schemas and determine the appropriate schema version.
    """

    # Class-level schema configuration for better maintainability
    _SCHEMA_CONFIG: ClassVar[
        dict[SchemaVersion, dict[str, str | type[XMLSchema10]] | dict[str, str | type[XMLSchema11]]]
    ] = {
        SchemaVersion.COMIC_INFO_V1: {
            "module_path": "darkseid.schemas.ComicInfo.v1",
            "file_name": "ComicInfo.xsd",
            "schema_class": XMLSchema10,
        },
        SchemaVersion.COMIC_INFO_V2: {
            "module_path": "darkseid.schemas.ComicInfo.v2",
            "file_name": "ComicInfo.xsd",
            "schema_class": XMLSchema10,
        },
        SchemaVersion.METRON_INFO_V1: {
            "module_path": "darkseid.schemas.MetronInfo.v1",
            "file_name": "MetronInfo.xsd",
            "schema_class": XMLSchema11,
        },
    }

    # Validation order: newest/most specific schemas first
    _VALIDATION_ORDER: ClassVar[list[SchemaVersion]] = [
        SchemaVersion.METRON_INFO_V1,
        SchemaVersion.COMIC_INFO_V2,
        SchemaVersion.COMIC_INFO_V1,
    ]

    def __init__(self, xml: bytes) -> None:
        """Initialize the ValidateMetadata instance with XML data.

        Args:
            xml: The XML data as bytes to be validated.

        Raises:
            ValidationError: If the XML data is empty or None.

        """
        if not xml:
            msg = "XML data cannot be empty or None"
            raise ValidationError(msg)

        self.xml = xml
        self._schema_cache: dict[SchemaVersion, XMLSchemaBase] = {}

    @classmethod
    def _get_schema_path(cls, schema_version: SchemaVersion) -> Path | None:
        """Get the path of the schema file for the given schema version.

        Args:
            schema_version: The version of the schema to retrieve.

        Returns:
            The path of the schema file or None if the schema version is unknown.

        """
        if schema_version == SchemaVersion.UNKNOWN:
            logger.warning("Cannot get schema path for unknown schema version")
            return None

        config = cls._SCHEMA_CONFIG.get(schema_version)
        if not config:
            logger.error(f"No configuration found for schema version: {schema_version}")
            return None

        try:
            module_path = config["module_path"]
            file_name = config["file_name"]

            with as_file(files(module_path).joinpath(file_name)) as schema_path:
                return schema_path

        except (ImportError, FileNotFoundError):
            logger.exception(f"Schema file not found for {schema_version}")
            return None

    @contextmanager
    def _get_schema(self, schema_version: SchemaVersion) -> Iterator[XMLSchemaBase | None]:
        """Context manager to get and cache schema instances.

        Args:
            schema_version: The schema version to retrieve.

        Yields:
            The schema instance or None if unavailable.

        """
        if schema_version in self._schema_cache:
            yield self._schema_cache[schema_version]
            return

        if schema_version == SchemaVersion.UNKNOWN:
            yield None
            return

        config = self._SCHEMA_CONFIG.get(schema_version)
        if not config:
            yield None
            return

        schema_path = self._get_schema_path(schema_version)
        if schema_path is None:
            yield None
            return

        try:
            schema_class = config["schema_class"]
            schema = schema_class(schema_path)
            self._schema_cache[schema_version] = schema
            yield schema
        except Exception:
            logger.exception(f"Failed to load schema {schema_version}")
            yield None

    def _is_valid(self, schema_version: SchemaVersion) -> bool:
        """Validate the XML against a specific schema version.

        Args:
            schema_version: The version of the schema to validate against.

        Returns:
            True if the XML is valid according to the schema, False otherwise.

        """
        with self._get_schema(schema_version) as schema:
            if schema is None:
                logger.debug(f"Schema not available for validation: {schema_version}")
                return False

            try:
                schema.validate(BytesIO(self.xml))
                logger.debug(f"XML validated successfully against {schema_version}")
            except XMLSchemaValidationError as e:
                logger.debug(f"XML validation failed for {schema_version}: {e}")
                return False
            except Exception:
                logger.exception(f"Unexpected error during validation for {schema_version}")
                return False
            else:
                return True

    def validate(self) -> SchemaVersion:
        """Determine and return the highest valid schema version for the XML metadata.

        This method checks the XML against all supported schema versions in order
        of preference (newest first) and returns the first valid match.

        Returns:
            The highest valid schema version found, or SchemaVersion.UNKNOWN
            if no valid schema is found.

        """
        logger.info("Starting XML validation process")

        for schema_version in self._VALIDATION_ORDER:
            logger.debug(f"Attempting validation with {schema_version}")

            if self._is_valid(schema_version):
                logger.info(f"XML successfully validated as {schema_version}")
                return schema_version

        logger.warning("XML did not validate against any known schema")
        return SchemaVersion.UNKNOWN

    def validate_all(self) -> dict[SchemaVersion, bool]:
        """Validate the XML against all available schema versions.

        This method is useful for debugging or when you need to know
        which schemas the XML is compatible with.

        Returns:
            A dictionary mapping each schema version to its validation result.

        """
        return {
            schema_version: self._is_valid(schema_version)
            for schema_version in self._VALIDATION_ORDER
        }

    def get_validation_errors(self, schema_version: SchemaVersion) -> list[str]:
        """Get detailed validation errors for a specific schema version.

        Args:
            schema_version: The schema version to validate against.

        Returns:
            A list of validation error messages.

        """
        errors = []

        with self._get_schema(schema_version) as schema:
            if schema is None:
                return [f"Schema not available: {schema_version}"]

            try:
                schema.validate(BytesIO(self.xml))
            except XMLSchemaValidationError as e:
                errors.append(str(e))
            except Exception as e:
                errors.append(f"Unexpected validation error: {e}")

        return errors

    def __repr__(self) -> str:
        """Return a string representation of the validator."""
        xml_size = len(self.xml) if self.xml else 0
        return f"ValidateMetadata(xml_size={xml_size} bytes)"
