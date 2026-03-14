"""Real test execution engine using Selenium + BeautifulSoup + Gemini LLM.

Replaces the simulated test execution with actual browser-driven testing.
The engine:
  1. Launches a headless Chrome browser
  2. Navigates to the target application URL
  3. Crawls the page with BeautifulSoup to discover interactive elements
  4. Sends natural language steps + discovered elements to Gemini LLM
  5. LLM returns structured Selenium commands
  6. Executes each command, taking real screenshots and measuring performance
  7. Detects real pass/fail based on actual execution outcomes
"""

import os
import re
import time
import uuid

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException
)

from src.llm_step_parser import parse_steps_with_llm

# Directory where real screenshots are saved
SCREENSHOT_DIR = os.path.join(os.path.dirname(__file__), "static", "screenshots")
os.makedirs(SCREENSHOT_DIR, exist_ok=True)


def _create_driver():
    """Create a headless Chrome WebDriver."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    return webdriver.Chrome(options=options)


def _discover_elements(driver):
    """Use BeautifulSoup to discover all interactive elements on the current page."""
    soup = BeautifulSoup(driver.page_source, "html.parser")
    elements = {
        "inputs": [],
        "buttons": [],
        "links": [],
        "forms": [],
    }
    for inp in soup.find_all("input"):
        elements["inputs"].append({
            "type": inp.get("type", "text"),
            "name": inp.get("name", ""),
            "id": inp.get("id", ""),
            "placeholder": inp.get("placeholder", ""),
        })
    for btn in soup.find_all("button"):
        elements["buttons"].append({
            "text": btn.get_text(strip=True),
            "type": btn.get("type", ""),
            "id": btn.get("id", ""),
            "class": " ".join(btn.get("class", [])),
        })
    for a in soup.find_all("a", href=True):
        elements["links"].append({
            "text": a.get_text(strip=True),
            "href": a["href"],
        })
    for form in soup.find_all("form"):
        elements["forms"].append({
            "action": form.get("action", ""),
            "method": form.get("method", ""),
        })
    return elements


def _find_input(driver, keyword):
    """Find an input element matching a keyword (name, id, type, placeholder, label).

    Uses multiple strategies including exact match, partial match,
    and word-level matching to handle LLM output like 'project name' → input[name='name'].
    """
    keyword_lower = keyword.lower().strip()
    # Also try individual words (e.g., "project name" → try "project", then "name")
    keyword_words = keyword_lower.split()

    # Strategy 1: Direct CSS attribute match
    for kw in [keyword_lower] + keyword_words:
        for attr in ["name", "id", "placeholder"]:
            try:
                el = driver.find_element(
                    By.CSS_SELECTOR,
                    f"input[{attr}*='{kw}' i]"
                )
                return el
            except NoSuchElementException:
                pass

    # Strategy 2: Match by type (e.g., "password", "email")
    for kw in [keyword_lower] + keyword_words:
        try:
            el = driver.find_element(By.CSS_SELECTOR, f"input[type='{kw}']")
            return el
        except NoSuchElementException:
            pass

    # Strategy 3: Match by associated label text
    try:
        labels = driver.find_elements(By.TAG_NAME, "label")
        for label in labels:
            label_text = label.text.lower()
            if keyword_lower in label_text or any(w in label_text for w in keyword_words):
                for_attr = label.get_attribute("for")
                if for_attr:
                    return driver.find_element(By.ID, for_attr)
                inp = label.find_element(By.TAG_NAME, "input")
                return inp
    except NoSuchElementException:
        pass

    # Strategy 4: Try textarea
    for kw in [keyword_lower] + keyword_words:
        for attr in ["name", "id", "placeholder"]:
            try:
                el = driver.find_element(
                    By.CSS_SELECTOR,
                    f"textarea[{attr}*='{kw}' i]"
                )
                return el
            except NoSuchElementException:
                pass

    # Strategy 5: Try select elements
    for kw in [keyword_lower] + keyword_words:
        for attr in ["name", "id"]:
            try:
                el = driver.find_element(
                    By.CSS_SELECTOR,
                    f"select[{attr}*='{kw}' i]"
                )
                return el
            except NoSuchElementException:
                pass

    # Strategy 6: First visible text input as last resort if keyword suggests a text field
    text_hints = ["name", "title", "text", "description", "subject", "query", "search"]
    if any(h in keyword_lower for h in text_hints):
        try:
            inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
            for inp in inputs:
                if inp.is_displayed():
                    return inp
        except NoSuchElementException:
            pass

    return None


def _find_clickable(driver, keyword):
    """Find a clickable element (button, link, submit) matching a keyword.

    Tries multiple matching strategies: exact text, partial text,
    cleaned text (without 'button'/'link' suffixes), and word-level matching.
    """
    keyword_lower = keyword.lower().strip()
    # Strip common suffixes the LLM might add (e.g., "New project link" → "New project")
    clean_keyword = re.sub(r"\s*(button|link|btn|tab|menu|icon)\s*$", "", keyword_lower, flags=re.I).strip()
    # All variations to try
    keywords = [keyword_lower, clean_keyword]
    # Add individual significant words (skip short words)
    keywords.extend([w for w in clean_keyword.split() if len(w) > 2])

    # Strategy 1: Buttons by text (exact then partial)
    try:
        buttons = driver.find_elements(By.TAG_NAME, "button")
        for kw in keywords:
            for btn in buttons:
                btn_text = btn.text.strip().lower()
                if btn_text and (kw == btn_text or kw in btn_text or btn_text in kw):
                    if btn.is_displayed():
                        return btn
    except NoSuchElementException:
        pass

    # Strategy 2: Links by text (exact then partial)
    try:
        links = driver.find_elements(By.TAG_NAME, "a")
        for kw in keywords:
            for link in links:
                link_text = link.text.strip().lower()
                if link_text and (kw == link_text or kw in link_text or link_text in kw):
                    if link.is_displayed():
                        return link
    except NoSuchElementException:
        pass

    # Strategy 3: Submit button if keyword suggests submission
    submit_words = ["submit", "sign in", "log in", "login", "save", "send", "pay",
                    "register", "create", "confirm", "ok", "yes", "apply"]
    if any(w in keyword_lower for w in submit_words):
        try:
            return driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
        except NoSuchElementException:
            pass
        try:
            return driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
        except NoSuchElementException:
            pass

    # Strategy 4: By id, class, or aria-label
    for kw in keywords:
        for attr in ["id", "aria-label"]:
            try:
                el = driver.find_element(By.CSS_SELECTOR, f"[{attr}*='{kw}' i]")
                if el.is_displayed():
                    return el
            except NoSuchElementException:
                pass

    return None


def _take_screenshot(driver, run_id, step_num):
    """Take a screenshot and return the path relative to static/."""
    filename = f"{run_id}_step_{step_num}.png"
    filepath = os.path.join(SCREENSHOT_DIR, filename)
    driver.save_screenshot(filepath)
    return f"/static/screenshots/{filename}"


def _parse_step(step_text):
    """Parse a natural language step into an action dict.

    Returns: {"action": str, "target": str, "value": str}

    Supported patterns:
      - Navigate/Go to <url>
      - Enter/Type/Input <value> in/into <field>
      - Enter/Type <field> (uses field name as both target and guess)
      - Click/Press/Tap <element>
      - Wait for <element/condition>
      - Verify/Check/Assert <condition>
      - Select <option> from <dropdown>
    """
    # Strip step numbers like "1.", "Step 1:", etc.
    text = re.sub(r"^(\d+[\.\):]?\s*|step\s+\d+[\.\):]?\s*)", "", step_text, flags=re.I).strip()

    # Navigate / Go to
    m = re.match(r"(?:navigate|go|open|visit|browse)\s+(?:to\s+)?(.+)", text, re.I)
    if m:
        return {"action": "navigate", "target": m.group(1).strip(), "value": ""}

    # Enter <value> in/into <field>
    m = re.match(r"(?:enter|type|input|fill)\s+(.+?)\s+(?:in|into|on|at)\s+(.+)", text, re.I)
    if m:
        return {"action": "enter", "target": m.group(2).strip(), "value": m.group(1).strip()}

    # Enter <field> (just field name, we'll use a default value)
    m = re.match(r"(?:enter|type|input|fill)\s+(.+)", text, re.I)
    if m:
        return {"action": "enter", "target": m.group(1).strip(), "value": ""}

    # Click / Press / Tap
    m = re.match(r"(?:click|press|tap|hit)\s+(?:on\s+)?(?:the\s+)?(.+)", text, re.I)
    if m:
        return {"action": "click", "target": m.group(1).strip(), "value": ""}

    # Wait for
    m = re.match(r"(?:wait|pause)\s+(?:for\s+)?(.+)", text, re.I)
    if m:
        return {"action": "wait", "target": m.group(1).strip(), "value": ""}

    # Verify / Check / Assert
    m = re.match(r"(?:verify|check|assert|confirm|ensure|see|expect)\s+(.+)", text, re.I)
    if m:
        return {"action": "verify", "target": m.group(1).strip(), "value": ""}

    # Select <option> from <dropdown>
    m = re.match(r"(?:select|choose|pick)\s+(.+?)\s+(?:from|in)\s+(.+)", text, re.I)
    if m:
        return {"action": "select", "target": m.group(2).strip(), "value": m.group(1).strip()}

    # Default: treat as a verify/check
    return {"action": "verify", "target": text, "value": ""}


def _execute_step(driver, parsed, base_url):
    """Execute a single parsed step against the browser.

    Returns a message describing what happened.
    """
    action = parsed["action"]
    target = parsed["target"]
    value = parsed["value"]

    if action == "navigate":
        # If target is a relative path, prepend base_url
        if target.startswith("/"):
            url = base_url.rstrip("/") + target
        elif target.startswith("http"):
            url = target
        else:
            url = base_url.rstrip("/") + "/" + target
        driver.get(url)
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        return f"Navigated to {url}"

    elif action == "enter":
        inp = _find_input(driver, target)
        if not inp:
            raise NoSuchElementException(f"Could not find input field for '{target}'")
        inp.clear()
        # If no value provided, generate a sensible default
        if not value:
            input_type = inp.get_attribute("type") or "text"
            defaults = {
                "email": "test@example.com",
                "password": "password123",
                "text": f"test_{target}",
                "number": "42",
            }
            value = defaults.get(input_type, f"test_{target}")
        inp.send_keys(value)
        return f"Entered '{value}' into '{target}'"

    elif action == "click":
        el = _find_clickable(driver, target)
        if not el:
            raise NoSuchElementException(f"Could not find clickable element for '{target}'")
        old_url = driver.current_url
        el.click()
        # Wait for page to stabilize — longer if the URL changes (navigation)
        time.sleep(1)
        try:
            WebDriverWait(driver, 5).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
        except TimeoutException:
            pass
        # If URL changed, give extra time for the new page to render
        if driver.current_url != old_url:
            time.sleep(1)
        return f"Clicked '{target}'"

    elif action == "wait":
        time.sleep(2)
        return f"Waited for '{target}'"

    elif action == "verify":
        page_text = driver.page_source.lower()
        if target.lower() in page_text:
            return f"Verified '{target}' is present on page"
        # Check page title
        if target.lower() in driver.title.lower():
            return f"Verified '{target}' in page title"
        raise AssertionError(f"Could not verify '{target}' on the page")

    elif action == "select":
        from selenium.webdriver.support.ui import Select
        sel_el = _find_input(driver, target)
        if sel_el and sel_el.tag_name == "select":
            Select(sel_el).select_by_visible_text(value)
            return f"Selected '{value}' from '{target}'"
        raise NoSuchElementException(f"Could not find select element for '{target}'")

    return f"Unknown action: {action}"


def execute_test(application_url, steps_raw, expected_outcome):
    """Execute a test scenario against a real application.

    Flow:
      1. Open target URL in headless Chrome
      2. Crawl page with BeautifulSoup → discover interactive elements
      3. Send steps + elements to Gemini LLM → get structured actions
      4. Execute each action with Selenium, taking screenshots + timing
      5. After navigation/clicks, re-discover elements for subsequent steps
      6. Verify expected outcome at the end

    Args:
        application_url: The target application URL (e.g., http://localhost:8080)
        steps_raw: Natural language test steps (free-form text)
        expected_outcome: What the test expects to see at the end

    Returns:
        dict with keys: status, execution_time, failure_message, diagnosis,
                       screenshots, performance, email_sent, step_results
    """
    run_id = uuid.uuid4().hex[:8]
    driver = _create_driver()
    screenshots = []
    performance = {}
    step_results = []
    failure_message = None
    diagnosis = None
    status = "Passed"

    start_time = time.time()

    try:
        # Step 1: Navigate to the application
        driver.get(application_url)
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )

        # Step 2: Discover elements on the landing page
        elements = _discover_elements(driver)

        # Take initial screenshot
        screenshots.append(_take_screenshot(driver, run_id, 0))
        performance["initial_load"] = round(time.time() - start_time, 3)

        # Step 3: Send ALL steps to LLM at once with current page elements
        # The LLM returns structured actions for what it can handle on the
        # current page. After page-changing actions (click/navigate), we
        # re-discover elements and re-send ONLY the unexecuted remaining
        # steps to the LLM for the new page context.
        raw_lines = [l.strip() for l in steps_raw.strip().splitlines() if l.strip()]
        global_step = 0

        # First LLM call: parse all steps against the landing page
        all_actions = parse_steps_with_llm(steps_raw, elements, application_url)

        for action in all_actions:
            action.setdefault("action", "verify")
            action.setdefault("target", "")
            action.setdefault("value", "")
            global_step += 1
            step_start = time.time()

            try:
                result_msg = _execute_step(driver, action, application_url)
                step_results.append({"step": global_step, "text": str(action),
                                     "status": "passed", "message": result_msg})
            except (NoSuchElementException, TimeoutException,
                    AssertionError, WebDriverException) as e:
                # Step failed — record failure
                failure_screenshot = _take_screenshot(driver, run_id, f"{global_step}_failure")
                screenshots.append(failure_screenshot)
                failure_message = f"{str(e)} at step {global_step}"
                diagnosis = _generate_diagnosis(driver, str(action), str(e))
                status = "Failed"
                step_results.append({"step": global_step, "text": str(action),
                                     "status": "failed", "message": str(e)})
                break

            # Take screenshot after successful step
            screenshots.append(_take_screenshot(driver, run_id, global_step))
            step_time = round(time.time() - step_start, 3)
            performance[f"step_{global_step}"] = step_time

            # Re-discover elements after clicks/navigation (page may have changed)
            if action.get("action") in ("click", "navigate"):
                time.sleep(1)
                try:
                    WebDriverWait(driver, 5).until(
                        lambda d: d.execute_script("return document.readyState") == "complete"
                    )
                except TimeoutException:
                    pass
                elements = _discover_elements(driver)

        # Step 5: Verify the expected outcome
        if status == "Passed" and expected_outcome:
            page_source = driver.page_source.lower()
            title = driver.title.lower()
            expected_lower = expected_outcome.lower()
            if expected_lower not in page_source and expected_lower not in title:
                words = expected_lower.split()
                match_count = sum(1 for w in words if w in page_source or w in title)
                if match_count < len(words) / 2:
                    status = "Failed"
                    failure_message = (
                        f"Expected outcome not found: '{expected_outcome}'. "
                        f"Current page: {driver.title}"
                    )
                    diagnosis = _generate_diagnosis(
                        driver, f"Verify: {expected_outcome}", failure_message
                    )
                    screenshots.append(
                        _take_screenshot(driver, run_id, "final_failure")
                    )

    except WebDriverException as e:
        status = "Failed"
        failure_message = f"Browser error: {str(e)}"
        diagnosis = f"The target application at {application_url} may be unreachable or returned an error."
    except Exception as e:
        status = "Failed"
        failure_message = f"Execution error: {str(e)}"
        diagnosis = f"An error occurred during test execution: {str(e)}"

    finally:
        execution_time = round(time.time() - start_time, 2)
        driver.quit()

    return {
        "status": status,
        "execution_time": execution_time,
        "failure_message": failure_message,
        "diagnosis": diagnosis,
        "screenshots": screenshots,
        "performance": performance,
        "email_sent": status == "Failed",
        "step_results": step_results,
    }


def _generate_diagnosis(driver, step_text, error_msg):
    """Generate a diagnostic message based on the failure context.

    Analyzes the current page state to provide actionable suggestions.
    """
    try:
        soup = BeautifulSoup(driver.page_source, "html.parser")
        title = soup.title.string if soup.title else "Unknown"
        # Check for common error indicators
        error_indicators = soup.find_all(
            class_=re.compile(r"error|alert|warning|danger", re.I)
        )
        page_errors = [el.get_text(strip=True)[:100] for el in error_indicators[:3]]

        parts = [f"Step failed: '{step_text}'"]
        parts.append(f"Error: {error_msg}")
        parts.append(f"Current page: {title}")

        if page_errors:
            parts.append(f"Page errors detected: {'; '.join(page_errors)}")

        # Suggest possible causes
        if "not find" in error_msg.lower():
            available = _discover_elements(driver)
            btn_texts = [b["text"] for b in available["buttons"] if b["text"]]
            input_names = [i["name"] or i["id"] for i in available["inputs"] if i["name"] or i["id"]]
            if btn_texts:
                parts.append(f"Available buttons: {', '.join(btn_texts[:5])}")
            if input_names:
                parts.append(f"Available inputs: {', '.join(input_names[:5])}")
            parts.append("Suggestion: Check that the element name in the test step matches "
                         "the actual UI element on the target application.")

        if "timeout" in error_msg.lower():
            parts.append("Suggestion: The page may be slow to load or the element "
                         "may not exist. Check the application URL and network connectivity.")

        return " | ".join(parts)

    except Exception:
        return f"Failed at step: '{step_text}'. Error: {error_msg}"
