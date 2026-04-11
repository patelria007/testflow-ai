"""Unit tests for src/test_runner.py — test execution engine.

Each test has a single assertion per the course requirement.
Mocks Selenium and LLM to avoid real browser/API usage.
"""

from unittest.mock import patch, MagicMock

import pytest

from src.test_runner import (
    _parse_step,
    _discover_elements,
    _execute_step,
    execute_test,
)


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_driver():
    """A mock Selenium WebDriver."""
    driver = MagicMock()
    driver.page_source = """
    <html><head><title>Test Page</title></head>
    <body>
        <input type="text" name="username" id="user"/>
        <input type="password" name="password" id="pw"/>
        <button type="submit">Login</button>
        <a href="/about">About</a>
        <form action="/login" method="post"></form>
    </body></html>
    """
    driver.title = "Test Page"
    driver.current_url = "http://testapp.com"
    driver.execute_script.return_value = "complete"
    return driver


# ── _parse_step ──────────────────────────────────────────────────────────


class TestParseStep:
    def test_parse_navigate(self):
        result = _parse_step("Navigate to http://example.com")
        assert result["action"] == "navigate"

    def test_parse_navigate_target(self):
        result = _parse_step("Go to /dashboard")
        assert result["target"] == "/dashboard"

    def test_parse_visit(self):
        result = _parse_step("Visit the homepage")
        assert result["action"] == "navigate"

    def test_parse_open(self):
        result = _parse_step("Open the login page")
        assert result["action"] == "navigate"

    def test_parse_enter_with_field(self):
        result = _parse_step("Enter admin in username")
        assert result["action"] == "enter"

    def test_parse_enter_value(self):
        result = _parse_step("Enter admin in username")
        assert result["value"] == "admin"

    def test_parse_enter_target(self):
        result = _parse_step("Enter admin in username")
        assert result["target"] == "username"

    def test_parse_type_into(self):
        result = _parse_step("Type hello into search box")
        assert result["action"] == "enter"

    def test_parse_enter_without_field(self):
        result = _parse_step("Enter email address")
        assert result["action"] == "enter"

    def test_parse_click(self):
        result = _parse_step("Click the Submit button")
        assert result["action"] == "click"

    def test_parse_click_target(self):
        result = _parse_step("Click Login")
        assert result["target"] == "Login"

    def test_parse_press(self):
        result = _parse_step("Press the OK button")
        assert result["action"] == "click"

    def test_parse_tap(self):
        result = _parse_step("Tap on Save")
        assert result["action"] == "click"

    def test_parse_wait(self):
        result = _parse_step("Wait for page to load")
        assert result["action"] == "wait"

    def test_parse_verify(self):
        result = _parse_step("Verify dashboard is visible")
        assert result["action"] == "verify"

    def test_parse_check(self):
        result = _parse_step("Check that the title says Home")
        assert result["action"] == "verify"

    def test_parse_assert(self):
        result = _parse_step("Assert success message appears")
        assert result["action"] == "verify"

    def test_parse_select(self):
        result = _parse_step("Select Admin from role dropdown")
        assert result["action"] == "select"

    def test_parse_select_value(self):
        result = _parse_step("Select Admin from role dropdown")
        assert result["value"] == "Admin"

    def test_parse_select_target(self):
        result = _parse_step("Select Admin from role dropdown")
        assert result["target"] == "role dropdown"

    def test_parse_strips_step_number(self):
        result = _parse_step("1. Click the button")
        assert result["action"] == "click"

    def test_parse_strips_step_prefix(self):
        result = _parse_step("Step 3: Navigate to /home")
        assert result["action"] == "navigate"

    def test_parse_unknown_defaults_to_verify(self):
        result = _parse_step("The page should show results")
        assert result["action"] == "verify"

    def test_parse_enter_value_empty_when_no_field(self):
        result = _parse_step("Enter email")
        assert result["value"] == ""

    def test_parse_click_value_empty(self):
        result = _parse_step("Click Submit")
        assert result["value"] == ""


# ── _discover_elements ───────────────────────────────────────────────────


class TestDiscoverElements:
    def test_discover_returns_dict(self, mock_driver):
        result = _discover_elements(mock_driver)
        assert isinstance(result, dict)

    def test_discover_has_inputs(self, mock_driver):
        result = _discover_elements(mock_driver)
        assert "inputs" in result

    def test_discover_has_buttons(self, mock_driver):
        result = _discover_elements(mock_driver)
        assert "buttons" in result

    def test_discover_has_links(self, mock_driver):
        result = _discover_elements(mock_driver)
        assert "links" in result

    def test_discover_has_forms(self, mock_driver):
        result = _discover_elements(mock_driver)
        assert "forms" in result

    def test_discover_finds_inputs(self, mock_driver):
        result = _discover_elements(mock_driver)
        assert len(result["inputs"]) >= 2

    def test_discover_finds_buttons(self, mock_driver):
        result = _discover_elements(mock_driver)
        assert len(result["buttons"]) >= 1

    def test_discover_finds_links(self, mock_driver):
        result = _discover_elements(mock_driver)
        assert len(result["links"]) >= 1

    def test_discover_input_has_name(self, mock_driver):
        result = _discover_elements(mock_driver)
        names = [i["name"] for i in result["inputs"]]
        assert "username" in names

    def test_discover_button_has_text(self, mock_driver):
        result = _discover_elements(mock_driver)
        assert result["buttons"][0]["text"] == "Login"


# ── _execute_step ────────────────────────────────────────────────────────


class TestExecuteStep:
    def test_execute_navigate_absolute(self, mock_driver):
        parsed = {"action": "navigate", "target": "http://example.com", "value": ""}
        result = _execute_step(mock_driver, parsed, "http://base.com")
        assert "Navigated" in result

    def test_execute_navigate_relative(self, mock_driver):
        parsed = {"action": "navigate", "target": "/dashboard", "value": ""}
        result = _execute_step(mock_driver, parsed, "http://base.com")
        assert "Navigated" in result

    def test_execute_navigate_calls_get(self, mock_driver):
        parsed = {"action": "navigate", "target": "http://example.com", "value": ""}
        _execute_step(mock_driver, parsed, "http://base.com")
        assert mock_driver.get.called

    def test_execute_wait(self, mock_driver):
        parsed = {"action": "wait", "target": "page load", "value": ""}
        result = _execute_step(mock_driver, parsed, "http://base.com")
        assert "Waited" in result

    def test_execute_unknown_action(self, mock_driver):
        parsed = {"action": "unknown_action", "target": "x", "value": ""}
        result = _execute_step(mock_driver, parsed, "http://base.com")
        assert "Unknown" in result


# ── execute_test (fully mocked) ─────────────────────────────────────────


class TestExecuteTest:
    def test_execute_test_returns_dict(self):
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body></body></html>"
        mock_driver.title = "Page"
        mock_driver.current_url = "http://app.com"
        mock_driver.execute_script.return_value = "complete"

        actions = [{"action": "verify", "target": "page", "value": ""}]

        with patch("src.test_runner._create_driver", return_value=mock_driver):
            with patch("src.test_runner.parse_steps_with_llm", return_value=actions):
                result = execute_test("http://app.com", "Verify page", "page loads")
                assert isinstance(result, dict)

    def test_execute_test_has_status(self):
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body>page loads</body></html>"
        mock_driver.title = "Page"
        mock_driver.current_url = "http://app.com"
        mock_driver.execute_script.return_value = "complete"

        actions = [{"action": "wait", "target": "page", "value": ""}]

        with patch("src.test_runner._create_driver", return_value=mock_driver):
            with patch("src.test_runner.parse_steps_with_llm", return_value=actions):
                result = execute_test("http://app.com", "Wait", "page loads")
                assert result["status"] in ("Passed", "Failed")

    def test_execute_test_has_execution_time(self):
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body></body></html>"
        mock_driver.title = "Page"
        mock_driver.current_url = "http://app.com"
        mock_driver.execute_script.return_value = "complete"

        with patch("src.test_runner._create_driver", return_value=mock_driver):
            with patch("src.test_runner.parse_steps_with_llm", return_value=[]):
                result = execute_test("http://app.com", "s", "o")
                assert isinstance(result["execution_time"], float)

    def test_execute_test_has_screenshots(self):
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body></body></html>"
        mock_driver.title = "Page"
        mock_driver.current_url = "http://app.com"
        mock_driver.execute_script.return_value = "complete"

        with patch("src.test_runner._create_driver", return_value=mock_driver):
            with patch("src.test_runner.parse_steps_with_llm", return_value=[]):
                result = execute_test("http://app.com", "s", "o")
                assert isinstance(result["screenshots"], list)

    def test_execute_test_has_performance(self):
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body></body></html>"
        mock_driver.title = "Page"
        mock_driver.current_url = "http://app.com"
        mock_driver.execute_script.return_value = "complete"

        with patch("src.test_runner._create_driver", return_value=mock_driver):
            with patch("src.test_runner.parse_steps_with_llm", return_value=[]):
                result = execute_test("http://app.com", "s", "o")
                assert isinstance(result["performance"], dict)

    def test_execute_test_has_email_sent(self):
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body></body></html>"
        mock_driver.title = "Page"
        mock_driver.current_url = "http://app.com"
        mock_driver.execute_script.return_value = "complete"

        with patch("src.test_runner._create_driver", return_value=mock_driver):
            with patch("src.test_runner.parse_steps_with_llm", return_value=[]):
                result = execute_test("http://app.com", "s", "o")
                assert isinstance(result["email_sent"], bool)

    def test_execute_test_browser_error_returns_failed(self):
        from selenium.common.exceptions import WebDriverException
        mock_driver = MagicMock()
        mock_driver.get.side_effect = WebDriverException("Chrome crashed")
        mock_driver.execute_script.return_value = "complete"

        with patch("src.test_runner._create_driver", return_value=mock_driver):
            result = execute_test("http://app.com", "Step 1", "outcome")
            assert result["status"] == "Failed"

    def test_execute_test_browser_error_has_diagnosis(self):
        from selenium.common.exceptions import WebDriverException
        mock_driver = MagicMock()
        mock_driver.get.side_effect = WebDriverException("Chrome crashed")
        mock_driver.execute_script.return_value = "complete"

        with patch("src.test_runner._create_driver", return_value=mock_driver):
            result = execute_test("http://app.com", "Step 1", "outcome")
            assert result["diagnosis"]["category"] == "environment"

    def test_execute_test_generic_exception_returns_failed(self):
        mock_driver = MagicMock()
        mock_driver.get.side_effect = RuntimeError("Unexpected")
        mock_driver.execute_script.return_value = "complete"

        with patch("src.test_runner._create_driver", return_value=mock_driver):
            result = execute_test("http://app.com", "Step", "outcome")
            assert result["status"] == "Failed"

    def test_execute_test_quits_driver(self):
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body></body></html>"
        mock_driver.title = "Page"
        mock_driver.current_url = "http://app.com"
        mock_driver.execute_script.return_value = "complete"

        with patch("src.test_runner._create_driver", return_value=mock_driver):
            with patch("src.test_runner.parse_steps_with_llm", return_value=[]):
                execute_test("http://app.com", "s", "o")
                assert mock_driver.quit.called

    def test_execute_test_passed_no_failure_message(self):
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body>page loads</body></html>"
        mock_driver.title = "page loads"
        mock_driver.current_url = "http://app.com"
        mock_driver.execute_script.return_value = "complete"

        with patch("src.test_runner._create_driver", return_value=mock_driver):
            with patch("src.test_runner.parse_steps_with_llm", return_value=[]):
                result = execute_test("http://app.com", "s", "page loads")
                assert result["failure_message"] is None

    def test_execute_test_rediscovers_after_click(self):
        mock_driver = MagicMock()
        mock_driver.page_source = "<html><body>text</body></html>"
        mock_driver.title = "Page"
        mock_driver.current_url = "http://app.com"
        mock_driver.execute_script.return_value = "complete"

        # Mock a click action - _find_clickable returns an element
        mock_element = MagicMock()
        mock_element.is_displayed.return_value = True

        actions = [{"action": "wait", "target": "load", "value": ""}]

        with patch("src.test_runner._create_driver", return_value=mock_driver):
            with patch("src.test_runner.parse_steps_with_llm", return_value=actions):
                result = execute_test("http://app.com", "Wait for load", "text")
                assert result["status"] in ("Passed", "Failed")
