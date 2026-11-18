# tests/services/test_bulk_import_template.py
import io

from openpyxl import load_workbook

from app.core.config import settings
from app.services import bulk_import_template as tpl
from app.services.bulk_import_logic import HEADER_DE, HEADER_EN, parse_rows
from app.services.bulk_import_reader import read_xlsx_rows


def _workbook():
    return load_workbook(io.BytesIO(tpl.build_template_bytes()))


def test_sheet_order_data_first_instructions_second():
    assert _workbook().sheetnames == [tpl.SHEET_DATA, tpl.SHEET_INSTRUCTIONS]


def test_data_sheet_has_only_the_header_row():
    rows = list(_workbook()[tpl.SHEET_DATA].iter_rows(values_only=True))
    assert rows == [(HEADER_DE, HEADER_EN)]


def test_our_own_reader_and_parser_accept_the_template():
    raw = read_xlsx_rows(
        tpl.build_template_bytes(), max_upload_bytes=settings.bulk_import_max_upload_bytes
    )
    parsed = parse_rows(
        raw, max_rows=settings.bulk_import_max_rows, max_len=2000, existing_keys=set()
    )
    assert list(parsed) == []


def test_instruction_numbers_follow_settings(monkeypatch):
    monkeypatch.setattr(settings, "bulk_import_max_rows", 37)
    monkeypatch.setattr(settings, "bulk_import_max_upload_bytes", 2_500_000)
    text = "\n".join(tpl._instruction_lines())
    assert "37 sentences" in text
    assert "2.5 MB" in text
