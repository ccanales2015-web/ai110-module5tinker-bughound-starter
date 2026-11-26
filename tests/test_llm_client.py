
from types import SimpleNamespace

from llm_client import GeminiClient


def test_gemini_client_passes_temperature_to_api():
    client = GeminiClient.__new__(GeminiClient)

    client.model_name = "gemini-2.5-flash"
    client.temperature = 0.7

    captured = {}

    class FakeTypes:
        @staticmethod
        def GenerateContentConfig(temperature):
            return {"temperature": temperature}

    class FakeModels:
        def generate_content(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(text="Mock Gemini response")

    client.types = FakeTypes()
    client.client = SimpleNamespace(models=FakeModels())

    result = client.complete("System prompt", "User prompt")

    assert result == "Mock Gemini response"
    assert captured["model"] == "gemini-2.5-flash"
    assert captured["config"]["temperature"] == 0.7
    assert "System prompt" in captured["contents"]
    assert "User prompt" in captured["contents"]


def test_gemini_client_handles_api_errors():
    client = GeminiClient.__new__(GeminiClient)

    client.model_name = "gemini-2.5-flash"
    client.temperature = 0.2
    client.types = SimpleNamespace(
        GenerateContentConfig=lambda **kwargs: kwargs
    )

    class FakeModels:
        def generate_content(self, **kwargs):
            raise RuntimeError("Simulated API failure")

    client.client = SimpleNamespace(models=FakeModels())

    result = client.complete("System prompt", "User prompt")

    assert result == ""
