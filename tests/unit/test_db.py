"""Unit tests for src/db.py — database helper functions.

Each test has a single assertion per the course requirement.
Uses the tmp_db fixture for an isolated in-memory-like SQLite database.
"""

import json

import pytest

import src.db as db


# ── init_db ──────────────────────────────────────────────────────────────


class TestInitDb:
    """Tests for init_db() schema creation and seed data."""

    def test_init_db_creates_users_table(self, tmp_db):
        conn = db.get_connection()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_init_db_creates_test_scenarios_table(self, tmp_db):
        conn = db.get_connection()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_scenarios'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_init_db_creates_test_runs_table(self, tmp_db):
        conn = db.get_connection()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='test_runs'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_init_db_creates_settings_table(self, tmp_db):
        conn = db.get_connection()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='settings'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_init_db_creates_saved_apps_table(self, tmp_db):
        conn = db.get_connection()
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='saved_apps'"
        ).fetchone()
        conn.close()
        assert row is not None

    def test_init_db_seeds_default_user(self, tmp_db):
        conn = db.get_connection()
        row = conn.execute(
            "SELECT email FROM users WHERE email = ?", ("test@example.com",)
        ).fetchone()
        conn.close()
        assert row["email"] == "test@example.com"

    def test_init_db_idempotent(self, tmp_db):
        """Calling init_db() twice does not duplicate the seed user."""
        db.init_db()
        conn = db.get_connection()
        count = conn.execute(
            "SELECT COUNT(*) as c FROM users WHERE email = ?", ("test@example.com",)
        ).fetchone()["c"]
        conn.close()
        assert count == 1


# ── reset_db ─────────────────────────────────────────────────────────────


class TestResetDb:
    def test_reset_db_clears_tests(self, tmp_db):
        db.insert_test("t", "http://x", "step", "outcome")
        db.reset_db()
        assert db.get_all_tests() == []

    def test_reset_db_re_seeds_user(self, tmp_db):
        db.reset_db()
        user = db.authenticate_user("test@example.com", "password123")
        assert user is not None


# ── create_user / authenticate_user ──────────────────────────────────────


class TestUserAuth:
    def test_create_user_returns_user_id(self, tmp_db):
        uid = db.create_user("new@test.com", "secret123")
        assert isinstance(uid, int)

    def test_create_user_duplicate_returns_none(self, tmp_db):
        db.create_user("dup@test.com", "pw1")
        result = db.create_user("dup@test.com", "pw2")
        assert result is None

    def test_authenticate_user_valid(self, tmp_db):
        user = db.authenticate_user("test@example.com", "password123")
        assert user["email"] == "test@example.com"

    def test_authenticate_user_wrong_password(self, tmp_db):
        result = db.authenticate_user("test@example.com", "wrong")
        assert result is None

    def test_authenticate_user_unknown_email(self, tmp_db):
        result = db.authenticate_user("nobody@x.com", "password123")
        assert result is None


# ── insert_test / get_all_tests / get_test_by_id ─────────────────────────


class TestTestScenarios:
    def test_insert_test_returns_id(self, tmp_db):
        tid = db.insert_test("Login", "http://app", "Step1\nStep2", "Success")
        assert isinstance(tid, int)

    def test_insert_test_default_status(self, tmp_db):
        tid = db.insert_test("Login", "http://app", "Step1", "Pass")
        test = db.get_test_by_id(tid)
        assert test["status"] == "Not Run"

    def test_get_all_tests_empty(self, tmp_db):
        assert db.get_all_tests() == []

    def test_get_all_tests_returns_list(self, tmp_db):
        db.insert_test("A", "http://a", "s", "o")
        db.insert_test("B", "http://b", "s", "o")
        assert len(db.get_all_tests()) == 2

    def test_get_test_by_id_found(self, tmp_db):
        tid = db.insert_test("X", "http://x", "s", "o")
        test = db.get_test_by_id(tid)
        assert test["name"] == "X"

    def test_get_test_by_id_not_found(self, tmp_db):
        assert db.get_test_by_id(9999) is None

    def test_insert_test_strips_whitespace(self, tmp_db):
        tid = db.insert_test("T", "http://t", "  step  ", "  out  ")
        test = db.get_test_by_id(tid)
        assert test["steps_raw"] == "step"


# ── update_test_status ───────────────────────────────────────────────────


class TestUpdateTestStatus:
    def test_update_test_status_to_passed(self, tmp_db):
        tid = db.insert_test("T", "http://t", "s", "o")
        db.update_test_status(tid, "Passed")
        assert db.get_test_by_id(tid)["status"] == "Passed"

    def test_update_test_status_to_failed(self, tmp_db):
        tid = db.insert_test("T", "http://t", "s", "o")
        db.update_test_status(tid, "Failed")
        assert db.get_test_by_id(tid)["status"] == "Failed"


# ── update_test ──────────────────────────────────────────────────────────


class TestUpdateTest:
    def test_update_test_changes_name(self, tmp_db):
        tid = db.insert_test("Old", "http://t", "s", "o")
        db.update_test(tid, "New", "http://t", "s", "o")
        assert db.get_test_by_id(tid)["name"] == "New"

    def test_update_test_changes_url(self, tmp_db):
        tid = db.insert_test("T", "http://old", "s", "o")
        db.update_test(tid, "T", "http://new", "s", "o")
        assert db.get_test_by_id(tid)["application_url"] == "http://new"

    def test_update_test_changes_steps(self, tmp_db):
        tid = db.insert_test("T", "http://t", "old step", "o")
        db.update_test(tid, "T", "http://t", "new step", "o")
        assert db.get_test_by_id(tid)["steps_raw"] == "new step"


# ── insert_test_run / get_test_run / get_latest_test_run ─────────────────


class TestTestRuns:
    def test_insert_test_run_returns_id(self, tmp_db):
        tid = db.insert_test("T", "http://t", "s", "o")
        rid = db.insert_test_run(tid, "Passed", 1.23)
        assert isinstance(rid, int)

    def test_insert_test_run_with_dict_diagnosis(self, tmp_db):
        tid = db.insert_test("T", "http://t", "s", "o")
        diag = {"category": "test_design", "summary": "oops"}
        rid = db.insert_test_run(tid, "Failed", 2.0, diagnosis=diag)
        run = db.get_test_run(rid)
        assert run["diagnosis"]["category"] == "test_design"

    def test_insert_test_run_with_string_diagnosis(self, tmp_db):
        tid = db.insert_test("T", "http://t", "s", "o")
        rid = db.insert_test_run(tid, "Failed", 2.0, diagnosis="plain text error")
        run = db.get_test_run(rid)
        assert run["diagnosis"]["explanation"] == "plain text error"

    def test_insert_test_run_with_screenshots(self, tmp_db):
        tid = db.insert_test("T", "http://t", "s", "o")
        shots = ["/static/screenshots/a.png", "/static/screenshots/b.png"]
        rid = db.insert_test_run(tid, "Passed", 1.0, screenshots=shots)
        run = db.get_test_run(rid)
        assert len(run["screenshots"]) == 2

    def test_insert_test_run_with_performance(self, tmp_db):
        tid = db.insert_test("T", "http://t", "s", "o")
        perf = {"step_1": 0.5, "step_2": 1.1}
        rid = db.insert_test_run(tid, "Passed", 1.6, performance=perf)
        run = db.get_test_run(rid)
        assert run["performance"]["step_1"] == 0.5

    def test_insert_test_run_email_sent_true(self, tmp_db):
        tid = db.insert_test("T", "http://t", "s", "o")
        rid = db.insert_test_run(tid, "Failed", 1.0, email_sent=True)
        run = db.get_test_run(rid)
        assert run["email_sent"] == 1

    def test_insert_test_run_email_sent_false(self, tmp_db):
        tid = db.insert_test("T", "http://t", "s", "o")
        rid = db.insert_test_run(tid, "Passed", 1.0, email_sent=False)
        run = db.get_test_run(rid)
        assert run["email_sent"] == 0

    def test_get_test_run_not_found(self, tmp_db):
        assert db.get_test_run(9999) is None

    def test_get_latest_test_run_returns_newest(self, tmp_db):
        tid = db.insert_test("T", "http://t", "s", "o")
        db.insert_test_run(tid, "Failed", 1.0)
        db.insert_test_run(tid, "Passed", 2.0)
        run = db.get_latest_test_run(tid)
        assert run["status"] == "Passed"

    def test_get_latest_test_run_not_found(self, tmp_db):
        tid = db.insert_test("T", "http://t", "s", "o")
        assert db.get_latest_test_run(tid) is None


# ── _parse_diagnosis ─────────────────────────────────────────────────────


class TestParseDiagnosis:
    def test_parse_diagnosis_none(self, tmp_db):
        assert db._parse_diagnosis(None) is None

    def test_parse_diagnosis_valid_json_dict(self, tmp_db):
        raw = json.dumps({"category": "test_design", "summary": "x"})
        result = db._parse_diagnosis(raw)
        assert result["category"] == "test_design"

    def test_parse_diagnosis_plain_string(self, tmp_db):
        result = db._parse_diagnosis("Something broke")
        assert result["category"] == "environment"

    def test_parse_diagnosis_plain_string_wraps_explanation(self, tmp_db):
        result = db._parse_diagnosis("Something broke")
        assert result["explanation"] == "Something broke"

    def test_parse_diagnosis_invalid_json(self, tmp_db):
        result = db._parse_diagnosis("{bad json")
        assert result["category"] == "environment"


# ── Settings ─────────────────────────────────────────────────────────────


class TestSettings:
    def test_get_setting_default(self, tmp_db):
        assert db.get_setting("nonexistent", "fallback") == "fallback"

    def test_set_and_get_setting(self, tmp_db):
        db.set_setting("report_email", "a@b.com")
        assert db.get_setting("report_email") == "a@b.com"

    def test_set_setting_overwrites(self, tmp_db):
        db.set_setting("key", "v1")
        db.set_setting("key", "v2")
        assert db.get_setting("key") == "v2"

    def test_get_all_settings_empty(self, tmp_db):
        assert db.get_all_settings() == {}

    def test_get_all_settings_with_data(self, tmp_db):
        db.set_setting("a", "1")
        db.set_setting("b", "2")
        s = db.get_all_settings()
        assert len(s) == 2


# ── Saved Apps ───────────────────────────────────────────────────────────


class TestSavedApps:
    def test_insert_saved_app_returns_id(self, tmp_db):
        aid = db.insert_saved_app("App", "http://app", "none")
        assert isinstance(aid, int)

    def test_get_all_saved_apps_empty(self, tmp_db):
        assert db.get_all_saved_apps() == []

    def test_get_all_saved_apps_with_data(self, tmp_db):
        db.insert_saved_app("A", "http://a", "none")
        assert len(db.get_all_saved_apps()) == 1

    def test_get_saved_app_found(self, tmp_db):
        aid = db.insert_saved_app("MyApp", "http://my", "basic", "user", "pw")
        app = db.get_saved_app(aid)
        assert app["name"] == "MyApp"

    def test_get_saved_app_not_found(self, tmp_db):
        assert db.get_saved_app(9999) is None

    def test_update_saved_app(self, tmp_db):
        aid = db.insert_saved_app("Old", "http://old", "none")
        db.update_saved_app(aid, "New", "http://new", "token", "", "", "abc")
        app = db.get_saved_app(aid)
        assert app["name"] == "New"

    def test_update_saved_app_changes_url(self, tmp_db):
        aid = db.insert_saved_app("A", "http://old", "none")
        db.update_saved_app(aid, "A", "http://new", "none")
        assert db.get_saved_app(aid)["url"] == "http://new"

    def test_delete_saved_app(self, tmp_db):
        aid = db.insert_saved_app("Del", "http://del", "none")
        db.delete_saved_app(aid)
        assert db.get_saved_app(aid) is None
