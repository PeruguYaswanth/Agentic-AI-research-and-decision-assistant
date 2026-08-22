import re
import logging
from typing import Dict, Any, Optional, List
from urllib.parse import urlparse
import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

# Known high-authority and domain reputations
HIGH_AUTHORITY_DOMAINS = {
    "openai.com": ("OpenAI Official", 0.98),
    "anthropic.com": ("Anthropic Official", 0.98),
    "github.com": ("GitHub", 0.95),
    "react.dev": ("React Official Documentation", 0.98),
    "nextjs.org": ("Next.js Official Documentation", 0.98),
    "python.org": ("Python Software Foundation", 0.98),
    "fastapi.tiangolo.com": ("FastAPI Official", 0.98),
    "docs.langchain.com": ("LangChain Documentation", 0.95),
    "reuters.com": ("Reuters", 0.95),
    "bloomberg.com": ("Bloomberg", 0.95),
    "coindesk.com": ("CoinDesk", 0.90),
    "coinmarketcap.com": ("CoinMarketCap", 0.92),
    "coingecko.com": ("CoinGecko", 0.92),
    "techcrunch.com": ("TechCrunch", 0.90),
    "theverge.com": ("The Verge", 0.88),
    "arstechnica.com": ("Ars Technica", 0.90),
    "wikipedia.org": ("Wikipedia", 0.90),
    "en.wikipedia.org": ("Wikipedia", 0.90),
    "npmjs.com": ("npm Registry", 0.95),
    "pypi.org": ("PyPI", 0.95),
    "gov": ("Government Official Source", 0.98),
    "edu": ("Academic / Research Institution", 0.95),
}

def extract_domain(url: str) -> str:
    try:
        netloc = urlparse(url).netloc.lower()
        return netloc.replace("www.", "")
    except Exception:
        return "web"

def calculate_authority(url: str, title: str) -> tuple[str, float]:
    domain = extract_domain(url)
    # Check exact domain or suffix
    for known_domain, (pub_name, score) in HIGH_AUTHORITY_DOMAINS.items():
        if domain == known_domain or domain.endswith("." + known_domain):
            return pub_name, score

    if domain.endswith(".gov"):
        return "Government Source", 0.98
    if domain.endswith(".edu"):
        return "Academic / University", 0.95
    if domain.endswith(".org"):
        return domain.capitalize(), 0.85

    # Default commercial / web domain
    return domain.capitalize(), 0.75

class PageFetcher:
    """
    Fetches real web page contents via HTTP, strips boilerplate/scripts,
    and extracts clean text passages and published dates for live verification.
    """
    def __init__(self, timeout: float = 5.0):
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 (AgenticResearchBot/2.0; +https://github.com/PeruguYaswanth)",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def fetch_page_content(self, url: str, query: Optional[str] = None) -> Dict[str, Any]:
        """
        Fetches and parses a single URL.
        Returns dictionary with title, publisher, authority_score, published_date, clean_text, and relevant_excerpts.
        """
        if not url or url.startswith("#") or url.startswith("javascript:"):
            return {
                "url": url,
                "success": False,
                "error": "Invalid URL"
            }

        domain = extract_domain(url)
        publisher, authority_score = calculate_authority(url, "")

        try:
            with httpx.Client(headers=self.headers, timeout=self.timeout, follow_redirects=True) as client:
                response = client.get(url)
                if response.status_code != 200:
                    return {
                        "url": url,
                        "domain": domain,
                        "publisher": publisher,
                        "authority_score": authority_score,
                        "success": False,
                        "status_code": response.status_code,
                        "clean_text": "",
                        "relevant_excerpts": []
                    }

                html = response.text
                return self._parse_html(html, url, query, publisher, authority_score)
        except Exception as e:
            logger.debug(f"Failed to fetch page {url}: {e}")
            return {
                "url": url,
                "domain": domain,
                "publisher": publisher,
                "authority_score": authority_score,
                "success": False,
                "error": str(e),
                "clean_text": "",
                "relevant_excerpts": []
            }

    def _parse_html(self, html: str, url: str, query: Optional[str], publisher: str, authority_score: float) -> Dict[str, Any]:
        soup = BeautifulSoup(html, "html.parser")

        # 1. Extract published date if available
        published_date = None
        date_meta_tags = [
            ("meta", {"property": "article:published_time"}),
            ("meta", {"property": "og:updated_time"}),
            ("meta", {"name": "pubdate"}),
            ("meta", {"name": "date"}),
            ("meta", {"name": "DC.date.issued"}),
            ("meta", {"itemprop": "datePublished"}),
        ]
        for tag, attrs in date_meta_tags:
            meta = soup.find(tag, attrs=attrs)
            if meta and meta.get("content"):
                published_date = meta["content"][:10]  # YYYY-MM-DD
                break

        if not published_date:
            time_tag = soup.find("time")
            if time_tag:
                published_date = time_tag.get("datetime") or time_tag.get_text()
                if published_date and len(published_date) >= 10:
                    published_date = published_date[:10]

        # 2. Extract page title
        title = ""
        if soup.title and soup.title.string:
            title = soup.title.string.strip()
        elif soup.find("h1"):
            title = soup.find("h1").get_text().strip()

        # 3. Clean boilerplates
        for element in soup(["script", "style", "nav", "footer", "header", "aside", "form", "noscript", "svg", "button", "iframe"]):
            element.decompose()

        # Extract textual content
        paragraphs = []
        # Look for article or main tags first
        main_content = soup.find(["article", "main"]) or soup.body or soup
        for p in main_content.find_all(["p", "h2", "h3", "li", "tr"]):
            text = p.get_text().strip()
            # Filter noise
            if len(text) > 25 and not any(skip in text.lower() for skip in ["cookie", "privacy policy", "all rights reserved", "terms of use", "subscribe"]):
                paragraphs.append(text)

        full_text = "\n".join(paragraphs)
        clean_text = re.sub(r"\s+", " ", full_text).strip()

        # 4. Extract query-relevant excerpts
        relevant_excerpts = []
        if query:
            keywords = [w.lower() for w in re.findall(r"[a-zA-Z0-9]+", query) if len(w) > 2 and w.lower() not in {"what", "when", "where", "which", "who", "how", "this", "that", "the", "and", "for"}]
            scored_paras = []
            for p in paragraphs:
                p_lower = p.lower()
                matches = sum(1 for kw in keywords if kw in p_lower)
                if matches > 0:
                    scored_paras.append((matches, p))
            scored_paras.sort(key=lambda x: x[0], reverse=True)
            relevant_excerpts = [p for _, p in scored_paras[:4]]

        if not relevant_excerpts and paragraphs:
            relevant_excerpts = paragraphs[:3]

        return {
            "url": url,
            "domain": extract_domain(url),
            "publisher": publisher,
            "authority_score": authority_score,
            "title": title or publisher,
            "published_date": published_date,
            "clean_text": clean_text[:3000],  # cap at dense 3000 chars
            "relevant_excerpts": relevant_excerpts,
            "success": True
        }

    def fetch_multiple_pages(self, urls: List[str], query: Optional[str] = None, max_pages: int = 5) -> List[Dict[str, Any]]:
        """
        Fetches multiple pages sequentially or in small batch with error safety.
        """
        results = []
        seen_domains = set()

        for url in urls:
            if len(results) >= max_pages:
                break
            domain = extract_domain(url)
            # Avoid fetching 5 pages from the exact same site
            if list(seen_domains).count(domain) >= 2:
                continue

            page_data = self.fetch_page_content(url, query=query)
            if page_data.get("success") and page_data.get("clean_text"):
                results.append(page_data)
                seen_domains.add(domain)

        return results
