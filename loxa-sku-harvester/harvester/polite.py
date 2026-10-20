"""Polite HTTP: robots.txt, rate limiting, retries, request counting."""
import time
import urllib.robotparser
from urllib.parse import urljoin, urlparse

import requests

USER_AGENT = "LoxaAgentBot/1.0 (partner onboarding; contact: growth@loxacover.com)"


class PoliteFetcher:
    def __init__(self, base_url, delay=1.0, timeout=20, retries=2):
        self.base = base_url.rstrip("/")
        self.delay = delay
        self.timeout = timeout
        self.retries = retries
        self.requests_made = 0
        self.blocked = 0
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "en-GB,en;q=0.9"})
        self._last = 0.0
        self.robots = urllib.robotparser.RobotFileParser()
        self.robots_found = False
        self.sitemaps = []
        self._load_robots()

    def _load_robots(self):
        status, text, _ = self._raw_get(self.base + "/robots.txt")
        if status == 200 and text:
            self.robots.parse(text.splitlines())
            self.robots_found = True
            self.sitemaps = [l.split(":", 1)[1].strip() for l in text.splitlines()
                             if l.lower().startswith("sitemap:")]

    def allowed(self, url):
        return True if not self.robots_found else self.robots.can_fetch(USER_AGENT, url)

    def _raw_get(self, url):
        for attempt in range(self.retries + 1):
            wait = self.delay - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            self.requests_made += 1
            try:
                r = self.session.get(url, timeout=self.timeout)
                if r.status_code in (429, 503) and attempt < self.retries:
                    time.sleep(max(self.delay, 2) * (attempt + 2))  # back off, then retry
                    continue
                return r.status_code, r.text, dict(r.headers)
            except requests.RequestException as e:
                if attempt == self.retries:
                    return f"error:{type(e).__name__}", None, {}
        return "error:retries", None, {}

    def get(self, url):
        """Rate-limited GET that honours robots.txt. Returns (status, text, headers)."""
        if not self.allowed(url):
            self.blocked += 1
            return "blocked_by_robots", None, {}
        return self._raw_get(url)


def absolute(href, page_url):
    return urljoin(page_url, href)


def same_host(url, base):
    return urlparse(url).netloc == urlparse(base).netloc
