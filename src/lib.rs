//! no_std Rust port of the fixed-point PID core, supervisor and control step
//! from stm32-pid-control-lab. Every i64 operation is checked: an overflow
//! returns `Err(Error::Overflow)` and leaves the state untouched.
#![no_std]

pub const PID_Q: u32 = 16;
pub const PID_ONE: i64 = 1 << PID_Q;
pub const OUT_MIN: i32 = 0;
pub const OUT_MAX: i32 = 1000;
pub const KP_Q16: i32 = 17309;
pub const KI_Q16: i32 = 1735;
pub const KD_Q16: i32 = 0;
pub const SUP_ADC_MIN: i32 = 50;
pub const SUP_ADC_MAX: i32 = 4045;
pub const SUP_FAULT_AFTER: i32 = 5;
pub const SUP_CLEAR_AFTER: i32 = 20;
pub const SUP_SAFE_OUTPUT: i32 = 0;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Error {
    Overflow,
}

fn mul(a: i64, b: i64) -> Result<i64, Error> {
    a.checked_mul(b).ok_or(Error::Overflow)
}

fn add(a: i64, b: i64) -> Result<i64, Error> {
    a.checked_add(b).ok_or(Error::Overflow)
}

fn sub(a: i64, b: i64) -> Result<i64, Error> {
    a.checked_sub(b).ok_or(Error::Overflow)
}

fn clamp64(x: i64, lo: i64, hi: i64) -> i64 {
    if x < lo {
        lo
    } else if x > hi {
        hi
    } else {
        x
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Pid {
    kp: i32,
    ki: i32,
    kd: i32,
    out_min: i32,
    out_max: i32,
    integral: i32,
    prev_pv: i32,
    primed: bool,
}

impl Pid {
    pub fn new(kp: i32, ki: i32, kd: i32, out_min: i32, out_max: i32) -> Self {
        Pid {
            kp,
            ki,
            kd,
            out_min,
            out_max,
            integral: 0,
            prev_pv: 0,
            primed: false,
        }
    }

    pub fn reset(&mut self) {
        self.integral = 0;
        self.prev_pv = 0;
        self.primed = false;
    }

    pub fn update(&mut self, setpoint: i32, measurement: i32) -> Result<i32, Error> {
        let lo = mul(i64::from(self.out_min), PID_ONE)?;
        let hi = mul(i64::from(self.out_max), PID_ONE)?;
        let error = sub(i64::from(setpoint), i64::from(measurement))?;
        let p_term = mul(i64::from(self.kp), error)?;
        let d_term = if self.primed {
            mul(
                i64::from(self.kd),
                sub(i64::from(self.prev_pv), i64::from(measurement))?,
            )?
        } else {
            0
        };
        let i_sum = add(i64::from(self.integral), mul(i64::from(self.ki), error)?)?;
        let i_term = clamp64(i_sum, lo.min(0), hi.max(0));
        let new_integral = i32::try_from(i_term).map_err(|_| Error::Overflow)?;
        let total = add(add(p_term, i_term)?, d_term)?;
        let out = clamp64(total, lo, hi) >> PID_Q;
        let out = i32::try_from(out).map_err(|_| Error::Overflow)?;
        // State changes only after every check has passed.
        self.prev_pv = measurement;
        self.primed = true;
        self.integral = new_integral;
        Ok(out)
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Default)]
pub struct Sup {
    bad: i32,
    good: i32,
    fault: bool,
}

impl Sup {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn step(&mut self, adc: i32, control_out: i32) -> i32 {
        if !(SUP_ADC_MIN..=SUP_ADC_MAX).contains(&adc) {
            self.good = 0;
            if self.bad < SUP_FAULT_AFTER {
                self.bad += 1;
            }
            if self.bad >= SUP_FAULT_AFTER {
                self.fault = true;
            }
        } else {
            self.bad = 0;
            if self.fault {
                self.good += 1;
                if self.good >= SUP_CLEAR_AFTER {
                    self.fault = false;
                    self.good = 0;
                }
            }
        }
        if self.fault {
            SUP_SAFE_OUTPUT
        } else {
            control_out
        }
    }

    pub fn fault(&self) -> bool {
        self.fault
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub struct Control {
    pid: Pid,
    sup: Sup,
}

impl Control {
    pub fn new() -> Self {
        Self::with_gains(KP_Q16, KI_Q16, KD_Q16)
    }

    pub fn with_gains(kp: i32, ki: i32, kd: i32) -> Self {
        Control {
            pid: Pid::new(kp, ki, kd, OUT_MIN, OUT_MAX),
            sup: Sup::new(),
        }
    }

    pub fn step(&mut self, setpoint: i32, adc: i32) -> Result<i32, Error> {
        let out = self.pid.update(setpoint, adc)?;
        let out = self.sup.step(adc, out);
        if self.sup.fault() {
            self.pid.reset();
        }
        Ok(out)
    }

    pub fn fault(&self) -> bool {
        self.sup.fault()
    }
}

impl Default for Control {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn overflow_is_reported_and_state_kept() {
        let mut pid = Pid::new(i32::MAX, 0, i32::MAX, OUT_MIN, OUT_MAX);
        pid.update(0, 0).unwrap();
        let before = pid;
        assert_eq!(pid.update(i32::MAX, i32::MIN), Err(Error::Overflow));
        assert_eq!(pid, before);
    }

    #[test]
    fn fault_after_five_bad_clears_after_twenty_good() {
        let mut s = Sup::new();
        for _ in 0..4 {
            assert_eq!(s.step(0, 500), 500);
        }
        assert!(!s.fault());
        assert_eq!(s.step(0, 500), SUP_SAFE_OUTPUT);
        assert!(s.fault());
        for _ in 0..19 {
            assert_eq!(s.step(2000, 500), SUP_SAFE_OUTPUT);
        }
        assert!(s.fault());
        assert_eq!(s.step(2000, 500), 500);
        assert!(!s.fault());
    }

    #[test]
    fn output_is_clamped() {
        let mut up = Pid::new(KP_Q16, KI_Q16, KD_Q16, OUT_MIN, OUT_MAX);
        assert_eq!(up.update(4095, 0), Ok(1000));
        let mut down = Pid::new(KP_Q16, KI_Q16, KD_Q16, OUT_MIN, OUT_MAX);
        assert_eq!(down.update(0, 4095), Ok(0));
    }
}
