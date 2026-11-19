#!/usr/bin/env python3
"""Computes totals from docs/scorecard.csv into docs/scorecard_totals.json.

Rule: a prediction at 50 percent or more is a hit when the event happened; a prediction under 50 percent
is a hit when it did not happen. Every row's stated result must agree with this rule.
"""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "docs" / "scorecard.csv"
DST = ROOT / "docs" / "scorecard_totals.json"
BINS = [(0, 60), (60, 80), (80, 90), (90, 101)]


def load():
    with open(SRC, newline="") as f:
        return list(csv.DictReader(f))


def expected(row):
    happened = row["event_happened"] == "yes"
    return "hit" if (int(row["pct"]) >= 50) == happened else "miss"


def totals(rows):
    bad = [r["id"] for r in rows if r["result"] != expected(r)]
    hits = sum(1 for r in rows if r["result"] == "hit")
    bins = []
    for lo, hi in BINS:
        sel = [r for r in rows if lo <= int(r["pct"]) < hi]
        if sel:
            bins.append({"range": f"{lo}-{min(hi - 1, 100)}", "n": len(sel),
                         "mean_confidence": round(sum(int(r["pct"]) for r in sel) / len(sel), 1),
                         "hit_rate": round(100 * sum(1 for r in sel if r["result"] == "hit") / len(sel), 1)})
    return {"rows": len(rows), "hits": hits, "misses": len(rows) - hits,
            "hit_rate_percent": round(100 * hits / len(rows), 1), "inconsistent_rows": bad, "calibration": bins}


def main():
    t = totals(load())
    DST.write_text(json.dumps(t, indent=2) + "\n")
    print(json.dumps(t, indent=2))
    return 1 if t["inconsistent_rows"] else 0


if __name__ == "__main__":
    sys.exit(main())
