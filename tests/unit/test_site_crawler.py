"""Unit tests for src/site_crawler.py — site crawling and element extraction.

Each test has a single assertion per the course requirement.
Mocks Selenium WebDriver to avoid real browser usage.
"""

from unittest.mock import patch, MagicMock, PropertyMock

import pytest

from src.site_crawler import _extract_page_info, _parse_credentials, crawl_site


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_driver():
    """Create a mock Selenium WebDriver with sample HTML."""
    driver = MagicMock()
    driver.page_source = """
    <html>
    <head><title>Test App</title></head>
    <body>
        <form action="/login" method="post">
            <input type="text" name="username" id="user" placeholder="Username"/>
            <input type="password" name="password" id="pw"/>
            <button type="submit">Sign In</button>
        </form>
        <a href="/register">Register</a>
        <a href="/about">About</a>
        <a href="#top">Top</a>
        <a href="javascript:void(0)">JS Link</a>
        <textarea name="notes" id="notes-area"></textarea>
        <select name="role" id="role-select">
            <option>Admin</option>
            <option>User</option>
        </select>
        <input type="hidden" name="csrf" value="token123"/>
    </body>
    </html>
    """
    driver.current_url = "http://testapp.com"
    driver.title = "Test App"
    return driver


# ── _extract_page_info ──────────────────────────────────────────────────


class TestExtractPageInfo:
    def test_extracts_page_url(self, mock_driver):
        info = _extract_page_info(mock_driver)
        assert info["url"] == "http://testapp.com"

    def test_extracts_page_title(self, mock_driver):
        info = _extract_page_info(mock_driver)
        assert info["title"] == "Test App"

    def test_extracts_inputs(self, mock_driver):
        info = _extract_page_info(mock_driver)
        assert len(info["inputs"]) >= 2

    def test_skips_hidden_inputs(self, mock_driver):
        info = _extract_page_info(mock_driver)
        names = [i["name"] for i in info["inputs"]]
        assert "csrf" not in names

    def test_extracts_textarea(self, mock_driver):
        info = _extract_page_info(mock_driver)
        tags = [i["tag"] for i in info["inputs"]]
        assert "textarea" in tags

    def test_extracts_select(self, mock_driver):
        info = _extract_page_info(mock_driver)
        tags = [i["tag"] for i in info["inputs"]]
        assert "select" in tags

    def test_extracts_buttons(self, mock_driver):
        info = _extract_page_info(mock_driver)
        assert any(b["text"] == "Sign In" for b in info["buttons"])

    def test_extracts_links(self, mock_driver):
        info = _extract_page_info(mock_driver)
        hrefs = [l["href"] for l in info["links"]]
        assert "/register" in hrefs

    def test_skips_hash_links(self, mock_driver):
        info = _extract_page_info(mock_driver)
        hrefs = [l["href"] for l in info["links"]]
        assert "#top" not in hrefs

    def test_skips_javascript_links(self, mock_driver):
        info = _extract_page_info(mock_driver)
        hrefs = [l["href"] for l in info["links"]]
        assert "javascript:void(0)" not in hrefs

    def test_extracts_forms(self, mock_driver):
        info = _extract_page_info(mock_driver)
        assert len(info["forms"]) >= 1

    def test_form_has_action(self, mock_driver):
        info = _extract_page_info(mock_driver)
        assert info["forms"][0]["action"] == "/login"

    def test_form_has_method(self, mock_driver):
        info = _extract_page_info(mock_driver)
        assert info["forms"][0]["method"] == "post"

    def test_form_fields_exclude_hidden(self, mock_driver):
        info = _extract_page_info(mock_driver)
        field_names = [f["name"] for f in info["forms"][0]["fields"]]
        assert "csrf" not in field_names

    def test_input_has_name(self, mock_driver):
        info = _extract_page_info(mock_driver)
        names = [i["name"] for i in info["inputs"]]
        assert "username" in names

    def test_input_has_type(self, mock_driver):
        info = _extract_page_info(mock_driver)
        types = [i["type"] for i in info["inputs"]]
        assert "password" in types


# ── _parse_credentials ──────────────────────────────────────────────────


class TestParseCredentials:
    def test_parse_credentials_empty_notes(self):
        user, pwd = _parse_credentials("")
        assert user is None

    def test_parse_credentials_none_notes(self):
        user, pwd = _parse_credentials(None)
        assert user is None

    def test_parse_credentials_username_password_format(self):
        user, pwd = _parse_credentials("username: admin, password: secret")
        assert user == "admin"

    def test_parse_credentials_password_extracted(self):
        user, pwd = _parse_credentials("username: admin, password: secret")
        assert pwd == "secret"

    def test_parse_credentials_user_pass_format(self):
        user, pwd = _parse_credentials("user=testuser pass=testpw")
        assert user == "testuser"

    def test_parse_credentials_slash_format(self):
        user, pwd = _parse_credentials("login with admin/admin123")
        assert user == "admin"

    def test_parse_credentials_slash_format_password(self):
        user, pwd = _parse_credentials("login with admin/admin123")
        assert pwd == "admin123"

    def test_parse_credentials_email_format(self):
        user, pwd = _parse_credentials("email: test@x.com password: pw123")
        assert user == "test@x.com"


# ── crawl_site (mocked) ────────────────────────────────────────────────


class TestCrawlSite:
    @staticmethod
    def _make_crawl_driver():
        """Create a properly configured mock driver for crawl_site tests."""
        driver = MagicMock()
        driver.page_source = "<html><head><title>App</title></head><body></body></html>"
        driver.current_url = "http://testapp.com"
        driver.title = "App"
        driver.execute_script.return_value = "complete"
        return driver

    def test_crawl_site_returns_dict(self):
        mock_driver = self._make_crawl_driver()
        with patch("src.site_crawler._create_driver", return_value=mock_driver):
            result = crawl_site("http://testapp.com")
            assert isinstance(result, dict)

    def test_crawl_site_has_pages_key(self):
        mock_driver = self._make_crawl_driver()
        with patch("src.site_crawler._create_driver", return_value=mock_driver):
            result = crawl_site("http://testapp.com")
            assert "pages" in result

    def test_crawl_site_has_app_url(self):
        mock_driver = self._make_crawl_driver()
        with patch("src.site_crawler._create_driver", return_value=mock_driver):
            result = crawl_site("http://testapp.com")
            assert result["app_url"] == "http://testapp.com"

    def test_crawl_site_no_error_on_success(self):
        mock_driver = self._make_crawl_driver()
        with patch("src.site_crawler._create_driver", return_value=mock_driver):
            result = crawl_site("http://testapp.com")
            assert result["error"] is None

    def test_crawl_site_passes_user_notes(self):
        mock_driver = self._make_crawl_driver()
        with patch("src.site_crawler._create_driver", return_value=mock_driver):
            result = crawl_site("http://testapp.com", user_notes="admin/admin")
            assert result["user_notes"] == "admin/admin"

    def test_crawl_site_driver_error_returns_error(self):
        from selenium.common.exceptions import WebDriverException
        mock_driver = MagicMock()
        mock_driver.get.side_effect = WebDriverException("Chrome not found")

        with patch("src.site_crawler._create_driver", return_value=mock_driver):
            result = crawl_site("http://testapp.com")
            assert result["error"] is not None

    def test_crawl_site_at_least_one_page(self):
        mock_driver = self._make_crawl_driver()
        with patch("src.site_crawler._create_driver", return_value=mock_driver):
            result = crawl_site("http://testapp.com")
            assert len(result["pages"]) >= 1

    def test_crawl_site_quits_driver(self):
        mock_driver = self._make_crawl_driver()
        with patch("src.site_crawler._create_driver", return_value=mock_driver):
            crawl_site("http://testapp.com")
            assert mock_driver.quit.called
