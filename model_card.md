# BugHound Mini Model Card (Reflection)

## 1) What is this system?

**Name:** BugHound

**Purpose:** Analyze a Python code snippet, identify potential problems, propose a correction, and evaluate the proposed correction using reliability checks before deciding whether automatic application is appropriate.

**Intended users:** Students learning agentic workflows, AI-assisted software development, and AI reliability concepts.

BugHound is an experimental debugging assistant. It is not intended to replace a developer's judgment or guarantee that generated code is correct.

## 2) How does it work?

BugHound follows a five-stage agent workflow:

1. **PLAN:** Establishes the intended analysis and correction workflow.
2. **ANALYZE:** Examines the supplied Python code for potential problems.
3. **ACT:** Proposes a correction based on the detected issues.
4. **TEST:** Evaluates the proposed correction using local reliability checks.
5. **REFLECT:** Determines whether the proposed correction meets the current criteria for automatic approval or requires human review.

In heuristic-only mode, BugHound uses pattern-based rules to identify issues such as `print()` statements, bare exception handlers, and TODO comments. Its heuristic fixer attempts targeted corrections, including replacing ordinary `print()` calls with logging statements.

In Gemini mode, Gemini performs the analysis and proposes rewritten code. BugHound then applies its local risk-assessment safeguards to the proposed result.

The risk-assessment component operates independently of the model used to generate the correction. It evaluates factors such as Python syntax validity, changes to return statements, issue severity, and structural differences.

The application also records an agent trace, allowing users to inspect the stages of the workflow.

## 3) Inputs and outputs

**Inputs:**

The following Python snippets and scenarios were used during development and testing:

- Simple functions containing `print()` statements.
- Functions containing multiple positional arguments in `print()` calls.
- Nested `print()` calls.
- `print()` calls containing keyword arguments, such as `sep`.
- Functions containing return statements.
- Code containing bare `except:` blocks.
- Code containing TODO comments.
- Code containing multiple potential issues.

The inputs ranged from short individual functions to functions containing nested calls and exception-handling structures.

**Outputs:**

BugHound successfully identified several types of potential issues:

- Code-quality issues involving `print()` statements.
- Reliability issues involving bare exception handlers.
- Maintainability issues involving TODO comments.

The heuristic fixer proposed replacements of ordinary `print()` calls with `logging.info()` calls. It was also improved to preserve multiple positional arguments through logging format strings.

The risk report provides:

- A numerical score from 0 to 100.
- A risk classification (low, medium, or high).
- Explanations for score deductions.
- A recommendation concerning automatic application.

The application also displays the proposed correction, a unified diff, and an agent execution trace.

## 4) Reliability and safety rules

Several safeguards are implemented in `reliability/risk_assessor.py`.

### Rule 1: Python syntax validation

**What it checks:** The proposed correction must contain syntactically valid Python code.

**Why it matters:** A correction that cannot be parsed as Python is not suitable for automatic application. This safeguard prevents obviously malformed code from receiving automatic approval.

**Possible false positive:** Code intended to be an incomplete fragment, rather than a complete Python module, could be rejected even if it is valid within its intended context.

**Possible false negative:** Syntactically valid code can still contain logical errors, incorrect calculations, or unintended behavior.

### Rule 2: Return-statement preservation

**What it checks:** BugHound compares the number of actual return statements in the original and proposed code using Python's Abstract Syntax Tree (AST).

If the proposed correction removes return statements, the risk score is reduced and a safety blocker prevents automatic approval.

**Why it matters:** Removing a return statement can change a function's behavior, particularly when callers depend on its return value.

**Possible false positive:** A return statement may be intentionally removed because the function's intended behavior has changed.

**Possible false negative:** A return statement can remain present while its expression is changed incorrectly. Counting return statements alone cannot establish semantic equivalence.

### Rule 3: Unchanged-code detection

**What it checks:** BugHound identifies proposed corrections that are identical to the original code.

**Why it matters:** An unchanged result should not be represented as a successful correction eligible for automatic application.

**Possible false positive:** A correction that only changes formatting or comments might be rejected despite being intentional.

**Possible false negative:** A proposed correction can differ from the original while still introducing a functional error.

### Rule 4: Issue-severity scoring

**What it checks:** The risk assessor deducts points according to detected issue severity:

- High severity: 40 points.
- Medium severity: 20 points.
- Low severity: 5 points.

**Why it matters:** More serious detected issues should influence the decision to approve a correction automatically.

**Possible false positive:** An issue may be classified as high severity even when its practical consequences are minor.

**Possible false negative:** An issue classified as low severity may have more serious consequences in a particular application context.

These safeguards are useful, but they do not establish that a proposed correction is functionally equivalent to the original program.

## 5) Observed failure modes

### Example 1: False-positive issue detection

The heuristic analyzer searches for the literal substring `print(` in the supplied source code.

Consequently, a string or comment containing that text can be mistaken for an actual print statement.

For example:

```python
message = "print(hello)"
```

This code contains no actual `print()` function call, but the original heuristic detection strategy can flag it.

The problem is that simple text matching does not distinguish executable Python statements from strings and comments.

An improvement would be to use AST-based detection consistently throughout the analyzer, rather than relying on substring matching.

### Example 2: Incorrect transformation of multiple print arguments

An early version of the heuristic fixer simply replaced `print(` with `logging.info(`.

For example:

```python
print("Hello", name)
```

became:

```python
logging.info("Hello", name)
```

This does not preserve the original output formatting reliably because Python's logging module interprets additional positional arguments as formatting arguments.

The desired transformation was:

```python
logging.info("Hello %s", name)
```

We addressed this by introducing an AST-based transformation that examines actual function calls and preserves multiple positional arguments.

Additional testing also exposed problems with nested calls, which required further refinement to prevent overlapping source replacements from corrupting the resulting code.

These failures demonstrated that apparently simple automated text substitutions can introduce unintended changes.

## 6) Heuristic vs Gemini comparison

A complete empirical comparison between heuristic mode and Gemini mode was not performed.

Heuristic mode was exercised extensively, including through the Streamlit application and automated regression tests.

Gemini's request configuration was tested using mocked components. These tests verified that the selected model, temperature, and prompts were passed to the simulated API interface. API error handling was also tested.

However, these tests do not establish how Gemini performs when analyzing actual code.

**Observed heuristic behavior:**

- Consistently detected the specific patterns covered by its detection rules.
- Proposed logging replacements for ordinary print statements.
- Required additional safeguards for nested calls and keyword arguments.
- Could miss problems outside its limited pattern-based detection rules.

**Gemini behavior:** Live detection accuracy, correction quality, and differences from heuristic behavior remain unverified.

**Risk scorer:** Its recommendations were useful in the tested scenarios. For example, it assigned a low risk score to an ordinary logging replacement while withholding automatic approval for more complicated transformations.

A future experiment should run identical snippets through both modes and compare detection accuracy, correction quality, and risk-assessment results.

## 7) Human-in-the-loop decision

One scenario where BugHound should refuse automatic application is when a proposed correction removes one or more return statements.

Removing a return statement can change a function's behavior even when the resulting code remains syntactically valid.

**Trigger:** The AST-based return-statement comparison detects fewer return statements in the proposed correction than in the original code.

**Implementation location:** The `reliability/risk_assessor.py` component is the appropriate location because this is a reliability and safety decision that should apply regardless of whether the correction originates from heuristics or Gemini.

**User-facing message:**

"Automatic application has been blocked because the proposed correction removes one or more return statements. This change may alter the function's behavior. Please review the original code and proposed correction manually before proceeding."

The current implementation already incorporates this safeguard through a safety blocker.

Human judgment remains necessary because syntactic validity and basic structural checks cannot establish complete behavioral equivalence.

## 8) Improvement idea

One improvement would be to expand AST-based analysis and validation so that BugHound can distinguish actual executable statements from strings, comments, and nested expressions more consistently.

This would reduce false-positive detections and make automated transformations more reliable.

The existing AST-based print transformation and return-statement checks provide a foundation for this improvement.

Additional targeted tests should cover strings, comments, nested function calls, keyword arguments, and changes to function behavior.

This would improve reliability without requiring a substantially more complicated architecture.

---

## AI assistance disclosure

OpenAI ChatGPT (GPT-6) assisted with drafting and editing this model card, organizing the documented observations, and explaining the implemented reliability safeguards. The project implementation, execution of tests, and verification of observed application behavior were performed through the user's development environment. Gemini live behavior was not independently tested.
