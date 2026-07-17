"""
Unit tests for SanitizingFilter — verifies that API keys and secrets
are redacted from log output and never emitted in plain text.

Required by Prompt 8 QA inspection: "accidental API key logging".
"""
from __future__ import annotations

import logging

import pytest

from app.core.logging import SanitizingFilter


@pytest.fixture
def sanitizing_filter() -> SanitizingFilter:
    return SanitizingFilter()


def _make_record(msg: str) -> logging.LogRecord:
    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname="",
        lineno=0,
        msg=msg,
        args=(),
        exc_info=None,
    )
    return record


class TestSanitizingFilter:

    def test_clean_message_passes_through(self, sanitizing_filter: SanitizingFilter):
        """Normal log messages must not be altered."""
        record = _make_record("Starting research for plan_id=abc-123 destination=Paris")
        sanitizing_filter.filter(record)
        assert record.msg == "Starting research for plan_id=abc-123 destination=Paris"

    def test_api_key_in_message_is_redacted(self, sanitizing_filter: SanitizingFilter):
        """A message containing 'api_key' must be fully redacted."""
        record = _make_record("Calling Serper api_key=sk-super-secret-value")
        sanitizing_filter.filter(record)
        assert "sk-super-secret-value" not in record.msg
        assert "REDACTED" in record.msg

    def test_secret_in_message_is_redacted(self, sanitizing_filter: SanitizingFilter):
        record = _make_record("Loaded secret=s3cr3t from env")
        sanitizing_filter.filter(record)
        assert "s3cr3t" not in record.msg
        assert "REDACTED" in record.msg

    def test_password_in_message_is_redacted(self, sanitizing_filter: SanitizingFilter):
        record = _make_record("DB password=hunter2 connected")
        sanitizing_filter.filter(record)
        assert "hunter2" not in record.msg

    def test_token_in_message_is_redacted(self, sanitizing_filter: SanitizingFilter):
        record = _make_record("Bearer token=eyJhbGciOiJIUzI1NiJ9...")
        sanitizing_filter.filter(record)
        assert "eyJhbGciOiJIUzI1NiJ9" not in record.msg

    def test_authorization_header_is_redacted(self, sanitizing_filter: SanitizingFilter):
        record = _make_record("Sending header: authorization: Bearer some-real-token")
        sanitizing_filter.filter(record)
        assert "some-real-token" not in record.msg

    def test_case_insensitive_detection(self, sanitizing_filter: SanitizingFilter):
        """Detection must be case-insensitive — 'API_KEY', 'Api_Key' etc."""
        record = _make_record("OPENAI_API_KEY=sk-abc123 loaded from environment")
        sanitizing_filter.filter(record)
        assert "sk-abc123" not in record.msg
        assert "REDACTED" in record.msg

    def test_filter_always_returns_true(self, sanitizing_filter: SanitizingFilter):
        """filter() must return True — records are always emitted (redacted if necessary)."""
        clean = _make_record("Normal message")
        dirty = _make_record("Contains api_key=bad")
        assert sanitizing_filter.filter(clean) is True
        assert sanitizing_filter.filter(dirty) is True

    def test_args_cleared_after_redaction(self, sanitizing_filter: SanitizingFilter):
        """record.args must be cleared so % formatting cannot resurrect the secret."""
        record = _make_record("api_key=%s")
        record.args = ("SUPER_SECRET_KEY",)
        sanitizing_filter.filter(record)
        assert record.args == ()
