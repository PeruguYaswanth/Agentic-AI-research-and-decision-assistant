import os
import logging
from typing import List, Dict, Any
import httpx
from app.config import settings

logger = logging.getLogger(__name__)

class WebSearchTool:
    def __init__(self):
        self.api_key = settings.TAVILY_API_KEY
        self.tavily_client = None
        if self.api_key and self.api_key.strip() and not self.api_key.startswith("your_"):
            try:
                from tavily import TavilyClient
                self.tavily_client = TavilyClient(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Tavily client: {e}")

    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        Searches web for query using live search providers (Tavily, DDGS, Wikipedia/HTTP API).
        Returns list of dicts with title, url, snippet, source.
        """
        results: List[Dict[str, Any]] = []

        # 1. Try Tavily API if configured
        if self.tavily_client:
            try:
                response = self.tavily_client.search(query=query, max_results=max_results, search_depth="basic")
                for item in response.get("results", []):
                    title = item.get("title") or "Web Source"
                    url = item.get("url") or "#"
                    snippet = item.get("content") or item.get("snippet") or ""
                    if snippet or title:
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet,
                            "source": "web"
                        })
                if results:
                    logger.info(f"Tavily search returned {len(results)} results for query: '{query}'")
                    return results
            except Exception as e:
                logger.error(f"Tavily search error for query '{query}': {e}")

        # 2. Try DuckDuckGo search (ddgs) - real live web search without requiring API keys
        try:
            from ddgs import DDGS
            with DDGS() as ddgs:
                ddg_results = list(ddgs.text(query, max_results=max_results))
                for item in ddg_results:
                    title = item.get("title") or "Web Source"
                    url = item.get("href") or item.get("url") or "#"
                    snippet = item.get("body") or item.get("snippet") or ""
                    if title or snippet:
                        results.append({
                            "title": title,
                            "url": url,
                            "snippet": snippet,
                            "source": "web"
                        })
                if results:
                    logger.info(f"DDGS search returned {len(results)} results for query: '{query}'")
                    return results
        except Exception as e:
            logger.warning(f"DDGS search error for query '{query}': {e}")

        # 3. Fallback: Wikipedia search API (real authoritative data and links)
        try:
            wiki_results = self._search_wikipedia(query, max_results=max_results)
            if wiki_results:
                logger.info(f"Wikipedia search returned {len(wiki_results)} results for query: '{query}'")
                return wiki_results
        except Exception as e:
            logger.warning(f"Wikipedia search fallback error for query '{query}': {e}")

        return results

    def _search_wikipedia(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 AgenticResearchAssistant/1.0"
        }
        # Extract keywords if query is conversational
        clean_query = query
        for phrase in ["give me movie names in which", "movies in which", "acted as a hero", "acted as hero", "movies of", "list of", "acted in", "hero in"]:
            clean_query = clean_query.lower().replace(phrase, "").strip()
        search_term = clean_query.strip() or query

        url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={httpx.URL(search_term).raw_path.decode()}&limit={max_results}&namespace=0&format=json"
        with httpx.Client(headers=headers, timeout=8.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                # data format: [query, [titles], [descriptions], [urls]]
                if len(data) >= 4 and isinstance(data[1], list):
                    results = []
                    for title, desc, link in zip(data[1], data[2], data[3]):
                        # If description is empty, fetch brief summary
                        snippet = desc
                        if not snippet:
                            summary_url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{httpx.URL(title).raw_path.decode()}"
                            try:
                                sum_resp = client.get(summary_url)
                                if sum_resp.status_code == 200:
                                    snippet = sum_resp.json().get("extract", "")
                            except Exception:
                                pass
                        results.append({
                            "title": title,
                            "url": link,
                            "snippet": snippet or f"Wikipedia article and details for {title}.",
                            "source": "web"
                        })
                    if results:
                        return results
        return []

