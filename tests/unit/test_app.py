"""Unit tests for src/app.py — Flask routes.

Each test has a single assertion per the course requirement.
Uses the client/logged_in_client fixtures from conftest.py.
"""

import pytest


# ── Index route ──────────────────────────────────────────────────────────


class TestIndex:
    def test_index_redirects_to_login(self, client):
        resp = client.get("/")
        assert resp.status_code == 302

    def test_index_redirect_location(self, client):
        resp = client.get("/", follow_redirects=False)
        assert "/login" in resp.headers["Location"]


# ── Login ────────────────────────────────────────────────────────────────


class TestLogin:
    def test_login_get_returns_200(self, client):
        resp = client.get("/login")
        assert resp.status_code == 200

    def test_login_get_contains_form(self, client):
        resp = client.get("/login")
        assert b"email" in resp.data

    def test_login_valid_credentials_redirects(self, client):
        resp = client.post("/login", data={
            "email": "test@example.com",
            "password": "password123",
        })
        assert resp.status_code == 302

    def test_login_valid_credentials_sets_session(self, client):
        client.post("/login", data={
            "email": "test@example.com",
            "password": "password123",
        })
        resp = client.get("/tests")
        assert resp.status_code == 200

    def test_login_invalid_credentials_stays_on_page(self, client):
        resp = client.post("/login", data={
            "email": "test@example.com",
            "password": "wrong",
        })
        assert resp.status_code == 200

    def test_login_invalid_credentials_shows_error(self, client):
        resp = client.post("/login", data={
            "email": "test@example.com",
            "password": "wrong",
        }, follow_redirects=True)
        assert b"Invalid email or password" in resp.data

    def test_login_empty_email(self, client):
        resp = client.post("/login", data={
            "email": "",
            "password": "password123",
        })
        assert b"Invalid email or password" in resp.data


# ── Register ─────────────────────────────────────────────────────────────


class TestRegister:
    def test_register_get_returns_200(self, client):
        resp = client.get("/register")
        assert resp.status_code == 200

    def test_register_valid_redirects(self, client):
        resp = client.post("/register", data={
            "email": "new@test.com",
            "password": "newpass123",
            "confirm_password": "newpass123",
        })
        assert resp.status_code == 302

    def test_register_password_mismatch(self, client):
        resp = client.post("/register", data={
            "email": "new@test.com",
            "password": "pass1",
            "confirm_password": "pass2",
        }, follow_redirects=True)
        assert b"Passwords do not match" in resp.data

    def test_register_short_password(self, client):
        resp = client.post("/register", data={
            "email": "new@test.com",
            "password": "abc",
            "confirm_password": "abc",
        }, follow_redirects=True)
        assert b"at least 6 characters" in resp.data

    def test_register_empty_email(self, client):
        resp = client.post("/register", data={
            "email": "",
            "password": "password123",
            "confirm_password": "password123",
        }, follow_redirects=True)
        assert b"Email and password are required" in resp.data

    def test_register_duplicate_email(self, client):
        resp = client.post("/register", data={
            "email": "test@example.com",
            "password": "password123",
            "confirm_password": "password123",
        }, follow_redirects=True)
        assert b"already exists" in resp.data


# ── Auth-protected routes redirect when not logged in ────────────────────


class TestAuthRedirects:
    def test_tests_redirects_when_not_logged_in(self, client):
        resp = client.get("/tests")
        assert resp.status_code == 302

    def test_create_test_redirects_when_not_logged_in(self, client):
        resp = client.get("/create-test")
        assert resp.status_code == 302

    def test_settings_redirects_when_not_logged_in(self, client):
        resp = client.get("/settings")
        assert resp.status_code == 302

    def test_discover_redirects_when_not_logged_in(self, client):
        resp = client.get("/discover")
        assert resp.status_code == 302

    def test_run_test_redirects_when_not_logged_in(self, client):
        resp = client.post("/run-test/1")
        assert resp.status_code == 302

    def test_test_results_redirects_when_not_logged_in(self, client):
        resp = client.get("/test-results/1")
        assert resp.status_code == 302


# ── Create Test ──────────────────────────────────────────────────────────


class TestCreateTest:
    def test_create_test_get_returns_200(self, logged_in_client):
        resp = logged_in_client.get("/create-test")
        assert resp.status_code == 200

    def test_create_test_post_redirects(self, logged_in_client):
        resp = logged_in_client.post("/create-test", data={
            "test_name": "Login Test",
            "application_url": "http://example.com",
            "steps_raw": "Go to login page\nEnter credentials",
            "expected_outcome": "Dashboard loads",
        })
        assert resp.status_code == 302

    def test_create_test_post_saves_test(self, logged_in_client):
        logged_in_client.post("/create-test", data={
            "test_name": "My Test",
            "application_url": "http://example.com",
            "steps_raw": "Step 1",
            "expected_outcome": "Pass",
        })
        resp = logged_in_client.get("/tests")
        assert b"My Test" in resp.data

    def test_create_test_flash_message(self, logged_in_client):
        resp = logged_in_client.post("/create-test", data={
            "test_name": "Flash Test",
            "application_url": "http://example.com",
            "steps_raw": "Step 1",
            "expected_outcome": "Pass",
        }, follow_redirects=True)
        assert b"Test scenario created successfully" in resp.data


# ── Test List ────────────────────────────────────────────────────────────


class TestTestList:
    def test_test_list_returns_200(self, logged_in_client):
        resp = logged_in_client.get("/tests")
        assert resp.status_code == 200

    def test_test_list_shows_test_name(self, logged_in_client):
        logged_in_client.post("/create-test", data={
            "test_name": "Visible Test",
            "application_url": "http://x.com",
            "steps_raw": "s",
            "expected_outcome": "o",
        })
        resp = logged_in_client.get("/tests")
        assert b"Visible Test" in resp.data

    def test_test_list_shows_not_run_status(self, logged_in_client):
        logged_in_client.post("/create-test", data={
            "test_name": "Status Test",
            "application_url": "http://x.com",
            "steps_raw": "s",
            "expected_outcome": "o",
        })
        resp = logged_in_client.get("/tests")
        assert b"Not Run" in resp.data


# ── Run Test (simulated) ────────────────────────────────────────────────


class TestRunTest:
    def test_run_test_redirects_to_results(self, logged_in_client):
        logged_in_client.post("/create-test", data={
            "test_name": "Run Me",
            "application_url": "http://x.com",
            "steps_raw": "Go to homepage",
            "expected_outcome": "page loads",
        })
        resp = logged_in_client.post("/run-test/1")
        assert resp.status_code == 302

    def test_run_test_nonexistent_test(self, logged_in_client):
        resp = logged_in_client.post("/run-test/9999", follow_redirects=True)
        assert b"Test not found" in resp.data

    def test_run_test_updates_status(self, logged_in_client):
        logged_in_client.post("/create-test", data={
            "test_name": "Status Update",
            "application_url": "http://x.com",
            "steps_raw": "Go to homepage",
            "expected_outcome": "page loads",
        })
        logged_in_client.post("/run-test/1")
        resp = logged_in_client.get("/tests")
        assert b"Passed" in resp.data

    def test_run_test_failing_test(self, logged_in_client):
        logged_in_client.post("/create-test", data={
            "test_name": "Fail Test",
            "application_url": "http://x.com",
            "steps_raw": "Try payment",
            "expected_outcome": "payment timeout",
        })
        logged_in_client.post("/run-test/1")
        resp = logged_in_client.get("/tests")
        assert b"Failed" in resp.data


# ── Test Results ─────────────────────────────────────────────────────────


class TestTestResults:
    def test_test_results_returns_200(self, logged_in_client):
        logged_in_client.post("/create-test", data={
            "test_name": "Results Test",
            "application_url": "http://x.com",
            "steps_raw": "Go to homepage",
            "expected_outcome": "page loads",
        })
        logged_in_client.post("/run-test/1")
        resp = logged_in_client.get("/test-results/1")
        assert resp.status_code == 200

    def test_test_results_nonexistent(self, logged_in_client):
        resp = logged_in_client.get("/test-results/9999", follow_redirects=True)
        assert b"Test not found" in resp.data


# ── Edit Test ────────────────────────────────────────────────────────────


class TestEditTest:
    def test_edit_test_get_returns_200(self, logged_in_client):
        logged_in_client.post("/create-test", data={
            "test_name": "Edit Me",
            "application_url": "http://x.com",
            "steps_raw": "s",
            "expected_outcome": "o",
        })
        resp = logged_in_client.get("/edit-test/1")
        assert resp.status_code == 200

    def test_edit_test_post_updates_name(self, logged_in_client):
        logged_in_client.post("/create-test", data={
            "test_name": "Old Name",
            "application_url": "http://x.com",
            "steps_raw": "s",
            "expected_outcome": "o",
        })
        logged_in_client.post("/edit-test/1", data={
            "test_name": "New Name",
            "application_url": "http://x.com",
            "steps_raw": "s",
            "expected_outcome": "o",
        })
        resp = logged_in_client.get("/tests")
        assert b"New Name" in resp.data

    def test_edit_test_nonexistent(self, logged_in_client):
        resp = logged_in_client.get("/edit-test/9999", follow_redirects=True)
        assert b"Test not found" in resp.data

    def test_edit_test_post_nonexistent(self, logged_in_client):
        resp = logged_in_client.post("/edit-test/9999", data={
            "test_name": "X",
            "application_url": "http://x",
            "steps_raw": "s",
            "expected_outcome": "o",
        }, follow_redirects=True)
        assert b"Test not found" in resp.data


# ── Apply Fix ────────────────────────────────────────────────────────────


class TestApplyFix:
    def test_apply_fix_updates_steps(self, logged_in_client):
        logged_in_client.post("/create-test", data={
            "test_name": "Fix Me",
            "application_url": "http://x.com",
            "steps_raw": "old step",
            "expected_outcome": "o",
        })
        logged_in_client.post("/apply-fix/1", data={
            "proposed_steps": "new step",
        })
        resp = logged_in_client.get("/edit-test/1")
        assert b"new step" in resp.data

    def test_apply_fix_resets_status(self, logged_in_client):
        logged_in_client.post("/create-test", data={
            "test_name": "Fix Status",
            "application_url": "http://x.com",
            "steps_raw": "Go to homepage",
            "expected_outcome": "page loads",
        })
        logged_in_client.post("/run-test/1")
        logged_in_client.post("/apply-fix/1", data={
            "proposed_steps": "new step",
        })
        resp = logged_in_client.get("/tests")
        assert b"Not Run" in resp.data

    def test_apply_fix_empty_proposed_steps(self, logged_in_client):
        logged_in_client.post("/create-test", data={
            "test_name": "No Fix",
            "application_url": "http://x.com",
            "steps_raw": "s",
            "expected_outcome": "o",
        })
        resp = logged_in_client.post("/apply-fix/1", data={
            "proposed_steps": "",
        }, follow_redirects=True)
        assert b"No proposed fix available" in resp.data

    def test_apply_fix_nonexistent_test(self, logged_in_client):
        resp = logged_in_client.post("/apply-fix/9999", data={
            "proposed_steps": "step",
        }, follow_redirects=True)
        assert b"Test not found" in resp.data


# ── Run All Tests ────────────────────────────────────────────────────────


class TestRunAllTests:
    def test_run_all_tests_no_tests(self, logged_in_client):
        resp = logged_in_client.post("/run-all-tests", follow_redirects=True)
        assert b"No tests to run" in resp.data

    def test_run_all_tests_with_tests(self, logged_in_client):
        logged_in_client.post("/create-test", data={
            "test_name": "T1",
            "application_url": "http://x.com",
            "steps_raw": "Go to homepage",
            "expected_outcome": "page loads",
        })
        resp = logged_in_client.post("/run-all-tests", follow_redirects=True)
        assert b"All tests executed" in resp.data

    def test_run_all_tests_counts_passed(self, logged_in_client):
        logged_in_client.post("/create-test", data={
            "test_name": "Pass1",
            "application_url": "http://x.com",
            "steps_raw": "Go to homepage",
            "expected_outcome": "page loads",
        })
        resp = logged_in_client.post("/run-all-tests", follow_redirects=True)
        assert b"1 passed" in resp.data


# ── Settings ─────────────────────────────────────────────────────────────


class TestSettings:
    def test_settings_get_returns_200(self, logged_in_client):
        resp = logged_in_client.get("/settings")
        assert resp.status_code == 200

    def test_settings_save_email(self, logged_in_client):
        resp = logged_in_client.post("/settings", data={
            "action": "save_settings",
            "report_email": "report@test.com",
        }, follow_redirects=True)
        assert b"Settings saved successfully" in resp.data

    def test_settings_add_app(self, logged_in_client):
        resp = logged_in_client.post("/settings", data={
            "action": "add_app",
            "app_name": "TestApp",
            "app_url": "http://testapp.com",
            "auth_type": "none",
            "app_username": "",
            "app_password": "",
            "app_token": "",
        }, follow_redirects=True)
        assert b"TestApp" in resp.data

    def test_settings_add_app_missing_fields(self, logged_in_client):
        resp = logged_in_client.post("/settings", data={
            "action": "add_app",
            "app_name": "",
            "app_url": "",
            "auth_type": "none",
        }, follow_redirects=True)
        assert b"Name and URL are required" in resp.data

    def test_settings_delete_app(self, logged_in_client):
        from src.db import insert_saved_app
        aid = insert_saved_app("Del", "http://del", "none")
        resp = logged_in_client.post("/settings", data={
            "action": "delete_app",
            "app_id": str(aid),
        }, follow_redirects=True)
        assert b"Application removed" in resp.data

    def test_settings_update_app(self, logged_in_client):
        from src.db import insert_saved_app
        aid = insert_saved_app("Old", "http://old", "none")
        resp = logged_in_client.post("/settings", data={
            "action": "update_app",
            "app_id": str(aid),
            "app_name": "Updated",
            "app_url": "http://updated",
            "auth_type": "none",
            "app_username": "",
            "app_password": "",
            "app_token": "",
        }, follow_redirects=True)
        assert b"Updated" in resp.data


# ── Discover ─────────────────────────────────────────────────────────────


class TestDiscover:
    def test_discover_get_returns_200(self, logged_in_client):
        resp = logged_in_client.get("/discover")
        assert resp.status_code == 200

    def test_discover_post_empty_url(self, logged_in_client):
        resp = logged_in_client.post("/discover", data={
            "app_url": "",
        }, follow_redirects=True)
        assert b"Please enter a URL" in resp.data


# ── Save Discovered ─────────────────────────────────────────────────────


class TestSaveDiscovered:
    def test_save_discovered_redirects(self, logged_in_client):
        resp = logged_in_client.post("/save-discovered", data={
            "app_url": "http://x.com",
            "total": "1",
            "selected": ["0"],
            "name_0": "Test 1",
            "steps_0": "Go to page",
            "outcome_0": "Page loads",
        })
        assert resp.status_code == 302

    def test_save_discovered_saves_scenario(self, logged_in_client):
        logged_in_client.post("/save-discovered", data={
            "app_url": "http://x.com",
            "total": "1",
            "selected": ["0"],
            "name_0": "Saved Scenario",
            "steps_0": "Go to page",
            "outcome_0": "Page loads",
        })
        resp = logged_in_client.get("/tests")
        assert b"Saved Scenario" in resp.data

    def test_save_discovered_flash_message(self, logged_in_client):
        resp = logged_in_client.post("/save-discovered", data={
            "app_url": "http://x.com",
            "total": "1",
            "selected": ["0"],
            "name_0": "Flash Scenario",
            "steps_0": "Step",
            "outcome_0": "Out",
        }, follow_redirects=True)
        assert b"saved successfully" in resp.data

    def test_save_discovered_none_selected(self, logged_in_client):
        resp = logged_in_client.post("/save-discovered", data={
            "app_url": "http://x.com",
            "total": "1",
        }, follow_redirects=True)
        assert b"0 test scenarios saved" in resp.data
