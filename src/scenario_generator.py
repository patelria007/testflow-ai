"""LLM-powered test scenario generator.

Takes a site map from the crawler and uses Gemini to generate
test scenarios based on the discovered pages and elements.
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


def generate_scenarios(site_map, max_scenarios=3, complexity="medium", focus_areas=""):
    """Generate test scenarios from a crawled site map using Gemini LLM.

    Constructs a prompt with the site description, complexity setting, and focus
    areas, sends it to Gemini, and parses the JSON response into scenario dicts.

    @param site_map: Dict from crawl_site() with keys 'pages', 'app_url', 'user_notes'
    @param max_scenarios: Maximum number of scenarios to generate
    @param complexity: Step count level: 'simple' (2-3), 'medium' (3-5), or 'complex' (5-8)
    @param focus_areas: Comma-separated list of areas to focus on (e.g., 'authentication,navigation')
    @return: List of scenario dicts, each with keys: name, steps, expected_outcome, category
    @throws ValueError: When the Gemini API key is not found
    @throws RuntimeError: When no available Gemini model can process the request
    """
    api_key = _load_api_key()
    if not api_key:
        raise ValueError("Gemini API key not found")

    client = genai.Client(api_key=api_key)

    # Build a concise description of the site for the LLM
    site_description = _build_site_description(site_map)
    user_notes = site_map.get("user_notes", "")

    # Map complexity to step ranges
    complexity_map = {
        "simple": "2-3 steps per scenario. Keep it basic — single actions like login or navigate.",
        "medium": "3-5 steps per scenario. Cover a complete user workflow.",
        "complex": "5-8 steps per scenario. Cover end-to-end multi-page flows with validations.",
    }
    complexity_instruction = complexity_map.get(complexity, complexity_map["medium"])

    # Build focus areas instruction
    focus_instruction = ""
    if focus_areas:
        areas = [a.strip() for a in focus_areas.split(",") if a.strip()]
        if areas:
            focus_instruction = f"\nFOCUS AREAS (prioritize these categories): {', '.join(areas)}\n"

    prompt = f"""You are a QA test engineer. Based on the following analysis of a web application,
generate exactly {max_scenarios} end-to-end test scenarios.

APPLICATION URL: {site_map['app_url']}

{"USER NOTES (from the tester — use these for credentials, context, and focus areas):" + chr(10) + user_notes + chr(10) if user_notes else ""}
COMPLEXITY: {complexity_instruction}
{focus_instruction}
SITE ANALYSIS:
{site_description}

Generate exactly {max_scenarios} test scenarios. Each scenario should be a realistic user flow
that tests an important feature of the application.

RULES:
1. Each scenario must have: name, steps (natural language), expected_outcome, and category.
2. Steps should be written as a user would describe them naturally (e.g., "Log in with admin/admin", "Click on Create Project").
3. Expected outcome should describe what the user expects to see after all steps complete.
4. Category should be one of: authentication, navigation, crud, search, error_handling.
5. Make scenarios diverse — don't generate all the same category. Cover different features.
6. Steps should reference actual elements and links you see in the site analysis.
7. Follow the COMPLEXITY instruction above for the number of steps per scenario.
8. If FOCUS AREAS are specified, ensure most scenarios cover those areas.
9. If the user provided credentials in notes, use those exact credentials in the test steps.
10. Each step should be on its own line (separated by newline).

Return ONLY a valid JSON array, no other text. Example format:
[
  {{
    "name": "Successful Login",
    "steps": "Go to the login page\\nEnter admin as username\\nEnter admin as password\\nClick Sign In",
    "expected_outcome": "Dashboard page is displayed",
    "category": "authentication"
  }}
]"""

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

    text = response.text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        text = text.rsplit("```", 1)[0]
        text = text.strip()

    scenarios = json.loads(text)
    return scenarios[:max_scenarios]


def _build_site_description(site_map):
    """Build a concise text description of the site map for the LLM prompt.

    Formats each crawled page's forms, buttons, links, and standalone inputs
    into a human-readable summary.

    @param site_map: Dict from crawl_site() containing a 'pages' list
    @return: Formatted string describing all discovered pages and their elements
    """
    parts = []
    for i, page in enumerate(site_map["pages"]):
        parts.append(f"\n--- Page {i+1}: {page['title']} ({page['url']}) ---")

        if page["forms"]:
            parts.append("Forms:")
            for form in page["forms"]:
                fields_desc = ", ".join(
                    f"{f['name']}({f['type']})" for f in form["fields"]
                )
                parts.append(f"  - {form['method'].upper()} {form['action']}: [{fields_desc}]")

        if page["buttons"]:
            parts.append("Buttons: " + ", ".join(b["text"] for b in page["buttons"]))

        if page["links"]:
            # Show top 10 most relevant links
            links_desc = ", ".join(
                f"\"{l['text']}\" -> {l['href']}" for l in page["links"][:10]
            )
            parts.append(f"Links: {links_desc}")

        if page["inputs"] and not page["forms"]:
            inputs_desc = ", ".join(
                f"{i['name'] or i['id']}({i['type']})" for i in page["inputs"]
            )
            parts.append(f"Standalone inputs: {inputs_desc}")

    return "\n".join(parts)
