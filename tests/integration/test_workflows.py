"""Integration tests for TestFlow AI workflows.

These tests exercise multiple components working together: Flask routes,
SQLite database, and application logic. External services (Gemini API,
Selenium) are mocked, but the database uses real SQLite (temporary files).
"""

import json
import os
import tempfile

import pytest

from src.app import create_app
from src import db as db_module


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _isolate_db(tmp_path, monkeypatch):
    """Give every test its own temporary SQLite database.

    Patches db_module.DB_PATH so all db helpers (get_connection, init_db, etc.)
    operate on a fresh file.  The Flask app factory calls init_db() which
    creates the schema and seeds the default user.
    """
    db_file = str(tmp_path / "test_testflow.db")
    monkeypatch.setattr(db_module, "DB_PATH", db_file)
    # Also ensure simulation mode is on so run-test never tries real Selenium
    monkeypatch.setenv("TESTFLOW_SIMULATE", "1")


@pytest.fixture()
def app():
    """Create a fresh Flask application for testing."""
    application = create_app()
    application.config["TESTING"] = True
    return application


@pytest.fixture()
def client(app):
    """Flask test client with a server-side session."""
    return app.test_client()


def _login(client, email="test@example.com", password="password123"):
    """Helper: log in via POST /login and return the response."""
    return client.post("/login", data={
        "email": email,
        "password": password,
    }, follow_redirects=True)


def _create_test_scenario(client, name="Login Test", url="http://example.com",
                          steps="Navigate to /login\nEnter email\nClick submit",
                          outcome="User sees dashboard"):
    """Helper: POST /create-test and return the response."""
    return client.post("/create-test", data={
        "test_name": name,
        "application_url": url,
        "steps_raw": steps,
        "expected_outcome": outcome,
    }, follow_redirects=True)


# ---------------------------------------------------------------------------
# 1. User registration + login flow
# ---------------------------------------------------------------------------

class TestRegistrationAndLoginFlow:
    """Register a new user, then authenticate and access protected routes."""

    def test_register_then_login_and_access_tests(self, client):
        # Register a brand-new user
        resp = client.post("/register", data={
            "email": "newuser@test.com",
            "password": "secret99",
            "confirm_password": "secret99",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Account created successfully" in resp.data

        # Log in with the new credentials
        resp = _login(client, "newuser@test.com", "secret99")
        assert resp.status_code == 200
        # After login we are redirected to /tests which shows the test list
        assert b"Tests" in resp.data or b"test" in resp.data.lower()

        # Verify session lets us access a protected page
        resp = client.get("/create-test")
        assert resp.status_code == 200
        assert b"Create Test" in resp.data

    def test_register_duplicate_email_rejected(self, client):
        # The default seeded user is test@example.com
        resp = client.post("/register", data={
            "email": "test@example.com",
            "password": "anything123",
            "confirm_password": "anything123",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"already exists" in resp.data

    def test_register_password_mismatch(self, client):
        resp = client.post("/register", data={
            "email": "mismatch@test.com",
            "password": "abcdef",
            "confirm_password": "ghijkl",
        }, follow_redirects=True)
        assert b"Passwords do not match" in resp.data

    def test_register_short_password(self, client):
        resp = client.post("/register", data={
            "email": "short@test.com",
            "password": "abc",
            "confirm_password": "abc",
        }, follow_redirects=True)
        assert b"at least 6 characters" in resp.data

    def test_login_wrong_password_shows_error(self, client):
        resp = _login(client, "test@example.com", "wrongpassword")
        assert resp.status_code == 200
        assert b"Invalid email or password" in resp.data

    def test_unauthenticated_redirects_to_login(self, client):
        for path in ("/tests", "/create-test", "/settings"):
            resp = client.get(path)
            assert resp.status_code == 302
            assert "/login" in resp.headers["Location"]


# ---------------------------------------------------------------------------
# 2. Test creation + retrieval workflow
# ---------------------------------------------------------------------------

class TestCreationAndRetrievalWorkflow:
    """Create a test scenario via the web UI and verify it persists."""

    def test_create_test_appears_in_list_and_db(self, client):
        _login(client)

        # Create a test scenario
        resp = _create_test_scenario(
            client,
            name="Checkout Flow",
            url="http://shop.example.com",
            steps="Navigate to /products\nAdd item to cart\nClick checkout",
            outcome="Order confirmation page",
        )
        assert resp.status_code == 200
        assert b"Test scenario created successfully" in resp.data

        # The redirect lands on /tests — verify the new test appears
        assert b"Checkout Flow" in resp.data

        # Also verify via the database directly
        tests = db_module.get_all_tests()
        assert len(tests) == 1
        assert tests[0]["name"] == "Checkout Flow"
        assert tests[0]["status"] == "Not Run"
        assert tests[0]["application_url"] == "http://shop.example.com"

    def test_create_multiple_tests_listed_in_order(self, client):
        _login(client)
        _create_test_scenario(client, name="Test Alpha")
        _create_test_scenario(client, name="Test Beta")
        _create_test_scenario(client, name="Test Gamma")

        resp = client.get("/tests")
        body = resp.data.decode()
        assert "Test Alpha" in body
        assert "Test Beta" in body
        assert "Test Gamma" in body

        tests = db_module.get_all_tests()
        assert len(tests) == 3
        assert tests[0]["name"] == "Test Alpha"
        assert tests[2]["name"] == "Test Gamma"


# ---------------------------------------------------------------------------
# 3. Test execution + results workflow (simulation mode)
# ---------------------------------------------------------------------------

class TestExecutionAndResultsWorkflow:
    """Create a test, run it in simulation mode, verify results are stored."""

    def test_passing_test_execution(self, client):
        _login(client)
        _create_test_scenario(
            client,
            name="Simple Pass Test",
            url="http://app.example.com",
            steps="Navigate to homepage\nClick login\nEnter credentials",
            outcome="User sees dashboard",
        )

        test = db_module.get_all_tests()[0]

        # Run the test
        resp = client.post(f"/run-test/{test['id']}", follow_redirects=True)
        assert resp.status_code == 200

        # Verify results page content
        body = resp.data.decode()
        assert "Passed" in body
        assert "Execution Time" in body

        # Verify database state
        run = db_module.get_latest_test_run(test["id"])
        assert run is not None
        assert run["status"] == "Passed"
        assert run["execution_time"] > 0
        assert run["failure_message"] is None
        assert isinstance(run["screenshots"], list)
        assert len(run["screenshots"]) > 0
        assert isinstance(run["performance"], dict)

        # Test status should be updated
        updated_test = db_module.get_test_by_id(test["id"])
        assert updated_test["status"] == "Passed"

    def test_failing_test_execution_with_diagnosis(self, client):
        _login(client)
        # The simulate logic triggers failure when expected_outcome contains "payment"
        _create_test_scenario(
            client,
            name="Payment Timeout Test",
            url="http://shop.example.com",
            steps="Navigate to /checkout\nEnter card details\nClick Pay Now",
            outcome="Payment confirmation displayed",
        )

        test = db_module.get_all_tests()[0]
        resp = client.post(f"/run-test/{test['id']}", follow_redirects=True)
        assert resp.status_code == 200

        body = resp.data.decode()
        assert "Failed" in body
        assert "Payment API timeout" in body

        run = db_module.get_latest_test_run(test["id"])
        assert run["status"] == "Failed"
        assert "Payment API timeout" in run["failure_message"]
        assert run["diagnosis"] is not None
        assert run["diagnosis"]["category"] == "application_bug"
        assert run["email_sent"] == 1

    def test_environment_failure_execution(self, client):
        _login(client)
        # expected_outcome containing "connection" triggers environment failure path
        _create_test_scenario(
            client,
            name="Network Failure Test",
            url="http://unreachable.example.com",
            steps="Navigate to homepage",
            outcome="Connection established",
        )

        test = db_module.get_all_tests()[0]
        resp = client.post(f"/run-test/{test['id']}", follow_redirects=True)
        assert resp.status_code == 200

        run = db_module.get_latest_test_run(test["id"])
        assert run["status"] == "Failed"
        assert run["diagnosis"]["category"] == "environment"
        assert "Connection refused" in run["failure_message"]

    def test_test_design_failure_execution(self, client):
        _login(client)
        # expected_outcome containing "element" triggers test_design failure
        _create_test_scenario(
            client,
            name="Bad Selector Test",
            url="http://app.example.com",
            steps="Navigate to /page\nClick nonexistent button",
            outcome="Element found successfully",
        )

        test = db_module.get_all_tests()[0]
        client.post(f"/run-test/{test['id']}", follow_redirects=True)

        run = db_module.get_latest_test_run(test["id"])
        assert run["status"] == "Failed"
        assert run["diagnosis"]["category"] == "test_design"
        assert "proposed_fix" in run["diagnosis"]

    def test_run_nonexistent_test_flashes_error(self, client):
        _login(client)
        resp = client.post("/run-test/9999", follow_redirects=True)
        assert resp.status_code == 200
        assert b"Test not found" in resp.data

    def test_results_page_for_unrun_test(self, client):
        _login(client)
        _create_test_scenario(client, name="Unrun Test")
        test = db_module.get_all_tests()[0]

        resp = client.get(f"/test-results/{test['id']}")
        assert resp.status_code == 200
        assert b"No execution results yet" in resp.data


# ---------------------------------------------------------------------------
# 4. Settings workflow
# ---------------------------------------------------------------------------

class TestSettingsWorkflow:
    """Login, update settings, verify persistence."""

    def test_save_and_retrieve_email_setting(self, client):
        _login(client)

        # Save a report email
        resp = client.post("/settings", data={
            "action": "save_settings",
            "report_email": "team@company.com",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Settings saved successfully" in resp.data

        # Verify it is persisted in the database
        assert db_module.get_setting("report_email") == "team@company.com"

        # Verify the settings page renders with the saved value
        resp = client.get("/settings")
        assert b"team@company.com" in resp.data

    def test_update_email_setting_overwrites(self, client):
        _login(client)

        client.post("/settings", data={
            "action": "save_settings",
            "report_email": "first@test.com",
        }, follow_redirects=True)

        client.post("/settings", data={
            "action": "save_settings",
            "report_email": "second@test.com",
        }, follow_redirects=True)

        assert db_module.get_setting("report_email") == "second@test.com"


# ---------------------------------------------------------------------------
# 5. Failure diagnosis integration (end-to-end via route)
# ---------------------------------------------------------------------------

class TestFailureDiagnosisIntegration:
    """Create a failing test, verify diagnosis is rendered on the results page."""

    def test_diagnosis_renders_on_results_page(self, client):
        _login(client)
        _create_test_scenario(
            client,
            name="Diagnosis Render Test",
            url="http://app.example.com",
            steps="Navigate to /checkout\nEnter card\nClick pay",
            outcome="Payment success shown",
        )

        test = db_module.get_all_tests()[0]
        client.post(f"/run-test/{test['id']}", follow_redirects=True)

        # Fetch the results page directly
        resp = client.get(f"/test-results/{test['id']}")
        body = resp.data.decode()

        assert "AI Diagnosis" in body
        assert "Application Bug" in body
        assert "Payment API timeout" in body
        assert "Recommendation" in body

    def test_passing_test_has_no_diagnosis(self, client):
        _login(client)
        _create_test_scenario(
            client,
            name="Happy Path",
            url="http://app.example.com",
            steps="Navigate to /home\nVerify page loads",
            outcome="Homepage displayed",
        )

        test = db_module.get_all_tests()[0]
        client.post(f"/run-test/{test['id']}", follow_redirects=True)

        resp = client.get(f"/test-results/{test['id']}")
        body = resp.data.decode()

        assert "Passed" in body
        # No failure section should be present
        assert "AI Diagnosis" not in body
        assert "Failure Details" not in body


# ---------------------------------------------------------------------------
# 6. Saved applications workflow
# ---------------------------------------------------------------------------

class TestSavedApplicationsWorkflow:
    """Add, view, and delete saved applications via settings."""

    def test_add_saved_app_appears_in_settings_and_create_test(self, client):
        _login(client)

        # Add a saved app
        resp = client.post("/settings", data={
            "action": "add_app",
            "app_name": "My Kanboard",
            "app_url": "http://localhost:8080",
            "auth_type": "credentials",
            "app_username": "admin",
            "app_password": "admin123",
            "app_token": "",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"My Kanboard" in resp.data

        # Verify DB state
        apps = db_module.get_all_saved_apps()
        assert len(apps) == 1
        assert apps[0]["name"] == "My Kanboard"
        assert apps[0]["auth_type"] == "credentials"
        assert apps[0]["username"] == "admin"

        # Verify the saved app appears in the create-test dropdown
        resp = client.get("/create-test")
        body = resp.data.decode()
        assert "My Kanboard" in body
        assert "http://localhost:8080" in body

    def test_delete_saved_app(self, client):
        _login(client)

        # Add then delete
        client.post("/settings", data={
            "action": "add_app",
            "app_name": "Temp App",
            "app_url": "http://tmp.example.com",
            "auth_type": "none",
        }, follow_redirects=True)

        apps = db_module.get_all_saved_apps()
        assert len(apps) == 1
        app_id = apps[0]["id"]

        resp = client.post("/settings", data={
            "action": "delete_app",
            "app_id": str(app_id),
        }, follow_redirects=True)
        assert b"Application removed" in resp.data
        assert len(db_module.get_all_saved_apps()) == 0

    def test_add_app_missing_fields_shows_error(self, client):
        _login(client)
        resp = client.post("/settings", data={
            "action": "add_app",
            "app_name": "",
            "app_url": "",
            "auth_type": "none",
        }, follow_redirects=True)
        assert b"Name and URL are required" in resp.data


# ---------------------------------------------------------------------------
# 7. Apply fix workflow
# ---------------------------------------------------------------------------

class TestApplyFixWorkflow:
    """Create a failing test with a diagnosis, apply the suggested fix."""

    def test_apply_fix_updates_test_steps_and_resets_status(self, client):
        _login(client)
        # Create a test that will produce a test_design failure with proposed_fix
        _create_test_scenario(
            client,
            name="Fix Me Test",
            url="http://app.example.com",
            steps="Navigate to /old-page\nClick broken selector",
            outcome="Element not found on page",
        )

        test = db_module.get_all_tests()[0]
        # Run it to produce the diagnosis
        client.post(f"/run-test/{test['id']}", follow_redirects=True)

        run = db_module.get_latest_test_run(test["id"])
        assert run["diagnosis"]["category"] == "test_design"
        proposed = run["diagnosis"]["proposed_fix"]
        assert proposed  # not empty

        # Apply the fix
        resp = client.post(f"/apply-fix/{test['id']}", data={
            "proposed_steps": proposed,
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Test steps updated with AI suggestion" in resp.data

        # Verify DB: steps changed, status reset
        updated = db_module.get_test_by_id(test["id"])
        assert updated["steps_raw"] == proposed
        assert updated["status"] == "Not Run"

    def test_apply_fix_nonexistent_test(self, client):
        _login(client)
        resp = client.post("/apply-fix/9999", data={
            "proposed_steps": "new steps",
        }, follow_redirects=True)
        assert b"Test not found" in resp.data

    def test_apply_fix_empty_steps_shows_error(self, client):
        _login(client)
        _create_test_scenario(client, name="No Fix Test")
        test = db_module.get_all_tests()[0]

        resp = client.post(f"/apply-fix/{test['id']}", data={
            "proposed_steps": "",
        }, follow_redirects=True)
        assert b"No proposed fix available" in resp.data


# ---------------------------------------------------------------------------
# 8. Edit test workflow
# ---------------------------------------------------------------------------

class TestEditTestWorkflow:
    """Edit an existing test scenario and verify changes persist."""

    def test_edit_test_updates_all_fields(self, client):
        _login(client)
        _create_test_scenario(client, name="Original Name")
        test = db_module.get_all_tests()[0]

        # GET the edit page
        resp = client.get(f"/edit-test/{test['id']}")
        assert resp.status_code == 200
        assert b"Original Name" in resp.data

        # POST the update
        resp = client.post(f"/edit-test/{test['id']}", data={
            "test_name": "Updated Name",
            "application_url": "http://new-url.com",
            "steps_raw": "Step 1 new\nStep 2 new",
            "expected_outcome": "New outcome",
        }, follow_redirects=True)
        assert resp.status_code == 200
        assert b"Test scenario updated successfully" in resp.data

        updated = db_module.get_test_by_id(test["id"])
        assert updated["name"] == "Updated Name"
        assert updated["application_url"] == "http://new-url.com"
        assert "Step 1 new" in updated["steps_raw"]
        assert updated["expected_outcome"] == "New outcome"


# ---------------------------------------------------------------------------
# 9. Run all tests workflow
# ---------------------------------------------------------------------------

class TestRunAllTestsWorkflow:
    """Run all tests sequentially and verify summary flash message."""

    def test_run_all_tests_mixed_results(self, client):
        _login(client)

        # Create a passing test
        _create_test_scenario(
            client, name="Pass Test",
            outcome="Homepage displayed",
        )
        # Create a failing test (payment keyword triggers failure)
        _create_test_scenario(
            client, name="Fail Test",
            outcome="Payment confirmed",
        )

        resp = client.post("/run-all-tests", follow_redirects=True)
        assert resp.status_code == 200
        body = resp.data.decode()
        assert "1 passed" in body
        assert "1 failed" in body

        tests = db_module.get_all_tests()
        statuses = {t["name"]: t["status"] for t in tests}
        assert statuses["Pass Test"] == "Passed"
        assert statuses["Fail Test"] == "Failed"

    def test_run_all_with_no_tests_shows_error(self, client):
        _login(client)
        resp = client.post("/run-all-tests", follow_redirects=True)
        assert b"No tests to run" in resp.data


# ---------------------------------------------------------------------------
# 10. Database round-trip integration
# ---------------------------------------------------------------------------

class TestDatabaseRoundTrip:
    """Verify data integrity through insert -> retrieve -> update cycles."""

    def test_test_run_json_fields_round_trip(self, client):
        """Ensure screenshots (list) and performance (dict) survive JSON serialization."""
        _login(client)
        _create_test_scenario(client, name="JSON Round Trip")
        test = db_module.get_all_tests()[0]

        client.post(f"/run-test/{test['id']}", follow_redirects=True)

        run = db_module.get_latest_test_run(test["id"])
        # screenshots should be a list of strings
        assert isinstance(run["screenshots"], list)
        for s in run["screenshots"]:
            assert isinstance(s, str)
            assert s.startswith("/static/screenshots/")

        # performance should be a dict of step -> float
        assert isinstance(run["performance"], dict)
        for key, val in run["performance"].items():
            assert key.startswith("step_")
            assert isinstance(val, float)

    def test_diagnosis_dict_round_trip(self, client):
        """Ensure structured diagnosis dicts survive JSON serialization in DB."""
        _login(client)
        _create_test_scenario(
            client, name="Diag Round Trip",
            outcome="Payment processed",
        )
        test = db_module.get_all_tests()[0]
        client.post(f"/run-test/{test['id']}", follow_redirects=True)

        run = db_module.get_latest_test_run(test["id"])
        diag = run["diagnosis"]
        assert isinstance(diag, dict)
        assert "category" in diag
        assert "summary" in diag
        assert "explanation" in diag
        assert "suggestion" in diag
        assert "proposed_fix" in diag
