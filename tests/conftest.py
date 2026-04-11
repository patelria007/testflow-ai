"""Shared pytest fixtures for TestFlow AI unit tests.

Provides:
  - tmp_db: a temporary SQLite database (per-test isolation)
  - app: a Flask app instance configured for testing
  - client: a Flask test client with session support
  - logged_in_client: a test client already authenticated
"""

import os
import tempfile

import pytest

import src.db as db_module
from src.app import create_app


@pytest.fixture()
def tmp_db(tmp_path):
    """Create a temporary SQLite database for each test.

    Patches src.db.DB_PATH so all db functions use the temp file.
    Calls init_db() to set up the schema and seed data.
    Restores the original DB_PATH after the test.
    """
    db_file = str(tmp_path / "test.db")
    original = db_module.DB_PATH
    db_module.DB_PATH = db_file
    db_module.init_db()
    yield db_file
    db_module.DB_PATH = original


@pytest.fixture()
def app(tmp_db):
    """Create a Flask application configured for testing.

    Uses the tmp_db fixture so the app talks to the temp database.
    """
    os.environ["TESTFLOW_SIMULATE"] = "1"
    application = create_app()
    application.config["TESTING"] = True
    application.config["SECRET_KEY"] = "test-secret"
    yield application
    os.environ.pop("TESTFLOW_SIMULATE", None)


@pytest.fixture()
def client(app):
    """Flask test client."""
    return app.test_client()


@pytest.fixture()
def logged_in_client(client):
    """Flask test client that is already logged in as the seed user."""
    client.post("/login", data={
        "email": "test@example.com",
        "password": "password123",
    })
    return client
