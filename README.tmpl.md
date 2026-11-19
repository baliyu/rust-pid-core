# rust-pid-core

A no_std Rust port of a fixed-point PID controller and sensor supervisor, checked against the original C code.

The C original is the control core of pid-control-lab (commit {{c_commit_short}}): pid.c, supervisor.c and control.c, about 80 lines in total. The Rust port keeps the same Q16.16 maths. The one deliberate difference is that every 64-bit operation is checked: an overflow returns an error and leaves the controller state unchanged, where the C code would hit signed overflow.

## AI assistance

This project was drafted with Claude (Anthropic) and checked by the author. Every commit carries the same note.

## What was checked

- Replay: a small C program drives the real C core under the undefined-behaviour sanitiser and writes {{rows}} rows of inputs and outputs. The Rust port reproduces every row exactly, on the PC and on an emulated Cortex-M3 (QEMU lm3s6965evb).
- Feather M0: the same replay runs on a physical Adafruit Feather M0 (SAMD21, Cortex-M0+). All {{rows}} rows match, at 558.6 cycles per control step on average, measured with SysTick over one run (results/feather_cycles.csv, figures/feather_cycles.png). The count includes parsing each row and comparing the result. USB serial did not start under Windows with this HAL (atsamd-hal 0.23, feather_m0 0.20.4), even with the crate's own example, while an Arduino sketch worked on the same board and PC. So the firmware saves its result in one flash page, and bossac reads it back through the bootloader.
- Mutation check: {{mutants}} deliberate bugs were put into the Rust port one at a time. The replay test with random vectors alone caught {{killed_before}} of {{mutants}}. Adding boundary vectors for the ADC limits raised that to {{killed_after}} of {{mutants}} (figures/mutation_kills.png).
- Predictions: before each run a prediction with a percentage was written down and scored afterwards from the pasted output. {{sc_rows}} predictions so far: {{sc_hits}} hit and {{sc_misses}} missed ({{hit_rate}} percent hit). The misses are kept in docs/scorecard.csv, and figures/calibration.png compares stated confidence with what happened.

## Limits

- The vectors come from the C code, so they show that the two agree. They do not show that the controller design is right.
- QEMU is not cycle accurate, so it gives no timing. The timing is one run on one Feather M0, the C core has not been timed on the same chip, and the count includes the parsing and comparison code around each step.
- The mutants are {{mutants}} hand-made changes, not the output of an exhaustive mutation tool.
- The scorecard is small and scored by hand, so treat the hit rate as a record of this project only.

## Layout

- src/lib.rs: the port (Pid, Sup, Control) with unit tests
- tests/replay.rs: replays vectors/vectors.csv against the port
- qemu-app/: bare-metal Cortex-M3 replay of the same vectors
- feather-app/: Feather M0 (SAMD21) firmware: a blink test, the replay that saves its result to flash (replay_flash), and a USB serial version (replay) that did not start under Windows. Flashed with the bossac that ships with the Arduino IDE
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

The Feather result: build replay_flash, convert it with llvm-objcopy -O binary, flash it at 0x2000 with bossac, double-tap reset, then read the result row back from the bootloader and decode it:

    (cd feather-app && cargo build --release --bin replay_flash)
    bossac --port=<COM port> -U --offset=0x3F000 --read=256 results/feather_result.bin
    python tools/parse_feather_result.py
    python tools/make_feather_figure.py
