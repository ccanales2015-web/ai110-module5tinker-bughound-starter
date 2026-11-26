from bughound_agent import BugHoundAgent
from llm_client import MockClient


def test_workflow_runs_in_offline_mode_and_returns_shape():
    agent = BugHoundAgent(client=None)  # heuristic-only
    code = "def f():\n    print('hi')\n    return True\n"
    result = agent.run(code)

    assert isinstance(result, dict)
    assert "issues" in result
    assert "fixed_code" in result
    assert "risk" in result
    assert "logs" in result

    assert isinstance(result["issues"], list)
    assert isinstance(result["fixed_code"], str)
    assert isinstance(result["risk"], dict)
    assert isinstance(result["logs"], list)
    assert len(result["logs"]) > 0


def test_offline_mode_detects_print_issue():
    agent = BugHoundAgent(client=None)
    code = "def f():\n    print('hi')\n    return True\n"
    result = agent.run(code)

    assert any(issue.get("type") == "Code Quality" for issue in result["issues"])


def test_offline_mode_proposes_logging_fix_for_print():
    agent = BugHoundAgent(client=None)
    code = "def f():\n    print('hi')\n    return True\n"
    result = agent.run(code)

    fixed = result["fixed_code"]
    assert "logging" in fixed
    assert "logging.info(" in fixed


def test_mock_client_forces_llm_fallback_to_heuristics_for_analysis():
    # MockClient returns non-JSON for analyzer prompts, so agent should fall back.
    agent = BugHoundAgent(client=MockClient())
    code = "def f():\n    print('hi')\n    return True\n"
    result = agent.run(code)

    assert any(issue.get("type") == "Code Quality" for issue in result["issues"])
    # Ensure we logged the fallback path
    assert any("Falling back to heuristics" in entry.get("message", "") for entry in result["logs"])

def test_offline_mode_preserves_multiple_print_arguments_in_logging():
    agent = BugHoundAgent(client=None)
    code = 'def greet(name):\n    print("Hello", name)\n'

    result = agent.run(code)
    fixed = result["fixed_code"]

    assert 'logging.info("Hello %s", name)' in fixed

def test_print_with_keyword_arguments_is_not_silently_approved():
    agent = BugHoundAgent(client=None)
    code = 'def greet(name):\n    print("Hello", name, sep=" - ")\n'

    result = agent.run(code)

    assert 'print("Hello", name, sep=" - ")' in result["fixed_code"]
    assert result["risk"]["should_autofix"] is False


def test_nested_print_calls_do_not_corrupt_source():
    agent = BugHoundAgent(client=None)
    code = 'def calculate():\n    print("Result:", print("calculating"))\n'

    result = agent.run(code)
    fixed = result["fixed_code"]

    # The resulting code must remain valid Python.
    import ast
    ast.parse(fixed)

    # Nested calls are preserved for human review.
    assert "print(" in fixed
    assert result["risk"]["should_autofix"] is False
    assert any(
        "print statements remain unresolved" in reason.lower()
        for reason in result["risk"]["reasons"]
    )