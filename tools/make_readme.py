#!/usr/bin/env python3
"""Fills README.tmpl.md with numbers read from committed data and writes README.md.
With --check it only compares the existing README.md with what would be written."""
import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def values():
    totals = json.loads((ROOT / "docs" / "scorecard_totals.json").read_text())
    vec_rows = len((ROOT / "vectors" / "vectors.csv").read_text().splitlines()) - 1
    after = read_csv(ROOT / "results" / "mutation.csv")
    before = read_csv(ROOT / "results" / "mutation_before_boundary.csv")
    commit = (ROOT / "vectors" / "PROVENANCE.txt").read_text().strip().split("=", 1)[1]
    return {
        "rows": str(vec_rows),
        "mutants": str(len(after)),
        "killed_before": str(sum(r["replay_test"] == "killed" for r in before)),
        "killed_after": str(sum(r["replay_test"] == "killed" for r in after)),
        "sc_rows": str(totals["rows"]),
        "sc_hits": str(totals["hits"]),
        "sc_misses": str(totals["misses"]),
        "hit_rate": f'{totals["hit_rate_percent"]:.1f}',
        "c_commit_short": commit[:7],
    }


def render():
    text = (ROOT / "README.tmpl.md").read_text()
    for key, val in values().items():
        text = text.replace("{{" + key + "}}", val)
    assert "{{" not in text, "unfilled placeholder"
    return text


def main():
    text = render()
    target = ROOT / "README.md"
    if "--check" in sys.argv:
        same = target.exists() and target.read_text() == text
        print("README up to date" if same else "README out of date")
        return 0 if same else 1
    target.write_text(text)
    print("wrote README.md")
    return 0


if __name__ == "__main__":
    sys.exit(main())
