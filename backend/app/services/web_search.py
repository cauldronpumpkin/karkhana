from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from collections.abc import AsyncGenerator

import html2text
import httpx
from duckduckgo_search import DDGS

logger = logging.getLogger(__name__)


class _RateLimiter:
    """Simple in-memory sliding window rate limiter."""

    def __init__(self, max_requests: int = 10, window_seconds: float = 60.0) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._timestamps: deque[float] = deque()

    async def acquire(self) -> None:
        now = time.monotonic()
        # Remove timestamps outside the current window
        while self._timestamps and self._timestamps[0] < now - self.window_seconds:
            self._timestamps.popleft()

        if len(self._timestamps) >= self.max_requests:
            wait_time = self._timestamps[0] - (now - self.window_seconds)
            if wait_time > 0:
                logger.debug("Rate limit reached, waiting %.2fs", wait_time)
                await asyncio.sleep(wait_time)
                # Re-check after waiting
                await self.acquire()
                return

        self._timestamps.append(now)


class WebSearchService:
    """Web search service using DuckDuckGo with rate limiting and caching."""

    def __init__(
        self,
        max_requests_per_minute: int = 10,
        cache_ttl_seconds: float = 3600.0,
    ) -> None:
        self._rate_limiter = _RateLimiter(
            max_requests=max_requests_per_minute,
            window_seconds=60.0,
        )
        self._cache_ttl = cache_ttl_seconds
        # Cache: query -> (timestamp, results)
        self._search_cache: dict[str, tuple[float, list[dict]]] = {}
        self._text_converter = html2text.HTML2Text()
        self._text_converter.ignore_links = False
        self._text_converter.ignore_images = True

    async def search(self, query: str, max_results: int = 5) -> list[dict]:
        """Search the web and return list of {title, url, snippet}.

        Returns empty list on failure (logged).
        """
        if not query.strip():
            return []

        # Check cache
        cached = self._get_cached(query)
        if cached is not None:
            logger.debug("Cache hit for query: %s", query)
            return cached

        await self._rate_limiter.acquire()

        try:
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self._ddgs_search(query, max_results),
            )
            self._cache_result(query, results)
            return results
        except Exception:
            logger.exception("Search failed for query: %s", query)
            return []

    async def fetch_page(self, url: str) -> str:
        """Fetch a URL and extract readable text.

        Returns empty string on failure (logged).
        """
        if not url.strip():
            return ""

        await self._rate_limiter.acquire()

        try:
            async with httpx.AsyncClient(
                follow_redirects=True,
                timeout=30.0,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                },
            ) as client:
                response = await client.get(url)
                response.raise_for_status()
                return self._text_converter.handle(response.text)
        except Exception:
            logger.exception("Failed to fetch page: %s", url)
            return ""

    def _ddgs_search(self, query: str, max_results: int) -> list[dict]:
        """Synchronous DuckDuckGo search call."""
        with DDGS() as ddgs:
            raw_results = ddgs.text(
                keywords=query,
                max_results=max_results,
            )
        return [
            {
                "title": r.get("title", ""),
                "url": r.get("href", ""),
                "snippet": r.get("body", ""),
            }
            for r in raw_results
        ]

    def _get_cached(self, query: str) -> list[dict] | None:
        """Return cached results if still valid."""
        entry = self._search_cache.get(query)
        if entry is None:
            return None
        timestamp, results = entry
        if time.monotonic() - timestamp > self._cache_ttl:
            del self._search_cache[query]
            return None
        return results

    def _cache_result(self, query: str, results: list[dict]) -> None:
        """Store results in cache."""
        self._search_cache[query] = (time.monotonic(), results)
