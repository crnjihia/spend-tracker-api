"""Unit tests for settings validation."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_invalid_log_level_rejected():
    """LOG_LEVEL must be a standard logging level."""
    with pytest.raises(ValidationError):
        Settings(LOG_LEVEL="NOPE")
