"""AI-powered failure diagnosis engine (Scenario 3).

Analyzes test failures using Gemini LLM to determine:
  1. Root cause category: test_design, application_bug, or environment
  2. Detailed explanation of what went wrong
  3. Actionable fix — either improved test steps or application fix suggestions

The analyzer receives the full failure context (error message, page state,
available elements, test steps, expected outcome) and returns a structured
diagnosis that the UI can render with clear next steps.
"""

import json
import os

from google import genai


_PROJECT_ROOT = os.path.join(os.path.dirname(__file__), "..")
_ENV_PATH = os.path.join(_PROJECT_ROOT, ".env")
_CONFIG_PATH = os.path.join(_PROJECT_ROOT, ".claude", ".config")


def _load_api_key():
    """Read the Gemini API key from .env, environment variable, or legacy .config.

    Checks the project .env file first, then legacy .claude/.config, then
    the GEMINI_API_KEY environment variable.

    @return: API key string, or empty string if not found
    """
    for path in (_ENV_PATH, _CONFIG_PATH):
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    if key.strip() in ("GEMINI_API_KEY", "gemini_token"):
                        return value.strip().strip("'\"")
        except FileNotFoundError:
            continue
    return os.environ.get("GEMINI_API_KEY", "")


def analyze_failure(error_message, step_text, page_title, page_errors,
                    available_elements, test_steps, expected_outcome, page_url):
    """Send failure context to Gemini and get a structured diagnosis.

    Constructs a prompt with full failure context and sends it to Gemini LLM.
    Falls back to rule-based analysis if the API key is missing or the call fails.

    @param error_message: The error that caused the test to fail
    @param step_text: Description of the step that failed
    @param page_title: Title of the page when the failure occurred
    @param page_errors: List of error text strings visible on the page
    @param available_elements: Dict of interactive elements discovered on the page
    @param test_steps: Original natural language test steps
    @param expected_outcome: Expected outcome of the test
    @param page_url: URL of the page where the failure occurred
    @return: Dict with keys: category, summary, explanation, suggestion, proposed_fix
    """
    api_key = _load_api_key()
    if not api_key:
        return _fallback_analysis(error_message, step_text, available_elements)

    prompt = f"""You are a test failure diagnosis expert. A black-box end-to-end test just failed.
Analyze the failure and determine the root cause.

FAILURE CONTEXT:
- Failed step: {step_text}
- Error message: {error_message}
- Current page title: {page_title}
- Page URL: {page_url}
- Errors visible on page: {json.dumps(page_errors) if page_errors else "None"}

AVAILABLE PAGE ELEMENTS:
- Buttons: {json.dumps(available_elements.get('buttons', [])[:10])}
- Inputs: {json.dumps(available_elements.get('inputs', [])[:10])}
- Links: {json.dumps(available_elements.get('links', [])[:10])}

ORIGINAL TEST STEPS:
{test_steps}

EXPECTED OUTCOME: {expected_outcome}

TASK: Classify the failure into ONE of these categories and provide actionable advice.

Categories:
1. "test_design" — The test steps are incorrect, incomplete, or reference elements that don't match the actual UI. For example: wrong button name, missing a prerequisite step, wrong field name, incorrect expected outcome.
2. "application_bug" — The application itself has a problem. The test steps are reasonable but the app is not functioning correctly. For example: error messages on page, broken functionality, server errors, unexpected behavior.
3. "environment" — Something outside both the test and app caused the failure. For example: network timeout, browser crash, service unavailable, DNS failure, port not reachable.

Return ONLY valid JSON with this exact structure:
{{
  "category": "test_design" or "application_bug" or "environment",
  "summary": "One sentence summarizing what went wrong",
  "explanation": "2-3 sentences explaining the root cause in detail",
  "suggestion": "What the user should do next",
  "proposed_fix": "If category is test_design: provide the COMPLETE improved test steps (all lines, not just the fix). If category is application_bug: describe specifically what needs to be fixed in the application. If category is environment: describe what to check."
}}"""

    try:
        client = genai.Client(api_key=api_key)
        models_to_try = ["gemini-2.5-flash", "gemini-2.0-flash-001", "gemini-2.0-flash-lite"]
        response = None
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                )
                break
            except Exception:
                continue

        if response is None:
            return _fallback_analysis(error_message, step_text, available_elements)

        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1]
            text = text.rsplit("```", 1)[0]
            text = text.strip()

        result = json.loads(text)
        # Ensure all required keys exist
        for key in ("category", "summary", "explanation", "suggestion", "proposed_fix"):
            result.setdefault(key, "")
        if result["category"] not in ("test_design", "application_bug", "environment"):
            result["category"] = "environment"
        return result

    except Exception:
        return _fallback_analysis(error_message, step_text, available_elements)


def _fallback_analysis(error_message, step_text, available_elements):
    """Perform rule-based failure analysis when Gemini is unavailable.

    Classifies the error into environment, test_design, or application_bug
    categories based on keyword matching in the error message.

    @param error_message: The error that caused the test to fail
    @param step_text: Description of the step that failed
    @param available_elements: Dict of interactive elements discovered on the page
    @return: Dict with keys: category, summary, explanation, suggestion, proposed_fix
    """
    error_lower = error_message.lower()
    btn_texts = [b.get("text", "") for b in available_elements.get("buttons", []) if b.get("text")]
    input_names = [i.get("name") or i.get("id") for i in available_elements.get("inputs", []) if i.get("name") or i.get("id")]

    # Environment issues
    if any(kw in error_lower for kw in ("timeout", "unreachable", "connection refused",
                                         "dns", "err_connection", "browser error")):
        return {
            "category": "environment",
            "summary": "The target application or network is not responding.",
            "explanation": f"The test failed with: {error_message}. This typically indicates "
                           "the target application is down, the URL is incorrect, or there is "
                           "a network connectivity issue.",
            "suggestion": "Verify the target application is running and accessible at the configured URL.",
            "proposed_fix": "Check that the application server is running, the port is correct, "
                            "and there are no firewall or network issues blocking the connection.",
        }

    # Element not found — likely test design issue
    if "not find" in error_lower or "no such element" in error_lower:
        available_info = ""
        if btn_texts:
            available_info += f"Available buttons: {', '.join(btn_texts[:5])}. "
        if input_names:
            available_info += f"Available inputs: {', '.join(input_names[:5])}. "

        return {
            "category": "test_design",
            "summary": f"The test references an element that doesn't exist on the page.",
            "explanation": f"Step '{step_text}' failed because the referenced element was not found "
                           f"on the current page. {available_info}"
                           "This usually means the test step uses a wrong name or the step order "
                           "is incorrect (e.g., trying to interact with an element before navigating "
                           "to the right page).",
            "suggestion": "Update the test steps to match the actual elements on the page.",
            "proposed_fix": f"Review the failed step and update element references to match "
                            f"what's available. {available_info}",
        }

    # Application errors on page
    if any(kw in error_lower for kw in ("error", "500", "exception", "server error", "forbidden")):
        return {
            "category": "application_bug",
            "summary": "The application returned an error during test execution.",
            "explanation": f"The test encountered an application error: {error_message}. "
                           "The test steps appear correct, but the application is not handling "
                           "the interaction properly.",
            "suggestion": "Investigate the application logs for the root cause of this error.",
            "proposed_fix": "Check application server logs, database connectivity, and any "
                            "recent deployments that may have introduced this bug.",
        }

    # Assertion / verification failure
    if "verify" in error_lower or "assert" in error_lower or "expected" in error_lower:
        return {
            "category": "test_design",
            "summary": "The expected outcome does not match what the application shows.",
            "explanation": f"Verification failed: {error_message}. The application may be working "
                           "correctly but producing different output than what the test expects, "
                           "or the test's expected outcome may need updating.",
            "suggestion": "Check if the expected outcome text matches the actual application output.",
            "proposed_fix": "Update the expected outcome to match the actual text shown by the "
                            "application, or fix the test steps if they navigate to the wrong page.",
        }

    # Generic fallback
    return {
        "category": "environment",
        "summary": f"Test failed: {error_message[:100]}",
        "explanation": f"The test failed at step '{step_text}' with error: {error_message}.",
        "suggestion": "Review the error details and check both the test configuration and application state.",
        "proposed_fix": "Verify the application is running correctly and the test steps are accurate.",
    }
