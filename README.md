# Black-Box End-to-End Testing SaaS Platform

## Project Description

A SaaS platform that tests applications from the user's perspective without requiring access to internal code. The platform validates complete user workflows across web applications using AI-powered intelligent testing capabilities.

### Key Features

- **Natural Language Test Creation**: Define test scenarios in plain English without coding
- **Real Browser Execution**: Selenium + BeautifulSoup execute tests against real target applications
- **AI-Powered Step Parsing**: Google Gemini LLM translates natural language steps into Selenium commands
- **Auto-Discovery**: Crawl any web app and auto-generate test scenarios with AI
- **Intelligent Failure Diagnosis**: AI categorizes failures (test design / application bug / environment) with actionable fix suggestions
- **Saved Applications & Credentials**: Store target app auth securely — never expose credentials in test steps
- **Comprehensive Reporting**: Real screenshots, performance metrics, and execution logs
- **Smart Notifications**: Configure report email for test failure alerts

## Setup

### 1. Install Docker
- **macOS/Windows**: Download [Docker Desktop](https://www.docker.com/products/docker-desktop)
- **Linux**: Follow [Docker installation guide](https://docs.docker.com/engine/install/)

### 2. Clone and Navigate to Project
```bash
git clone https://github.com/tmehtiyev2019/testflow-ai.git
cd testflow-ai
```

### 3. Build Docker Image
```bash
docker-compose build
```

### 4. Verify Installation
```bash
docker-compose run --rm testflow behave --version
# Expected output: behave 1.2.6
```

## Running Acceptance Tests

### Run Scenario 1 (Test Creation)
```bash
docker-compose run --rm testflow behave acceptance_tests/test_creation.feature
```

Expected output:
```
Feature: Test Scenario Creation
  Scenario: Create a simple web application test using natural language
    Given I am logged into the testing platform                                   # PASSED
    When I navigate to the "Create Test" page                                     # PASSED
    And I enter the test name "Checkout Flow Validation"                          # PASSED
    And I enter the application URL "https://example-shop.com"                    # PASSED
    And I provide the test steps in natural language:                             # PASSED
    And I set expected outcome "Cart displays 1 item successfully"                # PASSED
    And I click "Save Test"                                                       # PASSED
    Then I should see a confirmation message "Test scenario created successfully" # PASSED
    And the test should appear in my test list with status "Not Run"              # PASSED

1 feature passed, 0 failed, 0 skipped
1 scenario passed, 0 failed, 0 skipped
9 steps passed, 0 failed, 0 skipped
```

### Run Scenario 2 (Test Execution and Monitoring)
```bash
docker-compose run --rm testflow behave acceptance_tests/test_execution.feature
```

Expected output:
```
Feature: Test Execution and Monitoring

  Scenario: Execute a web application test and view results
    Given I have a saved test scenario "User Login Flow"            # PASSED
    And the test contains the following steps:                      # PASSED
    When I click "Run Test" for "User Login Flow"                   # PASSED
    And I wait for test execution to complete                       # PASSED
    Then I should see test status as "Passed"                       # PASSED
    And I should see execution time in seconds                      # PASSED
    And I should see screenshots for each step                      # PASSED
    And I should see performance metrics showing page load times    # PASSED

  Scenario: View detailed failure report when test fails
    Given I have a test scenario "Payment Processing"                                                           # PASSED
    And the test is configured to verify "Payment confirmation message"                                         # PASSED
    When I execute the test                                                                                     # PASSED
    And the payment API returns a timeout error                                                                 # PASSED
    Then I should see test status as "Failed"                                                                   # PASSED
    And I should see failure message "Payment API timeout at step 7"                                            # PASSED
    And I should see a screenshot of the failure point                                                          # PASSED
    And I should see AI-powered diagnosis suggesting "Payment gateway may be down or experiencing high latency" # PASSED
    And I should receive an email notification about the failure                                                # PASSED

1 feature passed, 0 failed, 0 skipped
2 scenarios passed, 0 failed, 0 skipped
17 steps passed, 0 failed, 0 skipped
```

### Run Scenario 3 (Intelligent Failure Diagnosis)
```bash
docker-compose run --rm testflow behave acceptance_tests/failure_diagnosis.feature
```

Expected output:
```
Feature: Intelligent Failure Diagnosis

  Scenario: View AI diagnosis with category classification when test fails
    Given I am logged in and have a failing test "Payment Processing" ...       # PASSED
    When I run the failing test                                                 # PASSED
    Then I should see the test status is "Failed"                               # PASSED
    And I should see a failure category badge "Application Bug"                 # PASSED
    And I should see a diagnosis summary                                        # PASSED
    And I should see a diagnosis explanation containing "payment"               # PASSED
    And I should see a recommendation section                                   # PASSED
    And I should see a proposed fix section                                     # PASSED
    And I should see a "Re-run Test" action button                              # PASSED

  Scenario: View test design failure and apply AI-suggested fix
    Given I am logged in and have a failing test "Broken Selector Test" ...     # PASSED
    When I run the failing test                                                 # PASSED
    Then I should see the test status is "Failed"                               # PASSED
    And I should see a failure category badge "Test Design Issue"               # PASSED
    And I should see an "Apply Suggested Fix" button                            # PASSED
    And I should see an "Edit Test Manually" link                               # PASSED
    When I click "Apply Suggested Fix"                                          # PASSED
    Then I should be redirected to the test list                                # PASSED
    And I should see a flash message "Test steps updated with AI suggestion"    # PASSED
    And the test status should be reset to "Not Run"                            # PASSED

  Scenario: View environment failure diagnosis with retry option
    Given I am logged in and have a failing test "Unreachable App Test" ...     # PASSED
    When I run the failing test                                                 # PASSED
    Then I should see the test status is "Failed"                               # PASSED
    And I should see a failure category badge "Environment Issue"               # PASSED
    And I should see a diagnosis explanation containing "could not be reached"  # PASSED
    And I should see a "Retry Test" action button                               # PASSED

1 feature passed, 0 failed, 0 skipped
3 scenarios passed, 0 failed, 0 skipped
25 steps passed, 0 failed, 0 skipped
```

### Run All Implemented Acceptance Tests (Scenarios 1, 2 & 3)
```bash
docker-compose run --rm testflow behave acceptance_tests/test_creation.feature acceptance_tests/test_execution.feature acceptance_tests/failure_diagnosis.feature
```

Expected output:
```
3 features passed, 0 failed, 0 skipped
6 scenarios passed, 0 failed, 0 skipped
51 steps passed, 0 failed, 0 skipped
```

### Run All Acceptance Tests
```bash
docker-compose run --rm testflow behave acceptance_tests/
```

Note: Scenario 4 (SWAP Challenge) is not yet implemented and will error with `NotImplementedError`.

## Running the Application (Interactive Mode with Real Target App)

Beyond acceptance tests, TestFlow AI can execute tests against real web applications using Selenium + Gemini LLM. This section explains how to set up and use the interactive mode.

### Prerequisites

- **Python 3.11+** installed locally
- **Google Chrome** installed (Selenium uses it in headless mode)
- **Docker Desktop** installed and running (for the target application)
- **Google Gemini API key** (for AI-powered step parsing and scenario generation)

### Step 1: Install Python Dependencies

```bash
pip install -r requirements.txt
```

### Step 2: Configure Gemini API Key

Create a config file with your Gemini API key:

```bash
mkdir -p .claude
echo "gemini_token='YOUR_GEMINI_API_KEY'" > .claude/.config
```

You can get a free Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey).

### Step 3: Deploy a Target Application (Kanboard)

The project uses [Kanboard](https://kanboard.org/) (open-source project management tool) as a demo target application:

```bash
docker run -d -p 8080:80 --name kanboard kanboard/kanboard
```

Verify it is running:
```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8080
# Expected: 200
```

Kanboard will be available at `http://localhost:8080` with default credentials:
- **Username**: `admin`
- **Password**: `admin`

### Step 4: Start TestFlow AI

```bash
python3 -c "from src.app import create_app; app = create_app(); app.run(port=5001)"
```

Open `http://localhost:5001` in your browser and login with:
- **Email**: `test@example.com`
- **Password**: `password123`

### Step 5: Create and Run a Test (Manual)

1. Click **"+ New Test"**
2. Fill in:
   - **Name**: `Kanboard Login & Create Project`
   - **URL**: `http://localhost:8080`
   - **Steps**:
     ```
     Log into the application using admin as both username and password
     After logging in, click on New project
     Type My Demo Project as the project name
     Save the project
     ```
   - **Expected Outcome**: `My Demo Project`
3. Click **"Save Test"**
4. Click **"Run Test"** — a loading overlay shows progress while:
   - Headless Chrome launches and navigates to Kanboard
   - BeautifulSoup discovers page elements
   - Gemini LLM translates steps to Selenium commands
   - Selenium executes each action with real screenshots
5. View results: status, execution time, real screenshots, performance metrics

### Step 5b: Failure Diagnosis (Scenario 3)

When a test fails, the results page now shows an **AI-powered diagnosis** with:

1. **Failure Category** — color-coded badge:
   - **Test Design Issue** (yellow) — your test steps are wrong or incomplete
   - **Application Bug** (red) — the target app has a problem
   - **Environment Issue** (blue) — network/timeout/infrastructure problem
2. **Detailed Explanation** — what went wrong and why
3. **Recommendation** — what to do next
4. **Proposed Fix** — either improved test steps or application fix description
5. **Action Buttons**:
   - **Apply Suggested Fix** — one-click updates test steps with AI suggestion
   - **Edit Test Manually** — opens the test editor
   - **Re-run / Retry Test** — re-execute after fixing the issue

### Step 5c: Settings & Saved Applications

1. Click **"Settings"** in the navigation bar
2. **Report Email** — enter your email to receive test failure notifications
3. **Saved Applications** — add target apps with their credentials:
   - Click **"+ Add Application"**
   - Enter name, URL, and auth type (None / Username & Password / API Token)
   - Credentials are stored securely and injected during test execution
   - No need to include auth details in test steps
4. When creating a test, select a saved app from the dropdown to auto-fill the URL

### Step 6: Auto-Discover Test Scenarios (AI Discover)

Instead of writing tests manually, let AI generate them:

1. Click **"AI Discover"** (or go to `/discover`)
2. Enter:
   - **URL**: `http://localhost:8080`
   - **Scenarios**: 3
   - **Complexity**: Medium (3-5 steps)
   - **Crawl Depth**: Normal (3 pages)
   - Select focus areas: **CRUD Operations**, **Authentication**
   - **Notes**: `username: admin, password: admin. Focus on project management features.`
3. Click **"Discover Test Scenarios"** — the system will:
   - Crawl Kanboard (login page → dashboard → project creation page)
   - Send discovered elements to Gemini LLM
   - Generate 3 diverse test scenarios
4. Review the generated scenarios, uncheck any you don't want
5. Click **"Save Selected Tests"**
6. Run them from the test list

### Stopping the Target Application

```bash
docker stop kanboard && docker rm kanboard
```

## Technology Stack

| Layer | Technology | Purpose |
|---|---|---|
| **Web Application** | Flask (Python) | Server-side rendering, routes, session management |
| **Database** | SQLite | Stores users, test scenarios, and execution results |
| **Browser Automation** | Selenium + headless Chromium | Drives a real browser against target applications |
| **HTML Parsing** | BeautifulSoup | Crawls target pages, discovers interactive elements |
| **LLM Integration** | Google Gemini API | Translates natural language → Selenium commands, auto-generates test scenarios |
| **Testing Framework** | Behave (BDD / Gherkin) | Acceptance tests with Given/When/Then syntax |
| **Containerization** | Docker | Reproducible test environment with Chromium pre-installed |

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        TestFlow AI Platform                         │
│                                                                     │
│  ┌──────────────┐   ┌──────────────┐   ┌────────────────────────┐  │
│  │   Flask Web   │   │   SQLite DB  │   │   Jinja2 Templates     │  │
│  │   Application │◄─►│              │   │                        │  │
│  │              │   │  - users     │   │  - login/register      │  │
│  │  /login      │   │  - scenarios │   │  - create_test         │  │
│  │  /create-test│   │  - test_runs │   │  - test_list           │  │
│  │  /tests      │   │              │   │  - test_results        │  │
│  │  /run-test   │   └──────────────┘   │  - discover            │  │
│  │  /discover   │                       └────────────────────────┘  │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │              Test Execution Engine                           │    │
│  │                                                             │    │
│  │  ┌─────────────┐  ┌──────────────┐  ┌──────────────────┐   │    │
│  │  │ Selenium    │  │ BeautifulSoup│  │ Gemini LLM       │   │    │
│  │  │ WebDriver   │  │ HTML Parser  │  │ (Google API)     │   │    │
│  │  │             │  │              │  │                  │   │    │
│  │  │ Drives      │  │ Discovers    │  │ Translates NL    │   │    │
│  │  │ headless    │◄─┤ forms,inputs │─►│ steps into       │   │    │
│  │  │ Chrome      │  │ buttons,links│  │ Selenium actions │   │    │
│  │  │ browser     │  │              │  │                  │   │    │
│  │  └─────────────┘  └──────────────┘  └──────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────┘    │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────┐                                    │
│  │   Target Application        │                                    │
│  │   (e.g., Kanboard on :8080) │                                    │
│  └─────────────────────────────┘                                    │
└─────────────────────────────────────────────────────────────────────┘
```

### How Each Component Works Together

**The core insight**: Selenium alone cannot understand natural language. BeautifulSoup alone can discover elements but cannot act on them. The LLM alone doesn't know what elements exist on the page. By combining all three, each handles what it's best at:

| Component | Role | What It's Good At | What It Can't Do |
|---|---|---|---|
| **BeautifulSoup** | Element Discovery | Parsing HTML, finding all forms/inputs/buttons with 100% accuracy | Cannot interact with the page or understand intent |
| **Gemini LLM** | Natural Language Understanding | Mapping "click the login button" to `{action: click, target: "Sign in"}` | Cannot see or interact with the actual page |
| **Selenium** | Browser Automation | Clicking buttons, typing text, taking screenshots, measuring load times | Cannot understand natural language or discover elements intelligently |

### Test Execution Pipeline (Stage by Stage)

```
STAGE 1: ELEMENT DISCOVERY (BeautifulSoup)
┌──────────────────────────────────────────────────────────────┐
│ Input: Target URL (e.g., http://localhost:8080)               │
│                                                              │
│ Selenium opens the URL in headless Chrome                    │
│         ↓                                                    │
│ BeautifulSoup parses the HTML and extracts:                  │
│   • Forms: action="/login/check", method="post"              │
│   • Inputs: username (text), password (password)             │
│   • Buttons: "Sign in" (submit)                              │
│   • Links: "Forgot password?" → /forgot-password             │
│                                                              │
│ Output: Structured element map (JSON)                        │
└──────────────────────────────────────────────────────────────┘
                          ↓
STAGE 2: STEP TRANSLATION (Gemini LLM)
┌──────────────────────────────────────────────────────────────┐
│ Input: User's natural language steps + discovered elements    │
│                                                              │
│ Prompt sent to Gemini:                                       │
│   "Here are the page elements: [username input, password     │
│    input, Sign in button]. The user wants to:                │
│    'Log in with admin credentials and create a project'      │
│    Convert to Selenium actions."                             │
│         ↓                                                    │
│ Gemini returns structured JSON:                              │
│   [                                                          │
│     {action: "enter", target: "username", value: "admin"},   │
│     {action: "enter", target: "password", value: "admin"},   │
│     {action: "click", target: "Sign in"},                    │
│     {action: "click", target: "New project"},                │
│     {action: "enter", target: "name", value: "My Project"},  │
│     {action: "click", target: "Save"}                        │
│   ]                                                          │
│                                                              │
│ Output: Ordered list of Selenium commands                    │
└──────────────────────────────────────────────────────────────┘
                          ↓
STAGE 3: EXECUTION (Selenium WebDriver)
┌──────────────────────────────────────────────────────────────┐
│ For each action in the list:                                  │
│                                                              │
│   1. Find the element on the page (by name, id, text, etc.) │
│   2. Execute the action (click, type, navigate)              │
│   3. Take a screenshot (saved as real PNG)                   │
│   4. Measure page load time                                  │
│   5. If the page changed (click/navigate):                   │
│      → Re-run Stage 1 to discover new elements              │
│                                                              │
│ If any step fails:                                           │
│   • Capture failure screenshot                               │
│   • Analyze page state for diagnosis                         │
│   • Report available elements vs. expected element           │
│                                                              │
│ Output: Screenshots, performance metrics, pass/fail status   │
└──────────────────────────────────────────────────────────────┘
                          ↓
STAGE 4: RESULTS (SQLite + Flask UI)
┌──────────────────────────────────────────────────────────────┐
│ All results saved to test_runs table:                         │
│   • status: "Passed" or "Failed"                             │
│   • execution_time: real seconds elapsed                     │
│   • screenshots: JSON array of PNG file paths                │
│   • performance: JSON object with per-step load times        │
│   • failure_message: actual error from Selenium              │
│   • diagnosis: AI analysis of what went wrong                │
│   • email_sent: notification flag                            │
│                                                              │
│ Results page displays everything with clickable screenshots  │
└──────────────────────────────────────────────────────────────┘
```

### Auto-Discovery Pipeline

When using the "AI Discover" feature, a separate pipeline runs:

```
URL + User Notes (credentials, focus areas)
        ↓
CRAWL: Selenium visits 1-5 pages, BeautifulSoup extracts elements from each
  Page 1: Login (forms, inputs, buttons)
  Page 2: Dashboard (links, navigation, search)
  Page 3: Create Project (forms, fields)
        ↓
GENERATE: Full site map sent to Gemini LLM with user preferences
  "Generate 3 medium-complexity test scenarios focused on CRUD and auth"
        ↓
REVIEW: User sees generated scenarios with checkboxes
  ☑ Successful Login (authentication)
  ☑ Create New Project (crud)
  ☐ Navigate to Settings (navigation)
        ↓
SAVE: Selected scenarios stored in test_scenarios table, ready to run
```

### Acceptance Tests (Simulation Mode)

When acceptance tests run (`TESTFLOW_SIMULATE=1`), the real execution engine is bypassed:

1. Behave starts and `environment.py` launches Flask on port 5000 in a background thread
2. A headless Chromium browser is opened via Selenium
3. Step definitions use Selenium to navigate the TestFlow AI web UI
4. `_simulate_execution()` returns deterministic mock results (no LLM or target app needed)
5. **Scenario 1**: Selenium creates a test via the form and verifies it appears in the list
6. **Scenario 2A**: Pre-seeded test runs → status "Passed", execution time, screenshots, metrics
7. **Scenario 2B**: Pre-seeded failing test → status "Failed", error message, AI diagnosis, email notification
8. **Scenario 3A**: Application bug failure → category badge "Application Bug", diagnosis summary, explanation, recommendation, proposed fix, "Re-run Test" button
9. **Scenario 3B**: Test design failure → category badge "Test Design Issue", "Apply Suggested Fix" button → click → test steps updated, status reset to "Not Run"
10. **Scenario 3C**: Environment failure → category badge "Environment Issue", explanation about unreachable target, "Retry Test" button
11. After tests complete, the browser and server shut down

## Acceptance Test Scenarios

### Scenario 1: Test Creation (Implemented)
- **User Story**: As a QA engineer, I want to create test scenarios in natural language
- **Flow**: Login → Navigate to "Create Test" → Fill form → Save → See confirmation → Test appears in list

### Scenario 2: Test Execution and Monitoring (Implemented)
- **User Story**: As a product manager, I want to execute tests and monitor results
- **Scenario 2A**: Run a passing test → see status "Passed", execution time, per-step screenshots, performance metrics
- **Scenario 2B**: Run a failing test → see status "Failed", error message, failure screenshot, AI diagnosis, email notification

### Scenario 3: Intelligent Failure Diagnosis (Implemented)
- **User Story**: As a developer, I want to understand why a test failed immediately so I can fix issues faster
- **Flow**: Test fails → AI analyzes error, page state, and available elements → Classifies failure as test design issue, application bug, or environment problem → Provides detailed explanation, recommendation, and proposed fix → Actionable buttons: "Apply Suggested Fix" (auto-updates test steps), "Edit Test Manually", or "Re-run Test"
- **Scenario 3A**: Application bug → "Application Bug" badge, diagnosis with payment-related explanation, "Re-run Test" button
- **Scenario 3B**: Test design issue → "Test Design Issue" badge, "Apply Suggested Fix" button updates test steps, status resets to "Not Run"
- **Scenario 3C**: Environment issue → "Environment Issue" badge, explanation about unreachable target, "Retry Test" button

### Scenario 4: SWAP CHALLENGE - Self-Healing Tests (Not yet implemented)
- **User Story**: As a development team, I want tests to adapt to UI changes automatically

## Project Structure

```
testflow-ai/
├── src/                                 # Source code
│   ├── __init__.py
│   ├── app.py                           # Flask application (routes for Scenarios 1, 2 & 3)
│   ├── db.py                            # SQLite database helpers (users, tests, runs, settings, apps)
│   ├── test_runner.py                   # Real Selenium execution engine (Scenario 2)
│   ├── failure_analyzer.py              # AI failure diagnosis engine (Scenario 3)
│   ├── llm_step_parser.py              # Gemini LLM: natural language → Selenium commands
│   ├── site_crawler.py                  # Multi-page crawler (BeautifulSoup + Selenium)
│   ├── scenario_generator.py            # Gemini LLM: auto-generate test scenarios
│   ├── static/screenshots/              # Real screenshots from test execution
│   └── templates/
│       ├── base.html                    # Base template with dark theme
│       ├── login.html                   # Login page
│       ├── register.html                # Registration page
│       ├── create_test.html             # Test creation form with saved app dropdown
│       ├── edit_test.html               # Test editing form
│       ├── test_list.html               # Test list with Run/Run All buttons
│       ├── test_results.html            # Results page with AI diagnosis & action buttons
│       ├── settings.html                # Settings: email, saved applications
│       └── discover.html                # AI auto-discovery page
├── acceptance_tests/                    # BDD test suite
│   ├── test_creation.feature            # Scenario 1 (Gherkin)
│   ├── test_execution.feature           # Scenario 2 (Gherkin)
│   ├── failure_diagnosis.feature        # Scenario 3 (Gherkin) - 3 sub-scenarios
│   ├── ai_capabilities.feature          # Scenario 4 - SWAP CHALLENGE (Gherkin)
│   ├── steps/                           # Step definitions
│   │   ├── test_creation_steps.py       # Selenium-based steps for Scenario 1
│   │   ├── test_execution_steps.py      # Selenium steps for Scenario 2 (17 steps)
│   │   ├── failure_diagnosis_steps.py   # Selenium steps for Scenario 3 (25 steps)
│   │   └── ai_capabilities_steps.py     # Stubs for Scenario 4
│   └── environment.py                   # Flask + Selenium setup/teardown
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── README.md
├── CHANGELOG.md
└── PRODUCT_SPECIFICATION.md
```

## Demo Guide (Step-by-Step)

This section provides a complete walkthrough for demoing all features of TestFlow AI, including the target application setup.

### Prerequisites
- **Docker Desktop** installed and running
- **Python 3.11+** installed locally
- **Google Chrome** installed
- **Google Gemini API key** (free from [Google AI Studio](https://aistudio.google.com/apikey))

### Step 1: Start the Target Application (Kanboard)
```bash
docker run -d -p 8080:80 --name kanboard kanboard/kanboard
```
- **Target App URL**: `http://localhost:8080`
- **Credentials**: `admin` / `admin`

### Step 2: Configure and Start TestFlow AI
```bash
# Install dependencies
pip install -r requirements.txt

# Configure Gemini API key
mkdir -p .claude
echo "gemini_token='YOUR_GEMINI_API_KEY'" > .claude/.config

# Start the application
python3 -c "from src.app import create_app; app = create_app(); app.run(port=5001)"
```
- **TestFlow AI URL**: `http://localhost:5001`
- **Login**: `test@example.com` / `password123`

### Step 3: Demo - Create a Test (Scenario 1)
1. Open `http://localhost:5001` and log in
2. Click **"+ New Test"**
3. Fill in:
   - **Name**: `Kanboard Login & Create Project`
   - **URL**: `http://localhost:8080`
   - **Steps**: `Log into the application using admin as both username and password. After logging in, click on New project. Type My Demo Project as the project name. Save the project.`
   - **Expected Outcome**: `My Demo Project`
4. Click **"Save Test"** → test appears in list with status "Not Run"

### Step 4: Demo - Run a Test (Scenario 2)
1. Click **"Run Test"** on the test you just created
2. Watch the loading overlay while:
   - Headless Chrome navigates to Kanboard
   - BeautifulSoup discovers page elements
   - Gemini translates steps to Selenium commands
   - Screenshots are taken at each step
3. View results: status, execution time, real screenshots, performance metrics

### Step 5: Demo - Failure Diagnosis (Scenario 3)
1. Create a test that will fail:
   - **Name**: `Broken Button Test`
   - **URL**: `http://localhost:8080`
   - **Steps**: `Navigate to the login page. Click the non-existent Submit Order button.`
   - **Expected Outcome**: `Order confirmation`
2. Click **"Run Test"** → test will fail
3. On the results page, observe:
   - **Failure Category Badge** (color-coded: yellow/red/blue)
   - **AI Diagnosis** with detailed explanation
   - **Recommendation** section with next steps
   - **Proposed Fix** with improved test steps
   - **Action Buttons**: "Apply Suggested Fix", "Edit Test Manually", or "Re-run Test"
4. Click **"Apply Suggested Fix"** → test steps auto-update from AI suggestion

### Step 6: Demo - Auto-Discovery
1. Click **"AI Discover"** in the nav bar
2. Enter `http://localhost:8080`, set 3 scenarios, Medium complexity
3. Click **"Discover Test Scenarios"** → AI crawls Kanboard and generates tests
4. Select scenarios and click **"Save Selected Tests"**

### Step 7: Run Acceptance Tests (Docker)
```bash
# Build Docker image
docker-compose build

# Run all implemented scenarios (1, 2, 3)
docker-compose run --rm testflow behave acceptance_tests/test_creation.feature acceptance_tests/test_execution.feature acceptance_tests/failure_diagnosis.feature

# Expected: 3 features passed, 6 scenarios passed, 51 steps passed
```

### Step 8: Cleanup
```bash
docker stop kanboard && docker rm kanboard
```

## Troubleshooting

### "docker: command not found"
Make sure Docker is installed and running. On macOS/Windows, check that Docker Desktop is open.

### Container build fails
```bash
docker-compose build --no-cache
```

### Tests not reflecting code changes
```bash
docker-compose down
docker-compose build
docker-compose run --rm testflow behave acceptance_tests/test_creation.feature
```

### Kanboard container won't start (port 8080 in use)
```bash
docker stop kanboard && docker rm kanboard
docker run -d -p 8080:80 --name kanboard kanboard/kanboard
```

### Real execution fails with "No available Gemini model"
Ensure your Gemini API key is valid and saved in `.claude/.config`:
```bash
cat .claude/.config
# Should show: gemini_token='AIza...'
```
