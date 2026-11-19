#!/usr/bin/env python3
"""Makes the result figures from committed data: mutation kills before and after the boundary vectors,
and prediction calibration (stated confidence against how often the event happened)."""
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
INK, KILLED, SURVIVED = "#1f2933", "#2a6fbb", "#e08a1e"
BINS = [(0, 60), (60, 80), (80, 90), (90, 101)]


def read_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def fig_mutation(before, after, out):
    assert [r["id"] for r in before] == [r["id"] for r in after], "mutant lists differ"
    n = len(after)
    fig, ax = plt.subplots(figsize=(7.4, 0.42 * n + 1.8))
    for j, rows in enumerate((before, after)):
        for i, r in enumerate(rows):
            killed = r["replay_test"] == "killed"
            ax.add_patch(plt.Rectangle((j + 0.04, i + 0.06), 0.92, 0.88, color=KILLED if killed else SURVIVED))
            ax.text(j + 0.5, i + 0.5, r["replay_test"], ha="center", va="center",
                    color="white" if killed else INK, fontsize=9)
    ax.set_xlim(0, 2)
    ax.set_ylim(n, 0)
    ax.set_yticks([i + 0.5 for i in range(n)])
    ax.set_yticklabels([f'{r["id"]} {r["description"]}' for r in after], color=INK, fontsize=9)
    ax.set_xticks([0.5, 1.5])
    ax.set_xticklabels(["random vectors only", "plus boundary vectors"], color=INK)
    ax.xaxis.tick_top()
    ax.tick_params(length=0)
    for s in ax.spines.values():
        s.set_visible(False)
    kb = sum(r["replay_test"] == "killed" for r in before)
    ka = sum(r["replay_test"] == "killed" for r in after)
    fig.suptitle(f"Mutants caught by the replay test: {kb} of {n}, then {ka} of {n}", color=INK, fontsize=11)
    fig.tight_layout(rect=(0, 0, 1, 0.94))
    fig.savefig(out, dpi=150)
    plt.close(fig)
    print(f"mutation: before {kb} of {n} killed, after {ka} of {n} killed")


def fig_calibration(rows, out):
    stats = []
    for lo, hi in BINS:
        sel = [r for r in rows if lo <= int(r["pct"]) < hi]
        if sel:
            happened = sum(r["event_happened"] == "yes" for r in sel)
            stats.append((f"{lo}-{min(hi - 1, 100)}", len(sel),
                          sum(int(r["pct"]) for r in sel) / len(sel), 100 * happened / len(sel)))
    fig, ax = plt.subplots(figsize=(6.4, 4.2))
    x = list(range(len(stats)))
    ax.bar(x, [s[3] for s in stats], width=0.55, color=KILLED, label="how often it happened")
    ax.scatter(x, [s[2] for s in stats], marker="D", s=46, color=SURVIVED, zorder=3, label="mean stated confidence")
    for i, s in enumerate(stats):
        ax.text(i, 4, f"n={s[1]}", ha="center", color="white", fontsize=9)
        ax.text(i + 0.33, s[3] + 1.5, f"{s[3]:.0f}", ha="left", color=INK, fontsize=9)
    ax.set_xticks(x)
    ax.set_xticklabels([s[0] for s in stats], color=INK)
    ax.set_xlabel("stated confidence bin (percent)", color=INK)
    ax.set_ylabel("percent", color=INK)
    ax.set_ylim(0, 108)
    ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.2), ncol=2, frameon=False, labelcolor=INK)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    ax.set_title(f"Predicted confidence against outcome (n={len(rows)})", color=INK, fontsize=11)
    fig.tight_layout()
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    for s in stats:
        print(f"calibration bin {s[0]}: n={s[1]}, mean confidence {s[2]:.1f}, event rate {s[3]:.1f}")


def main():
    (ROOT / "figures").mkdir(exist_ok=True)
    fig_mutation(read_csv(ROOT / "results" / "mutation_before_boundary.csv"),
                 read_csv(ROOT / "results" / "mutation.csv"), ROOT / "figures" / "mutation_kills.png")
    fig_calibration(read_csv(ROOT / "docs" / "scorecard.csv"), ROOT / "figures" / "calibration.png")
    return 0


if __name__ == "__main__":
    sys.exit(main())
