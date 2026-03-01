"""
Provenance Blockchain Metrics Scraper
Scrapes https://provenance.io/pulse for loan metrics and appends to Excel.
Run daily at 11:55 PM ET via cron or GitHub Actions.

Page defaults to 1W view. Script scrapes 1W first, then clicks 24h tab.
"""

import asyncio
import os
from datetime import datetime
import pytz
from playwright.async_api import async_playwright
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

EXCEL_FILE = "provenance_metrics.xlsx"
URL = "https://provenance.io/pulse"

HEADERS = [
    "Date",
    "24h Today's Loan Amount Funded",
    "24h Today's Loans Paid",
    "1W Loan Amount Funded",
    "1W Loans Paid"
]


async def get_metric_by_label(page, label: str) -> str:
    """Find a pulse-card-value span by its adjacent label span."""
    try:
        # Locate the label span, go up to parent card, then find the value span
        card = page.locator(f"span:has-text('{label}')").locator("xpath=..").first
        value = await card.locator("span.pulse-card-value").first.get_attribute("title", timeout=5000)
        if value:
            return value.strip()
        # Fallback: inner text
        value = await card.locator("span.pulse-card-value").first.inner_text(timeout=5000)
        return value.strip()
    except Exception as e:
        print(f"  WARNING: Could not find '{label}': {e}")
        return "N/A"


async def scrape_metrics():
    metrics = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print(f"Loading {URL}...")
        await page.goto(URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(4000)

        # --- Page defaults to 1W — scrape 1W first ---
        print("Scraping 1W metrics...")
        metrics["1w_loan_amount_funded"] = await get_metric_by_label(page, "Week's Loan Amount Funded")
        metrics["1w_loans_paid"] = await get_metric_by_label(page, "Week's Loans Paid")
        print(f"  1W Loan Amount Funded: {metrics['1w_loan_amount_funded']}")
        print(f"  1W Loans Paid: {metrics['1w_loans_paid']}")

        # --- Click the 24h tab ---
        print("Clicking 24h tab...")
        await page.locator("button.pulse-pill:has-text('24h')").first.click()
        await page.wait_for_timeout(3000)

        # --- Scrape 24h ---
        print("Scraping 24h metrics...")
        metrics["24h_loan_amount_funded"] = await get_metric_by_label(page, "Today's Loan Amount Funded")
        metrics["24h_loans_paid"] = await get_metric_by_label(page, "Today's Loans Paid")
        print(f"  24h Loan Amount Funded: {metrics['24h_loan_amount_funded']}")
        print(f"  24h Loans Paid: {metrics['24h_loans_paid']}")

        await browser.close()

    return metrics


def setup_workbook():
    wb = Workbook()
    ws = wb.active
    ws.title = "Provenance Metrics"

    header_font = Font(name="Arial", bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", start_color="1F4E79")
    center_align = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin")
    )

    ws.append(HEADERS)
    for col_idx in range(1, len(HEADERS) + 1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = thin_border

    col_widths = [24, 36, 26, 30, 20]
    for i, w in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.row_dimensions[1].height = 30
    ws.freeze_panes = "A2"

    wb.save(EXCEL_FILE)
    print(f"Created new workbook: {EXCEL_FILE}")


def append_row(date_str: str, metrics: dict):
    if not os.path.exists(EXCEL_FILE):
        setup_workbook()

    wb = load_workbook(EXCEL_FILE)
    ws = wb.active

    row_data = [
        date_str,
        metrics.get("24h_loan_amount_funded", "N/A"),
        metrics.get("24h_loans_paid", "N/A"),
        metrics.get("1w_loan_amount_funded", "N/A"),
        metrics.get("1w_loans_paid", "N/A"),
    ]

    next_row = ws.max_row + 1
    fill_color = "D6E4F0" if next_row % 2 == 0 else "FFFFFF"
    fill = PatternFill("solid", start_color=fill_color)
    thin_border = Border(
        left=Side(style="thin"), right=Side(style="thin"),
        top=Side(style="thin"), bottom=Side(style="thin")
    )
    center_align = Alignment(horizontal="center", vertical="center")

    ws.append(row_data)
    for col_idx in range(1, len(row_data) + 1):
        cell = ws.cell(row=next_row, column=col_idx)
        cell.font = Font(name="Arial")
        cell.fill = fill
        cell.border = thin_border
        cell.alignment = center_align

    wb.save(EXCEL_FILE)
    print(f"Row {next_row} saved: {row_data}")


async def main():
    et = pytz.timezone("America/New_York")
    now_et = datetime.now(et)
    date_str = now_et.strftime("%Y-%m-%d %I:%M %p ET")

    print(f"Starting scrape at {date_str}")
    metrics = await scrape_metrics()
    append_row(date_str, metrics)
    print("Done.")


if __name__ == "__main__":
    asyncio.run(main())
