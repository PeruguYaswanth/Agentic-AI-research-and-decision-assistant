import os
import re
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import httpx

from app.config import settings
from app.tools.page_fetcher import PageFetcher, extract_domain, calculate_authority

logger = logging.getLogger(__name__)

class WebSearchTool:
    def __init__(self):
        self.api_key = settings.TAVILY_API_KEY
        self.tavily_client = None
        self.page_fetcher = PageFetcher(timeout=4.5)

        if self.api_key and self.api_key.strip() and not self.api_key.startswith("your_"):
            try:
                from tavily import TavilyClient
                self.tavily_client = TavilyClient(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Failed to initialize Tavily client: {e}")

    def fetch_direct_live_data(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Specialized sub-second live API data fetcher for real-time crypto prices, weather, etc.
        Returns formatted live evidence dictionary if query matches.
        """
        q_lower = query.lower()

        # 1. Crypto / Bitcoin live price
        if any(term in q_lower for term in ["bitcoin", "btc", "ethereum", "eth", "solana", "sol", "crypto price"]):
            coin_id = "bitcoin"
            coin_name = "Bitcoin (BTC)"
            if "ethereum" in q_lower or "eth" in q_lower:
                coin_id = "ethereum"
                coin_name = "Ethereum (ETH)"
            elif "solana" in q_lower or "sol" in q_lower:
                coin_id = "solana"
                coin_name = "Solana (SOL)"

            try:
                with httpx.Client(timeout=4.0) as client:
                    resp = client.get(f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd,inr&include_24hr_change=true")
                    if resp.status_code == 200:
                        data = resp.json()
                        if coin_id in data:
                            price_usd = data[coin_id].get("usd")
                            price_inr = data[coin_id].get("inr", price_usd * 83.5 if price_usd else 0.0)
                            change_24h = data[coin_id].get("usd_24h_change", 0.0)
                            change_str = f"+{change_24h:.2f}%" if change_24h >= 0 else f"{change_24h:.2f}%"
                            now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

                            return {
                                "title": f"{coin_name} Live Market Price",
                                "url": f"https://www.coingecko.com/en/coins/{coin_id}",
                                "publisher": "CoinGecko Real-Time Market API",
                                "authority_score": 0.99,
                                "published_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                                "snippet": f"The current live price of {coin_name} as of {now_str} is ${price_usd:,.2f} USD (approx ₹{price_inr:,.2f} INR), with a 24-hour change of {change_str}.",
                                "full_content": f"Real-time cryptocurrency market data: {coin_name} current trading price is ${price_usd:,.2f} USD. 24h market price change: {change_str}. Currency in INR: ₹{price_inr:,.2f}.",
                                "source": "web"
                            }
            except Exception as e:
                logger.debug(f"Direct crypto price fetch error: {e}")

        # 2. Weather in major cities (e.g. Hyderabad, New York, etc.)
        if "weather" in q_lower or "temperature" in q_lower:
            city_match = re.search(r"weather in ([a-zA-Z\s]+)", q_lower)
            if city_match:
                city = city_match.group(1).strip().title()
                try:
                    with httpx.Client(timeout=4.0) as client:
                        # Geocoding
                        geo_resp = client.get(f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json")
                        if geo_resp.status_code == 200:
                            geo_data = geo_resp.json()
                            if geo_data.get("results"):
                                loc = geo_data["results"][0]
                                lat = loc["latitude"]
                                lon = loc["longitude"]
                                country = loc.get("country", "")

                                weather_resp = client.get(f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m")
                                if weather_resp.status_code == 200:
                                    w_data = weather_resp.json().get("current", {})
                                    temp = w_data.get("temperature_2m")
                                    humidity = w_data.get("relative_humidity_2m")
                                    wind = w_data.get("wind_speed_10m")
                                    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

                                    return {
                                        "title": f"Live Weather for {city}, {country}",
                                        "url": f"https://open-meteo.com",
                                        "publisher": "Open-Meteo Global Weather Service",
                                        "authority_score": 0.98,
                                        "published_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                                        "snippet": f"The current live temperature in {city}, {country} is {temp}°C with {humidity}% relative humidity and wind speed of {wind} km/h (recorded {now_str}).",
                                        "full_content": f"Live meteorological report for {city}, {country}: Temperature: {temp}°C. Humidity: {humidity}%. Wind Speed: {wind} km/h.",
                                        "source": "web"
                                    }
                except Exception as e:
                    logger.debug(f"Direct weather fetch error: {e}")

        return None

    def search_and_fetch_pages(self, query: str, max_results: int = 5, fetch_pages: bool = True) -> List[Dict[str, Any]]:
        """
        Executes live search and fetches page contents for top results.
        Returns a list of structured source items with full evidence and authority scores.
        """
        evidence_items: List[Dict[str, Any]] = []

        # 1. Check if direct live factual API exists for real-time queries
        direct_data = self.fetch_direct_live_data(query)
        if direct_data:
            evidence_items.append(direct_data)

        # 2. Perform live search via Tavily, DDGS, or Wikipedia
        search_hits = self._execute_search_queries([query], max_results=max_results)

        if not search_hits and not evidence_items:
            logger.warning(f"No search hits found for query: '{query}'")
            return []

        # 3. Fetch full page contents for top URLs to extract verified paragraphs
        if fetch_pages and search_hits:
            urls_to_fetch = [hit["url"] for hit in search_hits if hit.get("url") and hit["url"] != "#"][:4]
            fetched_pages = self.page_fetcher.fetch_multiple_pages(urls_to_fetch, query=query, max_pages=4)

            # Map fetched pages by URL
            page_map = {p["url"]: p for p in fetched_pages}

            for hit in search_hits:
                url = hit.get("url", "")
                page = page_map.get(url)

                pub_name, auth_score = calculate_authority(url, hit.get("title", ""))
                published_date = None
                full_content = hit.get("snippet", "")

                if page and page.get("clean_text"):
                    # Use extracted excerpts and clean text
                    excerpts = "\n\n".join(page.get("relevant_excerpts", []))
                    if excerpts:
                        full_content = excerpts
                    else:
                        full_content = page["clean_text"][:1500]

                    if page.get("published_date"):
                        published_date = page["published_date"]
                    if page.get("publisher"):
                        pub_name = page["publisher"]
                    if page.get("authority_score"):
                        auth_score = max(auth_score, page["authority_score"])

                evidence_items.append({
                    "title": hit.get("title") or pub_name,
                    "url": url,
                    "publisher": pub_name,
                    "authority_score": auth_score,
                    "published_date": published_date,
                    "snippet": hit.get("snippet") or full_content[:250],
                    "full_content": full_content,
                    "source": "web"
                })
        else:
            for hit in search_hits:
                pub_name, auth_score = calculate_authority(hit.get("url", ""), hit.get("title", ""))
                evidence_items.append({
                    "title": hit.get("title") or pub_name,
                    "url": hit.get("url"),
                    "publisher": pub_name,
                    "authority_score": auth_score,
                    "published_date": None,
                    "snippet": hit.get("snippet", ""),
                    "full_content": hit.get("snippet", ""),
                    "source": "web"
                })

        # Deduplicate and sort by authority and content richness
        unique_items = []
        seen_urls = set()
        for item in evidence_items:
            url = item.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_items.append(item)
            elif not url and item not in unique_items:
                unique_items.append(item)

        # Sort: priority to high authority and items with full content
        unique_items.sort(key=lambda x: (x.get("authority_score", 0.7), len(x.get("full_content", ""))), reverse=True)
        return unique_items[:max_results + 1]

    def _execute_search_queries(self, queries: List[str], max_results: int = 5) -> List[Dict[str, Any]]:
        raw_results: List[Dict[str, Any]] = []

        for q in queries:
            # A. Try Tavily API
            if self.tavily_client:
                try:
                    response = self.tavily_client.search(query=q, max_results=max_results, search_depth="advanced")
                    for item in response.get("results", []):
                        title = item.get("title") or "Web Source"
                        url = item.get("url") or "#"
                        snippet = item.get("content") or item.get("snippet") or ""
                        if snippet or title:
                            raw_results.append({
                                "title": title,
                                "url": url,
                                "snippet": snippet,
                                "source": "web"
                            })
                    if raw_results:
                        continue
                except Exception as e:
                    logger.debug(f"Tavily search error for query '{q}': {e}")

            # B. Try DuckDuckGo (ddgs)
            try:
                from ddgs import DDGS
                with DDGS() as ddgs:
                    ddg_results = list(ddgs.text(q, max_results=max_results))
                    for item in ddg_results:
                        title = item.get("title") or "Web Source"
                        url = item.get("href") or item.get("url") or "#"
                        snippet = item.get("body") or item.get("snippet") or ""
                        if title or snippet:
                            raw_results.append({
                                "title": title,
                                "url": url,
                                "snippet": snippet,
                                "source": "web"
                            })
            except Exception as e:
                logger.debug(f"DDGS search error for query '{q}': {e}")

            # C. Wikipedia fallback
            if not raw_results:
                try:
                    wiki_results = self._search_wikipedia(q, max_results=max_results)
                    raw_results.extend(wiki_results)
                except Exception as e:
                    logger.debug(f"Wikipedia fallback error: {e}")

        return raw_results

    def _search_wikipedia(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AgenticResearchBot/2.0"
        }
        clean_query = query
        for phrase in ["give me movie names in which", "movies in which", "acted as a hero", "acted as hero", "movies of", "list of", "acted in", "hero in", "what is", "who is", "latest", "current"]:
            clean_query = clean_query.lower().replace(phrase, "").strip()
        search_term = clean_query.strip() or query

        url = f"https://en.wikipedia.org/w/api.php?action=opensearch&search={httpx.URL(search_term).raw_path.decode()}&limit={max_results}&namespace=0&format=json"
        with httpx.Client(headers=headers, timeout=5.0) as client:
            resp = client.get(url)
            if resp.status_code == 200:
                data = resp.json()
                if len(data) >= 4 and isinstance(data[1], list):
                    results = []
                    for title, desc, link in zip(data[1], data[2], data[3]):
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
                            "snippet": snippet or f"Wikipedia documentation and details for {title}.",
                            "source": "web"
                        })
                    return results
        return []

    # Backward compatibility wrapper
    def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        return self.search_and_fetch_pages(query, max_results=max_results, fetch_pages=True)
