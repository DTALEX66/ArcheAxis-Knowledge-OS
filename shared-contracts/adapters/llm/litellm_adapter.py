"""LiteLLM adapter — unified provider gateway with real execution evidence."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    content: str = ""
    model: str = ""
    tokens_used: int = 0
    finish_reason: str = "stop"
    actual_model: str = "unknown"
    actual_finish_reason: str = "unknown"


def _value(item: Any, name: str, default: Any = None) -> Any:
    if isinstance(item, dict):
        return item.get(name, default)
    return getattr(item, name, default)


def complete(
    prompt: str,
    model: str = "deepseek/deepseek-chat",
    max_tokens: int = 2000,
    image_data_url: str | None = None,
    **kwargs: Any,
) -> LLMResponse:
    """Execute a LiteLLM completion; provider errors propagate to the caller."""
    if not prompt.strip():
        raise ValueError("prompt is required")
    content: str | list[dict[str, Any]] = prompt
    if image_data_url is not None:
        prefixes = ("data:image/png;base64,", "data:image/jpeg;base64,")
        if not isinstance(image_data_url, str) or not image_data_url.startswith(prefixes):
            raise ValueError("only inline original PNG/JPEG is accepted")
        encoded = image_data_url.split(",", 1)[1]
        if len(encoded) > 85336 or len(base64.b64decode(encoded, validate=True)) > 64000:
            raise ValueError("original image byte budget exceeded")
        content = [
            {"type": "text", "text": prompt},
            {"type": "image_url", "image_url": {"url": image_data_url}},
        ]
    from litellm import completion

    response = completion(
        model=model,
        messages=[{"role": "user", "content": content}],
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
        actual_model=str(_value(response, "model", "unknown") or "unknown"),
        tokens_used=int(_value(usage, "total_tokens", 0) or 0),
        finish_reason=str(_value(choice, "finish_reason", "stop") or "stop"),
        actual_finish_reason=str(_value(choice, "finish_reason", "unknown") or "unknown"),
    )
