"""The real (non-mock) LiteLLM path of llm.complete_json, using LiteLLM's offline mock_response.

Checks JSON parsing, code-fence stripping, cost recording and invalid-output handling.
"""

import litellm
import pytest

from app import llm
from app.config import get_settings
from app.schemas import AIProfileDraft


@pytest.fixture
def real_model(monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_model", "openai/gpt-4o-mini")
    original = litellm.completion

    def answer(text):
        # Same call the gateway makes, but LiteLLM returns `text` without any network call.
        monkeypatch.setattr(litellm, "completion", lambda **kw: original(**kw, mock_response=text, api_key="none"))

    return answer


def test_valid_json_is_parsed_and_costed(real_model):
    real_model('{"draft": "I build finance dashboards.", "unsupported_claims": ["CFA charter"]}')
    out, usage = llm.complete_json("system", "user", AIProfileDraft, mock_output=lambda: {})
    assert out.unsupported_claims == ["CFA charter"]
    assert usage.model == "openai/gpt-4o-mini" and usage.input_tokens > 0 and usage.cost_usd > 0


def test_code_fences_are_stripped(real_model):
    real_model('```json\n{"draft": "ok", "unsupported_claims": []}\n```')
    out, _ = llm.complete_json("system", "user", AIProfileDraft, mock_output=lambda: {})
    assert out.draft == "ok"


@pytest.mark.parametrize("text", ["not json at all", '{"unsupported_claims": []}', '{"draft": ""}'])
def test_invalid_output_raises_with_usage(real_model, text):
    real_model(text)
    with pytest.raises(llm.LLMError) as err:
        llm.complete_json("system", "user", AIProfileDraft, mock_output=lambda: {})
    assert "Invalid model output" in str(err.value) and err.value.usage.input_tokens > 0


def test_call_failure_raises(monkeypatch):
    monkeypatch.setattr(get_settings(), "llm_model", "openai/gpt-4o-mini")

    def boom(**kw):
        raise TimeoutError("slow")

    monkeypatch.setattr(litellm, "completion", boom)
    with pytest.raises(llm.LLMError, match="Model call failed: TimeoutError"):
        llm.complete_json("system", "user", AIProfileDraft, mock_output=lambda: {})
