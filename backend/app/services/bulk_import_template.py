# app/services/bulk_import_template.py
"""Build the downloadable .xlsx import template (N5c), in memory.

Sheet 1 holds only the header row (the importer reads the first sheet only).
Sheet 2 explains the rules; its numbers come from Settings at call time.
Pure and fast (no I/O beyond an in-memory buffer), so it needs no thread hop.
"""
import io

from openpyxl import Workbook

from app.core.config import settings
from app.services.bulk_import_logic import HEADER_DE, HEADER_EN

SHEET_DATA = "Sentences"
SHEET_INSTRUCTIONS = "Instructions"


def _instruction_lines() -> list[str]:
    max_mb = settings.bulk_import_max_upload_bytes / 1_000_000
    return [
        "How to import sentences",
        f'1. Fill the "{SHEET_DATA}" sheet: one sentence pair per row, German in column "{HEADER_DE}", English in column "{HEADER_EN}".',
        "2. Keep the header row (row 1) as it is. Only the first sheet is read.",
        f"3. At most {settings.bulk_import_max_rows} sentences per file and {max_mb:g} MB per upload.",
        "4. Empty rows are skipped.",
        "5. Duplicates are flagged as warnings, not blocked. You decide what to keep.",
        "6. You can review and edit every row (including topics) before saving.",
    ]


def build_template_bytes() -> bytes:
    wb = Workbook()
    data = wb.active
    data.title = SHEET_DATA
    data.append([HEADER_DE, HEADER_EN])
    data.column_dimensions["A"].width = 50
    data.column_dimensions["B"].width = 50

    info = wb.create_sheet(SHEET_INSTRUCTIONS)
    for line in _instruction_lines():
        info.append([line])
    info.column_dimensions["A"].width = 110

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()
