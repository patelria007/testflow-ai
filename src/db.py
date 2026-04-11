"""SQLite database helpers for Scenario 1 (Test Creation) and Scenario 2 (Test Execution).

This module provides all database operations needed by Scenarios 1 and 2.

Scenario 1 flow:
    register/login -> navigate to "Create Test" -> fill form -> save -> see test in list

Scenario 2 flow:
    pre-seed test -> click "Run Test" -> view results (status, time, screenshots, metrics)

Schema — users table (Authentication):
    id               INTEGER  Primary key (auto-increment).
    email            TEXT     User email (unique).                (used at /login and /register)
    password_hash    TEXT     Werkzeug-hashed password.           (never stored in plain text)

Schema — test_scenarios table (Scenario 1):
    id               INTEGER  Primary key (auto-increment).
    name             TEXT     Test name entered by user.          (Scenario 1: step "I enter the test name")
    application_url  TEXT     Target app URL.                     (Scenario 1: step "I enter the application URL")
    steps_raw        TEXT     Natural language test steps.        (Scenario 1: step "I provide the test steps")
    expected_outcome TEXT     Expected result of the test.        (Scenario 1: step "I set expected outcome")
    status           TEXT     Defaults to "Not Run".              (Scenario 1 & 2: test execution status)

Schema — test_runs table (Scenario 2):
    id               INTEGER  Primary key (auto-increment).
    test_id          INTEGER  FK to test_scenarios.id.            (Scenario 2: links run to its test)
    status           TEXT     "Passed" or "Failed".               (Scenario 2: step "I should see test status as")
    execution_time   REAL     Seconds taken to execute.           (Scenario 2: step "I should see execution time")
    failure_message  TEXT     Error message if failed.            (Scenario 2: step "I should see failure message")
    diagnosis        TEXT     AI-powered failure diagnosis.       (Scenario 2: step "AI-powered diagnosis suggesting")
    screenshots      TEXT     JSON array of screenshot paths.     (Scenario 2: step "screenshots for each step")
    performance      TEXT     JSON object with page load times.   (Scenario 2: step "performance metrics")
    email_sent       INTEGER  1 if failure email was sent.        (Scenario 2: step "receive an email notification")
    created_at       TEXT     ISO timestamp of execution.
"""

import sqlite3
import os
import json
from datetime import datetime, timezone

from werkzeug.security import generate_password_hash, check_password_hash

# Default DB path; can be overridden via environment variable for testing.
DB_PATH = os.environ.get("TESTFLOW_DB", "testflow.db")


def get_connection() -> sqlite3.Connection:
    """Return a connection to the SQLite database.

    Uses sqlite3.Row so rows can be accessed by column name.

    @return: sqlite3.Connection configured with Row factory
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_user(email: str, password: str) -> int | None:
    """Register a new user with a hashed password.

    Uses werkzeug's generate_password_hash for secure pbkdf2:sha256 hashing.

    @param email: User email address (must be unique)
    @param password: Plain-text password to hash and store
    @return: New user id on success, or None if the email already exists
    @throws sqlite3.IntegrityError: Caught internally when email is duplicate
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            (email, generate_password_hash(password, method="pbkdf2:sha256")),
        )
        conn.commit()
        user_id = cursor.lastrowid
    except sqlite3.IntegrityError:
        user_id = None
    conn.close()
    return user_id


def authenticate_user(email: str, password: str) -> dict | None:
    """Validate email and password against the database.

    Uses werkzeug's check_password_hash to compare against the stored hash.

    @param email: User email address to look up
    @param password: Plain-text password to verify against the stored hash
    @return: Dict of user row data on success, or None if credentials are invalid
    """
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()
    if row and check_password_hash(row["password_hash"], password):
        return dict(row)
    return None


def init_db() -> None:
    """Create all database tables if they do not exist and seed the default test user.

    Called once at Flask app startup. Creates users, test_scenarios, settings,
    saved_apps, and test_runs tables.

    @return: None
    """
    conn = get_connection()
    # Authentication: stores registered users with hashed passwords.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL
        )
        """
    )
    # Seed a default test user so acceptance tests can log in.
    # Uses werkzeug's password hashing — never stores plain text.
    existing = conn.execute("SELECT id FROM users WHERE email = ?", ("test@example.com",)).fetchone()
    if not existing:
        conn.execute(
            "INSERT INTO users (email, password_hash) VALUES (?, ?)",
            ("test@example.com", generate_password_hash("password123", method="pbkdf2:sha256")),
        )
        conn.commit()
    # Scenario 1: stores test definitions created by the user.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS test_scenarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            application_url TEXT NOT NULL,
            steps_raw TEXT NOT NULL,
            expected_outcome TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Not Run'
        )
        """
    )
    # Settings: user preferences (email, notifications).
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT NOT NULL UNIQUE,
            value TEXT NOT NULL
        )
        """
    )
    # Saved applications: store target app credentials separately from tests.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS saved_apps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            auth_type TEXT NOT NULL DEFAULT 'none',
            username TEXT,
            password TEXT,
            api_token TEXT
        )
        """
    )
    # Scenario 2: stores execution results when a test is run.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS test_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            test_id INTEGER NOT NULL,
            status TEXT NOT NULL,
            execution_time REAL NOT NULL,
            failure_message TEXT,
            diagnosis TEXT,
            screenshots TEXT,
            performance TEXT,
            email_sent INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            FOREIGN KEY (test_id) REFERENCES test_scenarios(id)
        )
        """
    )
    conn.commit()
    conn.close()


def reset_db() -> None:
    """Drop and recreate all tables for a clean database state.

    Called in environment.py before_scenario to ensure each test starts fresh.

    @return: None
    """
    conn = get_connection()
    conn.execute("DROP TABLE IF EXISTS test_runs")
    conn.execute("DROP TABLE IF EXISTS test_scenarios")
    conn.execute("DROP TABLE IF EXISTS users")
    conn.execute("DROP TABLE IF EXISTS settings")
    conn.execute("DROP TABLE IF EXISTS saved_apps")
    conn.commit()
    conn.close()
    init_db()


# --- Settings helpers ---

def get_setting(key: str, default: str = "") -> str:
    """Retrieve a setting value by its key from the settings table.

    @param key: The setting key to look up
    @param default: Value to return if the key does not exist
    @return: The setting value, or the default if not found
    """
    conn = get_connection()
    row = conn.execute("SELECT value FROM settings WHERE key = ?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    """Set a setting value, inserting a new row or updating the existing one.

    @param key: The setting key to set
    @param value: The value to store for the key
    @return: None
    """
    conn = get_connection()
    conn.execute(
        "INSERT INTO settings (key, value) VALUES (?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    conn.commit()
    conn.close()


def get_all_settings() -> dict:
    """Return all settings as a key-value dict.

    @return: Dict mapping setting keys to their values
    """
    conn = get_connection()
    rows = conn.execute("SELECT key, value FROM settings").fetchall()
    conn.close()
    return {row["key"]: row["value"] for row in rows}


# --- Saved apps helpers ---

def insert_saved_app(name: str, url: str, auth_type: str,
                     username: str = "", password: str = "", api_token: str = "") -> int:
    """Save a target application with its credentials to the database.

    @param name: Display name for the application
    @param url: Base URL of the target application
    @param auth_type: Authentication type (e.g., 'none', 'basic', 'token')
    @param username: Login username for the application
    @param password: Login password for the application
    @param api_token: API token for token-based authentication
    @return: Row id of the newly inserted saved app
    """
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO saved_apps (name, url, auth_type, username, password, api_token)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, url, auth_type, username, password, api_token),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_all_saved_apps() -> list[dict]:
    """Return all saved applications ordered by id.

    @return: List of dicts, each representing a saved application row
    """
    conn = get_connection()
    rows = conn.execute("SELECT * FROM saved_apps ORDER BY id").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_saved_app(app_id: int) -> dict | None:
    """Return a single saved application by its id.

    @param app_id: Primary key of the saved app to retrieve
    @return: Dict of the saved app row, or None if not found
    """
    conn = get_connection()
    row = conn.execute("SELECT * FROM saved_apps WHERE id = ?", (app_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_saved_app(app_id: int, name: str, url: str, auth_type: str,
                     username: str = "", password: str = "", api_token: str = "") -> None:
    """Update an existing saved application's details.

    @param app_id: Primary key of the saved app to update
    @param name: New display name for the application
    @param url: New base URL of the target application
    @param auth_type: New authentication type
    @param username: New login username
    @param password: New login password
    @param api_token: New API token
    @return: None
    """
    conn = get_connection()
    conn.execute(
        """
        UPDATE saved_apps
        SET name = ?, url = ?, auth_type = ?, username = ?, password = ?, api_token = ?
        WHERE id = ?
        """,
        (name, url, auth_type, username, password, api_token, app_id),
    )
    conn.commit()
    conn.close()


def delete_saved_app(app_id: int) -> None:
    """Delete a saved application from the database.

    @param app_id: Primary key of the saved app to delete
    @return: None
    """
    conn = get_connection()
    conn.execute("DELETE FROM saved_apps WHERE id = ?", (app_id,))
    conn.commit()
    conn.close()


def insert_test(name: str, application_url: str, steps_raw: str, expected_outcome: str) -> int:
    """Insert a new test scenario into the database.

    Called when the user clicks Save Test on the create test form.
    The status column defaults to 'Not Run'.

    @param name: Test scenario name entered by the user
    @param application_url: Target application URL to test against
    @param steps_raw: Natural language test steps (free-form text)
    @param expected_outcome: Expected result of the test execution
    @return: Row id of the newly inserted test scenario
    """
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO test_scenarios (name, application_url, steps_raw, expected_outcome)
        VALUES (?, ?, ?, ?)
        """,
        (name, application_url, steps_raw.strip(), expected_outcome.strip()),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_all_tests() -> list[dict]:
    """Return all saved test scenarios as a list of dicts.

    Used by the /tests route to render the test list page. Each dict contains:
    id, name, application_url, steps_raw, expected_outcome, status.

    @return: List of dicts, each representing a test scenario row
    """
    conn = get_connection()
    rows = conn.execute("SELECT * FROM test_scenarios ORDER BY id").fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_test_by_id(test_id: int) -> dict | None:
    """Return a single test scenario by its id.

    Used when executing a test or viewing its results.

    @param test_id: Primary key of the test scenario to retrieve
    @return: Dict of the test scenario row, or None if not found
    """
    conn = get_connection()
    row = conn.execute("SELECT * FROM test_scenarios WHERE id = ?", (test_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def update_test_status(test_id: int, status: str) -> None:
    """Update the status column of a test scenario.

    Called after test execution to set status to 'Passed' or 'Failed'.

    @param test_id: Primary key of the test scenario to update
    @param status: New status value (e.g., 'Passed', 'Failed', 'Not Run')
    @return: None
    """
    conn = get_connection()
    conn.execute("UPDATE test_scenarios SET status = ? WHERE id = ?", (status, test_id))
    conn.commit()
    conn.close()


def update_test(test_id: int, name: str, application_url: str, steps_raw: str, expected_outcome: str) -> None:
    """Update an existing test scenario's details.

    @param test_id: Primary key of the test scenario to update
    @param name: Updated test scenario name
    @param application_url: Updated target application URL
    @param steps_raw: Updated natural language test steps
    @param expected_outcome: Updated expected result
    @return: None
    """
    conn = get_connection()
    conn.execute(
        """
        UPDATE test_scenarios
        SET name = ?, application_url = ?, steps_raw = ?, expected_outcome = ?
        WHERE id = ?
        """,
        (name, application_url, steps_raw.strip(), expected_outcome.strip(), test_id),
    )
    conn.commit()
    conn.close()


def insert_test_run(test_id: int, status: str, execution_time: float,
                    failure_message: str | None = None,
                    diagnosis: str | None = None,
                    screenshots: list | None = None,
                    performance: dict | None = None,
                    email_sent: bool = False) -> int:
    """Insert a test execution run record into the database.

    Called after test execution to store results. Serializes diagnosis (dict or string),
    screenshots (list), and performance (dict) as JSON for storage.

    @param test_id: Foreign key to the test scenario that was executed
    @param status: Execution result, either 'Passed' or 'Failed'
    @param execution_time: Seconds elapsed during execution
    @param failure_message: Error description if the test failed, or None
    @param diagnosis: AI-generated diagnosis as dict or string, or None
    @param screenshots: List of screenshot file paths, or None
    @param performance: Dict of page load times per step, or None
    @param email_sent: Whether a failure notification email was sent
    @return: Row id of the newly inserted test run
    """
    # Serialize diagnosis: accepts both string (legacy) and dict (Scenario 3)
    if isinstance(diagnosis, dict):
        diagnosis_json = json.dumps(diagnosis)
    else:
        diagnosis_json = diagnosis

    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO test_runs
            (test_id, status, execution_time, failure_message, diagnosis,
             screenshots, performance, email_sent, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            test_id, status, execution_time,
            failure_message, diagnosis_json,
            json.dumps(screenshots or []),
            json.dumps(performance or {}),
            1 if email_sent else 0,
            datetime.now(timezone.utc).isoformat(),
        ),
    )
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def _parse_diagnosis(raw):
    """Parse the diagnosis field from the database.

    Returns a structured dict if the value is valid JSON, or wraps a plain-text
    string into the standard diagnosis dict format.

    @param raw: Raw diagnosis value from the database (JSON string, plain text, or None)
    @return: Structured diagnosis dict with category, summary, explanation, suggestion, proposed_fix, or None
    """
    if not raw:
        return None
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return parsed
    except (json.JSONDecodeError, TypeError):
        pass
    # Legacy plain-text diagnosis — wrap it
    return {
        "category": "environment",
        "summary": raw[:200],
        "explanation": raw,
        "suggestion": "",
        "proposed_fix": "",
    }


def get_test_run(run_id: int) -> dict | None:
    """Return a single test run by its id with parsed JSON fields.

    Deserializes screenshots, performance, and diagnosis from their stored JSON format.

    @param run_id: Primary key of the test run to retrieve
    @return: Dict of the test run row with parsed fields, or None if not found
    """
    conn = get_connection()
    row = conn.execute("SELECT * FROM test_runs WHERE id = ?", (run_id,)).fetchone()
    conn.close()
    if row:
        result = dict(row)
        result["screenshots"] = json.loads(result["screenshots"])
        result["performance"] = json.loads(result["performance"])
        result["diagnosis"] = _parse_diagnosis(result["diagnosis"])
        return result
    return None


def get_latest_test_run(test_id: int) -> dict | None:
    """Return the most recent test run for a given test scenario.

    Retrieves the latest run by id descending and deserializes JSON fields.

    @param test_id: Foreign key of the test scenario whose latest run to retrieve
    @return: Dict of the most recent test run with parsed fields, or None if no runs exist
    """
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM test_runs WHERE test_id = ? ORDER BY id DESC LIMIT 1",
        (test_id,),
    ).fetchone()
    conn.close()
    if row:
        result = dict(row)
        result["screenshots"] = json.loads(result["screenshots"])
        result["performance"] = json.loads(result["performance"])
        result["diagnosis"] = _parse_diagnosis(result["diagnosis"])
        return result
    return None
