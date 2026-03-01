"""
Provenance Blockchain Metrics Scraper
Scrapes https://provenance.io/pulse for loan metrics and appends to Excel.
Run daily at 11:55 PM ET via cron or GitHub Actions.
"""

import asyncio
import re
import os
from datetime import datetime
import pytz
from playwright.async_api import async_playwright
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

EXCEL_FILE = "provenance_metrics.xlsx"
URL = "https://provenance.io/pulse"

# Columns: A=Date, B=24h Loan Amount Funded, C=24h Loans Paid, D=1W Loan Amount Funded, E=1W Loans Paid
HEADERS = [
    "Date",
    "24h Today's Loan Amount Funded",
    "24h Today's Loans Paid",
    "1W Loan Amount Funded",
    "1W Loans Paid"
]


async def scrape_metrics():
    """Scrape 24h and 1W loan metrics from Provenance Pulse."""
    metrics = {}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        print(f"Loading {URL}...")
        await page.goto(URL, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)  # Extra wait for dynamic content

        # --- Scrape 24h (default active tab) ---
        print("Scraping 24h metrics...")
        metrics["24h_loan_amount_funded"] = await extract_metric(
            page, "Today's Loan Amount Funded"
        )
        metrics["24h_loans_paid"] = await extract_metric(
            page, "Today's Loans Paid"
        )

        # --- Click 1W tab ---
        print("Switching to 1W tab...")
        week_tab = page.locator("text=1w").first
        await week_tab.click()
        await page.wait_for_timeout(3000)

        # --- Scrape 1W ---
        print("Scraping 1W metrics...")
        metrics["1w_loan_amount_funded"] = await extract_metric(
            page, "Today's Loan Amount Funded"
        )
        metrics["1w_loans_paid"] = await extract_metric(
            page, "Today's Loans Paid"
        )

        await browser.close()

    return metrics


async def extract_metric(page, label: str) -> str:
    """Find a metric card by label and return its primary value."""
    try:
        # Find the card containing the label text
        card = page.locator(f"text={label}").locator("..").locator("..")
        value = await card.locator("h2, h3, [class*='value'], [class*='amount'], [class*='metric']").first.inner_text(timeout=5000)
        return value.strip()
    except Exception:
        # Fallback: search all text nodes near the label
        try:
            elements = await page.locator(f"*:has-text('{label}')").all()
            for el in elements:
                parent = el.locator("..")
                text = await parent.inner_text(timeout=3000)
                lines = [l.strip() for l in text.split("\n") if l.strip()]
                # The value is typically the largest number/dollar amount in the card
                for line in lines:
                    if re.match(r'^[\$\d,\.KMB]+$', line) and len(line) > 0:
                        return line
        except Exception:
            pass
    return "N/A"


def parse_value(raw: str) -> str:
    """Clean up the raw scraped value."""
    if not raw or raw == "N/A":
        return "N/A"
    return raw.strip()


def setup_workbook():
    """Create a new workbook with headers and formatting."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Provenance Metrics"

    # Header styling
    header_font = Font(name="Arial", bold=True, color="FFFFFF")
    header_fill = PatternFill("solid", start_color="1F4E79")
    center_align = Alignment(horizontal="center", vertical="center")
    thin_border = Border(
        left=Side(style="thin"),
        right=Side(style="thin"),
        top=Side(style="thin"),
        bottom=Side(style="thin")
    )

    ws.append(HEADERS)
    for col_idx, _ in enumerate(HEADERS, start=1):
        cell = ws.cell(row=1, column=col_idx)
        cell.font = header_font
        cell.fill = header_fill
        cell.alignment = center_align
        cell.border = thin_border

    # Column widths
    col_widths = [18, 36, 26, 30, 20]
    for i, w in enumerate(col_widths, start=1):
        ws.column_dimensions[get_column_letter(i)].width = w

    ws.row_dimensions[1].height = 30
    ws.freeze_panes = "A2"

    wb.save(EXCEL_FILE)
    print(f"Created new workbook: {EXCEL_FILE}")
    return wb


def append_row(date_str: str, metrics: dict):
    """Append a new data row to the Excel file."""
    if not os.path.exists(EXCEL_FILE):
        setup_workbook()

    wb = load_workbook(EXCEL_FILE)
    ws = wb.active

    row_data = [
        date_str,
        parse_value(metrics.get("24h_loan_amount_funded", "N/A")),
        parse_value(metrics.get("24h_loans_paid", "N/A")),
        parse_value(metrics.get("1w_loan_amount_funded", "N/A")),
        parse_value(metrics.get("1w_loans_paid", "N/A")),
    ]

    # Alternating row colors
    next_row = ws.max_row + 1
    row_fill_color = "D6E4F0" if next_row % 2 == 0 else "FFFFFF"
    fill = PatternFill("solid", start_color=row_fill_color)
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
    print(f"Appended row {next_row}: {row_data}")


async def main():
    et = pytz.timezone("America/New_York")
    now_et = datetime.now(et)
    date_str = now_et.strftime("%Y-%m-%d %I:%M %p ET")

    print(f"Starting scrape at {date_str}")

    try:
        metrics = await scrape_metrics()
        print(f"Scraped metrics: {metrics}")
        append_row(date_str, metrics)
        print("Done. Data saved to Excel.")
    except Exception as e:
        print(f"ERROR: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
