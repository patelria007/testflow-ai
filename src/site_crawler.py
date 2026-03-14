"""Multi-page site crawler using Selenium + BeautifulSoup.

Crawls a target application (2-3 pages deep) and builds a site map
containing all interactive elements discovered on each page.
"""

import time

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import WebDriverException


def _create_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1280,900")
    return webdriver.Chrome(options=options)


def _extract_page_info(driver):
    """Extract all interactive elements and metadata from the current page."""
    soup = BeautifulSoup(driver.page_source, "html.parser")

    page = {
        "url": driver.current_url,
        "title": driver.title,
        "inputs": [],
        "buttons": [],
        "links": [],
        "forms": [],
    }

    for inp in soup.find_all(["input", "textarea", "select"]):
        if inp.get("type") == "hidden":
            continue
        page["inputs"].append({
            "tag": inp.name,
            "type": inp.get("type", "text"),
            "name": inp.get("name", ""),
            "id": inp.get("id", ""),
            "placeholder": inp.get("placeholder", ""),
        })

    for btn in soup.find_all("button"):
        text = btn.get_text(strip=True)
        if text:
            page["buttons"].append({"text": text, "type": btn.get("type", "")})

    for a in soup.find_all("a", href=True):
        text = a.get_text(strip=True)
        href = a["href"]
        if text and not href.startswith(("#", "javascript:", "mailto:")):
            page["links"].append({"text": text, "href": href})

    for form in soup.find_all("form"):
        fields = []
        for f in form.find_all(["input", "textarea", "select"]):
            if f.get("type") != "hidden":
                fields.append({
                    "tag": f.name,
                    "type": f.get("type", "text"),
                    "name": f.get("name", ""),
                })
        if fields:
            page["forms"].append({
                "action": form.get("action", ""),
                "method": form.get("method", "get"),
                "fields": fields,
            })

    return page


def crawl_site(url, max_pages=3, user_notes=""):
    """Crawl a target application and return a site map.

    Args:
        url: The starting URL to crawl.
        max_pages: Maximum number of pages to visit (default 3).
        user_notes: Optional notes from the user (e.g., credentials, hints).

    Returns:
        dict with:
            - "pages": list of page info dicts
            - "app_url": the starting URL
            - "user_notes": the user's custom notes
            - "error": error message if crawl failed, else None
    """
    driver = _create_driver()
    visited = set()
    pages = []

    try:
        # Page 1: Landing page
        driver.get(url)
        WebDriverWait(driver, 10).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        time.sleep(1)

        landing = _extract_page_info(driver)
        pages.append(landing)
        visited.add(driver.current_url)

        # Try to log in if the page has a login form and user provided credentials
        _try_auto_login(driver, landing, user_notes)
        # After login attempt, re-check if page changed
        if driver.current_url not in visited:
            post_login = _extract_page_info(driver)
            pages.append(post_login)
            visited.add(driver.current_url)
            # Use the post-login page as the base for further crawling
            landing = post_login

        # Find interesting links to follow (prioritize auth, create, settings)
        priority_keywords = ["login", "register", "sign", "create", "new", "add",
                             "settings", "profile", "dashboard", "project", "admin"]

        links_to_visit = []
        base = url.rstrip("/")
        for link in landing["links"]:
            href = link["href"]
            # Build full URL
            if href.startswith("/"):
                full_url = base + href
            elif href.startswith("http"):
                full_url = href
            else:
                full_url = base + "/" + href

            # Skip external links
            if not full_url.startswith(base):
                continue
            if full_url in visited:
                continue

            # Prioritize interesting pages
            score = sum(1 for kw in priority_keywords if kw in href.lower() or kw in link["text"].lower())
            links_to_visit.append((score, full_url, link["text"]))

        # Sort by priority score (highest first)
        links_to_visit.sort(key=lambda x: -x[0])

        # Visit top pages up to max_pages
        for _, link_url, link_text in links_to_visit[:max_pages - 1]:
            if link_url in visited:
                continue
            try:
                driver.get(link_url)
                WebDriverWait(driver, 10).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
                time.sleep(1)
                page_info = _extract_page_info(driver)
                pages.append(page_info)
                visited.add(driver.current_url)
            except WebDriverException:
                continue

        return {"pages": pages, "app_url": url, "user_notes": user_notes, "error": None}

    except WebDriverException as e:
        return {"pages": pages, "app_url": url, "user_notes": user_notes, "error": str(e)}
    finally:
        driver.quit()


def _try_auto_login(driver, page_info, user_notes):
    """Attempt to log in if the page has a login form.

    Extracts credentials from user_notes or tries common defaults.
    """
    # Check if this looks like a login page
    has_password = any(
        i["type"] == "password" for i in page_info["inputs"]
    )
    if not has_password:
        return

    # Extract credentials from user notes
    username, password = _parse_credentials(user_notes)
    if not username:
        return

    # Find and fill the username/email field
    from selenium.webdriver.common.by import By
    try:
        inputs = driver.find_elements(By.CSS_SELECTOR, "input:not([type='hidden'])")
        password_field = None
        username_field = None

        for inp in inputs:
            inp_type = inp.get_attribute("type") or "text"
            inp_name = (inp.get_attribute("name") or "").lower()
            if inp_type == "password":
                password_field = inp
            elif inp_type in ("text", "email") and not username_field:
                username_field = inp

        if username_field and password_field:
            username_field.clear()
            username_field.send_keys(username)
            password_field.clear()
            password_field.send_keys(password)

            # Click submit
            try:
                btn = driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                btn.click()
            except Exception:
                try:
                    btn = driver.find_element(By.CSS_SELECTOR, "input[type='submit']")
                    btn.click()
                except Exception:
                    return

            time.sleep(2)
            from selenium.webdriver.support.ui import WebDriverWait
            try:
                WebDriverWait(driver, 5).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            except Exception:
                pass

    except Exception:
        pass


def _parse_credentials(user_notes):
    """Extract username/password from user notes text.

    Looks for patterns like:
      - username: admin, password: admin
      - login with admin/admin
      - user=admin pass=admin
      - credentials: admin admin
    """
    import re
    if not user_notes:
        return None, None

    notes_lower = user_notes.lower()

    # Pattern: username: X password: Y (or user/pass variants)
    m = re.search(
        r"(?:username|user|login|email)\s*[:=]\s*(\S+)", notes_lower
    )
    username = m.group(1).strip(",.;'\"") if m else None

    m = re.search(
        r"(?:password|pass|pwd)\s*[:=]\s*(\S+)", notes_lower
    )
    password = m.group(1).strip(",.;'\"") if m else None

    # Pattern: login with X/Y or credentials X Y
    if not username or not password:
        m = re.search(r"(\S+)\s*/\s*(\S+)", user_notes)
        if m:
            username = username or m.group(1).strip(",.;'\"")
            password = password or m.group(2).strip(",.;'\"")

    return username, password
