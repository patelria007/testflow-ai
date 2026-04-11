"""Unit tests for src/scenario_generator.py — AI scenario generation.

Each test has a single assertion per the course requirement.
Mocks the Gemini API to avoid real API calls.
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from src.scenario_generator import generate_scenarios, _build_site_description, _load_api_key


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture()
def sample_site_map():
    """A sample site map as returned by crawl_site()."""
    return {
        "app_url": "http://testapp.com",
        "user_notes": "admin/admin",
        "pages": [
            {
                "url": "http://testapp.com",
                "title": "Login",
                "inputs": [
                    {"tag": "input", "type": "text", "name": "username", "id": "user", "placeholder": "Username"},
                    {"tag": "input", "type": "password", "name": "password", "id": "pw", "placeholder": ""},
                ],
                "buttons": [{"text": "Sign In", "type": "submit"}],
                "links": [{"text": "Register", "href": "/register"}],
                "forms": [{"action": "/login", "method": "post", "fields": [
                    {"tag": "input", "type": "text", "name": "username"},
                    {"tag": "input", "type": "password", "name": "password"},
                ]}],
            },
            {
                "url": "http://testapp.com/dashboard",
                "title": "Dashboard",
                "inputs": [],
                "buttons": [{"text": "New Project", "type": "button"}],
                "links": [{"text": "Settings", "href": "/settings"}],
                "forms": [],
            },
        ],
    }


@pytest.fixture()
def mock_scenarios():
    """Sample scenarios that the LLM would return."""
    return [
        {
            "name": "Successful Login",
            "steps": "Go to login page\nEnter admin as username\nEnter admin as password\nClick Sign In",
            "expected_outcome": "Dashboard is displayed",
            "category": "authentication",
        },
        {
            "name": "Create New Project",
            "steps": "Log in\nClick New Project\nEnter project name\nClick Save",
            "expected_outcome": "Project created successfully",
            "category": "crud",
        },
    ]


# ── _build_site_description ──────────────────────────────────────────────


class TestBuildSiteDescription:
    def test_includes_page_title(self, sample_site_map):
        desc = _build_site_description(sample_site_map)
        assert "Login" in desc

    def test_includes_page_url(self, sample_site_map):
        desc = _build_site_description(sample_site_map)
        assert "http://testapp.com" in desc

    def test_includes_buttons(self, sample_site_map):
        desc = _build_site_description(sample_site_map)
        assert "Sign In" in desc

    def test_includes_links(self, sample_site_map):
        desc = _build_site_description(sample_site_map)
        assert "Register" in desc

    def test_includes_forms(self, sample_site_map):
        desc = _build_site_description(sample_site_map)
        assert "Forms:" in desc

    def test_includes_second_page(self, sample_site_map):
        desc = _build_site_description(sample_site_map)
        assert "Dashboard" in desc

    def test_multiple_pages_numbered(self, sample_site_map):
        desc = _build_site_description(sample_site_map)
        assert "Page 1" in desc

    def test_includes_page_2(self, sample_site_map):
        desc = _build_site_description(sample_site_map)
        assert "Page 2" in desc


# ── generate_scenarios ───────────────────────────────────────────────────


class TestGenerateScenarios:
    def test_raises_without_api_key(self, sample_site_map):
        with patch("src.scenario_generator._load_api_key", return_value=""):
            with pytest.raises(ValueError, match="API key not found"):
                generate_scenarios(sample_site_map)

    def test_returns_list(self, sample_site_map, mock_scenarios):
        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_scenarios)
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("src.scenario_generator._load_api_key", return_value="fake-key"):
            with patch("src.scenario_generator.genai.Client", return_value=mock_client):
                result = generate_scenarios(sample_site_map)
                assert isinstance(result, list)

    def test_returns_correct_count(self, sample_site_map, mock_scenarios):
        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_scenarios)
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("src.scenario_generator._load_api_key", return_value="fake-key"):
            with patch("src.scenario_generator.genai.Client", return_value=mock_client):
                result = generate_scenarios(sample_site_map, max_scenarios=2)
                assert len(result) == 2

    def test_respects_max_scenarios_limit(self, sample_site_map):
        many_scenarios = [
            {"name": f"Test {i}", "steps": "s", "expected_outcome": "o", "category": "c"}
            for i in range(10)
        ]
        mock_response = MagicMock()
        mock_response.text = json.dumps(many_scenarios)
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("src.scenario_generator._load_api_key", return_value="fake-key"):
            with patch("src.scenario_generator.genai.Client", return_value=mock_client):
                result = generate_scenarios(sample_site_map, max_scenarios=3)
                assert len(result) <= 3

    def test_scenario_has_name(self, sample_site_map, mock_scenarios):
        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_scenarios)
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("src.scenario_generator._load_api_key", return_value="fake-key"):
            with patch("src.scenario_generator.genai.Client", return_value=mock_client):
                result = generate_scenarios(sample_site_map)
                assert "name" in result[0]

    def test_scenario_has_steps(self, sample_site_map, mock_scenarios):
        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_scenarios)
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("src.scenario_generator._load_api_key", return_value="fake-key"):
            with patch("src.scenario_generator.genai.Client", return_value=mock_client):
                result = generate_scenarios(sample_site_map)
                assert "steps" in result[0]

    def test_scenario_has_expected_outcome(self, sample_site_map, mock_scenarios):
        mock_response = MagicMock()
        mock_response.text = json.dumps(mock_scenarios)
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("src.scenario_generator._load_api_key", return_value="fake-key"):
            with patch("src.scenario_generator.genai.Client", return_value=mock_client):
                result = generate_scenarios(sample_site_map)
                assert "expected_outcome" in result[0]

    def test_handles_code_fenced_response(self, sample_site_map, mock_scenarios):
        mock_response = MagicMock()
        mock_response.text = f'```json\n{json.dumps(mock_scenarios)}\n```'
        mock_client = MagicMock()
        mock_client.models.generate_content.return_value = mock_response

        with patch("src.scenario_generator._load_api_key", return_value="fake-key"):
            with patch("src.scenario_generator.genai.Client", return_value=mock_client):
                result = generate_scenarios(sample_site_map)
                assert len(result) > 0

    def test_all_models_fail_raises_runtime_error(self, sample_site_map):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = Exception("model fail")

        with patch("src.scenario_generator._load_api_key", return_value="fake-key"):
            with patch("src.scenario_generator.genai.Client", return_value=mock_client):
                with pytest.raises(RuntimeError, match="No available Gemini model"):
                    generate_scenarios(sample_site_map)


# ── _load_api_key ────────────────────────────────────────────────────────


class TestLoadApiKey:
    def test_load_from_env_var(self):
        with patch.dict("os.environ", {"GEMINI_API_KEY": "env-key-123"}):
            with patch("builtins.open", side_effect=FileNotFoundError):
                assert _load_api_key() == "env-key-123"

    def test_returns_empty_when_missing(self):
        import os
        env_backup = os.environ.pop("GEMINI_API_KEY", None)
        try:
            with patch("builtins.open", side_effect=FileNotFoundError):
                assert _load_api_key() == ""
        finally:
            if env_backup is not None:
                os.environ["GEMINI_API_KEY"] = env_backup
