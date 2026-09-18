"""Tests de ingestion/load_raw.py : validation des feuilles avant toute écriture."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

duckdb = pytest.importorskip("duckdb")

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ingestion" / "load_raw.py"
FILE_NAME = "awale_boissons_starter_dataset.xlsx"

COLUMNS = {
    "campaign_spend_export": [
        "platform", "campaign_name", "date_start", "date_end",
        "spend", "impressions", "clicks", "objective",
    ],
    "media_plan": [
        "plan_id", "month", "channel", "planned_budget_fcfa",
        "invoiced_fcfa", "objective", "owner", "notes",
    ],
    "pos_sales_daily": [
        "sale_date", "pos_id", "pos_name", "commune", "channel",
        "product_sku", "units_sold", "revenue_fcfa",
    ],
    "whatsapp_orders": [
        "order_ref", "received_at", "customer_phone", "items_text",
        "amount_fcfa", "delivery_zone", "status",
    ],
    "social_comments": [
        "comment_id", "platform", "post_id", "published_at",
        "author_handle", "comment_text", "like_count", "reply_to_id",
    ],
}


def workbook(folder: Path, mutate=None) -> None:
    sheets = {
        name: pd.DataFrame([{c: "x" for c in cols}], columns=cols)
        for name, cols in COLUMNS.items()
    }
    if mutate:
        mutate(sheets)

    folder.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(folder / FILE_NAME) as writer:
        for name, frame in sheets.items():
            frame.to_excel(writer, sheet_name=name, index=False)


def run_load(folder: Path):
    db = folder / "test.duckdb"
    # PYTHONUTF8 : sur Windows, la sortie d'erreur du script serait sinon en cp1252.
    env = {
        "AWALE_RAW_DIR": str(folder),
        "AWALE_DUCKDB_PATH": str(db),
        "PYTHONUTF8": "1",
    }
    import os

    result = subprocess.run(
        [sys.executable, str(SCRIPT)],
        env={**os.environ, **env},
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result, db


def raw_tables(db: Path) -> list[str]:
    if not db.exists():
        return []
    con = duckdb.connect(str(db), read_only=True)
    try:
        return sorted(
            r[0]
            for r in con.execute(
                "SELECT table_name FROM information_schema.tables WHERE table_name LIKE 'raw_%'"
            ).fetchall()
        )
    finally:
        con.close()


def test_valid_workbook_loads_the_five_raw_tables(tmp_path):
    workbook(tmp_path)
    result, db = run_load(tmp_path)

    assert result.returncode == 0, result.stderr
    assert len(raw_tables(db)) == 5


def test_missing_column_stops_the_run_and_writes_nothing(tmp_path):
    workbook(tmp_path, lambda s: s.__setitem__("pos_sales_daily", s["pos_sales_daily"].drop(columns=["revenue_fcfa"])))
    result, db = run_load(tmp_path)

    assert result.returncode != 0
    assert "revenue_fcfa" in result.stderr
    assert raw_tables(db) == []  # aucune table du nouveau mois n'a été écrite


def test_empty_sheet_stops_the_run_instead_of_keeping_old_data(tmp_path):
    workbook(tmp_path, lambda s: s.__setitem__("media_plan", s["media_plan"].iloc[0:0]))
    result, db = run_load(tmp_path)

    assert result.returncode != 0
    assert "media_plan" in result.stderr and "vide" in result.stderr
    assert raw_tables(db) == []


def test_missing_sheet_gives_a_clear_message(tmp_path):
    workbook(tmp_path, lambda s: s.pop("whatsapp_orders"))
    result, db = run_load(tmp_path)

    assert result.returncode != 0
    assert "whatsapp_orders" in result.stderr and "introuvable" in result.stderr
    assert raw_tables(db) == []
