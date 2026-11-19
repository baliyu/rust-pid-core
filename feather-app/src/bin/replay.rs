//! Replays every vector on the Adafruit Feather M0 (SAMD21, Cortex-M0+ at 48 MHz) and reports the result
//! over USB serial once a second, with the cycles used per control step (measured with SysTick).
#![no_std]
#![no_main]
#![allow(static_mut_refs)]

use panic_halt as _;

use core::fmt::Write;

use cortex_m::interrupt::free as disable_interrupts;
use cortex_m::peripheral::syst::SystClkSource;
use cortex_m::peripheral::{NVIC, SYST};
use heapless::String;
use usb_device::bus::UsbBusAllocator;
use usb_device::prelude::*;
use usbd_serial::{SerialPort, USB_CLASS_CDC};

use bsp::hal;
use bsp::pac;
use feather_m0 as bsp;

use bsp::{entry, pin_alias};
use hal::clock::GenericClockController;
use hal::prelude::*;
use hal::usb::UsbBus;
use pac::{interrupt, CorePeripherals, Peripherals};
use rust_pid_core::Control;

const BLOB: &[u8] = include_bytes!("../../../qemu-app/vectors.bin");

static mut USB_ALLOCATOR: Option<UsbBusAllocator<UsbBus>> = None;
static mut USB_BUS: Option<UsbDevice<UsbBus>> = None;
static mut USB_SERIAL: Option<SerialPort<UsbBus>> = None;

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

/// Returns (rows, mismatches, cycles). Cycles come from SysTick and cover parsing each row,
/// the control step and the comparison, summed over scenarios.
fn replay() -> (u32, u32, u32) {
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
        cycles += start.wrapping_sub(end) & 0x00FF_FFFF;
    }
    (rows, mismatches, cycles)
}

fn serial_write(data: &[u8]) {
    let mut written = 0;
    let mut tries = 0u32;
    while written < data.len() && tries < 20_000 {
        let n = disable_interrupts(|_| unsafe {
            USB_SERIAL
                .as_mut()
                .map(|s| s.write(&data[written..]).unwrap_or(0))
                .unwrap_or(0)
        });
        written += n;
        tries += 1;
    }
}

unsafe fn poll_usb() {
    if let Some(usb_dev) = USB_BUS.as_mut() {
        if let Some(serial) = USB_SERIAL.as_mut() {
            usb_dev.poll(&mut [serial]);
            let mut buf = [0u8; 64];
            if let Ok(count) = serial.read(&mut buf) {
                let _ = count;
            }
        }
    }
}

#[interrupt]
fn USB() {
    unsafe {
        poll_usb();
    }
}

#[entry]
fn main() -> ! {
    let mut peripherals = Peripherals::take().unwrap();
    let mut core = CorePeripherals::take().unwrap();
    // Same clock setup as the crate's own USB serial example.
    let mut clocks = GenericClockController::with_internal_32kosc(
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

    // The replay runs before USB starts, so USB interrupts cannot add cycles to the measurement.
    let (rows, mismatches, cycles) = replay();
    let per_step = cycles / rows.max(1);

    let bus_allocator = unsafe {
        USB_ALLOCATOR = Some(bsp::usb_allocator(
            peripherals.usb,
            &mut clocks,
            &mut peripherals.pm,
            pins.usb_dm,
            pins.usb_dp,
        ));
        USB_ALLOCATOR.as_ref().unwrap()
    };
    unsafe {
        USB_SERIAL = Some(SerialPort::new(bus_allocator));
        USB_BUS = Some(
            UsbDeviceBuilder::new(bus_allocator, UsbVidPid(0x16c0, 0x27dd))
                .strings(&[StringDescriptors::new(LangID::EN)
                    .manufacturer("rust-pid-core")
                    .product("PID replay")
                    .serial_number("0001")])
                .expect("Failed to set strings")
                .device_class(USB_CLASS_CDC)
                .build(),
        );
    }
    unsafe {
        core.NVIC.set_priority(interrupt::USB, 1);
        NVIC::unmask(interrupt::USB);
    }

    loop {
        red_led.set_high().unwrap();
        let mut msg: String<128> = String::new();
        write!(msg, "rows={} mismatches={} cycles={} per_step={}\r\n", rows, mismatches, cycles, per_step).ok();
        serial_write(msg.as_bytes());
        cortex_m::asm::delay(24_000_000);
        red_led.set_low().unwrap();
        cortex_m::asm::delay(24_000_000);
    }
}
