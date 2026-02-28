"""Tests for csv_reader module."""

import pytest

from csv_reader import CsvReadResult, read_email_csv
from models import EmailRecord


# ---------------------------------------------------------------------------
# CsvReadResult
# ---------------------------------------------------------------------------


class TestCsvReadResult:
    """Tests for CsvReadResult data container."""

    def test_records_property_returns_tuple(self):
        records = (
            EmailRecord(
                name="Alice",
                email="alice@example.com",
                subject="Hi",
                body="Body",
            ),
        )
        result = CsvReadResult(records, ())

        assert result.records == records

    def test_errors_property_returns_tuple(self):
        errors = ("error 1", "error 2")
        result = CsvReadResult((), errors)

        assert result.errors == errors

    def test_has_errors_true_when_errors_present(self):
        result = CsvReadResult((), ("some error",))

        assert result.has_errors is True

    def test_has_errors_false_when_no_errors(self):
        result = CsvReadResult((), ())

        assert result.has_errors is False

    @pytest.mark.parametrize(
        ("n_records", "n_errors", "expected"),
        [
            (3, 0, "유효: 3건, 오류: 0건"),
            (0, 2, "유효: 0건, 오류: 2건"),
            (5, 1, "유효: 5건, 오류: 1건"),
        ],
        ids=["all-valid", "all-errors", "mixed"],
    )
    def test_summary_format(self, n_records, n_errors, expected):
        records = tuple(
            EmailRecord(
                name=f"User{i}",
                email=f"user{i}@example.com",
                subject="Sub",
                body="Body",
            )
            for i in range(n_records)
        )
        errors = tuple(f"error {i}" for i in range(n_errors))

        result = CsvReadResult(records, errors)

        assert result.summary == expected


# ---------------------------------------------------------------------------
# read_email_csv - valid input
# ---------------------------------------------------------------------------


class TestReadEmailCsvValid:
    """Tests for read_email_csv with valid input."""

    def test_valid_csv_returns_records(self, valid_csv_path):
        result = read_email_csv(str(valid_csv_path))

        assert len(result.records) == 3
        assert result.has_errors is False

    def test_valid_csv_record_fields(self, valid_csv_path):
        result = read_email_csv(str(valid_csv_path))
        first = result.records[0]

        assert first.name == "Alice Kim"
        assert first.email == "alice@example.com"
        assert first.subject == "Welcome"

    def test_valid_csv_returns_immutable_records(self, valid_csv_path):
        result = read_email_csv(str(valid_csv_path))

        assert isinstance(result.records, tuple)


# ---------------------------------------------------------------------------
# read_email_csv - file not found
# ---------------------------------------------------------------------------


class TestReadEmailCsvFileNotFound:
    """Tests for read_email_csv when file does not exist."""

    def test_missing_file_exits_with_code_1(self):
        with pytest.raises(SystemExit) as exc_info:
            read_email_csv("/nonexistent/path/emails.csv")

        assert exc_info.value.code == 1


# ---------------------------------------------------------------------------
# read_email_csv - empty / malformed
# ---------------------------------------------------------------------------


class TestReadEmailCsvEmpty:
    """Tests for read_email_csv with empty or header-only files."""

    def test_empty_file_returns_error(self, tmp_path):
        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("", encoding="utf-8")

        result = read_email_csv(str(csv_file))

        assert result.has_errors is True
        assert "비어있습니다" in result.errors[0]

    def test_missing_columns_returns_error(self, tmp_path):
        csv_file = tmp_path / "bad_cols.csv"
        csv_file.write_text("name,email\nAlice,alice@example.com\n", encoding="utf-8")

        result = read_email_csv(str(csv_file))

        assert result.has_errors is True
        assert "필수 컬럼 누락" in result.errors[0]

    def test_missing_columns_lists_which_are_missing(self, tmp_path):
        csv_file = tmp_path / "partial_cols.csv"
        csv_file.write_text("name,email\nAlice,alice@example.com\n", encoding="utf-8")

        result = read_email_csv(str(csv_file))

        assert "body" in result.errors[0]
        assert "subject" in result.errors[0]


# ---------------------------------------------------------------------------
# read_email_csv - row-level errors
# ---------------------------------------------------------------------------


class TestReadEmailCsvRowErrors:
    """Tests for read_email_csv with invalid rows."""

    def test_invalid_row_skipped(self, tmp_path):
        csv_file = tmp_path / "bad_row.csv"
        csv_file.write_text(
            "name,email,subject,body\n"
            ",invalid-email,Subject,Body\n"
            "Bob,bob@example.com,Hello,World\n",
            encoding="utf-8",
        )

        result = read_email_csv(str(csv_file))

        assert len(result.records) == 1
        assert result.records[0].name == "Bob"

    def test_invalid_row_error_recorded(self, tmp_path):
        csv_file = tmp_path / "bad_row2.csv"
        csv_file.write_text(
            "name,email,subject,body\n"
            ",bad-email,,\n",
            encoding="utf-8",
        )

        result = read_email_csv(str(csv_file))

        assert result.has_errors is True
        assert any("행 2" in err for err in result.errors)

    def test_mixed_valid_and_invalid_rows(self, tmp_path):
        csv_file = tmp_path / "mixed.csv"
        csv_file.write_text(
            "name,email,subject,body\n"
            "Alice,alice@example.com,Sub1,Body1\n"
            ",,, \n"
            "Carol,carol@example.com,Sub3,Body3\n",
            encoding="utf-8",
        )

        result = read_email_csv(str(csv_file))

        assert len(result.records) == 2
        assert result.has_errors is True
        assert result.summary == "유효: 2건, 오류: 4건"


# ---------------------------------------------------------------------------
# read_email_csv - encoding error
# ---------------------------------------------------------------------------


class TestReadEmailCsvEncoding:
    """Tests for read_email_csv with encoding issues."""

    def test_wrong_encoding_returns_error(self, tmp_path):
        csv_file = tmp_path / "euc_kr.csv"
        content = "name,email,subject,body\n한글,test@example.com,제목,본문\n"
        csv_file.write_bytes(content.encode("euc-kr"))

        result = read_email_csv(str(csv_file), encoding="utf-8")

        assert result.has_errors is True
        assert "인코딩 오류" in result.errors[0]
