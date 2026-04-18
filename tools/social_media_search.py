"""
Social-media search tool.
Searches Twitter/X (via RapidAPI Twitter scraper) and Reddit for
content relevant to a topic.
Falls back gracefully when API keys are absent.
"""
import os
import json
from typing import List, Dict

import requests


# ── Twitter / X ───────────────────────────────────────────────────────────────

def _search_twitter(query: str, max_results: int = 10) -> List[Dict]:
    rapid_key = os.getenv("RAPIDAPI_KEY", "")
    if not rapid_key:
        return []
    try:
        url = "https://twitter154.p.rapidapi.com/search/search"
        resp = requests.get(
            url,
            headers={
                "X-RapidAPI-Key": rapid_key,
                "X-RapidAPI-Host": "twitter154.p.rapidapi.com",
            },
            params={"query": query, "limit": max_results, "language": "en"},
            timeout=10,
        )
        data = resp.json()
        results = []
        for tweet in data.get("results", []):
            results.append({
                "source": "twitter",
                "text": tweet.get("text", ""),
                "user": tweet.get("user", {}).get("username", ""),
                "likes": tweet.get("favorite_count", 0),
                "url": f"https://twitter.com/i/web/status/{tweet.get('tweet_id', '')}",
            })
        return results
    except Exception as exc:
        print(f"[social_search] Twitter error: {exc}")
        return []


# ── Reddit ────────────────────────────────────────────────────────────────────

def _search_reddit(query: str, max_results: int = 10) -> List[Dict]:
    try:
        url = "https://www.reddit.com/search.json"
        resp = requests.get(
            url,
            params={"q": query, "limit": max_results, "sort": "relevance"},
            headers={"User-Agent": "WebsiteBuilderBot/1.0"},
            timeout=10,
        )
        data = resp.json()
        results = []
        for post in data.get("data", {}).get("children", []):
            d = post.get("data", {})
            results.append({
                "source": "reddit",
                "title": d.get("title", ""),
                "text": d.get("selftext", "")[:500],
                "subreddit": d.get("subreddit", ""),
                "url": f"https://reddit.com{d.get('permalink', '')}",
            })
        return results
    except Exception as exc:
        print(f"[social_search] Reddit error: {exc}")
        return []


# ── Public API ────────────────────────────────────────────────────────────────

def search_social(query: str, max_results: int = 10) -> str:
    """Return a JSON string combining Twitter + Reddit results."""
    results = _search_twitter(query, max_results) + _search_reddit(query, max_results)
    return json.dumps(results, ensure_ascii=False)


def social_context_for_topic(topic: str) -> str:
    """
    Aggregate social-media content about a topic into a short readable
    context string for AI agents.
    """
    raw = json.loads(search_social(topic, 10))
    if not raw:
        return f"No social-media data available for: {topic}"
    lines = []
    for item in raw[:8]:
        src = item.get("source", "")
        if src == "twitter":
            lines.append(f"[Twitter @{item.get('user')}] {item.get('text', '')}")
        elif src == "reddit":
            lines.append(f"[Reddit r/{item.get('subreddit')}] {item.get('title', '')} — {item.get('text', '')}")
    return "\n".join(lines)
