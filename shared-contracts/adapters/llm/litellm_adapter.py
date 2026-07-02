"""LiteLLM adapter — 100+ provider unified gateway.

Fallback: direct provider call.
"""
from dataclasses import dataclass, field

@dataclass
class LLMResponse:
    content: str = ""
    model: str = ""
    tokens_used: int = 0
    finish_reason: str = "stop"

def complete(prompt: str, model: str = "deepseek/deepseek-chat",
             max_tokens: int = 2000) -> LLMResponse:
    """Phase 1 stub; Phase 2: integrate litellm."""
    return LLMResponse(
        content=f"[stub: LiteLLM] prompt_len={len(prompt)}", model=model)
