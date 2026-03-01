"""
Debug v2 - prints FULL page text with no truncation, loan lines highlighted.
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

        # Print ALL lines - no truncation
        text = await page.inner_text("body")
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        
        print(f"\nTotal non-empty lines: {len(lines)}")
        print("\n--- ALL PAGE LINES ---")
        for i, line in enumerate(lines):
            print(f"{i:03d}: {line}")
        print("--- END ALL LINES ---\n")

        # Specifically highlight loan lines with context
        print("--- LOAN LINES WITH CONTEXT (±2 lines) ---")
        for i, line in enumerate(lines):
            if any(k in line.lower() for k in ["loan", "funded", "paid"]):
                start = max(0, i-2)
                end = min(len(lines), i+3)
                print(f"\n  >> Match at line {i}: '{line}'")
                for j in range(start, end):
                    marker = ">>>" if j == i else "   "
                    print(f"  {marker} [{j}] {lines[j]}")
        print("--- END ---")

        # Now click 24h and repeat
        print("\n\nClicking 24h tab...")
        try:
            await page.locator("button.pulse-pill:has-text('24h')").first.click()
            await page.wait_for_timeout(3000)
            print("Clicked 24h tab successfully")
            
            text2 = await page.inner_text("body")
            lines2 = [l.strip() for l in text2.split("\n") if l.strip()]
            print("\n--- 24H LOAN LINES WITH CONTEXT ---")
            for i, line in enumerate(lines2):
                if any(k in line.lower() for k in ["loan", "funded", "paid"]):
                    start = max(0, i-2)
                    end = min(len(lines2), i+3)
                    print(f"\n  >> Match at line {i}: '{line}'")
                    for j in range(start, end):
                        marker = ">>>" if j == i else "   "
                        print(f"  {marker} [{j}] {lines2[j]}")
            print("--- END ---")
        except Exception as e:
            print(f"Could not click 24h: {e}")

        await page.screenshot(path="debug_screenshot.png", full_page=True)
        print("\nScreenshot saved.")
        await browser.close()

asyncio.run(debug())
