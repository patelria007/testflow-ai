"""Unit tests for src/llm_step_parser.py — LLM step parsing.

Each test has a single assertion per the course requirement.
Mocks the Gemini API to avoid real API calls.
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from src.llm_step_parser import parse_steps_with_llm, _load_api_key


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture()
def sample_elements():
    """Sample page elements discovered by BeautifulSoup."""
    return {
        "inputs": [
            {"type": "text", "name": "username", "id": "user", "placeholder": "Username"},
            {"type": "password", "name": "password", "id": "pw", "placeholder": "Password"},
        ],
        "buttons": [{"text": "Sign In", "type": "submit", "id": "login-btn", "class": "btn"}],
        "links": [{"text": "Register", "href": "/register"}],
        "forms": [{"action": "/login", "method": "post"}],
    }


@pytest.fixture()
def mock_llm_response():
    """Factory fixture for creating mock LLM responses."""
    def _make(actions):
        mock_response = MagicMock()
        mock_response.text = json.dumps(actions)
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response
        return mock_client
    return _make


# ── parse_steps_with_llm ────────────────────────────────────────────────


class TestParseStepsWithLlm:
    def test_raises_without_api_key(self, sample_elements):
        with patch("src.llm_step_parser._load_api_key", return_value=""):
            with pytest.raises(ValueError, match="API key not found"):
                parse_steps_with_llm("Click login", sample_elements, "http://app")

    def test_returns_list_of_actions(self, sample_elements, mock_llm_response):
        actions = [
            {"action": "enter", "target": "username", "value": "admin"},
            {"action": "click", "target": "Sign In", "value": ""},
        ]
        mock_client = mock_llm_response(actions)

        with patch("src.llm_step_parser._load_api_key", return_value="fake-key"):
            with patch("src.llm_step_parser.genai.Client", return_value=mock_client):
                result = parse_steps_with_llm("Login as admin", sample_elements, "http://app")
                assert isinstance(result, list)

    def test_returns_correct_number_of_actions(self, sample_elements, mock_llm_response):
        actions = [
            {"action": "enter", "target": "username", "value": "admin"},
            {"action": "enter", "target": "password", "value": "admin"},
            {"action": "click", "target": "Sign In", "value": ""},
        ]
        mock_client = mock_llm_response(actions)

        with patch("src.llm_step_parser._load_api_key", return_value="fake-key"):
            with patch("src.llm_step_parser.genai.Client", return_value=mock_client):
                result = parse_steps_with_llm("Login", sample_elements, "http://app")
                assert len(result) == 3

    def test_action_has_action_key(self, sample_elements, mock_llm_response):
        actions = [{"action": "click", "target": "Submit", "value": ""}]
        mock_client = mock_llm_response(actions)

        with patch("src.llm_step_parser._load_api_key", return_value="fake-key"):
            with patch("src.llm_step_parser.genai.Client", return_value=mock_client):
                result = parse_steps_with_llm("Click submit", sample_elements, "http://app")
                assert result[0]["action"] == "click"

    def test_action_has_target_key(self, sample_elements, mock_llm_response):
        actions = [{"action": "enter", "target": "email", "value": "a@b.com"}]
        mock_client = mock_llm_response(actions)

        with patch("src.llm_step_parser._load_api_key", return_value="fake-key"):
            with patch("src.llm_step_parser.genai.Client", return_value=mock_client):
                result = parse_steps_with_llm("Enter email", sample_elements, "http://app")
                assert result[0]["target"] == "email"

    def test_handles_code_fenced_response(self, sample_elements):
        mock_response = MagicMock()
        mock_response.text = '```json\n[{"action": "navigate", "target": "/home", "value": ""}]\n```'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("src.llm_step_parser._load_api_key", return_value="fake-key"):
            with patch("src.llm_step_parser.genai.Client", return_value=mock_client):
                result = parse_steps_with_llm("Go home", sample_elements, "http://app")
                assert result[0]["action"] == "navigate"

    def test_all_models_fail_raises_runtime_error(self, sample_elements):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("model error")

        with patch("src.llm_step_parser._load_api_key", return_value="fake-key"):
            with patch("src.llm_step_parser.genai.Client", return_value=mock_client):
                with pytest.raises(RuntimeError, match="No available Gemini model"):
                    parse_steps_with_llm("Do stuff", sample_elements, "http://app")

    def test_navigate_action_target(self, sample_elements, mock_llm_response):
        actions = [{"action": "navigate", "target": "http://example.com", "value": ""}]
        mock_client = mock_llm_response(actions)

        with patch("src.llm_step_parser._load_api_key", return_value="fake-key"):
            with patch("src.llm_step_parser.genai.Client", return_value=mock_client):
                result = parse_steps_with_llm("Go to example.com", sample_elements, "http://app")
                assert "example.com" in result[0]["target"]


# ── _load_api_key ────────────────────────────────────────────────────────


class TestLoadApiKey:
    def test_load_from_env_var(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "env-key"}):
            with patch("builtins.open", side_effect=FileNotFoundError):
                assert _load_api_key() == "env-key"

    def test_returns_empty_when_no_key(self):
        import os
        env_backup = os.environ.pop("GEMINI_API_KEY", None)
        try:
            with patch("builtins.open", side_effect=FileNotFoundError):
                assert _load_api_key() == ""
        finally:
            if env_backup is not None:
                os.environ["GEMINI_API_KEY"] = env_backup
