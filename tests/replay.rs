//! Replays vectors/vectors.csv (made by vectors/gen_vectors.sh from the real C core)
//! through the Rust port. Every output and fault flag must match exactly.
use rust_pid_core::Control;

const VECTORS: &str = include_str!("../vectors/vectors.csv");

#[test]
fn replay_matches_c_core_bit_for_bit() {
    let mut ctl = Control::new();
    let mut scenario = -1i64;
    let mut rows = 0u32;
    let mut mismatches = 0u32;
    for line in VECTORS.lines().skip(1) {
        let f: Vec<i64> = line.split(',').map(|x| x.parse().unwrap()).collect();
        assert_eq!(f.len(), 9);
        if f[0] != scenario {
            scenario = f[0];
            assert_eq!(f[1], 0, "a scenario must start at step 0");
            ctl = Control::with_gains(f[2] as i32, f[3] as i32, f[4] as i32);
        }
        let out = ctl
            .step(f[5] as i32, f[6] as i32)
            .expect("no overflow expected on vectors the C core ran under UBSan");
        let fault = i64::from(ctl.fault());
        rows += 1;
        if i64::from(out) != f[7] || fault != f[8] {
            mismatches += 1;
            if mismatches <= 5 {
                eprintln!(
                    "MISMATCH scenario {} step {}: rust out={} fault={}, C out={} fault={}",
                    f[0], f[1], out, fault, f[7], f[8]
                );
            }
        }
    }
    println!("replayed {rows} rows, {mismatches} mismatches");
    assert_eq!(rows, 10500);
    assert_eq!(mismatches, 0);
}
