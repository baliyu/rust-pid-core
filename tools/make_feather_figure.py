#!/usr/bin/env python3
"""Draw figures/feather_cycles.png from results/feather_cycles.csv.

Usage: make_feather_figure.py [CSV [OUT]]
"""
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
BAR = "#3b6ea5"
INK = "#222222"
MUTED = "#666666"
GRID = "#e4e4e4"


def make(csv_path, out):
    with Path(csv_path).open() as f:
        rows = list(csv.DictReader(f))
    total = rows[-1]
    scen = rows[:-1]
    labels = [r["scenario"] for r in scen]
    vals = [float(r["cycles_per_step"]) for r in scen]
    mean = float(total["cycles_per_step"])
    fig, ax = plt.subplots(figsize=(8, 4.4))
    bars = ax.bar(labels, vals, width=0.6, color=BAR)
    ax.bar_label(bars, fmt="%.0f", padding=2, fontsize=9, color=INK)
    ax.axhline(mean, color=MUTED, linestyle="--", linewidth=1)
    ax.annotate(f"all rows\n{mean:.1f}", xy=(1, mean), xycoords=("axes fraction", "data"),
                xytext=(6, 0), textcoords="offset points", ha="left", va="center", fontsize=9, color=INK)
    ax.set_ylim(0, max(vals) * 1.15)
    ax.set_xlabel("scenario (order in the vector file)", color=INK)
    ax.set_ylabel("cycles per control step", color=INK)
    ax.set_title("Cycles per control step on the Feather M0 (SAMD21)", loc="left", fontsize=12, color=INK, pad=24)
    ax.text(0, 1.03, f"SysTick count, includes parsing and comparing each row. One run, {total['rows']} rows, {total['mismatches']} mismatches.",
            transform=ax.transAxes, fontsize=9, color=MUTED)
    ax.yaxis.grid(True, color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color(MUTED)
    ax.tick_params(colors=INK)
    fig.subplots_adjust(left=0.1, right=0.86, top=0.82, bottom=0.15)
    fig.savefig(out, dpi=150)
    plt.close(fig)


def main(argv):
    csv_path = argv[0] if len(argv) > 0 else ROOT / "results" / "feather_cycles.csv"
    out = argv[1] if len(argv) > 1 else ROOT / "figures" / "feather_cycles.png"
    make(csv_path, out)
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
