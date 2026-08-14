"""DOM Extraction Helper — Milestone: DOM Layer.

Every scraper delegates ALL page.locator() calls to this helper.
If a site changes its HTML structure, you fix one file — not 15.

Design principles:
- Accept lists of fallback selectors (most-specific first)
- Return empty/None gracefully — never raise on a missing element
- Log which selector matched at DEBUG level
- Expand collapsible sections before extracting
"""

from __future__ import annotations

import asyncio
from typing import List, Optional
from playwright.async_api import Page, Locator
from loguru import logger


class DOMHelper:
    """Centralised DOM interaction layer for all Playwright scrapers."""

    def __init__(self, page: Page, default_timeout: int = 1500):
        self.page = page
        self.default_timeout = default_timeout

    # ── Locator resolution ────────────────────────────────────────────────────

    async def _find_section_by_heading(self, heading_text: str) -> Optional[Locator]:
        """Find an artdeco-card section whose h2 contains the given text (case-insensitive).

        LinkedIn's modern profile renders sections as React cards without stable IDs.
        This method scans all card sections for a matching h2 heading.
        """
        try:
            el_handle = await self.page.evaluate_handle(
                """
                (text) => {
                    const sections = document.querySelectorAll('section.artdeco-card');
                    for (const sec of sections) {
                        const h2 = sec.querySelector('h2');
                        if (h2 && h2.innerText.trim().toLowerCase().includes(text.toLowerCase())) {
                            return sec;
                        }
                    }
                    return null;
                }
                """,
                heading_text
            )
            # el_handle is a JSHandle, we need to get the element
            el = el_handle.as_element()
            if el:
                logger.debug(f"DOMHelper: heading-based match for '{heading_text}'")
                return self.page.locator("section.artdeco-card").filter(has=self.page.locator(f"h2:has-text('{heading_text}')")).first
        except Exception as e:
            logger.debug(f"DOMHelper._find_section_by_heading('{heading_text}') failed: {e}")
        return None

    async def find_section(
        self,
        selectors: List[str],
        timeout: Optional[int] = None,
    ) -> Optional[Locator]:
        """Return the first Locator that resolves to ≥1 visible element.

        Supports a special 'heading:<text>' pseudo-selector that finds an
        artdeco-card section by its h2 heading text — robust against LinkedIn
        DOM structure changes.

        Args:
            selectors: Ordered list of CSS/XPath or 'heading:<text>' selectors.
            timeout:   Per-selector wait timeout in ms (default: self.default_timeout).

        Returns:
            A Locator for the first matching selector, or None if all fail.
        """
        t = timeout or self.default_timeout
        for sel in selectors:
            # Special heading-based search
            if sel.startswith("heading:"):
                heading_text = sel[len("heading:"):].strip()
                loc = await self._find_section_by_heading(heading_text)
                if loc:
                    return loc
                continue

            try:
                loc = self.page.locator(sel)
                await loc.first.wait_for(state="attached", timeout=t)
                count = await loc.count()
                if count > 0:
                    logger.debug(f"DOMHelper: selector matched — '{sel}' ({count} elements)")
                    return loc
            except Exception:
                logger.debug(f"DOMHelper: selector not found — '{sel}'")
        logger.debug(f"DOMHelper: no selectors matched from {selectors}")
        return None

    # ── Text extraction ───────────────────────────────────────────────────────

    async def extract_text(
        self,
        selectors: List[str],
        timeout: Optional[int] = None,
    ) -> str:
        """Extract trimmed inner text from the first matching element.

        Returns:
            Text content, or empty string if nothing matched.
        """
        loc = await self.find_section(selectors, timeout)
        if loc is None:
            return ""
        try:
            text = await loc.first.inner_text()
            return text.strip()
        except Exception as e:
            logger.debug(f"DOMHelper.extract_text failed: {e}")
            return ""

    async def extract_all_text(
        self,
        selectors: List[str],
        timeout: Optional[int] = None,
    ) -> List[str]:
        """Extract trimmed inner text from ALL matching elements.

        Returns:
            List of non-empty text strings, or [] if nothing matched.
        """
        loc = await self.find_section(selectors, timeout)
        if loc is None:
            return []
        try:
            count = await loc.count()
            texts = []
            for i in range(count):
                text = await loc.nth(i).inner_text()
                stripped = text.strip()
                if stripped:
                    texts.append(stripped)
            return texts
        except Exception as e:
            logger.debug(f"DOMHelper.extract_all_text failed: {e}")
            return []

    async def extract_attribute(
        self,
        selectors: List[str],
        attribute: str,
        timeout: Optional[int] = None,
    ) -> str:
        """Extract an HTML attribute value from the first matching element.

        Returns:
            Attribute value string, or empty string if not found.
        """
        loc = await self.find_section(selectors, timeout)
        if loc is None:
            return ""
        try:
            value = await loc.first.get_attribute(attribute)
            return (value or "").strip()
        except Exception as e:
            logger.debug(f"DOMHelper.extract_attribute('{attribute}') failed: {e}")
            return ""

    # ── Interaction helpers ───────────────────────────────────────────────────

    async def safe_click(
        self,
        selectors: List[str],
        timeout: Optional[int] = None,
    ) -> bool:
        """Click the first matching element.

        Returns:
            True if click succeeded, False otherwise.
        """
        loc = await self.find_section(selectors, timeout)
        if loc is None:
            return False
        try:
            await loc.first.click(timeout=timeout or self.default_timeout)
            logger.debug(f"DOMHelper.safe_click: clicked element matching {selectors}")
            return True
        except Exception as e:
            logger.debug(f"DOMHelper.safe_click failed: {e}")
            return False

    async def expand_section(
        self,
        selectors: List[str],
        timeout: Optional[int] = None,
    ) -> bool:
        """Click a 'Show more' / expand button and wait briefly for content to load.

        Returns:
            True if the button was found and clicked, False if not found.
        """
        clicked = await self.safe_click(selectors, timeout)
        if clicked:
            # Brief settle time for animated expansions
            await asyncio.sleep(0.4)
            logger.debug(f"DOMHelper.expand_section: expanded via {selectors}")
        return clicked

    async def wait_for_any(
        self,
        selectors: List[str],
        timeout: int = 5000,
    ) -> Optional[str]:
        """Wait until ANY of the given selectors appears on the page.

        Returns:
            The selector string that matched first, or None if all timed out.
        """
        async def _try(sel: str) -> Optional[str]:
            try:
                await self.page.wait_for_selector(sel, timeout=timeout)
                return sel
            except Exception:
                return None

        tasks = [asyncio.create_task(_try(sel)) for sel in selectors]
        for coro in asyncio.as_completed(tasks):
            result = await coro
            if result:
                # Cancel remaining
                for t in tasks:
                    t.cancel()
                logger.debug(f"DOMHelper.wait_for_any: first match — '{result}'")
                return result
        return None

    # ── Convenience: structured block extraction ──────────────────────────────

    async def extract_blocks(
        self,
        container_selectors: List[str],
        item_selector: str,
        fields: dict[str, List[str]],
        timeout: Optional[int] = None,
    ) -> List[dict]:
        """Extract a repeated list of structured items within a container.

        Args:
            container_selectors: Selectors for the section container element.
            item_selector:       CSS selector for each repeated item inside container.
            fields:              Mapping of field_name → list of relative child selectors.
            timeout:             Timeout in ms.

        Returns:
            List of dicts, one per item, with keys matching `fields`.

        Example:
            await dom.extract_blocks(
                container_selectors=["#experience-section", ".experience"],
                item_selector=".pvs-list__item",
                fields={
                    "title":   [".t-bold span", ".mr1 span"],
                    "company": [".t-normal span", ".pv-entity__secondary-title"],
                },
            )
        """
        container = await self.find_section(container_selectors, timeout)
        if container is None:
            return []

        try:
            items = container.locator(item_selector)
            count = await items.count()
            results = []
            for i in range(count):
                item = items.nth(i)
                record = {}
                for field_name, child_selectors in fields.items():
                    for child_sel in child_selectors:
                        try:
                            # Support attribute extraction using @ syntax (e.g., 'a@href' or '@href')
                            if "@" in child_sel:
                                base_sel, attr_name = child_sel.split("@", 1)
                                actual_child = item.locator(base_sel) if base_sel.strip() else item
                                if base_sel.strip() and await actual_child.count() == 0:
                                    continue
                                val = await actual_child.first.get_attribute(attr_name)
                            else:
                                child = item.locator(child_sel)
                                if await child.count() > 0:
                                    val = await child.first.inner_text()
                                else:
                                    continue
                            record[field_name] = (val or "").strip()
                            break
                        except Exception:
                            continue
                    if field_name not in record:
                        record[field_name] = ""
                if any(record.values()):
                    results.append(record)
            return results
        except Exception as e:
            logger.debug(f"DOMHelper.extract_blocks failed: {e}")
            return []
