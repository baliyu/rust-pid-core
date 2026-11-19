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
