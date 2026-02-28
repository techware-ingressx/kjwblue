"""Tests for CLI entry point (main.py)."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from csv_reader import CsvReadResult
from main import build_parser, main
from models import EmailRecord, SendResult


# ===================================================================
# build_parser
# ===================================================================

class TestBuildParser:
    """Tests for build_parser function."""

    def test_parses_csv_file_positional(self):
        parser = build_parser()
        args = parser.parse_args(["emails.csv"])
        assert args.csv_file == "emails.csv"

    def test_parses_dry_run_flag(self):
        parser = build_parser()
        args = parser.parse_args(["emails.csv", "--dry-run"])
        assert args.dry_run is True

    def test_dry_run_default_false(self):
        parser = build_parser()
        args = parser.parse_args(["emails.csv"])
        assert args.dry_run is False

    def test_parses_schedule_option(self):
        parser = build_parser()
        args = parser.parse_args(["emails.csv", "--schedule", "10:30"])
        assert args.schedule == "10:30"

    def test_parses_log_path_option(self):
        parser = build_parser()
        args = parser.parse_args(["emails.csv", "--log-path", "my_log.csv"])
        assert args.log_path == "my_log.csv"

    def test_log_path_default_none(self):
        parser = build_parser()
        args = parser.parse_args(["emails.csv"])
        assert args.log_path is None

    def test_parses_encoding_option(self):
        parser = build_parser()
        args = parser.parse_args(["emails.csv", "--encoding", "euc-kr"])
        assert args.encoding == "euc-kr"

    def test_encoding_default_utf8(self):
        parser = build_parser()
        args = parser.parse_args(["emails.csv"])
        assert args.encoding == "utf-8"


# ===================================================================
# main
# ===================================================================

class TestMain:
    """Tests for main function."""

    def _make_csv_result(self, records=(), errors=()):
        return CsvReadResult(records=records, errors=errors)

    @patch("main.read_email_csv")
    def test_dry_run_prints_preview(self, mock_read, capsys, sample_records):
        mock_read.return_value = self._make_csv_result(records=sample_records)

        with patch("sys.argv", ["prog", "emails.csv", "--dry-run"]):
            main()

        captured = capsys.readouterr()
        assert "DRY-RUN" in captured.out
        assert "Alice Kim" in captured.out

    @patch("main.read_email_csv")
    def test_dry_run_no_records_exits(self, mock_read):
        mock_read.return_value = self._make_csv_result()

        with patch("sys.argv", ["prog", "emails.csv", "--dry-run"]):
            with pytest.raises(SystemExit):
                main()

    @patch("main.send_all_emails")
    @patch("main.create_rate_limiter")
    @patch("main.load_smtp_config")
    @patch("main.read_email_csv")
    def test_normal_send_calls_send_all_emails(
        self, mock_read, mock_config, mock_rate, mock_send,
        sample_records, smtp_config,
    ):
        mock_read.return_value = self._make_csv_result(records=sample_records)
        mock_config.return_value = smtp_config
        mock_rate.return_value = MagicMock()
        mock_send.return_value = ()

        with patch("sys.argv", ["prog", "emails.csv", "--log-path", "test.csv"]):
            main()

        mock_send.assert_called_once()
        call_args = mock_send.call_args[0]
        assert call_args[0] == sample_records

    @patch("main.schedule_send")
    @patch("main.read_email_csv")
    def test_schedule_option_calls_schedule_send(
        self, mock_read, mock_schedule, sample_records,
    ):
        mock_read.return_value = self._make_csv_result(records=sample_records)

        with patch("sys.argv", ["prog", "emails.csv", "--schedule", "14:00"]):
            main()

        mock_schedule.assert_called_once()
        assert mock_schedule.call_args[0][0] == "14:00"

    @patch("main.read_email_csv")
    def test_no_valid_records_exits(self, mock_read):
        mock_read.return_value = self._make_csv_result(
            errors=("행 2: 'name' 값이 비어있습니다",),
        )

        with patch("sys.argv", ["prog", "emails.csv"]):
            with pytest.raises(SystemExit):
                main()

    @patch("main.read_email_csv")
    def test_csv_errors_printed_as_warnings(self, mock_read, capsys):
        mock_read.return_value = self._make_csv_result(
            errors=("행 2: 잘못된 이메일 형식 'bad'",),
        )

        with patch("sys.argv", ["prog", "emails.csv", "--dry-run"]):
            with pytest.raises(SystemExit):
                main()

        captured = capsys.readouterr()
        assert "경고" in captured.out

    @patch("main.send_all_emails")
    @patch("main.create_rate_limiter")
    @patch("main.load_smtp_config")
    @patch("main.read_email_csv")
    def test_custom_encoding_passed_to_reader(
        self, mock_read, mock_config, mock_rate, mock_send,
        sample_records, smtp_config,
    ):
        mock_read.return_value = self._make_csv_result(records=sample_records)
        mock_config.return_value = smtp_config
        mock_rate.return_value = MagicMock()
        mock_send.return_value = ()

        with patch(
            "sys.argv",
            ["prog", "emails.csv", "--encoding", "euc-kr", "--log-path", "t.csv"],
        ):
            main()

        mock_read.assert_called_with("emails.csv", encoding="euc-kr")
