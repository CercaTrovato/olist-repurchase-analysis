"""Round-3 role-02 single reproducible entry point.

Usage (from this scripts/ directory):
    python run_all.py --smoke     # 5,000-row small sample: inputs -> candidates -> evidence -> plots
    python run_all.py             # full: inputs -> candidates -> evidence -> plots -> spec -> verify

Each stage runs in a FRESH subprocess so a stage cannot silently reuse another
stage's in-memory state.  Any non-zero exit aborts the whole pipeline.

Input locations can be overridden with R3_H02_DIR / R3_ROLE01_DIR / R3_H05_DIR /
R3_RAW_DIR / R3_PRIVATE_IN / R3_PRIVATE_OUT; see r3_common.py.
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent

SMOKE_STAGES = [
    ("r3_inputs.py", True),
    ("r3_build_candidates.py", True),
    ("r3_evidence.py", True),
    ("r3_plots.py", True),
]
FULL_STAGES = [
    ("r3_inputs.py", False),
    ("r3_build_candidates.py", False),
    ("r3_evidence.py", False),
    ("r3_plots.py", False),
    ("r3_spec.py", False),
    ("r3_verify.py", False),
]


def run(stage: str, smoke: bool) -> None:
    cmd = [sys.executable, str(HERE / stage)] + (["--smoke"] if smoke else [])
    print("\n$ " + " ".join(cmd), flush=True)
    subprocess.run(cmd, cwd=HERE, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--smoke", action="store_true", help="5,000-row small sample")
    args = ap.parse_args()
    stages = SMOKE_STAGES if args.smoke else FULL_STAGES
    print("=== Round3 role-02 pipeline: %s (%d stages) ===" %
          ("SMOKE" if args.smoke else "FULL", len(stages)), flush=True)
    for stage, smoke in stages:
        run(stage, smoke)
    print("\n=== pipeline finished: %s ===" % ("SMOKE" if args.smoke else "FULL"), flush=True)


if __name__ == "__main__":
    main()
