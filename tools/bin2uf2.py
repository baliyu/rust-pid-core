#!/usr/bin/env python3
"""Converts a raw .bin into a UF2 file for the Adafruit Feather M0 bootloader (SAMD21, application at 0x2000).

Usage: bin2uf2.py input.bin output.uf2 [--base 0x2000] [--family 0x68ed2b88]
"""
import argparse
import struct
import sys
from pathlib import Path

MAGIC0, MAGIC1, MAGIC_END = 0x0A324655, 0x9E5D5157, 0x0AB16F30
FLAG_FAMILY_PRESENT = 0x00002000
SAMD21_FAMILY = 0x68ED2B88
PAYLOAD = 256


def to_uf2(data, base=0x2000, family=SAMD21_FAMILY):
    count = (len(data) + PAYLOAD - 1) // PAYLOAD
    out = bytearray()
    for i in range(count):
        chunk = data[i * PAYLOAD:(i + 1) * PAYLOAD]
        block = struct.pack("<IIIIIIII", MAGIC0, MAGIC1, FLAG_FAMILY_PRESENT, base + i * PAYLOAD, PAYLOAD, i, count, family)
        block += chunk.ljust(476, b"\x00")
        block += struct.pack("<I", MAGIC_END)
        assert len(block) == 512
        out += block
    return bytes(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--base", type=lambda s: int(s, 0), default=0x2000)
    ap.add_argument("--family", type=lambda s: int(s, 0), default=SAMD21_FAMILY)
    args = ap.parse_args()
    data = Path(args.input).read_bytes()
    uf2 = to_uf2(data, args.base, args.family)
    Path(args.output).write_bytes(uf2)
    print(f"{len(data)} bytes -> {len(uf2) // 512} blocks, {len(uf2)} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
