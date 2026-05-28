import os
import requests
from typing import List, Dict


def web_search(query: str, num_results: int = 5) -> List[Dict]:
    """Search the web. Returns list of {title, url, snippet}."""
    key = os.getenv("BRAVE_SEARCH_API_KEY")
    if not key:
        print(
            f"  [WARN] BRAVE_SEARCH_API_KEY not set — skipping search for: {query!r}\n"
            "         Set the key in .env or environment to enable live collection."
        )
        return []
    return _brave_search(query, num_results, key)


def _brave_search(query: str, n: int, key: str) -> List[Dict]:
    resp = requests.get(
        "https://api.search.brave.com/res/v1/web/search",
        headers={"Accept": "application/json", "X-Subscription-Token": key},
        params={"q": query, "count": n},
        timeout=15,
    )
    resp.raise_for_status()
    results = resp.json().get("web", {}).get("results", [])
    return [
        {
            "title": r.get("title", ""),
            "url": r.get("url", ""),
            "snippet": r.get("description", ""),
        }
        for r in results
    ]
