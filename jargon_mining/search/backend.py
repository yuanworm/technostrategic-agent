"""
Web search backend.

The agents use Anthropic's server-side `web_search_20250305` tool, so live web
search is handled by Anthropic with the same ANTHROPIC_API_KEY — no separate
search-provider key is required.

This module is kept as a no-op shim so callers passing a `search_fn` continue
to work. If you ever want to route searches through your own provider
(Brave, Tavily, SerpAPI), implement it here and update `agents/base.py` to
use a client-side tool definition instead of the server-side one.
"""

from typing import List, Dict


def web_search(query: str, num_results: int = 5) -> List[Dict]:  # noqa: ARG001
    """No-op. Real search runs server-side inside Anthropic's web_search tool."""
    return []
