"""LLM-powered test scenario generator.

Takes a site map from the crawler and uses Gemini to generate
test scenarios based on the discovered pages and elements.
"""

import json
import os

from google import genai

_CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", ".claude", ".config")


def _load_api_key():
    try:
        with open(_CONFIG_PATH) as f:
            for line in f:
                if "gemini_token" in line:
                    return line.split("=", 1)[1].strip().strip("'\"")
    except FileNotFoundError:
        pass
    return os.environ.get("GEMINI_API_KEY", "")


def generate_scenarios(site_map, max_scenarios=3, complexity="medium", focus_areas=""):
    """Generate test scenarios from a crawled site map.

    Args:
        site_map: dict from crawl_site() with "pages" and "app_url"
        max_scenarios: Maximum number of scenarios to generate
        complexity: "simple" (2-3 steps), "medium" (3-5 steps), "complex" (5-8 steps)
        focus_areas: Comma-separated list of areas to focus on

    Returns:
        list of scenario dicts: [{"name", "steps", "expected_outcome", "category"}, ...]
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
    """Build a concise text description of the site map for the LLM prompt."""
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
