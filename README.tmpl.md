# rust-pid-core

A no_std Rust port of a fixed-point PID controller and sensor supervisor, checked against the original C code.

The C original is the control core of pid-control-lab (commit {{c_commit_short}}): pid.c, supervisor.c and control.c, about 80 lines in total. The Rust port keeps the same Q16.16 maths. The one deliberate difference is that every 64-bit operation is checked: an overflow returns an error and leaves the controller state unchanged, where the C code would hit signed overflow.

## AI assistance

This project was drafted with Claude (Anthropic) and checked by the author. Every commit carries the same note.

## What was checked

- Replay: a small C program drives the real C core under the undefined-behaviour sanitiser and writes {{rows}} rows of inputs and outputs. The Rust port reproduces every row exactly, on the PC and on an emulated Cortex-M3 (QEMU lm3s6965evb).
- Mutation check: {{mutants}} deliberate bugs were put into the Rust port one at a time. The replay test with random vectors alone caught {{killed_before}} of {{mutants}}. Adding boundary vectors for the ADC limits raised that to {{killed_after}} of {{mutants}} (figures/mutation_kills.png).
- Predictions: before each run a prediction with a percentage was written down and scored afterwards from the pasted output. {{sc_rows}} predictions so far: {{sc_hits}} hit and {{sc_misses}} missed ({{hit_rate}} percent hit). The misses are kept in docs/scorecard.csv, and figures/calibration.png compares stated confidence with what happened.

## Limits

- The vectors come from the C code, so they show that the two agree. They do not show that the controller design is right.
- QEMU is not cycle accurate, so there are no timing results here. The code has not been run on a physical board yet.
- The mutants are {{mutants}} hand-made changes, not the output of an exhaustive mutation tool.
- The scorecard is small and scored by hand, so treat the hit rate as a record of this project only.

## Layout

- src/lib.rs: the port (Pid, Sup, Control) with unit tests
- tests/replay.rs: replays vectors/vectors.csv against the port
- qemu-app/: bare-metal Cortex-M3 replay of the same vectors
- vectors/: generator built from the C core, and the vectors
- tools/: scripts for the blob, mutation check, scorecard totals, figures and this README
- results/, figures/, docs/: mutation results, figures, scorecard
- tests_py/: tests for every script

## Reproduce

Linux or WSL with Rust, gcc and qemu-system-arm:

    cargo test
    cargo clippy --all-targets -- -D warnings
    cargo build --lib --target thumbv7m-none-eabi
    (cd qemu-app && cargo run --release)
    pip install -r requirements.txt && python -m pytest tests_py
    bash tools/mutate.sh

Regenerating the vectors needs the C core: CORE_DIR=<path to pid-control-lab/core> bash vectors/gen_vectors.sh
