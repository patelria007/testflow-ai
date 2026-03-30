"""Step definitions for Scenario 3: Intelligent Failure Diagnosis.

Uses Selenium to drive a real headless Chromium browser against the Flask app.
Scenario 3 has three sub-scenarios:
    3A — Application bug failure: category badge, diagnosis, recommendation, re-run button.
    3B — Test design failure: category badge, apply suggested fix, test steps updated.
    3C — Environment failure: category badge, diagnosis, retry button.

The steps pre-seed test data directly into the database, then use the web UI
to run the test and verify the AI diagnosis on the results page.
"""

from behave import given, when, then
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

from src.db import insert_test, get_test_by_id


# ---------------------------------------------------------------------------
# Shared Given: log in and seed a failing test
# ---------------------------------------------------------------------------

@given('I am logged in and have a failing test "{test_name}" with expected outcome "{expected}"')
def step_logged_in_with_failing_test(context, test_name, expected):
    """Scenario 3: seed a test designed to fail, then log in via Selenium."""
    steps_map = {
        "Payment confirmation message": (
            "1. Navigate to /checkout\n"
            "2. Enter card number\n"
            "3. Enter expiry date\n"
            "4. Enter CVV\n"
            "5. Click Pay Now\n"
            "6. Wait for processing\n"
            "7. Verify confirmation"
        ),
        "element not found on page": (
            "1. Navigate to /dashboard\n"
            "2. Click the non-existent button\n"
            "3. Verify element is visible"
        ),
        "connection refused by server": (
            "1. Navigate to http://unreachable-host:9999\n"
            "2. Wait for page to load\n"
            "3. Verify homepage content"
        ),
    }
    steps_raw = steps_map.get(expected, "1. Navigate to /test\n2. Verify page")

    test_id = insert_test(
        name=test_name,
        application_url="http://localhost:5000",
        steps_raw=steps_raw,
        expected_outcome=expected,
    )
    context.test_state["test_name"] = test_name
    context.test_state["test_id"] = test_id

    # Log in so we have an active session
    context.driver.get(f"{context.base_url}/login")
    context.driver.find_element(By.ID, "email").send_keys("test@example.com")
    context.driver.find_element(By.ID, "password").send_keys("password123")
    context.driver.find_element(By.ID, "login-btn").click()
    WebDriverWait(context.driver, 5).until(lambda d: "/login" not in d.current_url)


# ---------------------------------------------------------------------------
# Shared When: run the failing test
# ---------------------------------------------------------------------------

@when('I run the failing test')
def step_run_failing_test(context):
    """Scenario 3: navigate to test list and click Run Test."""
    test_name = context.test_state["test_name"]
    context.driver.get(f"{context.base_url}/tests")
    WebDriverWait(context.driver, 5).until(
        EC.presence_of_element_located((By.CLASS_NAME, "test-name"))
    )

    rows = context.driver.find_elements(By.TAG_NAME, "tr")
    for row in rows:
        name_cells = row.find_elements(By.CLASS_NAME, "test-name")
        if name_cells and name_cells[0].text == test_name:
            run_btn = row.find_element(By.CLASS_NAME, "run-test-btn")
            run_btn.click()
            break
    else:
        raise AssertionError(f"Test '{test_name}' not found in test list")

    # Wait for results page
    WebDriverWait(context.driver, 30).until(
        lambda d: "/test-results/" in d.current_url
    )
    WebDriverWait(context.driver, 10).until(
        EC.presence_of_element_located((By.CLASS_NAME, "test-run-status"))
    )


# ---------------------------------------------------------------------------
# Then: verify status
# ---------------------------------------------------------------------------

@then('I should see the test status is "{status}"')
def step_see_status(context, status):
    """Scenario 3: verify test run status on results page."""
    status_el = context.driver.find_element(By.CLASS_NAME, "test-run-status")
    actual = status_el.text.strip()
    assert actual == status, f"Expected status '{status}', got '{actual}'"


# ---------------------------------------------------------------------------
# Then: verify diagnosis sections
# ---------------------------------------------------------------------------

@then('I should see a failure category badge "{category_text}"')
def step_see_category_badge(context, category_text):
    """Scenario 3: verify the category badge text on the diagnosis section."""
    badge = context.driver.find_element(By.CLASS_NAME, "category-badge")
    actual = badge.text.strip().lower()
    assert category_text.lower() in actual, f"Expected category '{category_text}', got '{actual}'"


@then('I should see a diagnosis summary')
def step_see_diagnosis_summary(context):
    """Scenario 3: verify the diagnosis summary is present and non-empty."""
    summary_el = context.driver.find_element(By.CLASS_NAME, "diagnosis-summary")
    assert summary_el.text.strip(), "Diagnosis summary is empty"


@then('I should see a diagnosis explanation containing "{keyword}"')
def step_see_diagnosis_explanation(context, keyword):
    """Scenario 3: verify the diagnosis explanation contains expected keyword."""
    explanation_el = context.driver.find_element(By.CLASS_NAME, "diagnosis-text")
    actual = explanation_el.text.strip().lower()
    assert keyword.lower() in actual, \
        f"Expected explanation to contain '{keyword}', got '{actual}'"


@then('I should see a recommendation section')
def step_see_recommendation(context):
    """Scenario 3: verify the recommendation/suggestion text is present."""
    suggestion_el = context.driver.find_element(By.CLASS_NAME, "suggestion-text")
    assert suggestion_el.text.strip(), "Recommendation section is empty"


@then('I should see a proposed fix section')
def step_see_proposed_fix(context):
    """Scenario 3: verify the proposed fix text is present."""
    fix_el = context.driver.find_element(By.CLASS_NAME, "proposed-fix-text")
    assert fix_el.text.strip(), "Proposed fix section is empty"


@then('I should see a "{button_text}" action button')
def step_see_action_button(context, button_text):
    """Scenario 3: verify an action button with the given text exists."""
    buttons = context.driver.find_elements(By.CLASS_NAME, "btn-action")
    texts = [b.text.strip() for b in buttons]
    assert any(button_text in t for t in texts), \
        f"Expected button '{button_text}', found: {texts}"


@then('I should see an "{button_text}" button')
def step_see_named_button(context, button_text):
    """Scenario 3B: verify the Apply Suggested Fix button is present."""
    buttons = context.driver.find_elements(By.CLASS_NAME, "btn-action")
    texts = [b.text.strip() for b in buttons]
    assert any(button_text in t for t in texts), \
        f"Expected button '{button_text}', found: {texts}"


@then('I should see an "{link_text}" link')
def step_see_named_link(context, link_text):
    """Scenario 3B: verify the Edit Test Manually link is present."""
    links = context.driver.find_elements(By.TAG_NAME, "a")
    texts = [l.text.strip() for l in links]
    assert any(link_text in t for t in texts), \
        f"Expected link '{link_text}', found: {texts}"


# ---------------------------------------------------------------------------
# Scenario 3B: Apply Suggested Fix flow
# ---------------------------------------------------------------------------

@when('I click "Apply Suggested Fix"')
def step_click_apply_fix(context):
    """Scenario 3B: click the Apply Suggested Fix button."""
    buttons = context.driver.find_elements(By.CLASS_NAME, "btn-fix")
    assert len(buttons) > 0, "Apply Suggested Fix button not found"
    buttons[0].click()

    # Wait for redirect to test list
    WebDriverWait(context.driver, 10).until(
        lambda d: "/tests" in d.current_url and "/test-results/" not in d.current_url
    )


@then('I should be redirected to the test list')
def step_redirected_to_test_list(context):
    """Scenario 3B: verify we are on the test list page."""
    assert "/tests" in context.driver.current_url, \
        f"Expected /tests URL, got {context.driver.current_url}"


@then('I should see a flash message "{message}"')
def step_see_flash_message(context, message):
    """Scenario 3B: verify a flash message is displayed."""
    page_source = context.driver.page_source
    assert message in page_source, \
        f"Expected flash message '{message}' not found on page"


@then('the test status should be reset to "{status}"')
def step_test_status_reset(context, status):
    """Scenario 3B: verify the test status was reset after applying fix."""
    test_id = context.test_state["test_id"]
    test = get_test_by_id(test_id)
    assert test["status"] == status, \
        f"Expected test status '{status}', got '{test['status']}'"
