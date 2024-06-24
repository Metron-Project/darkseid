import pytest

from darkseid.archivers.__init__ import UnknownArchiver


@pytest.mark.parametrize("expected_name", ["Unknown"], ids=["happy_path"])
def test_name(expected_name):
    # Act
    result = UnknownArchiver.name()

    # Assert
    assert result == expected_name
