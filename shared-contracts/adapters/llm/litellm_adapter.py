"""LiteLLM adapter — unified provider gateway with real execution evidence."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    content: str = ""
    model: str = ""
    tokens_used: int = 0
    finish_reason: str = "stop"


def _value(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def complete(
    prompt: str,
    model: str = "deepseek/deepseek-chat",
    max_tokens: int = 2000,
    **kwargs: Any,
) -> LLMResponse:
    """Execute a LiteLLM completion; provider errors propagate to the caller."""
    if not prompt.strip():
        raise ValueError("prompt is required")
    from litellm import completion

    response = completion(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=max_tokens,
        **kwargs,
    )
    choices = _value(response, "choices", []) or []
    if not choices:
        raise RuntimeError("LiteLLM returned no choices")
    choice = choices[0]
    message = _value(choice, "message", {})
    content = _value(message, "content", "") or ""
    usage = _value(response, "usage", {})
    return LLMResponse(
        content=str(content),
        model=str(_value(response, "model", model) or model),
        tokens_used=int(_value(usage, "total_tokens", 0) or 0),
        finish_reason=str(_value(choice, "finish_reason", "stop") or "stop"),
    )
