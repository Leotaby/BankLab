"""Polite HTTP client with rate limiting and retries."""

import logging
import time
from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class PoliteRequester:
    """HTTP client with rate limiting, retries, and proper headers.

    Implements SEC EDGAR requirements:
    - User-Agent header with contact info
    - Rate limiting (max 10 requests/second)
    - Exponential backoff on errors
    """

    def __init__(
        self,
        user_agent: str,
        rate_limit: float = 0.1,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
    ):
        """Initialize polite requester.

        Args:
            user_agent: User-Agent header value (required by SEC)
            rate_limit: Minimum seconds between requests
            max_retries: Number of retry attempts on failure
            backoff_factor: Exponential backoff multiplier
        """
        self.user_agent = user_agent
        self.rate_limit = rate_limit
        self._last_request_time: float = 0

        # Configure session with retries
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        # Set default headers
        self.session.headers.update(
            {
                "User-Agent": self.user_agent,
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
            }
        )

    def _wait_for_rate_limit(self) -> None:
        """Wait if needed to respect rate limit."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit:
            sleep_time = self.rate_limit - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.3f}s")
            time.sleep(sleep_time)

    def get(self, url: str, **kwargs: Any) -> requests.Response:
        """Make rate-limited GET request.

        Args:
            url: Target URL
            **kwargs: Additional arguments passed to requests.get

        Returns:
            Response object

        Raises:
            requests.RequestException: On request failure after retries
        """
        self._wait_for_rate_limit()
        logger.debug(f"GET {url}")

        try:
            response = self.session.get(url, timeout=30, **kwargs)
            response.raise_for_status()
            return response
        finally:
            self._last_request_time = time.time()

    def get_json(self, url: str, **kwargs: Any) -> dict[str, Any]:
        """Make rate-limited GET request and parse JSON response.

        Args:
            url: Target URL
            **kwargs: Additional arguments passed to requests.get

        Returns:
            Parsed JSON as dictionary
        """
        response = self.get(url, **kwargs)
        return response.json()

    def get_text(self, url: str, **kwargs: Any) -> str:
        """Make rate-limited GET request and return text content.

        Args:
            url: Target URL
            **kwargs: Additional arguments passed to requests.get

        Returns:
            Response text content
        """
        response = self.get(url, **kwargs)
        return response.text

    def get_bytes(self, url: str, **kwargs: Any) -> bytes:
        """Make rate-limited GET request and return raw bytes.

        Args:
            url: Target URL
            **kwargs: Additional arguments passed to requests.get

        Returns:
            Response content as bytes
        """
        response = self.get(url, **kwargs)
        return response.content
