"""Build docs/generated/sensitivity_explorer.html from the sensitivity JSON files.

Usage (from lockerlab/):
    lockerlab --home . sensitivity --avg-sale 25
    lockerlab --home . sensitivity --avg-sale 50
    lockerlab --home . sensitivity --avg-sale 100
    python tools/sensitivity_page.py
"""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GEN = ROOT / "docs" / "generated"

KEEP = ("size", "scenario", "bid_cents", "gross_cents", "cash_profit_cents", "economic_profit_at_15_cents",
        "economic_profit_at_25_cents", "economic_profit_at_40_cents", "cash_roi", "labor_hours",
        "cash_profit_per_hour_cents", "cash_required_cents", "acquisition_cents", "transport_cents",
        "disposal_cents", "selling_and_tax_cents", "vehicle", "trips", "pathways")


def main() -> None:
    data = {}
    for f in sorted(GEN.glob("sensitivity_colorado_springs_avg*.json")):
        d = json.loads(f.read_text())
        avg = d["avg_sale_cents"] // 100
        data[avg] = {
            "bids": d["bids"], "grosses": d["grosses"], "profiles": d["profiles"],
            "cells": [{k: c[k] for k in KEEP} for c in d["cells"]],
            "breakevens": d["breakevens"],
        }
    html = (ROOT / "tools" / "sensitivity_page.template.html").read_text()
    html = html.replace("/*__DATA__*/null", json.dumps(data, separators=(",", ":")))
    out = GEN / "sensitivity_explorer.html"
    out.write_text(html)
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
