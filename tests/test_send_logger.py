"""Tests for send result logging (send_logger.py)."""

import csv
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import SendResult
from send_logger import (
    CSV_COLUMNS,
    append_result,
    append_results,
    format_summary,
    write_log_header,
)


# ===================================================================
# write_log_header
# ===================================================================

class TestWriteLogHeader:
    """Tests for write_log_header function."""

    def test_creates_file_with_header(self, tmp_path):
        log_file = tmp_path / "log.csv"
        write_log_header(str(log_file))

        assert log_file.exists()
        with open(log_file, encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
        assert tuple(header) == CSV_COLUMNS

    def test_does_not_overwrite_existing_file(self, tmp_path):
        log_file = tmp_path / "log.csv"
        log_file.write_text("existing,content\n", encoding="utf-8")

        write_log_header(str(log_file))

        content = log_file.read_text(encoding="utf-8")
        assert content == "existing,content\n"

    def test_duplicate_call_preserves_header(self, tmp_path):
        log_file = tmp_path / "log.csv"
        write_log_header(str(log_file))
        write_log_header(str(log_file))

        with open(log_file, encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
        assert len(rows) == 1
        assert tuple(rows[0]) == CSV_COLUMNS


# ===================================================================
# append_result
# ===================================================================

class TestAppendResult:
    """Tests for append_result function."""

    def test_appends_success_row(self, tmp_path, success_result):
        log_file = tmp_path / "log.csv"
        append_result(str(log_file), success_result)

        with open(log_file, encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
        assert len(rows) == 2
        data_row = rows[1]
        assert data_row[4] == "success"
        assert data_row[5] == ""

    def test_appends_failure_row(self, tmp_path, failure_result):
        log_file = tmp_path / "log.csv"
        append_result(str(log_file), failure_result)

        with open(log_file, encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
        data_row = rows[1]
        assert data_row[4] == "failure"
        assert data_row[5] == "SMTP connection refused"

    def test_auto_creates_header(self, tmp_path, success_result):
        log_file = tmp_path / "log.csv"
        assert not log_file.exists()

        append_result(str(log_file), success_result)

        with open(log_file, encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
        assert tuple(rows[0]) == CSV_COLUMNS
        assert len(rows) == 2

    def test_timestamp_is_iso_format(self, tmp_path, success_result):
        log_file = tmp_path / "log.csv"
        append_result(str(log_file), success_result)

        with open(log_file, encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
        timestamp_str = rows[1][0]
        parsed = datetime.fromisoformat(timestamp_str)
        assert parsed == success_result.timestamp

    def test_preserves_all_fields(self, tmp_path, success_result):
        log_file = tmp_path / "log.csv"
        append_result(str(log_file), success_result)

        with open(log_file, encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
        data_row = rows[1]
        assert data_row[1] == success_result.name
        assert data_row[2] == success_result.email
        assert data_row[3] == success_result.subject


# ===================================================================
# append_results
# ===================================================================

class TestAppendResults:
    """Tests for append_results function."""

    def test_appends_multiple_rows(self, tmp_path, mixed_results):
        log_file = tmp_path / "log.csv"
        append_results(str(log_file), mixed_results)

        with open(log_file, encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
        assert len(rows) == 4  # 1 header + 3 data rows

    def test_empty_results_writes_only_header(self, tmp_path):
        log_file = tmp_path / "log.csv"
        append_results(str(log_file), ())

        with open(log_file, encoding="utf-8", newline="") as f:
            rows = list(csv.reader(f))
        assert len(rows) == 1
        assert tuple(rows[0]) == CSV_COLUMNS


# ===================================================================
# format_summary
# ===================================================================

class TestFormatSummary:
    """Tests for format_summary function."""

    def test_all_success(self, success_result):
        results = (success_result, success_result)
        summary = format_summary(results)
        assert "성공 2건" in summary
        assert "실패 0건" in summary
        assert "총 2건" in summary

    def test_all_failure(self, failure_result):
        results = (failure_result, failure_result, failure_result)
        summary = format_summary(results)
        assert "성공 0건" in summary
        assert "실패 3건" in summary
        assert "총 3건" in summary

    def test_mixed_results(self, mixed_results):
        summary = format_summary(mixed_results)
        assert "성공 2건" in summary
        assert "실패 1건" in summary
        assert "총 3건" in summary

    def test_empty_results(self):
        summary = format_summary(())
        assert "성공 0건" in summary
        assert "실패 0건" in summary
        assert "총 0건" in summary
