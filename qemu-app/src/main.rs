//! Smoke test on QEMU's Cortex-M3 (lm3s6965evb): five control steps printed over semihosting.
#![no_std]
#![no_main]

use cortex_m_rt::entry;
use cortex_m_semihosting::{debug, hprintln};
use panic_semihosting as _;
use rust_pid_core::Control;

#[entry]
fn main() -> ! {
    let mut ctl = Control::new();
    for adc in [1000, 1500, 2000, 2048, 2048] {
        match ctl.step(2048, adc) {
            Ok(out) => {
                let _ = hprintln!("adc={} out={} fault={}", adc, out, ctl.fault());
            }
            Err(_) => {
                let _ = hprintln!("overflow");
                debug::exit(debug::EXIT_FAILURE);
            }
        }
    }
    let _ = hprintln!("done");
    debug::exit(debug::EXIT_SUCCESS);
    loop {}
}
