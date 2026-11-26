import ast
from typing import Dict, List

def _parse_python(code: str):
    """Parse and compile Python source, returning its AST if valid."""
    try:
        tree = ast.parse(code)
        compile(tree, "<bughound>", "exec")
        return tree
    except SyntaxError:
        return None

def _count_return_statements(tree) -> int:
    """Count actual return statements in a Python syntax tree."""
    return sum(
        isinstance(node, ast.Return)
        for node in ast.walk(tree)
    )

def _count_print_calls(tree) -> int:
    """Count actual print() calls in a Python syntax tree."""
    return sum(
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "print"
        for node in ast.walk(tree)
    )

def assess_risk(
    original_code: str,
    fixed_code: str,
    issues: List[Dict[str, str]],
) -> Dict[str, object]:
    """
    Simple, explicit risk assessment used as a guardrail layer.

    Returns a dict with:
    - score: int from 0 to 100
    - level: "low" | "medium" | "high"
    - reasons: list of strings explaining deductions
    - should_autofix: bool
    """

    reasons: List[str] = []
    score = 100
    safety_blockers = False

    if not fixed_code.strip():
        return {
            "score": 0,
            "level": "high",
            "reasons": ["No fix was produced."],
            "should_autofix": False,
        }

    # ----------------------------
    # Syntax and no-op validation
    # ----------------------------
    fixed_tree = _parse_python(fixed_code)

    if fixed_tree is None:
        return {
            "score": 0,
            "level": "high",
            "reasons": ["Proposed fix contains invalid Python syntax."],
            "should_autofix": False,
        }

    if original_code.strip() == fixed_code.strip():
        return {
            "score": 0,
            "level": "high",
            "reasons": ["Proposed fix is unchanged from the original code."],
            "should_autofix": False,
        }

    original_lines = original_code.strip().splitlines()
    fixed_lines = fixed_code.strip().splitlines()

    # ----------------------------
    # Issue severity based risk
    # ----------------------------
    for issue in issues:
        severity = str(issue.get("severity", "")).lower()

        if severity == "high":
            score -= 40
            reasons.append("High severity issue detected.")
        elif severity == "medium":
            score -= 20
            reasons.append("Medium severity issue detected.")
        elif severity == "low":
            score -= 5
            reasons.append("Low severity issue detected.")

    # ----------------------------
    # Structural change checks
    # ----------------------------
    if len(fixed_lines) < len(original_lines) * 0.5:
        score -= 20
        reasons.append("Fixed code is much shorter than original.")

    original_tree = _parse_python(original_code)

    if original_tree is not None:
        original_returns = _count_return_statements(original_tree)
        fixed_returns = _count_return_statements(fixed_tree)

        if fixed_returns < original_returns:
            score -= 30
            safety_blockers = True
            reasons.append(
                "Return statements were removed; verify behavior manually."
            )

    # ----------------------------
    # Unresolved print statements
    # ----------------------------
    has_code_quality_issue = any(
        issue.get("type") == "Code Quality"
        for issue in issues
    )

    if has_code_quality_issue and _count_print_calls(fixed_tree) > 0:
        score -= 20
        safety_blockers = True
        reasons.append(
            "Print statements remain unresolved; human review required."
        )

    if "except:" in original_code and "except:" not in fixed_code:
        # This is usually good, but still risky.
        score -= 5
        reasons.append("Bare except was modified, verify correctness.")

    # ----------------------------
    # Clamp score
    # ----------------------------
    score = max(0, min(100, score))

    # ----------------------------
    # Risk level
    # ----------------------------
    if score >= 75:
        level = "low"
    elif score >= 40:
        level = "medium"
    else:
        level = "high"

    # ----------------------------
    # Auto-fix policy
    # ----------------------------
    should_autofix = level == "low" and not safety_blockers

    if not reasons:
        reasons.append("No significant risks detected.")

    return {
        "score": score,
        "level": level,
        "reasons": reasons,
        "should_autofix": should_autofix,
    }
