//! Replays every vector (packed by tools/make_blob.py) on QEMU's Cortex-M3 (lm3s6965evb).
//! Prints the row and mismatch counts over semihosting and exits non-zero on any mismatch.
#![no_std]
#![no_main]

use cortex_m_rt::entry;
use cortex_m_semihosting::{debug, hprintln};
use panic_semihosting as _;
use rust_pid_core::Control;

const BLOB: &[u8] = include_bytes!("../vectors.bin");

fn u16_at(o: usize) -> u16 {
    u16::from_le_bytes([BLOB[o], BLOB[o + 1]])
}

fn i16_at(o: usize) -> i16 {
    i16::from_le_bytes([BLOB[o], BLOB[o + 1]])
}

fn u32_at(o: usize) -> u32 {
    u32::from_le_bytes([BLOB[o], BLOB[o + 1], BLOB[o + 2], BLOB[o + 3]])
}

fn i32_at(o: usize) -> i32 {
    i32::from_le_bytes([BLOB[o], BLOB[o + 1], BLOB[o + 2], BLOB[o + 3]])
}

#[entry]
fn main() -> ! {
    let n = u32_at(0) as usize;
    let mut pos = 4 + n * 16;
    let mut rows = 0u32;
    let mut mismatches = 0u32;
    let _ = hprintln!("blob={} bytes, scenarios={}", BLOB.len(), n);
    for s in 0..n {
        let h = 4 + s * 16;
        let mut ctl = Control::with_gains(i32_at(h), i32_at(h + 4), i32_at(h + 8));
        let count = u32_at(h + 12) as usize;
        for _ in 0..count {
            let sp = i32::from(u16_at(pos));
            let adc = i32::from(u16_at(pos + 2));
            let want_out = i32::from(i16_at(pos + 4));
            let want_fault = BLOB[pos + 6] != 0;
            pos += 7;
            let got = ctl.step(sp, adc);
            let good = matches!(got, Ok(o) if o == want_out) && ctl.fault() == want_fault;
            rows += 1;
            if !good {
                mismatches += 1;
                if mismatches <= 3 {
                    let _ = hprintln!("MISMATCH scenario={} row={} want={}", s, rows, want_out);
                }
            }
        }
    }
    let _ = hprintln!("rows={} mismatches={}", rows, mismatches);
    if mismatches == 0 {
        debug::exit(debug::EXIT_SUCCESS);
    } else {
        debug::exit(debug::EXIT_FAILURE);
    }
    loop {}
}
