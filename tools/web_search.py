"""
Web search tool — uses Tavily (preferred) or falls back to DuckDuckGo HTML scraping.
Returns structured content relevant to a website topic.
"""
import os
import json
import urllib.parse
from typing import List, Dict

import requests


def _tavily_search(query: str, max_results: int = 5) -> List[Dict]:
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        return []
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "max_results": max_results,
                "include_answer": True,
            },
            timeout=15,
        )
        data = resp.json()
        results = []
        if data.get("answer"):
            results.append({"title": "Summary", "content": data["answer"], "url": ""})
        for r in data.get("results", []):
            results.append({
                "title": r.get("title", ""),
                "content": r.get("content", ""),
                "url": r.get("url", ""),
            })
        return results
    except Exception as exc:
        print(f"[web_search] Tavily error: {exc}")
        return []


def _ddg_search(query: str, max_results: int = 5) -> List[Dict]:
    """Fallback: lightweight DuckDuckGo Instant Answer API."""
    try:
        url = (
            "https://api.duckduckgo.com/?q="
            + urllib.parse.quote_plus(query)
            + "&format=json&no_redirect=1&no_html=1"
        )
        resp = requests.get(url, timeout=10, headers={"User-Agent": "WebsiteBuilderBot/1.0"})
        data = resp.json()
        results = []
        abstract = data.get("AbstractText", "")
        if abstract:
            results.append({"title": data.get("Heading", query), "content": abstract, "url": data.get("AbstractURL", "")})
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append({
                    "title": topic.get("Text", "")[:80],
                    "content": topic.get("Text", ""),
                    "url": topic.get("FirstURL", ""),
                })
        return results
    except Exception as exc:
        print(f"[web_search] DDG error: {exc}")
        return []


def search_web(query: str, max_results: int = 5) -> str:
    """Return a JSON string of search results for the given query."""
    results = _tavily_search(query, max_results) or _ddg_search(query, max_results)
    return json.dumps(results, ensure_ascii=False)


def search_for_website_content(topic: str) -> str:
    """
    High-level helper: searches multiple queries about the topic and
    returns a combined context string for the AI content agent.
    """
    queries = [
        topic,
        f"{topic} overview key facts",
        f"{topic} services products features",
    ]
    all_content = []
    for q in queries:
        results = json.loads(search_web(q, 3))
        for r in results:
            if r.get("content"):
                all_content.append(f"## {r['title']}\n{r['content']}\n")
    return "\n".join(all_content) if all_content else f"No external content found for: {topic}"
