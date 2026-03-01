"""
Debug v3 - writes full page text to files instead of printing (bypasses log truncation).
"""
import asyncio
from playwright.async_api import async_playwright

URL = "https://provenance.io/pulse"

async def debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("Loading page (1W default)...")
        await page.goto(URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000)
        print(f"Title: {await page.title()}")

        # Write 1W full text to file
        text_1w = await page.inner_text("body")
        with open("page_text_1w.txt", "w") as f:
            f.write(text_1w)
        print(f"1W page text written ({len(text_1w)} chars)")

        # Highlight loan lines to stdout (short enough to not truncate)
        lines = [l.strip() for l in text_1w.split("\n") if l.strip()]
        print(f"Total lines: {len(lines)}")
        print("\n--- 1W LOAN LINES WITH CONTEXT ---")
        for i, line in enumerate(lines):
            if any(k in line.lower() for k in ["loan", "funded", "paid"]):
                start, end = max(0, i-2), min(len(lines), i+3)
                print(f"\n>> Line {i}: '{line}'")
                for j in range(start, end):
                    print(f"  {'>>>' if j==i else '   '} [{j}] {repr(lines[j])}")
        print("--- END 1W ---\n")

        # Click 24h
        print("Clicking 24h tab...")
        try:
            await page.locator("button.pulse-pill:has-text('24h')").first.click()
            await page.wait_for_timeout(3000)
            print("Clicked successfully")
        except Exception as e:
            print(f"Click failed: {e}")
            # Try alternate selectors
            for sel in ["text=24h", "button:has-text('24h')", "[class*='pill']:has-text('24h')"]:
                try:
                    await page.locator(sel).first.click(timeout=2000)
                    print(f"Clicked with fallback: {sel}")
                    await page.wait_for_timeout(3000)
                    break
                except:
                    print(f"Fallback failed: {sel}")

        # Write 24h full text to file
        text_24h = await page.inner_text("body")
        with open("page_text_24h.txt", "w") as f:
            f.write(text_24h)
        print(f"24h page text written ({len(text_24h)} chars)")

        print("\n--- 24H LOAN LINES WITH CONTEXT ---")
        lines2 = [l.strip() for l in text_24h.split("\n") if l.strip()]
        for i, line in enumerate(lines2):
            if any(k in line.lower() for k in ["loan", "funded", "paid"]):
                start, end = max(0, i-2), min(len(lines2), i+3)
                print(f"\n>> Line {i}: '{line}'")
                for j in range(start, end):
                    print(f"  {'>>>' if j==i else '   '} [{j}] {repr(lines2[j])}")
        print("--- END 24H ---")

        await page.screenshot(path="debug_screenshot.png", full_page=True)
        print("\nDone. Check artifacts for page_text_1w.txt and page_text_24h.txt")
        await browser.close()

asyncio.run(debug())
