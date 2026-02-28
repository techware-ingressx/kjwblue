"""Tests for SMTP email sending (smtp_sender.py)."""

import smtplib
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from models import EmailRecord, RateLimitState, SendResult, SmtpConfig
from smtp_sender import (
    create_smtp_connection,
    send_all_emails,
    send_single_email,
    send_with_retry,
)


# ===================================================================
# send_single_email
# ===================================================================

class TestSendSingleEmail:
    """Tests for send_single_email function."""

    def test_success_returns_success_status(
        self, sample_record, smtp_config, mock_smtp_connection,
    ):
        result = send_single_email(
            sample_record, smtp_config, mock_smtp_connection,
        )

        assert result.status == "success"
        assert result.name == sample_record.name
        assert result.email == sample_record.email
        assert result.error_message == ""

    def test_success_calls_sendmail(
        self, sample_record, smtp_config, mock_smtp_connection,
    ):
        send_single_email(sample_record, smtp_config, mock_smtp_connection)

        mock_smtp_connection.sendmail.assert_called_once()
        args = mock_smtp_connection.sendmail.call_args
        assert args[0][0] == smtp_config.sender_email
        assert args[0][1] == sample_record.email

    def test_recipients_refused_returns_failure(
        self, sample_record, smtp_config, mock_smtp_connection,
    ):
        mock_smtp_connection.sendmail.side_effect = smtplib.SMTPRecipientsRefused(
            {sample_record.email: (550, b"User unknown")},
        )

        result = send_single_email(
            sample_record, smtp_config, mock_smtp_connection,
        )

        assert result.status == "failure"
        assert "수신 거부" in result.error_message

    def test_general_exception_returns_failure(
        self, sample_record, smtp_config, mock_smtp_connection,
    ):
        mock_smtp_connection.sendmail.side_effect = RuntimeError("Network error")

        result = send_single_email(
            sample_record, smtp_config, mock_smtp_connection,
        )

        assert result.status == "failure"
        assert "Network error" in result.error_message

    def test_result_has_timestamp(
        self, sample_record, smtp_config, mock_smtp_connection,
    ):
        result = send_single_email(
            sample_record, smtp_config, mock_smtp_connection,
        )
        assert isinstance(result.timestamp, datetime)


# ===================================================================
# send_with_retry
# ===================================================================

class TestSendWithRetry:
    """Tests for send_with_retry function."""

    @patch("smtp_sender.time.sleep")
    def test_first_attempt_success(
        self, mock_sleep, sample_record, smtp_config, mock_smtp_connection,
    ):
        result = send_with_retry(
            sample_record, smtp_config, mock_smtp_connection,
        )

        assert result.status == "success"
        mock_sleep.assert_not_called()

    @patch("smtp_sender.time.sleep")
    def test_second_attempt_success(
        self, mock_sleep, sample_record, smtp_config, mock_smtp_connection,
    ):
        mock_smtp_connection.sendmail.side_effect = [
            RuntimeError("Transient error"),
            {},
        ]

        result = send_with_retry(
            sample_record, smtp_config, mock_smtp_connection,
        )

        assert result.status == "success"
        mock_sleep.assert_called_once_with(1)

    @patch("smtp_sender.time.sleep")
    def test_all_attempts_fail(
        self, mock_sleep, sample_record, smtp_config, mock_smtp_connection,
    ):
        mock_smtp_connection.sendmail.side_effect = RuntimeError("Persistent error")

        result = send_with_retry(
            sample_record, smtp_config, mock_smtp_connection, max_retries=3,
        )

        assert result.status == "failure"
        assert "Persistent error" in result.error_message

    @patch("smtp_sender.time.sleep")
    def test_exponential_backoff_sleep_calls(
        self, mock_sleep, sample_record, smtp_config, mock_smtp_connection,
    ):
        mock_smtp_connection.sendmail.side_effect = RuntimeError("Fail")

        send_with_retry(
            sample_record, smtp_config, mock_smtp_connection, max_retries=3,
        )

        assert mock_sleep.call_args_list == [call(1), call(2)]

    @patch("smtp_sender.time.sleep")
    def test_single_retry_no_sleep_on_final_attempt(
        self, mock_sleep, sample_record, smtp_config, mock_smtp_connection,
    ):
        mock_smtp_connection.sendmail.side_effect = RuntimeError("Fail")

        send_with_retry(
            sample_record, smtp_config, mock_smtp_connection, max_retries=1,
        )

        mock_sleep.assert_not_called()


# ===================================================================
# create_smtp_connection
# ===================================================================

class TestCreateSmtpConnection:
    """Tests for create_smtp_connection function."""

    @patch("smtp_sender.ssl.create_default_context")
    @patch("smtp_sender.smtplib.SMTP")
    def test_smtp_created_with_host_and_port(
        self, mock_smtp_cls, mock_ssl, smtp_config,
    ):
        create_smtp_connection(smtp_config)

        mock_smtp_cls.assert_called_once_with(
            smtp_config.host, smtp_config.port,
        )

    @patch("smtp_sender.ssl.create_default_context")
    @patch("smtp_sender.smtplib.SMTP")
    def test_starttls_called(self, mock_smtp_cls, mock_ssl, smtp_config):
        mock_conn = MagicMock()
        mock_smtp_cls.return_value = mock_conn

        create_smtp_connection(smtp_config)

        mock_conn.starttls.assert_called_once()

    @patch("smtp_sender.ssl.create_default_context")
    @patch("smtp_sender.smtplib.SMTP")
    def test_login_called_with_credentials(
        self, mock_smtp_cls, mock_ssl, smtp_config,
    ):
        mock_conn = MagicMock()
        mock_smtp_cls.return_value = mock_conn

        create_smtp_connection(smtp_config)

        mock_conn.login.assert_called_once_with(
            smtp_config.sender_email, smtp_config.app_password,
        )

    @patch("smtp_sender.ssl.create_default_context")
    @patch("smtp_sender.smtplib.SMTP")
    def test_returns_connection(self, mock_smtp_cls, mock_ssl, smtp_config):
        mock_conn = MagicMock()
        mock_smtp_cls.return_value = mock_conn

        result = create_smtp_connection(smtp_config)

        assert result is mock_conn


# ===================================================================
# send_all_emails
# ===================================================================

class TestSendAllEmails:
    """Tests for send_all_emails function."""

    @patch("smtp_sender.append_result")
    @patch("smtp_sender.wait_if_needed")
    @patch("smtp_sender.create_smtp_connection")
    def test_sends_all_records(
        self,
        mock_create_conn,
        mock_wait,
        mock_append,
        sample_records,
        smtp_config,
        rate_state,
        tmp_path,
    ):
        mock_conn = MagicMock()
        mock_conn.sendmail.return_value = {}
        mock_create_conn.return_value = mock_conn
        mock_wait.side_effect = lambda s: RateLimitState(
            sent_count=s.sent_count + 1,
            daily_limit=s.daily_limit,
            interval_seconds=s.interval_seconds,
            last_sent_at=1.0,
        )

        results = send_all_emails(
            sample_records, smtp_config, str(tmp_path / "log.csv"), rate_state,
        )

        assert len(results) == 3
        assert all(r.status == "success" for r in results)

    @patch("smtp_sender.append_result")
    @patch("smtp_sender.create_smtp_connection")
    def test_connection_failure_returns_all_failures(
        self,
        mock_create_conn,
        mock_append,
        sample_records,
        smtp_config,
        rate_state,
        tmp_path,
    ):
        mock_create_conn.side_effect = ConnectionRefusedError("Connection refused")

        results = send_all_emails(
            sample_records, smtp_config, str(tmp_path / "log.csv"), rate_state,
        )

        assert len(results) == 3
        assert all(r.status == "failure" for r in results)
        assert all("SMTP 연결 실패" in r.error_message for r in results)

    @patch("smtp_sender.append_result")
    @patch("smtp_sender.create_smtp_connection")
    def test_connection_failure_logs_all_results(
        self,
        mock_create_conn,
        mock_append,
        sample_records,
        smtp_config,
        rate_state,
        tmp_path,
    ):
        mock_create_conn.side_effect = ConnectionRefusedError("refused")

        send_all_emails(
            sample_records, smtp_config, str(tmp_path / "log.csv"), rate_state,
        )

        assert mock_append.call_count == 3

    @patch("smtp_sender.append_result")
    @patch("smtp_sender.wait_if_needed")
    @patch("smtp_sender.create_smtp_connection")
    def test_rate_limit_reached_stops_sending(
        self,
        mock_create_conn,
        mock_wait,
        mock_append,
        sample_records,
        smtp_config,
        tmp_path,
    ):
        mock_conn = MagicMock()
        mock_create_conn.return_value = mock_conn
        exhausted_state = RateLimitState(sent_count=450, daily_limit=450)

        results = send_all_emails(
            sample_records, smtp_config, str(tmp_path / "log.csv"), exhausted_state,
        )

        assert len(results) == 3
        assert all(r.status == "failure" for r in results)
        assert all("한도" in r.error_message for r in results)
        mock_conn.sendmail.assert_not_called()

    @patch("smtp_sender.append_result")
    @patch("smtp_sender.wait_if_needed")
    @patch("smtp_sender.create_smtp_connection")
    def test_quit_called_on_success(
        self,
        mock_create_conn,
        mock_wait,
        mock_append,
        sample_record,
        smtp_config,
        rate_state,
        tmp_path,
    ):
        mock_conn = MagicMock()
        mock_conn.sendmail.return_value = {}
        mock_create_conn.return_value = mock_conn
        mock_wait.side_effect = lambda s: RateLimitState(
            sent_count=s.sent_count + 1,
            daily_limit=s.daily_limit,
            interval_seconds=s.interval_seconds,
            last_sent_at=1.0,
        )

        send_all_emails(
            (sample_record,), smtp_config, str(tmp_path / "log.csv"), rate_state,
        )

        mock_conn.quit.assert_called_once()

    @patch("smtp_sender.append_result")
    @patch("smtp_sender.wait_if_needed")
    @patch("smtp_sender.create_smtp_connection")
    def test_quit_called_even_on_send_failure(
        self,
        mock_create_conn,
        mock_wait,
        mock_append,
        sample_record,
        smtp_config,
        rate_state,
        tmp_path,
    ):
        mock_conn = MagicMock()
        mock_conn.sendmail.side_effect = RuntimeError("Send failed")
        mock_create_conn.return_value = mock_conn
        mock_wait.side_effect = lambda s: RateLimitState(
            sent_count=s.sent_count + 1,
            daily_limit=s.daily_limit,
            interval_seconds=s.interval_seconds,
            last_sent_at=1.0,
        )

        send_all_emails(
            (sample_record,), smtp_config, str(tmp_path / "log.csv"), rate_state,
        )

        mock_conn.quit.assert_called_once()

    @patch("smtp_sender.append_result")
    @patch("smtp_sender.wait_if_needed")
    @patch("smtp_sender.create_smtp_connection")
    def test_results_logged_via_append_result(
        self,
        mock_create_conn,
        mock_wait,
        mock_append,
        sample_records,
        smtp_config,
        rate_state,
        tmp_path,
    ):
        mock_conn = MagicMock()
        mock_conn.sendmail.return_value = {}
        mock_create_conn.return_value = mock_conn
        mock_wait.side_effect = lambda s: RateLimitState(
            sent_count=s.sent_count + 1,
            daily_limit=s.daily_limit,
            interval_seconds=s.interval_seconds,
            last_sent_at=1.0,
        )
        log_path = str(tmp_path / "log.csv")

        send_all_emails(
            sample_records, smtp_config, log_path, rate_state,
        )

        assert mock_append.call_count == 3
        for c in mock_append.call_args_list:
            assert c[0][0] == log_path
