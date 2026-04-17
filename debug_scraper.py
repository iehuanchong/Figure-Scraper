"""
Debug v4: clicks every tab (24h, 1m, 3m), writes separate files per tab.
Output files: tab_24h.txt, tab_1m.txt, tab_3m.txt
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
        print("Loading page (default = 1W)...")
        await page.goto(URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(5000)

        for tab in ["24h", "1m", "3m"]:
            print(f"\n--- Clicking '{tab}' tab ---")

            # Try several selector strategies
            clicked = False
            strategies = [
                f"button.pulse-pill:has-text('{tab}')",
                f"button:has-text('{tab}')",
                f"[class*='pill']:has-text('{tab}')",
                f"text={tab}",
            ]
            for sel in strategies:
                try:
                    buttons = page.locator(sel)
                    count = await buttons.count()
                    print(f"  Selector '{sel}' found {count} match(es)")
                    if count >= 2:
                        await buttons.nth(1).click(timeout=3000)
                        clicked = True
                        print(f"  Clicked nth(1)")
                        break
                    elif count == 1:
                        await buttons.first.click(timeout=3000)
                        clicked = True
                        print(f"  Clicked first")
                        break
                except Exception as e:
                    print(f"  '{sel}' failed: {e}")

            if not clicked:
                print(f"  WARNING: Could not click '{tab}' tab with any strategy")

            await page.wait_for_timeout(3000)

            # Write full text to named file
            text = await page.inner_text("body")
            fname = f"tab_{tab.replace('h','h')}.txt"
            with open(fname, "w") as f:
                f.write(text)
            print(f"  Written to {fname} ({len(text)} chars)")

            # Print loan lines with context
            lines = [l.strip() for l in text.split("\n") if l.strip()]
            print(f"  Loan/funded/paid lines:")
            for i, line in enumerate(lines):
                if any(k in line.lower() for k in ["loan", "funded", "paid"]):
                    start, end = max(0, i-1), min(len(lines), i+4)
                    print(f"\n    >> [{i}] '{line}'")
                    for j in range(start, end):
                        print(f"       {'>>>' if j==i else '   '} {repr(lines[j])}")

        await browser.close()
        print("\n\nDone.")

asyncio.run(debug())
