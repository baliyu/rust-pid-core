#!/usr/bin/env python3
"""Packs vectors/vectors.csv into qemu-app/vectors.bin (7 bytes per row) for the QEMU replay.

Layout (little endian): u32 scenario count; per scenario i32 kp, i32 ki, i32 kd, u32 rows;
then every row in order as u16 setpoint, u16 adc, i16 expected out, u8 expected fault.
With --check it only compares the existing file with what would be written.
"""
import csv
import struct
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CSV = ROOT / "vectors" / "vectors.csv"
BIN = ROOT / "qemu-app" / "vectors.bin"


def build():
    with open(CSV, newline="") as f:
        rows = list(csv.DictReader(f))
    scen = {}
    for r in rows:
        scen.setdefault(int(r["scenario"]), []).append(r)
    out = bytearray(struct.pack("<I", len(scen)))
    for s in sorted(scen):
        first = scen[s][0]
        out += struct.pack("<iiiI", int(first["kp"]), int(first["ki"]), int(first["kd"]), len(scen[s]))
    for s in sorted(scen):
        for step, r in enumerate(scen[s]):
            assert int(r["step"]) == step, "steps must be consecutive"
            out += struct.pack("<HHhB", int(r["setpoint"]), int(r["adc"]), int(r["out"]), int(r["fault"]))
    return bytes(out)


def main():
    data = build()
    if "--check" in sys.argv:
        same = BIN.exists() and BIN.read_bytes() == data
        print("blob up to date" if same else "blob out of date")
        return 0 if same else 1
    BIN.write_bytes(data)
    print(f"wrote {BIN.name}: {len(data)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
