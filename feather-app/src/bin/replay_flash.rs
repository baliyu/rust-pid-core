//! Replays every vector on the Feather M0 (SAMD21, Cortex-M0+ at 48 MHz), measures cycles with SysTick,
//! and saves the result into one flash page so it can be read back through the bootloader (no USB needed).
#![no_std]
#![no_main]

use panic_halt as _;

use cortex_m::peripheral::syst::SystClkSource;
use cortex_m::peripheral::SYST;

use bsp::hal;
use bsp::pac;
use feather_m0 as bsp;

use bsp::{entry, pin_alias};
use hal::clock::GenericClockController;
use hal::prelude::*;
use pac::{CorePeripherals, Peripherals};
use rust_pid_core::Control;

const BLOB: &[u8] = include_bytes!("../../../qemu-app/vectors.bin");
/// "REP2" in little endian.
const MAGIC: u32 = 0x3250_4552;
/// Start of a 256 byte flash row far from the bootloader (first 8 KB) and from the app.
const RESULT_ADDR: u32 = 0x0003_F000;

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

/// Fills the 16 word record: magic, rows, mismatches, total cycles, cycles per step, scenario count,
/// then up to 10 per scenario cycle counts. Cycles come from SysTick and include parsing each row,
/// the control step and the comparison.
fn replay(rec: &mut [u32; 16]) {
    let n = u32_at(0) as usize;
    let mut pos = 4 + n * 16;
    let mut rows = 0u32;
    let mut mismatches = 0u32;
    let mut cycles = 0u32;
    for s in 0..n {
        let h = 4 + s * 16;
        let mut ctl = Control::with_gains(i32_at(h), i32_at(h + 4), i32_at(h + 8));
        let count = u32_at(h + 12) as usize;
        let start = SYST::get_current();
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
            }
        }
        let end = SYST::get_current();
        let spent = start.wrapping_sub(end) & 0x00FF_FFFF;
        cycles += spent;
        if s < 10 {
            rec[6 + s] = spent;
        }
    }
    rec[0] = MAGIC;
    rec[1] = rows;
    rec[2] = mismatches;
    rec[3] = cycles;
    rec[4] = cycles / rows.max(1);
    rec[5] = n as u32;
}

/// Erases the flash row at `addr` and writes one 64 byte page there, using the NVM controller registers.
fn nvm_save(addr: u32, words: &[u32; 16]) {
    const NVM: u32 = 0x4100_4000;
    let ctrla = NVM as *mut u16;
    let ctrlb = (NVM + 0x04) as *mut u32;
    let intflag = (NVM + 0x14) as *const u8;
    let addr_reg = (NVM + 0x1C) as *mut u32;
    unsafe {
        let wait = || {
            while core::ptr::read_volatile(intflag) & 1 == 0 {}
        };
        wait();
        // Manual write: the page is written only by the explicit write page command.
        let b = core::ptr::read_volatile(ctrlb);
        core::ptr::write_volatile(ctrlb, b | 0x80);
        // Erase the 256 byte row (the address register holds a 16 bit word address).
        core::ptr::write_volatile(addr_reg, addr >> 1);
        core::ptr::write_volatile(ctrla, 0xA502);
        wait();
        // Clear the page buffer, fill it, then write the page.
        core::ptr::write_volatile(ctrla, 0xA544);
        wait();
        let dst = addr as *mut u32;
        for (i, w) in words.iter().enumerate() {
            core::ptr::write_volatile(dst.add(i), *w);
        }
        core::ptr::write_volatile(addr_reg, addr >> 1);
        core::ptr::write_volatile(ctrla, 0xA504);
        wait();
    }
}

#[entry]
fn main() -> ! {
    let mut peripherals = Peripherals::take().unwrap();
    let core = CorePeripherals::take().unwrap();
    let _clocks = GenericClockController::with_internal_32kosc(
        peripherals.gclk,
        &mut peripherals.pm,
        &mut peripherals.sysctrl,
        &mut peripherals.nvmctrl,
    );
    let pins = bsp::Pins::new(peripherals.port);
    let mut red_led: bsp::RedLed = pin_alias!(pins.red_led).into();

    let mut syst = core.SYST;
    syst.set_clock_source(SystClkSource::Core);
    syst.set_reload(0x00FF_FFFF);
    syst.clear_current();
    syst.enable_counter();

    let mut rec = [0xFFFF_FFFFu32; 16];
    replay(&mut rec);
    nvm_save(RESULT_ADDR, &rec);

    // Slow blink: all vectors matched. Fast blink: at least one mismatch.
    let half = if rec[2] == 0 { 24_000_000 } else { 4_800_000 };
    loop {
        red_led.set_high().unwrap();
        cortex_m::asm::delay(half);
        red_led.set_low().unwrap();
        cortex_m::asm::delay(half);
    }
}
