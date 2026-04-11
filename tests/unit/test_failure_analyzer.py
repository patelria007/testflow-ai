"""Unit tests for src/failure_analyzer.py — AI failure diagnosis.

Each test has a single assertion per the course requirement.
Mocks the Gemini API to avoid real API calls.
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from src.failure_analyzer import analyze_failure, _fallback_analysis, _load_api_key


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture()
def sample_elements():
    """Sample page elements for testing."""
    return {
        "buttons": [{"text": "Submit", "type": "submit"}, {"text": "Cancel", "type": "button"}],
        "inputs": [{"name": "email", "id": "email-input"}, {"name": "password", "id": "pw"}],
        "links": [{"text": "Home", "href": "/"}],
    }


# ── _fallback_analysis ──────────────────────────────────────────────────


class TestFallbackAnalysis:
    def test_fallback_timeout_returns_environment(self, sample_elements):
        result = _fallback_analysis("Connection timeout", "step1", sample_elements)
        assert result["category"] == "environment"

    def test_fallback_connection_refused(self, sample_elements):
        result = _fallback_analysis("connection refused to host", "step1", sample_elements)
        assert result["category"] == "environment"

    def test_fallback_unreachable(self, sample_elements):
        result = _fallback_analysis("host unreachable", "step1", sample_elements)
        assert result["category"] == "environment"

    def test_fallback_dns_error(self, sample_elements):
        result = _fallback_analysis("DNS resolution failed", "step1", sample_elements)
        assert result["category"] == "environment"

    def test_fallback_browser_error(self, sample_elements):
        result = _fallback_analysis("browser error crashed", "step1", sample_elements)
        assert result["category"] == "environment"

    def test_fallback_element_not_found(self, sample_elements):
        result = _fallback_analysis("Could not find element 'xyz'", "step1", sample_elements)
        assert result["category"] == "test_design"

    def test_fallback_no_such_element(self, sample_elements):
        result = _fallback_analysis("no such element on page", "step1", sample_elements)
        assert result["category"] == "test_design"

    def test_fallback_server_error(self, sample_elements):
        result = _fallback_analysis("500 server error returned", "step1", sample_elements)
        assert result["category"] == "application_bug"

    def test_fallback_forbidden(self, sample_elements):
        result = _fallback_analysis("403 Forbidden response", "step1", sample_elements)
        assert result["category"] == "application_bug"

    def test_fallback_verify_failure(self, sample_elements):
        result = _fallback_analysis("Could not verify 'dashboard'", "step1", sample_elements)
        assert result["category"] == "test_design"

    def test_fallback_assert_failure(self, sample_elements):
        result = _fallback_analysis("Assertion failed: expected X", "step1", sample_elements)
        assert result["category"] == "test_design"

    def test_fallback_generic_returns_environment(self, sample_elements):
        result = _fallback_analysis("something unknown", "step1", sample_elements)
        assert result["category"] == "environment"

    def test_fallback_has_summary(self, sample_elements):
        result = _fallback_analysis("timeout error", "step1", sample_elements)
        assert len(result["summary"]) > 0

    def test_fallback_has_explanation(self, sample_elements):
        result = _fallback_analysis("timeout error", "step1", sample_elements)
        assert "timeout" in result["explanation"].lower()

    def test_fallback_has_suggestion(self, sample_elements):
        result = _fallback_analysis("timeout error", "step1", sample_elements)
        assert len(result["suggestion"]) > 0

    def test_fallback_has_proposed_fix(self, sample_elements):
        result = _fallback_analysis("timeout error", "step1", sample_elements)
        assert "proposed_fix" in result

    def test_fallback_element_not_found_mentions_buttons(self, sample_elements):
        result = _fallback_analysis("Could not find element", "step1", sample_elements)
        assert "Submit" in result["explanation"]

    def test_fallback_element_not_found_mentions_inputs(self, sample_elements):
        result = _fallback_analysis("Could not find element", "step1", sample_elements)
        assert "email" in result["explanation"]


# ── analyze_failure with mocked LLM ─────────────────────────────────────


class TestAnalyzeFailure:
    def test_analyze_failure_no_api_key_uses_fallback(self, sample_elements):
        with patch("src.failure_analyzer._load_api_key", return_value=""):
            result = analyze_failure(
                "timeout error", "step1", "Login", [], sample_elements,
                "Go to login", "Dashboard", "http://app"
            )
            assert result["category"] == "environment"

    def test_analyze_failure_with_api_key_calls_llm(self, sample_elements):
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "category": "test_design",
            "summary": "Wrong button",
            "explanation": "The test clicks a non-existent button",
            "suggestion": "Use the correct button name",
            "proposed_fix": "Click Submit instead",
        })

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("src.failure_analyzer._load_api_key", return_value="fake-key"):
            with patch("src.failure_analyzer.genai.Client", return_value=mock_client):
                result = analyze_failure(
                    "element not found", "Click Save", "Dashboard", [], sample_elements,
                    "Click Save", "Saved", "http://app"
                )
                assert result["category"] == "test_design"

    def test_analyze_failure_llm_returns_code_fenced_json(self, sample_elements):
        mock_response = MagicMock()
        mock_response.text = '```json\n{"category": "application_bug", "summary": "x", "explanation": "y", "suggestion": "z", "proposed_fix": "w"}\n```'

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("src.failure_analyzer._load_api_key", return_value="fake-key"):
            with patch("src.failure_analyzer.genai.Client", return_value=mock_client):
                result = analyze_failure(
                    "error", "step", "Title", [], sample_elements,
                    "steps", "outcome", "http://app"
                )
                assert result["category"] == "application_bug"

    def test_analyze_failure_llm_exception_uses_fallback(self, sample_elements):
        with patch("src.failure_analyzer._load_api_key", return_value="fake-key"):
            with patch("src.failure_analyzer.genai.Client", side_effect=Exception("API down")):
                result = analyze_failure(
                    "timeout error", "step1", "Title", [], sample_elements,
                    "steps", "outcome", "http://app"
                )
                assert result["category"] == "environment"

    def test_analyze_failure_invalid_category_defaults_to_environment(self, sample_elements):
        mock_response = MagicMock()
        mock_response.text = json.dumps({
            "category": "unknown_category",
            "summary": "x", "explanation": "y",
            "suggestion": "z", "proposed_fix": "w",
        })

        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("src.failure_analyzer._load_api_key", return_value="fake-key"):
            with patch("src.failure_analyzer.genai.Client", return_value=mock_client):
                result = analyze_failure(
                    "error", "step", "Title", [], sample_elements,
                    "steps", "outcome", "http://app"
                )
                assert result["category"] == "environment"

    def test_analyze_failure_all_models_fail_uses_fallback(self, sample_elements):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("model error")

        with patch("src.failure_analyzer._load_api_key", return_value="fake-key"):
            with patch("src.failure_analyzer.genai.Client", return_value=mock_client):
                result = analyze_failure(
                    "Could not find element", "step", "Title", [], sample_elements,
                    "steps", "outcome", "http://app"
                )
                assert result["category"] == "test_design"

    def test_analyze_failure_result_has_all_keys(self, sample_elements):
        with patch("src.failure_analyzer._load_api_key", return_value=""):
            result = analyze_failure(
                "error", "step", "Title", [], sample_elements,
                "steps", "outcome", "http://app"
            )
            assert all(k in result for k in ("category", "summary", "explanation", "suggestion", "proposed_fix"))


# ── _load_api_key ────────────────────────────────────────────────────────


class TestLoadApiKey:
    def test_load_api_key_from_env_var(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "test-key-123"}):
            with patch("builtins.open", side_effect=FileNotFoundError):
                result = _load_api_key()
                assert result == "test-key-123"

    def test_load_api_key_returns_empty_when_missing(self):
        with patch.dict("os.environ", {}, clear=True):
            # Remove GEMINI_API_KEY if present
            import os
            env_backup = os.environ.pop("GEMINI_API_KEY", None)
            try:
                with patch("builtins.open", side_effect=FileNotFoundError):
                    result = _load_api_key()
                    assert result == ""
            finally:
                if env_backup is not None:
                    os.environ["GEMINI_API_KEY"] = env_backup
