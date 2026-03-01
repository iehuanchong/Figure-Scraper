"""
Debug script - dumps page HTML and attempts to find metric cards.
Run this to diagnose why values are returning N/A.
"""

import asyncio
import re
from playwright.async_api import async_playwright

URL = "https://provenance.io/pulse"

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("Loading page...")
        await page.goto(URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000)

        # 1. Print page title to confirm it loaded
        title = await page.title()
        print(f"Page title: {title}")

        # 2. Print full page text content (condensed)
        text = await page.inner_text("body")
        print("\n--- FULL PAGE TEXT (first 3000 chars) ---")
        print(text[:3000])
        print("--- END ---\n")

        # 3. Look specifically for loan-related text
        print("--- LOAN-RELATED LINES ---")
        for line in text.split("\n"):
            line = line.strip()
            if line and any(k in line.lower() for k in ["loan", "funded", "paid", "amount"]):
                print(repr(line))
        print("--- END ---\n")

        # 4. Dump all elements with dollar amounts or large numbers
        print("--- ELEMENTS WITH $ OR NUMBERS ---")
        elements = await page.locator("*").all()
        seen = set()
        for el in elements[:500]:  # limit to avoid timeout
            try:
                tag = await el.evaluate("e => e.tagName")
                txt = (await el.inner_text(timeout=500)).strip()
                if txt and txt not in seen and len(txt) < 100:
                    if re.search(r'\$[\d,]+|^\d{1,3}(,\d{3})*$', txt):
                        class_name = await el.get_attribute("class") or ""
                        seen.add(txt)
                        print(f"  <{tag} class='{class_name}'> {txt}")
            except Exception:
                continue
        print("--- END ---\n")

        # 5. Save screenshot for visual confirmation
        await page.screenshot(path="debug_screenshot.png", full_page=True)
        print("Screenshot saved: debug_screenshot.png")

        # 6. Try clicking 1W tab
        print("\nAttempting to click 1W tab...")
        try:
            # Try various selectors for the tab
            for selector in ["text=1w", "text=1W", "[data-period='1w']", "button:has-text('1w')", "span:has-text('1w')"]:
                try:
                    await page.locator(selector).first.click(timeout=3000)
                    print(f"  Clicked with selector: {selector}")
                    await page.wait_for_timeout(2000)
                    break
                except Exception:
                    print(f"  Selector failed: {selector}")
        except Exception as e:
            print(f"  Could not click 1W tab: {e}")

        # 7. Print text after tab click
        text_after = await page.inner_text("body")
        print("\n--- PAGE TEXT AFTER 1W CLICK (first 1000 chars) ---")
        print(text_after[:1000])

        await browser.close()

asyncio.run(debug())
