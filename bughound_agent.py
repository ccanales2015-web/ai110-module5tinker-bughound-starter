import json
import os
import re
import ast
from typing import Any, Dict, List, Optional, Tuple

from reliability.risk_assessor import assess_risk

# Directory where prompt templates live, relative to this file
PROMPTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "prompts")

def _replace_print_calls_with_logging(code: str) -> str:
    """Replace ordinary positional print calls with logging calls."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return code

    # Avoid overlapping replacements from nested print() calls.
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if not isinstance(node.func, ast.Name) or node.func.id != "print":
            continue

        nested_print = any(
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id == "print"
            for child in ast.walk(node)
            if child is not node
        )

        if nested_print:
            return code

    lines = code.splitlines(keepends=True)
    offsets = [0]

    for line in lines:
        offsets.append(offsets[-1] + len(line))

    def absolute_position(lineno: int, column: int) -> int:
        line = lines[lineno - 1]
        char_column = len(
            line.encode("utf-8")[:column].decode("utf-8")
        )
        return offsets[lineno - 1] + char_column

    replacements = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        if not isinstance(node.func, ast.Name) or node.func.id != "print":
            continue

        # Leave calls with keyword arguments unchanged for human review.
        if node.keywords:
            continue

        args = [
            ast.get_source_segment(code, arg)
            for arg in node.args
        ]

        if any(arg is None for arg in args):
            continue

        if not args:
            replacement = 'logging.info("")'

        elif (
            isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
            and len(args) > 1
        ):
            message = node.args[0].value.replace("%", "%%")
            message += " %s" * (len(args) - 1)

            replacement = (
                f"logging.info({json.dumps(message, ensure_ascii=False)}, "
                f"{', '.join(args[1:])})"
            )

        elif len(args) == 1:
            replacement = f"logging.info({args[0]})"

        else:
            message = " ".join(["%s"] * len(args))
            replacement = (
                f"logging.info({json.dumps(message)}, "
                f"{', '.join(args)})"
            )

        start = absolute_position(node.lineno, node.col_offset)
        end = absolute_position(node.end_lineno, node.end_col_offset)

        replacements.append((start, end, replacement))

    # Replace from the end so earlier source positions remain valid.
    for start, end, replacement in sorted(
        replacements, reverse=True
    ):
        code = code[:start] + replacement + code[end:]

    return code

def _load_prompt(filename: str) -> str:
    """Load a prompt template from the prompts/ folder."""
    path = os.path.join(PROMPTS_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class BugHoundAgent:
    """
    BugHound runs a small agentic workflow:

    1) PLAN: decide what to look for
    2) ANALYZE: detect issues (heuristics or LLM)
    3) ACT: propose a fix (heuristics or LLM)
    4) TEST: run simple reliability checks
    5) REFLECT: decide whether to apply the fix automatically
    """

    def __init__(self, client: Optional[Any] = None):
        # client should implement: complete(system_prompt: str, user_prompt: str) -> str
        self.client = client
        self.logs: List[Dict[str, str]] = []

    # ----------------------------
    # Public API
    # ----------------------------
    def run(self, code_snippet: str) -> Dict[str, Any]:
        self.logs = []
        self._log("PLAN", "Planning a quick scan + fix proposal workflow.")

        issues = self.analyze(code_snippet)
        self._log("ANALYZE", f"Found {len(issues)} issue(s).")

        fixed_code = self.propose_fix(code_snippet, issues)
        if fixed_code.strip() == "":
            self._log("ACT", "No fix produced (refused, error, or empty output).")

        risk = assess_risk(original_code=code_snippet, fixed_code=fixed_code, issues=issues)
        self._log("TEST", f"Risk assessed as {risk.get('level', 'unknown')} (score={risk.get('score', '-')}).")

        if risk.get("should_autofix"):
            self._log("REFLECT", "Fix appears safe enough to auto-apply under current policy.")
        else:
            self._log("REFLECT", "Fix is not safe enough to auto-apply. Human review recommended.")

        return {
            "issues": issues,
            "fixed_code": fixed_code,
            "risk": risk,
            "logs": self.logs,
        }

    # ----------------------------
    # Workflow steps
    # ----------------------------
    def analyze(self, code_snippet: str) -> List[Dict[str, str]]:
        if not self._can_call_llm():
            self._log("ANALYZE", "Using heuristic analyzer (offline mode).")
            return self._heuristic_analyze(code_snippet)

        self._log("ANALYZE", "Using LLM analyzer.")

        # Load prompt templates from prompts/ folder
        system_prompt = _load_prompt("analyzer_system.txt")
        user_template = _load_prompt("analyzer_user.txt")
        user_prompt = user_template.replace("{{CODE}}", code_snippet)

        # UPDATED: Added exception handling for API errors/rate limits
        try:
            raw = self.client.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        except Exception as e:
            self._log("ANALYZE", f"API Error: {str(e)}. Falling back to heuristics.")
            return self._heuristic_analyze(code_snippet)

        issues = self._parse_json_array_of_issues(raw)

        if issues is None:
            self._log("ANALYZE", "LLM output was not parseable JSON. Falling back to heuristics.")
            return self._heuristic_analyze(code_snippet)

        return issues

    def propose_fix(self, code_snippet: str, issues: List[Dict[str, str]]) -> str:
        if not issues:
            self._log("ACT", "No issues, returning original code unchanged.")
            return code_snippet

        if not self._can_call_llm():
            self._log("ACT", "Using heuristic fixer (offline mode).")
            return self._heuristic_fix(code_snippet, issues)

        self._log("ACT", "Using LLM fixer.")

        # Load prompt templates from prompts/ folder
        system_prompt = _load_prompt("fixer_system.txt")
        user_template = _load_prompt("fixer_user.txt")
        user_prompt = user_template.replace("{{ISSUES}}", json.dumps(issues)).replace("{{CODE}}", code_snippet)

        # UPDATED: Added exception handling for API errors/rate limits
        try:
            raw = self.client.complete(system_prompt=system_prompt, user_prompt=user_prompt)
        except Exception as e:
            self._log("ACT", f"API Error: {str(e)}. Falling back to heuristic fixer.")
            return self._heuristic_fix(code_snippet, issues)

        cleaned = self._strip_code_fences(raw).strip()

        if not cleaned:
            self._log("ACT", "LLM returned empty output. Falling back to heuristic fixer.")
            return self._heuristic_fix(code_snippet, issues)

        return cleaned

    # ----------------------------
    # Heuristic analyzer/fixer
    # ----------------------------
    def _heuristic_analyze(self, code: str) -> List[Dict[str, str]]:
        issues: List[Dict[str, str]] = []

        if "print(" in code:
            issues.append(
                {
                    "type": "Code Quality",
                    "severity": "Low",
                    "msg": "Found print statements. Consider using logging for non-toy code.",
                }
            )

        if re.search(r"\bexcept\s*:\s*(\n|#|$)", code):
            issues.append(
                {
                    "type": "Reliability",
                    "severity": "High",
                    "msg": "Found a bare `except:`. Catch a specific exception or use `except Exception as e:`.",
                }
            )

        if "TODO" in code:
            issues.append(
                {
                    "type": "Maintainability",
                    "severity": "Medium",
                    "msg": "Found TODO comments. Unfinished logic can hide bugs or missing cases.",
                }
            )

        return issues

    def _heuristic_fix(self, code: str, issues: List[Dict[str, str]]) -> str:
        fixed = code

        if any(i.get("type") == "Reliability" for i in issues):
            fixed = re.sub(r"\bexcept\s*:\s*", "except Exception as e:\n        # [BugHound] log or handle the error\n        ", fixed)

        if any(i.get("type") == "Code Quality" for i in issues):
            if "import logging" not in fixed:
                fixed = "import logging\n\n" + fixed
            fixed = _replace_print_calls_with_logging(fixed)

        return fixed

    # ----------------------------
    # Parsing + utilities
    # ----------------------------
    def _parse_json_array_of_issues(self, text: str) -> Optional[List[Dict[str, str]]]:
        text = text.strip()
        parsed = self._try_json_loads(text)
        if isinstance(parsed, list):
            return self._normalize_issues(parsed)

        array_str = self._extract_first_json_array(text)
        if array_str:
            parsed2 = self._try_json_loads(array_str)
            if isinstance(parsed2, list):
                return self._normalize_issues(parsed2)

        return None

    def _normalize_issues(self, arr: List[Any]) -> List[Dict[str, str]]:
        issues: List[Dict[str, str]] = []
        for item in arr:
            if not isinstance(item, dict):
                continue
            issues.append(
                {
                    "type": str(item.get("type", "Issue")),
                    "severity": str(item.get("severity", "Unknown")),
                    "msg": str(item.get("msg", "")).strip(),
                }
            )
        return issues

    def _try_json_loads(self, s: str) -> Any:
        try:
            return json.loads(s)
        except Exception:
            return None

    def _extract_first_json_array(self, s: str) -> Optional[str]:
        start = s.find("[")
        if start == -1:
            return None
        depth = 0
        for i in range(start, len(s)):
            if s[i] == "[":
                depth += 1
            elif s[i] == "]":
                depth -= 1
                if depth == 0:
                    return s[start : i + 1]
        return None

    def _strip_code_fences(self, text: str) -> str:
        text = text.strip()
        match = re.search(r"```(?:python)?\s*(.*?)\s*```", text, flags=re.DOTALL | re.IGNORECASE)
        if match:
            return match.group(1)
        return text

    def _can_call_llm(self) -> bool:
        return self.client is not None and hasattr(self.client, "complete")

    def _log(self, step: str, message: str) -> None:
        self.logs.append({"step": step, "message": message})
