# 🐶 BugHound

BugHound is a small, agent-style debugging tool. It analyzes a Python code snippet, proposes a fix, and runs basic reliability checks before deciding whether the fix is safe to apply automatically.

---

## What BugHound Does

Given a short Python snippet, BugHound:

1. **Analyzes** the code for potential issues
   - Uses heuristics in offline mode
   - Uses Gemini when API access is enabled

2. **Proposes a fix**
   - Either heuristic-based or LLM-generated
   - Attempts minimal, behavior-preserving changes
   - Uses Python's Abstract Syntax Tree (AST) to identify and transform actual function calls rather than relying solely on text replacement
   - Handles multiple positional arguments and nested calls in supported print-statement transformations

3. **Assesses risk**
   - Scores the proposed fix
   - Validates Python syntax
   - Detects unchanged proposed code
   - Checks for removed return statements
   - Considers the severity of detected issues
   - Flags potentially unsafe changes for human review

4. **Shows its work**
   - Displays detected issues
   - Shows a diff between original and fixed code
   - Logs each agent step

---

## Setup

### 1. Create a virtual environment (recommended)

```bash
python -m venv .venv
source .venv/bin/activate   # macOS/Linux
# or
.venv\Scripts\activate      # Windows
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

---

## Running in Offline (Heuristic) Mode

No API key required.

```bash
streamlit run bughound_app.py
```

In the sidebar, select:

* **Model mode:** Heuristic only (no API)

This mode uses built-in pattern-based rules and is useful for testing the workflow without network access.

---

## Running with Gemini

### 1. Set up your API key

Copy the example file:

```bash
cp .env.example .env
```

Edit `.env` and add your Gemini API key:

```text
GEMINI_API_KEY=your_real_key_here
```

### 2. Run the app

```bash
streamlit run bughound_app.py
```

In the sidebar, select:

* **Model mode:** Gemini (requires API key)
* Choose a Gemini model and temperature

BugHound will now use Gemini for analysis and fix generation, while still applying local reliability checks.

---

## Running Tests

Tests focus on **reliability logic**, **agent behavior**, and **LLM client configuration**, rather than the UI.

```bash
python -m pytest -v
```

The automated tests cover:

* Risk scoring and safety guardrails
* Python syntax validation
* Detection of unchanged proposed corrections
* Return-statement preservation
* Heuristic fallbacks when LLM output is invalid
* AST-based print-call transformations
* Multiple print arguments and nested calls
* Human-review requirements for unsupported print transformations
* Gemini temperature configuration and API error handling
* End-to-end agent workflow behavior

These tests verify specific behaviors and safeguards; they do not guarantee that every proposed correction preserves program semantics.
