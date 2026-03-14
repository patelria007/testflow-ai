"""LLM-powered natural language to Selenium action translator.

Uses Google Gemini to interpret free-form test steps and map them to
structured Selenium commands based on the actual elements discovered
on the target page via BeautifulSoup.
"""

import json
import os

from google import genai

# Load Gemini API key from .config file
_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", ".claude", ".config")


def _load_api_key():
    """Read the Gemini API key from the .config file."""
    try:
        with open(_CONFIG_PATH) as f:
            for line in f:
                if "gemini_token" in line:
                    return line.split("=", 1)[1].strip().strip("'\"")
    except FileNotFoundError:
        pass
    # Fallback to environment variable
    return os.environ.get("GEMINI_API_KEY", "")


def parse_steps_with_llm(steps_raw, page_elements, page_url):
    """Send natural language steps + page elements to Gemini, get structured actions.

    Args:
        steps_raw: The user's free-form natural language test steps.
        page_elements: Dict of discovered elements from BeautifulSoup
                       (inputs, buttons, links, forms).
        page_url: The target application URL.

    Returns:
        List of action dicts: [{"action": str, "target": str, "value": str}, ...]
    """
    api_key = _load_api_key()
    if not api_key:
        raise ValueError("Gemini API key not found in .config or GEMINI_API_KEY env var")

    client = genai.Client(api_key=api_key)

    prompt = f"""You are a test automation assistant. Your job is to convert natural language
test steps into structured Selenium commands.

TARGET APPLICATION: {page_url}

CURRENT PAGE ELEMENTS (discovered via BeautifulSoup — this is the starting page only):

INPUTS:
{json.dumps(page_elements.get('inputs', []), indent=2)}

BUTTONS:
{json.dumps(page_elements.get('buttons', []), indent=2)}

LINKS:
{json.dumps(page_elements.get('links', []), indent=2)}

FORMS:
{json.dumps(page_elements.get('forms', []), indent=2)}

USER'S TEST STEPS (natural language):
{steps_raw}

Convert EVERY user step into a structured JSON action. Use ONLY these action types:
- "navigate": Go to a URL. target = the URL path or full URL.
- "enter": Type text into an input field. target = the best matching input identifier (name, id, or type). value = what to type.
- "click": Click an element. target = the best matching button text, link text, or identifier.
- "wait": Wait for something. target = description of what to wait for.
- "verify": Check something is on the page. target = text or element to verify.
- "select": Pick from a dropdown. target = the select element identifier. value = option text.

CRITICAL RULES:
1. Generate actions for ALL steps — do NOT skip any step.
2. The page elements shown are only from the STARTING page. After clicks/navigation, new pages will load with different elements. You must still generate actions for those later steps using your best guess for element names (e.g., "name", "title", "Save", "Submit").
3. For steps on the current page, match to the ACTUAL elements listed above.
4. For steps on pages that will appear later (after login, after navigation), use common sense for element names — web apps typically use standard names like "name", "title", "email", "submit", etc.
5. If the user says "click sign in" and there's a button with text="Sign in", use target="Sign in".
6. For login steps, if no explicit credentials are given, use reasonable defaults like "admin"/"admin".
7. Ignore any formatting artifacts like markdown, pipes, or bullet points — focus on the intent.
8. Each user step should produce at least one action. A single natural language step like "log in with admin/admin" should produce multiple actions (enter username, enter password, click submit).

Return ONLY a valid JSON array, no other text. Example:
[
  {{"action": "enter", "target": "username", "value": "admin"}},
  {{"action": "enter", "target": "password", "value": "admin"}},
  {{"action": "click", "target": "Sign in"}},
  {{"action": "click", "target": "New project"}},
  {{"action": "enter", "target": "name", "value": "My Project"}},
  {{"action": "click", "target": "Save"}}
]"""

    # Try available Gemini models in order of preference
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
        raise RuntimeError("No available Gemini model could process the request")

    # Parse the JSON response
    text = response.text.strip()
    # Remove markdown code fence if present
    if text.startswith("```"):
        text = text.split("\n", 1)[1]  # remove first line
        text = text.rsplit("```", 1)[0]  # remove last fence
        text = text.strip()

    actions = json.loads(text)
    return actions
