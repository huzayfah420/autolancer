"""The only path to a language model.

- LLM_MODEL=mock: deterministic fake output and a fixed tiny cost (tests, local dev).
- Otherwise: LiteLLM with the configured model, JSON mode, and Pydantic validation.

Either way the caller gets (validated_output, usage) or an LLMError that still
carries the usage, so the cost of a failed or invalid call is recorded too.
"""

import json
from collections.abc import Callable
from dataclasses import dataclass

from pydantic import BaseModel, ValidationError

from .config import get_settings

MOCK_COST_USD = 0.001  # charged per mock call so the daily cap can be tested


@dataclass
class Usage:
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0


class LLMError(Exception):
    """Model call failed or returned output that did not match the schema."""

    def __init__(self, message: str, usage: Usage):
        super().__init__(message)
        self.usage = usage


def _strip_fences(text: str) -> str:
    # Some models wrap JSON in ```json fences even in JSON mode.
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else ""
        text = text.rsplit("```", 1)[0]
    return text.strip()


def complete_json[T: BaseModel](
    system: str, user: str, schema: type[T], mock_output: Callable[[], dict]
) -> tuple[T, Usage]:
    settings = get_settings()
    # The JSON schema is part of the prompt so any model knows the exact shape required.
    system_full = f"{system}\n\nReply with one JSON object matching this JSON schema:\n{json.dumps(schema.model_json_schema())}"

    if settings.llm_model == "mock":
        usage = Usage("mock", (len(system_full) + len(user)) // 4, 200, MOCK_COST_USD)
        try:
            return schema.model_validate(mock_output()), usage
        except ValidationError as e:
            raise LLMError(f"Invalid model output: {e.error_count()} validation errors", usage)

    import litellm  # imported lazily: it is slow to import and unused in mock mode

    litellm.drop_params = True  # ignore params (e.g. response_format) a provider lacks
    usage = Usage(settings.llm_model)
    try:
        resp = litellm.completion(
            model=settings.llm_model,
            messages=[{"role": "system", "content": system_full}, {"role": "user", "content": user}],
            response_format={"type": "json_object"},
            temperature=0,
            timeout=settings.llm_timeout_seconds,
            num_retries=1,
        )
    except Exception as e:
        raise LLMError(f"Model call failed: {type(e).__name__}", usage)

    usage.input_tokens = getattr(resp.usage, "prompt_tokens", 0) or 0
    usage.output_tokens = getattr(resp.usage, "completion_tokens", 0) or 0
    try:
        usage.cost_usd = float(litellm.completion_cost(completion_response=resp) or 0.0)
    except Exception:
        usage.cost_usd = 0.0  # unknown price for this model; tokens are still recorded

    try:
        content = resp.choices[0].message.content or ""
        return schema.model_validate_json(_strip_fences(content)), usage
    except ValidationError as e:
        raise LLMError(f"Invalid model output: {e.error_count()} validation errors", usage)
