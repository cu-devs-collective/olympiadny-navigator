import io
import json
import logging
from unittest import mock

import loguru

from app.core.logging import InterceptHandler, _json_log_record, _text_log_format


def test_text_log_format_renders_bound_context() -> None:
    output = io.StringIO()
    sink_id = loguru.logger.add(output, format=_text_log_format)
    try:
        loguru.logger.bind(
            method="GET",
            request_id="request-1",
            status_code=200,
        ).info("HTTP request completed")
    finally:
        loguru.logger.remove(sink_id)

    rendered = output.getvalue()
    assert "HTTP request completed" in rendered
    assert 'method="GET"' in rendered
    assert 'request_id="request-1"' in rendered
    assert "status_code=200" in rendered


def test_json_log_format_is_compact_and_flat() -> None:
    records: list[loguru.Record] = []
    sink_id = loguru.logger.add(lambda message: records.append(message.record))
    try:
        loguru.logger.bind(
            method="GET",
            request_id="request-1",
            status_code=200,
        ).info("HTTP request completed")
    finally:
        loguru.logger.remove(sink_id)

    payload = json.loads(_json_log_record(records[0]))
    assert payload["level"] == "INFO"
    assert payload["message"] == "HTTP request completed"
    assert payload["method"] == "GET"
    assert payload["request_id"] == "request-1"
    assert payload["status_code"] == 200
    assert payload["timestamp"].endswith("Z")
    assert "icon" not in payload
    assert "time" not in payload


def test_http_client_debug_records_are_dropped_before_interception() -> None:
    record = logging.LogRecord(
        name="httpcore2._trace",
        level=logging.DEBUG,
        pathname=__file__,
        lineno=1,
        msg="headers include Cookie: secret",
        args=(),
        exc_info=None,
    )

    with mock.patch.object(loguru.logger, "opt") as loguru_opt:
        InterceptHandler().emit(record)

    loguru_opt.assert_not_called()
