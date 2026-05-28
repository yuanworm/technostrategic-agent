"""Shared agentic loop: system prompt + tool use for web_search → text output."""

import json
from typing import Callable, List, Dict
import anthropic

_WEB_SEARCH_TOOL = {
    "name": "web_search",
    "description": (
        "Search the web for current information. Use targeted queries to find "
        "job postings, forum threads, annual reports, practitioner blogs, regulatory "
        "filings, and other primary sources. Make multiple searches with different "
        "queries to cover the required source types."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "The search query string",
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (1–10)",
                "default": 5,
            },
        },
        "required": ["query"],
    },
}

_MAX_ITERATIONS = 30


def run_agent(
    system_prompt: str,
    user_message: str,
    model: str,
    search_fn: Callable[[str, int], List[Dict]],
) -> str:
    """
    Run an agentic loop with web_search tool access.
    Returns the final text response from the model.
    """
    client = anthropic.Anthropic()

    # Use prompt caching on the (long, fixed) system prompt
    system = [
        {
            "type": "text",
            "text": system_prompt,
            "cache_control": {"type": "ephemeral"},
        }
    ]

    messages = [{"role": "user", "content": user_message}]

    for iteration in range(_MAX_ITERATIONS):
        response = client.messages.create(
            model=model,
            max_tokens=8096,
            system=system,
            tools=[_WEB_SEARCH_TOOL],
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            return _extract_text(response)

        if response.stop_reason == "tool_use":
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    query = block.input.get("query", "")
                    n = block.input.get("num_results", 5)
                    print(f"    [search] {query!r}")
                    results = search_fn(query, n)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(results),
                        }
                    )

            messages.append({"role": "assistant", "content": response.content})
            messages.append({"role": "user", "content": tool_results})
        else:
            # stop_reason is max_tokens or something unexpected
            return _extract_text(response)

    raise RuntimeError(
        f"Agent exceeded {_MAX_ITERATIONS} iterations without completing. "
        "Check for a runaway tool-use loop."
    )


def _extract_text(response) -> str:
    parts = []
    for block in response.content:
        if hasattr(block, "text"):
            parts.append(block.text)
    return "\n".join(parts)
