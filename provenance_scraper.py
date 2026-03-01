"""
Provenance Blockchain Metrics Scraper
Scrapes https://provenance.io/pulse daily at 11:55 PM ET.
Writes to both data.json (for GitHub Pages website) and provenance_metrics.xlsx.

Fields captured:
  24h: loan_amount_funded, loans_funded, loan_amount_paid, loans_paid
  1W:  loan_amount_funded, loans_funded
  All: total_participants
"""

import asyncio
import json
import os
from datetime import datetime
import pytz
from playwright.async_api import async_playwright
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

EXCEL_FILE = "provenance_metrics.xlsx"
JSON_FILE  = "data.json"
URL        = "https://provenance.io/pulse"

HEADERS = [
    "Date",
    "Loan Amt Funded (24h)", "Loans Funded (24h)",
    "Loan Amt Funded (1W)",  "Loans Funded (1W)",
    "Loan Amt Paid (24h)",   "Loans Paid (24h)",
    "Total Participants",
]


def extract_from_text(text: str, label: str) -> str:
    """
    Page text format per card:
        Label
        i          ← tooltip icon line
        $value     ← the value we want
        delta
        (pct%)
        Week/Today
    """
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    for i, line in enumerate(lines):
        if line == label and i + 2 < len(lines):
            return lines[i + 2]
    return "N/A"


async def scrape_metrics():
    metrics = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print(f"Loading {URL}...")
        await page.goto(URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(4000)

        # ── Scrape 1W (default view) ──────────────────────────────────────
        print("Scraping 1W metrics...")
        text_1w = await page.inner_text("body")

        metrics["loan_amount_funded_1w"] = extract_from_text(text_1w, "Week's Loan Amount Funded")
        metrics["loans_funded_1w"]        = extract_from_text(text_1w, "Week's Loans Funded")
        metrics["total_participants"]     = extract_from_text(text_1w, "Total Participants")

        print(f"  1W Loan Amount Funded : {metrics['loan_amount_funded_1w']}")
        print(f"  1W Loans Funded       : {metrics['loans_funded_1w']}")
        print(f"  Total Participants    : {metrics['total_participants']}")

        # ── Click SECOND section's 24h tab ───────────────────────────────
        print("Clicking 24h tab (second tab group)...")
        try:
            tab_buttons = page.locator("button.pulse-pill:has-text('24h')")
            count = await tab_buttons.count()
            print(f"  Found {count} '24h' tab button(s)")
            await tab_buttons.nth(1 if count >= 2 else 0).click()
            await page.wait_for_timeout(3000)
            print("  Clicked successfully")
        except Exception as e:
            print(f"  Click failed: {e}")

        # ── Scrape 24h ────────────────────────────────────────────────────
        print("Scraping 24h metrics...")
        text_24h = await page.inner_text("body")

        metrics["loan_amount_funded_24h"] = extract_from_text(text_24h, "Today's Loan Amount Funded")
        metrics["loans_funded_24h"]        = extract_from_text(text_24h, "Today's Loans Funded")
        metrics["loan_amount_paid_24h"]    = extract_from_text(text_24h, "Today's Loan Amount Paid")
        metrics["loans_paid_24h"]          = extract_from_text(text_24h, "Today's Loans Paid")

        print(f"  24h Loan Amount Funded : {metrics['loan_amount_funded_24h']}")
        print(f"  24h Loans Funded       : {metrics['loans_funded_24h']}")
        print(f"  24h Loan Amount Paid   : {metrics['loan_amount_paid_24h']}")
        print(f"  24h Loans Paid         : {metrics['loans_paid_24h']}")

        await browser.close()

    return metrics


# ── JSON ──────────────────────────────────────────────────────────────────────

def update_json(date_str: str, metrics: dict):
    data = []
    if os.path.exists(JSON_FILE):
        with open(JSON_FILE, "r") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                data = []

    entry = {"date": date_str, **metrics}
    data.append(entry)

    with open(JSON_FILE, "w") as f:
        json.dump(data, f, indent=2)
    print(f"data.json updated ({len(data)} total records)")


# ── Excel ─────────────────────────────────────────────────────────────────────

def setup_workbook():
    wb = Workbook()
    ws = wb.active
    ws.title = "Provenance Metrics"

    header_font  = Font(name="Arial", bold=True, color="FFFFFF")
    header_fill  = PatternFill("solid", start_color="1F4E79")
    center_align = Alignment(horizontal="center", vertical="center")
    thin_border  = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"),  bottom=Side(style="thin")
    )

    ws.append(HEADERS)
    for col_idx in range(1, len(HEADERS) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font      = header_font
        cell.fill      = header_fill
        cell.alignment = center_align
        cell.border    = thin_border

    col_widths = [24, 24, 20, 24, 20, 22, 18, 22]
    for i, w in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.row_dimensions[1].height = 30
    ws.freeze_panes = "A2"
    wb.save(EXCEL_FILE)
    print(f"Created new workbook: {EXCEL_FILE}")


def append_excel_row(date_str: str, metrics: dict):
    if not os.path.exists(EXCEL_FILE):
        setup_workbook()

    wb = load_workbook(EXCEL_FILE)
    ws = wb.active

    row_data = [
        date_str,
        metrics.get("loan_amount_funded_24h", "N/A"),
        metrics.get("loans_funded_24h",        "N/A"),
        metrics.get("loan_amount_funded_1w",  "N/A"),
        metrics.get("loans_funded_1w",         "N/A"),
        metrics.get("loan_amount_paid_24h",    "N/A"),
        metrics.get("loans_paid_24h",          "N/A"),
        metrics.get("total_participants",      "N/A"),
    ]

    next_row     = ws.max_row + 1
    fill_color   = "D6E4F0" if next_row % 2 == 0 else "FFFFFF"
    fill         = PatternFill("solid", start_color=fill_color)
    thin_border  = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"),  bottom=Side(style="thin")
    )
    center_align = Alignment(horizontal="center", vertical="center")

    ws.append(row_data)
    for col_idx in range(1, len(row_data) + 1):
        cell           = ws.cell(row=next_row, column=col_idx)
        cell.font      = Font(name="Arial")
        cell.fill      = fill
        cell.border    = thin_border
        cell.alignment = center_align

    wb.save(EXCEL_FILE)
    print(f"Excel row {next_row} saved: {row_data}")


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    et      = pytz.timezone("America/New_York")
    now_et  = datetime.now(et)
    date_str = now_et.strftime("%Y-%m-%d %I:%M %p ET")

    print(f"Starting scrape at {date_str}")
    metrics = await scrape_metrics()
    update_json(date_str, metrics)
    append_excel_row(date_str, metrics)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
