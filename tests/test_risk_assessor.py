from reliability.risk_assessor import assess_risk


def test_no_fix_is_high_risk():
    risk = assess_risk(
        original_code="print('hi')\n",
        fixed_code="",
        issues=[{"type": "Code Quality", "severity": "Low", "msg": "print"}],
    )
    assert risk["level"] == "high"
    assert risk["should_autofix"] is False
    assert risk["score"] == 0


def test_low_risk_when_minimal_change_and_low_severity():
    original = "import logging\n\ndef add(a, b):\n    return a + b\n"
    fixed = "import logging\n\ndef add(a, b):\n    return a + b\n"
    risk = assess_risk(
        original_code=original,
        fixed_code=fixed,
        issues=[{"type": "Code Quality", "severity": "Low", "msg": "minor"}],
    )
    assert risk["level"] == "high"
    assert risk["should_autofix"] is False
    assert any("unchanged" in r.lower() for r in risk["reasons"])

def test_high_severity_issue_drives_score_down():
    original = "def f():\n    try:\n        return 1\n    except:\n        return 0\n"
    fixed = "def f():\n    try:\n        return 1\n    except Exception as e:\n        return 0\n"
    risk = assess_risk(
        original_code=original,
        fixed_code=fixed,
        issues=[{"type": "Reliability", "severity": "High", "msg": "bare except"}],
    )
    assert risk["score"] <= 60
    assert risk["level"] in ("medium", "high")


def test_missing_return_is_penalized():
    original = "def f(x):\n    return x + 1\n"
    fixed = "def f(x):\n    x + 1\n"
    risk = assess_risk(
        original_code=original,
        fixed_code=fixed,
        issues=[],
    )
    assert risk["score"] < 100
    assert any("Return" in r or "return" in r for r in risk["reasons"])

def test_invalid_python_cannot_be_auto_approved():
    original = "def greet():\n    return 'hello'\n"
    fixed = "def greet(:\n    return 'hello'\n"

    risk = assess_risk(original, fixed, [])

    assert risk["should_autofix"] is False
    assert risk["level"] == "high"
    assert any("syntax" in reason.lower() for reason in risk["reasons"])


def test_unchanged_code_is_not_approved_as_a_fix():
    original = "def greet():\n    return 'hello'\n"

    risk = assess_risk(original, original, [])

    assert risk["should_autofix"] is False
    assert any("unchanged" in reason.lower() for reason in risk["reasons"])


def test_removed_return_is_detected_even_if_word_remains_in_string():
    original = 'def calculate():\n    return 42\n'
    fixed = 'def calculate():\n    message = "return"\n'

    risk = assess_risk(original, fixed, [])

    assert risk["score"] < 100
    assert risk["should_autofix"] is False
    assert any("return" in reason.lower() for reason in risk["reasons"])
