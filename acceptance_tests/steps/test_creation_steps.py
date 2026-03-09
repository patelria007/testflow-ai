"""Step definitions for Scenario 1: Test Scenario Creation.

Uses Selenium to drive a real headless Chromium browser against the Flask app.
Each step interacts with the actual web UI (forms, buttons, page content).
"""

from behave import given, when, then
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# --- Scenario 1: Login step ---

@given('I am logged into the testing platform')
def step_logged_in(context):
    """Navigate to /login, fill in credentials, and submit the form."""
    context.driver.get(f"{context.base_url}/login")
    context.driver.find_element(By.ID, "email").send_keys("test@example.com")
    context.driver.find_element(By.ID, "password").send_keys("password123")
    context.driver.find_element(By.ID, "login-btn").click()
    # Wait for login redirect to complete so the session cookie is set
    WebDriverWait(context.driver, 5).until(
        lambda d: "/login" not in d.current_url
    )


# --- Scenario 1: Navigation step ---

@when('I navigate to the "Create Test" page')
def step_navigate_to_create_test(context):
    """Navigate directly to the test creation page."""
    context.driver.get(f"{context.base_url}/create-test")


# --- Scenario 1: Form input steps ---

@when('I enter the test name "{test_name}"')
def step_enter_test_name(context, test_name):
    """Type the test name into the form field."""
    context.driver.find_element(By.ID, "test_name").send_keys(test_name)
    context.test_state["test_name"] = test_name


@when('I enter the application URL "{url}"')
def step_enter_application_url(context, url):
    """Type the application URL into the form field."""
    context.driver.find_element(By.ID, "application_url").send_keys(url)


@when('I provide the test steps in natural language:')
def step_provide_nl_steps(context):
    """Type the natural language steps into the textarea."""
    steps_text = (context.text or "").strip()
    context.driver.find_element(By.ID, "steps_raw").send_keys(steps_text)


@when('I set expected outcome "{outcome}"')
def step_set_expected_outcome(context, outcome):
    """Type the expected outcome into the form field."""
    context.driver.find_element(By.ID, "expected_outcome").send_keys(outcome)


# --- Scenario 1: Save action ---

@when('I click "Save Test"')
def step_save_test(context):
    """Click the Save Test button to submit the form."""
    context.driver.find_element(By.ID, "save-test-btn").click()
    # Wait for redirect to /tests to complete
    WebDriverWait(context.driver, 5).until(
        lambda d: "/tests" in d.current_url
    )


# --- Scenario 1: Verification steps ---

@then('I should see a confirmation message "{message}"')
def step_see_confirmation(context, message):
    """Assert the flash confirmation message is visible on the page."""
    # Wait for the message to appear in the page
    WebDriverWait(context.driver, 5).until(
        lambda d: message in d.page_source
    )


@then('the test should appear in my test list with status "{status}"')
def step_test_appears_in_list(context, status):
    """Assert the test name and status appear in the test list table."""
    name = context.test_state["test_name"]
    # We should already be on the test list page (redirected after save).
    names = context.driver.find_elements(By.CLASS_NAME, "test-name")
    statuses = context.driver.find_elements(By.CLASS_NAME, "test-status")

    found = False
    for n, s in zip(names, statuses):
        if n.text == name and s.text == status:
            found = True
            break

    assert found, (
        f"Expected test '{name}' with status '{status}' in list. "
        f"Found: {[(n.text, s.text) for n, s in zip(names, statuses)]}"
    )
