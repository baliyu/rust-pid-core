"""Tests for every script in tools/ and vectors/: each one is run or checked, not just present."""
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PY = [sys.executable, "-I"]
CORE = Path(os.environ.get("CORE_DIR", "/mnt/c/stm32-pid-control-lab/core"))
TEXT_SUFFIXES = {".rs", ".py", ".sh", ".md", ".csv", ".toml", ".json", ".c", ".txt", ".x", ".yml"}


def run(cmd):
    return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True)


def test_blob_is_up_to_date():
    r = run(PY + ["tools/make_blob.py", "--check"])
    assert r.returncode == 0, r.stdout + r.stderr


def test_scorecard_is_consistent_and_counted():
    r = run(PY + ["tools/scorecard_totals.py"])
    assert r.returncode == 0, r.stdout + r.stderr
    totals = json.loads((ROOT / "docs" / "scorecard_totals.json").read_text())
    rows = len((ROOT / "docs" / "scorecard.csv").read_text().splitlines()) - 1
    assert totals["rows"] == rows
    assert totals["inconsistent_rows"] == []


@pytest.mark.skipif(shutil.which("gcc") is None or not CORE.exists(), reason="gcc or the C core is not available")
def test_vectors_regenerate_identically():
    path = ROOT / "vectors" / "vectors.csv"
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    r = run(["bash", "vectors/gen_vectors.sh"])
    assert r.returncode == 0, r.stderr
    assert hashlib.sha256(path.read_bytes()).hexdigest() == before


def test_every_mutation_anchor_matches_once():
    src = (ROOT / "src" / "lib.rs").read_text()
    script = (ROOT / "tools" / "mutate.sh").read_text().splitlines()
    lines = [line for line in script if line.startswith("mutate M")]
    assert len(lines) == 10
    for line in lines:
        parts = shlex.split(line)
        assert len(parts) == 5, line
        assert src.count(parts[3]) == 1, parts[1]
        assert parts[3] != parts[4], parts[1]


def test_figures_are_made():
    r = run(PY + ["tools/make_figures.py"])
    assert r.returncode == 0, r.stdout + r.stderr
    for name in ("mutation_kills.png", "calibration.png"):
        assert (ROOT / "figures" / name).stat().st_size > 15000


def test_no_em_dashes_in_tracked_text_files():
    files = run(["git", "ls-files"]).stdout.split()
    bad = [f for f in files if Path(f).suffix in TEXT_SUFFIXES and "\u2014" in (ROOT / f).read_text(errors="ignore")]
    assert bad == []


def test_every_script_is_covered_here():
    me = Path(__file__).read_text()
    scripts = sorted(p.name for pattern in ("tools/*.py", "tools/*.sh", "vectors/*.sh") for p in ROOT.glob(pattern))
    assert scripts, "no scripts found"
    missing = [s for s in scripts if s not in me]
    assert missing == [], missing


def test_readme_is_up_to_date():
    r = run(PY + ["tools/make_readme.py", "--check"])
    assert r.returncode == 0, r.stdout + r.stderr


def test_bin2uf2_blocks_are_valid(tmp_path):
    import struct

    data = bytes(range(256)) * 2 + b"\x01\x02\x03"
    src, dst = tmp_path / "in.bin", tmp_path / "out.uf2"
    src.write_bytes(data)
    r = run(PY + ["tools/bin2uf2.py", str(src), str(dst)])
    assert r.returncode == 0, r.stdout + r.stderr
    raw = dst.read_bytes()
    assert len(raw) == 3 * 512
    payload = b""
    for i in range(3):
        block = raw[i * 512:(i + 1) * 512]
        m0, m1, flags, addr, size, num, total, family = struct.unpack("<IIIIIIII", block[:32])
        assert (m0, m1) == (0x0A324655, 0x9E5D5157)
        assert (flags, addr, size, num, total, family) == (0x2000, 0x2000 + 256 * i, 256, i, 3, 0x68ED2B88)
        assert struct.unpack("<I", block[508:])[0] == 0x0AB16F30
        payload += block[32:32 + 256]
    assert payload[:len(data)] == data


def _feather_paths():
    root = Path(__file__).resolve().parent.parent
    return root, root / "tools" / "parse_feather_result.py", root / "tools" / "make_feather_figure.py"


def test_feather_result_decodes_and_csv_is_up_to_date(tmp_path):
    import csv

    root, parse, _ = _feather_paths()
    out = tmp_path / "cycles.csv"
    r = subprocess.run([sys.executable, str(parse), str(root / "results" / "feather_result.bin"),
                        str(root / "qemu-app" / "vectors.bin"), str(out)], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert out.read_bytes() == (root / "results" / "feather_cycles.csv").read_bytes()
    with out.open() as f:
        rows = list(csv.DictReader(f))
    total = rows[-1]
    assert total["scenario"] == "all" and total["mismatches"] == "0"
    assert sum(int(x["cycles"]) for x in rows[:-1]) == int(total["cycles"])
    assert sum(int(x["rows"]) for x in rows[:-1]) == int(total["rows"])


def test_feather_parser_rejects_bad_dumps(tmp_path):
    root, parse, _ = _feather_paths()
    good = (root / "results" / "feather_result.bin").read_bytes()
    for name, index in (("magic", 0), ("total", 12)):
        data = bytearray(good)
        data[index] ^= 0xFF if name == "magic" else 0x01
        bad = tmp_path / (name + ".bin")
        bad.write_bytes(bytes(data))
        out = tmp_path / (name + ".csv")
        r = subprocess.run([sys.executable, str(parse), str(bad), str(root / "qemu-app" / "vectors.bin"), str(out)],
                           capture_output=True, text=True)
        assert r.returncode != 0, name
        assert not out.exists(), name


def test_feather_figure_is_made(tmp_path):
    root, _, fig = _feather_paths()
    out = tmp_path / "f.png"
    r = subprocess.run([sys.executable, str(fig), str(root / "results" / "feather_cycles.csv"), str(out)],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    assert out.stat().st_size > 10000
    assert (root / "figures" / "feather_cycles.png").exists()


def test_readme_states_the_measured_feather_numbers():
    import csv

    root, _, _ = _feather_paths()
    with (root / "results" / "feather_cycles.csv").open() as f:
        total = list(csv.DictReader(f))[-1]
    readme = (root / "README.md").read_text()
    assert f"{total['cycles_per_step']} cycles per control step" in readme
    assert "results/feather_cycles.csv" in readme
