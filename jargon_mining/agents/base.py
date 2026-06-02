"""Shared agentic loop: system prompt + Anthropic server-side web_search → text output."""

import time
from typing import Callable, List, Dict, Optional
import anthropic

# Anthropic's server-side web search tool. The model issues queries and Anthropic
# executes the search on its infrastructure — no separate Brave/Tavily/etc. key.
_WEB_SEARCH_TOOL = {
    "type": "web_search_20250305",
    "name": "web_search",
    "max_uses": 30,
}

_MAX_ITERATIONS = 40
_MAX_RETRIES = 6
_BASE_BACKOFF_S = 8


def run_agent(
    system_prompt: str,
    user_message: str,
    model: str,
    search_fn: Optional[Callable[[str, int], List[Dict]]] = None,
) -> str:
    """
    Run an agentic loop with Anthropic's server-side web search tool.

    `search_fn` is accepted for backwards compatibility but ignored — the search
    is executed by Anthropic, not by the caller.
    """
    del search_fn

    client = anthropic.Anthropic()

    system = [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    messages = [{"role": "user", "content": user_message}]

    for _ in range(_MAX_ITERATIONS):
        response = _create_with_retry(
            client,
            model=model,
            max_tokens=8096,
            system=system,
            tools=[_WEB_SEARCH_TOOL],
            messages=messages,
        )

        for block in response.content:
            if getattr(block, "type", None) == "server_tool_use":
                query = getattr(block, "input", {}).get("query", "")
                if query:
                    print(f"    [search] {query!r}", flush=True)

        if response.stop_reason == "end_turn":
            return _extract_text(response)

        return _extract_text(response)

    raise RuntimeError(
        f"Agent exceeded {_MAX_ITERATIONS} iterations without completing."
    )


def _create_with_retry(client: anthropic.Anthropic, **kwargs):
    """Call messages.create with exponential-backoff retry on 429/overload."""
    for attempt in range(_MAX_RETRIES):
        try:
            return client.messages.create(**kwargs)
        except anthropic.RateLimitError as e:
            wait = _retry_after(e) or _BASE_BACKOFF_S * (2 ** attempt)
            print(
                f"    [rate-limit] {e.__class__.__name__}: waiting {wait}s "
                f"(attempt {attempt + 1}/{_MAX_RETRIES})",
                flush=True,
            )
            time.sleep(wait)
        except anthropic.APIStatusError as e:
            if getattr(e, "status_code", None) in (529, 503, 500):
                wait = _BASE_BACKOFF_S * (2 ** attempt)
                print(
                    f"    [retry] {e.status_code} from API: waiting {wait}s "
                    f"(attempt {attempt + 1}/{_MAX_RETRIES})",
                    flush=True,
                )
                time.sleep(wait)
            else:
                raise
    raise RuntimeError(f"Exceeded {_MAX_RETRIES} retries on Anthropic API.")


def _retry_after(exc: anthropic.RateLimitError) -> Optional[int]:
    """Read the Retry-After header if present, else None."""
    resp = getattr(exc, "response", None)
    if resp is None:
        return None
    val = resp.headers.get("retry-after") or resp.headers.get("anthropic-ratelimit-input-tokens-reset")
    if not val:
        return None
    try:
        return max(1, int(float(val)))
    except (TypeError, ValueError):
        return None


def _extract_text(response) -> str:
    parts = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "\n".join(parts)
