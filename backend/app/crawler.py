"""
Playwright-based crawler.

Given a starting URL, fetch the home page and follow a small, curated set of
internal links — about / contact / shipping / faq / privacy / terms — because
those pages contain the trust + consistency signals the audit looks for.

Everything is wrapped in try/except: a bad link must NOT crash the run.
"""
from __future__ import annotations

import asyncio
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, TimeoutError as PWTimeout

from .config import settings


# Keywords used to score whether an internal link is worth crawling.
PAGE_INTENT_KEYWORDS: dict[str, list[str]] = {
    "about": ["about", "company", "who-we-are", "story"],
    "contact": ["contact", "reach", "get-in-touch", "support"],
    "shipping": ["shipping", "delivery", "ship", "logistics"],
    "faq": ["faq", "help", "questions", "q-and-a"],
    "policy": ["policy", "terms", "privacy", "refund", "return"],
    "pricing": ["pricing", "plans"],
}

ALL_KEYWORDS: list[str] = [k for v in PAGE_INTENT_KEYWORDS.values() for k in v]


@dataclass
class FetchedPage:
    url: str
    intent: str  # "home" | "about" | "contact" | "shipping" | "faq" | "policy" | "pricing" | "other"
    title: str
    html: str
    text: str
    final_url: str
    ok: bool = True
    error: str = ""


@dataclass
class CrawlResult:
    start_url: str
    base_url: str
    pages: list[FetchedPage] = field(default_factory=list)
    ssl_ok: bool = False
    error: str = ""

    def page_by_intent(self, intent: str) -> FetchedPage | None:
        for p in self.pages:
            if p.intent == intent and p.ok:
                return p
        return None


def _normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if not re.match(r"^https?://", url, re.IGNORECASE):
        url = "https://" + url
    return url


def _classify_link(href: str) -> str:
    h = href.lower()
    for intent, kws in PAGE_INTENT_KEYWORDS.items():
        for kw in kws:
            if kw in h:
                return intent
    return "other"


def _extract_internal_links(html: str, base_url: str) -> list[tuple[str, str]]:
    """Return [(absolute_url, intent), ...] for same-host links of interest."""
    found: list[tuple[str, str]] = []
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        return found

    base_host = urlparse(base_url).netloc.lower()
    seen: set[str] = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        abs_url = urljoin(base_url, href)
        try:
            parsed = urlparse(abs_url)
        except Exception:
            continue
        if parsed.scheme not in ("http", "https"):
            continue
        # Same registrable host (ignore subdomain differences only loosely)
        if base_host and parsed.netloc and base_host.split(":")[0] not in parsed.netloc:
            continue
        intent = _classify_link(abs_url)
        if intent == "other":
            continue
        clean = abs_url.split("#")[0]
        if clean in seen:
            continue
        seen.add(clean)
        found.append((clean, intent))
    return found


async def _fetch_one(browser: Browser, url: str, intent: str) -> FetchedPage:
    """Fetch a single URL with Playwright. Never raises."""
    page = None
    try:
        context = await browser.new_context(
            user_agent=(
                "Mozilla/5.0 (compatible; CompareYourWebsite/1.0; "
                "+https://compareyourwebsite.com/bot)"
            ),
            ignore_https_errors=False,
            viewport={"width": 1280, "height": 800},
        )
        page = await context.new_page()
        response = await page.goto(
            url, timeout=settings.PAGE_TIMEOUT_MS, wait_until="domcontentloaded"
        )
        # Give SPAs a beat to hydrate, but don't hang on it.
        try:
            await page.wait_for_load_state("networkidle", timeout=4000)
        except PWTimeout:
            pass

        title = await page.title()
        html = await page.content()
        text = ""
        try:
            text = await page.inner_text("body")
        except Exception:
            try:
                text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
            except Exception:
                text = ""

        final_url = page.url
        await context.close()

        if response is None:
            return FetchedPage(
                url=url, intent=intent, title="", html="", text="",
                final_url=url, ok=False, error="No response",
            )

        if response.status >= 400:
            return FetchedPage(
                url=url, intent=intent, title=title, html=html, text=text,
                final_url=final_url, ok=False, error=f"HTTP {response.status}",
            )

        return FetchedPage(
            url=url, intent=intent, title=title or "", html=html or "",
            text=text or "", final_url=final_url, ok=True,
        )
    except PWTimeout:
        return FetchedPage(
            url=url, intent=intent, title="", html="", text="",
            final_url=url, ok=False, error="Timeout",
        )
    except Exception as e:
        return FetchedPage(
            url=url, intent=intent, title="", html="", text="",
            final_url=url, ok=False, error=f"{type(e).__name__}: {e}",
        )
    finally:
        if page is not None:
            try:
                await page.close()
            except Exception:
                pass


async def crawl_site(start_url: str) -> CrawlResult:
    """
    Crawl a small set of pages from `start_url`. Always returns a CrawlResult;
    on hard failure the .error field is set and .pages may be empty.
    """
    norm = _normalize_url(start_url)
    if not norm:
        return CrawlResult(start_url=start_url, base_url="", error="Empty URL")

    parsed = urlparse(norm)
    base_url = f"{parsed.scheme}://{parsed.netloc}"
    result = CrawlResult(start_url=norm, base_url=base_url, ssl_ok=parsed.scheme == "https")

    try:
        async with async_playwright() as pw:
            try:
                browser = await pw.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"],
                )
            except Exception as e:
                result.error = f"Could not launch browser: {e}"
                return result

            try:
                # Step 1 — fetch home
                home = await _fetch_one(browser, norm, "home")
                result.pages.append(home)

                if not home.ok or not home.html:
                    # If we cannot read the home page, abort gracefully.
                    if not result.error:
                        result.error = home.error or "Home page unreachable"
                    await browser.close()
                    return result

                # Step 2 — discover internal links
                links = _extract_internal_links(home.html, home.final_url or norm)
                # de-dup by intent so we get a balanced spread
                picked: list[tuple[str, str]] = []
                seen_intents: set[str] = set()
                for u, intent in links:
                    key = (intent, u)
                    if len(picked) >= settings.MAX_PAGES_PER_SITE - 1:
                        break
                    # Prefer 1 per intent first, then fill remaining slots
                    if intent in seen_intents and len(picked) >= len(
                        PAGE_INTENT_KEYWORDS
                    ):
                        continue
                    picked.append((u, intent))
                    seen_intents.add(intent)

                # Step 3 — fetch them in parallel (small concurrency)
                if picked:
                    tasks = [_fetch_one(browser, u, i) for u, i in picked]
                    fetched = await asyncio.gather(*tasks, return_exceptions=True)
                    for f in fetched:
                        if isinstance(f, FetchedPage):
                            result.pages.append(f)

            finally:
                try:
                    await browser.close()
                except Exception:
                    pass
    except Exception as e:
        result.error = f"Crawl failed: {type(e).__name__}: {e}"
        return result

    return result
