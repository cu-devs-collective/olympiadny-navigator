from unittest import mock

from app.api import __main__ as api_main
from app.core.config import Settings


def test_main_returns_success_after_server_stops() -> None:
    with (
        mock.patch.object(api_main, "get_settings", return_value=Settings()),
        mock.patch.object(api_main, "configure_logging"),
        mock.patch.object(api_main, "shutdown_logging") as shutdown_logging,
        mock.patch.object(api_main.uvicorn, "run") as run,
    ):
        exit_code = api_main.main()

    assert exit_code == 0
    run.assert_called_once()
    shutdown_logging.assert_called_once_with()


def test_main_logs_unhandled_exception_and_returns_failure() -> None:
    error = RuntimeError("startup failed")

    with (
        mock.patch.object(api_main, "get_settings", return_value=Settings()),
        mock.patch.object(api_main, "configure_logging"),
        mock.patch.object(api_main, "shutdown_logging") as shutdown_logging,
        mock.patch.object(api_main.uvicorn, "run", side_effect=error),
        mock.patch.object(api_main.loguru.logger, "exception") as log_exception,
    ):
        exit_code = api_main.main()

    assert exit_code == 1
    log_exception.assert_called_once_with("API terminated unexpectedly")
    shutdown_logging.assert_called_once_with()
