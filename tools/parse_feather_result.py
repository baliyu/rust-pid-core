#!/usr/bin/env python3
"""Decode the result row read back from the Feather M0 and write results/feather_cycles.csv.

Usage: parse_feather_result.py [DUMP [BLOB [OUT]]]

DUMP is the 256 byte flash row at 0x3F000 saved with bossac (only the first 64 bytes are used).
BLOB is qemu-app/vectors.bin, whose header gives the number of rows in each scenario.
"""
import csv
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAGIC = 0x32504552
SYSTICK_WRAP = 0x00FFFFFF


def decode(dump, blob):
    if len(dump) < 64:
        raise SystemExit("dump is shorter than 64 bytes")
    w = struct.unpack("<16I", dump[:64])
    if w[0] != MAGIC:
        raise SystemExit(f"bad magic {w[0]:08x}")
    rows, mismatches, cycles, per_step, n = w[1:6]
    if not 1 <= n <= 10:
        raise SystemExit(f"bad scenario count {n}")
    scen = list(w[6:6 + n])
    if struct.unpack_from("<I", blob, 0)[0] != n:
        raise SystemExit("scenario count differs from the vector blob")
    counts = [struct.unpack_from("<I", blob, 4 + 16 * i + 12)[0] for i in range(n)]
    if min(counts) == 0 or sum(counts) != rows:
        raise SystemExit("row counts differ from the vector blob")
    if sum(scen) != cycles:
        raise SystemExit("scenario cycles do not add up to the total")
    if per_step != cycles // rows:
        raise SystemExit("per step average does not match")
    if max(scen) >= SYSTICK_WRAP:
        raise SystemExit("a scenario reached the SysTick wrap, so its count is unreliable")
    return rows, mismatches, cycles, counts, scen


def main(argv):
    dump = Path(argv[0]) if len(argv) > 0 else ROOT / "results" / "feather_result.bin"
    blob = Path(argv[1]) if len(argv) > 1 else ROOT / "qemu-app" / "vectors.bin"
    out = Path(argv[2]) if len(argv) > 2 else ROOT / "results" / "feather_cycles.csv"
    rows, mismatches, cycles, counts, scen = decode(dump.read_bytes(), blob.read_bytes())
    with out.open("w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["scenario", "rows", "cycles", "cycles_per_step", "mismatches"])
        for i, (n_rows, c) in enumerate(zip(counts, scen)):
            w.writerow([i, n_rows, c, f"{c / n_rows:.1f}", ""])
        w.writerow(["all", rows, cycles, f"{cycles / rows:.1f}", mismatches])
    print(f"rows={rows} mismatches={mismatches} cycles={cycles} per_step={cycles / rows:.1f} -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
