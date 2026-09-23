import pydantic
import pytest

from app.core.config import LoggingSettings


def test_log_levels_reject_loguru_only_levels() -> None:
    with pytest.raises(pydantic.ValidationError):
        LoggingSettings.model_validate({"level": "SUCCESS"})

    with pytest.raises(pydantic.ValidationError):
        LoggingSettings.model_validate({"sql_level": "TRACE"})
