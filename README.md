# 🐶 BugHound

BugHound is a small, agent-style debugging tool. It analyzes Python code, proposes fixes, and evaluates their reliability before recommending automatic application or human review.

## What BugHound Does

Given a short Python snippet, BugHound:

1. **Analyzes code**
   - Uses heuristics in offline mode.
   - Uses Gemini when API access is enabled.

2. **Proposes fixes**
   - Uses heuristic-based or LLM-generated corrections.
   - Attempts minimal, behavior-preserving changes.
   - Uses Python's Abstract Syntax Tree (AST) to identify actual function calls instead of relying solely on text replacement.
   - Supports transformations involving multiple positional `print()` arguments and nested calls.
   - Leaves `print()` calls with keyword arguments unchanged for human review.

3. **Assesses risk**
   - Validates Python syntax.
   - Detects unchanged proposed code.
   - Checks whether return statements have been removed.
   - Considers the severity of detected issues.
   - Flags potentially unsafe changes for human review.

4. **Shows its work**
   - Displays detected issues.
   - Shows differences between original and corrected code.
   - Logs agent execution steps.

---

## Setup

### 1. Create a virtual environment (recommended)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

```powershell
python -m pip install -r requirements.txt
```

---

## Running in Offline (Heuristic) Mode

No API key is required.

```powershell
streamlit run bughound_app.py
```

In the sidebar, select **Heuristic only (no API)**.

This mode uses built-in pattern-based rules and runs without network access.

---

## Running with Gemini

Gemini mode requires a Gemini API key.

1. Copy `.env.example` to `.env` if `.env.example` exists in the project.
2. Open `.env` and add your key:

```text
GEMINI_API_KEY=your_real_key_here
```

3. Run the application:

```powershell
streamlit run bughound_app.py
```

In the sidebar, select **Gemini (requires API key)** and choose a model and temperature.

Gemini performs analysis and fix generation, while BugHound continues to apply its local reliability checks.

Keep `.env` private. Do not commit your API key to version control.

---

## Running Tests

Run the automated test suite from the project directory:

```powershell
python -m pytest -v
```

The tests cover:

- Risk scoring and safety guardrails.
- Python syntax validation.
- Detection of unchanged proposed corrections.
- Return-statement preservation.
- Heuristic fallback when LLM output is invalid.
- AST-based print-call transformations.
- Multiple print arguments and nested calls.
- Human-review handling for print calls with keyword arguments.
- Gemini temperature configuration and API error handling.
- Agent workflow behavior.

The tests verify specific behaviors and safeguards. They do not guarantee that every proposed correction preserves program semantics.

---

## Current Testing Note

The automated test suite has been run in heuristic/offline mode and with mocked Gemini client components. A live Gemini analysis comparison has not been completed.

---

## AI Assistance Disclosure

OpenAI ChatGPT (GPT-6) assisted with drafting and editing this README. The project implementation and test execution were performed in the user's development environment.
