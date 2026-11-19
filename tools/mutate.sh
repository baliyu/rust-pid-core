#!/usr/bin/env bash
# Mutation check: applies one deliberate bug at a time to src/lib.rs, runs the tests, restores the file.
# Writes results/mutation.csv with one row per mutant.
set -u
cd "$(dirname "$0")/.." || exit 1
. "$HOME/.cargo/env" 2>/dev/null
SRC=src/lib.rs
BACKUP="$(mktemp)"
cp "$SRC" "$BACKUP"
restore() { cp "$BACKUP" "$SRC"; }
trap restore EXIT
OUT=results/mutation.csv
echo "id,description,replay_test,all_tests" > "$OUT"

status() { # runs cargo test with the given args and prints killed, survived or build_error
  if cargo test "$@" > /tmp/mut.log 2>&1; then echo survived
  elif grep -q 'could not compile' /tmp/mut.log; then echo build_error
  else echo killed; fi
}

mutate() { # id description old new
  restore
  python3 -I -c '
import sys
p = "src/lib.rs"
s = open(p).read()
old, new = sys.argv[1], sys.argv[2]
assert s.count(old) == 1, "anchor count %d" % s.count(old)
open(p, "w").write(s.replace(old, new))
' "$3" "$4" || { echo "$1,$2,ANCHOR_FAIL,ANCHOR_FAIL" >> "$OUT"; return; }
  r=$(status --test replay)
  a=$(status)
  echo "$1,$2,$r,$a" >> "$OUT"
}

mutate M1 "swap kp and ki" 'pub fn new(kp: i32, ki: i32, kd: i32, out_min: i32, out_max: i32) -> Self {' 'pub fn new(ki: i32, kp: i32, kd: i32, out_min: i32, out_max: i32) -> Self {'
mutate M2 "remove anti-windup clamp" 'clamp64(i_sum, lo.min(0), hi.max(0))' 'i_sum'
mutate M3 "fault after 4 bad samples" 'pub const SUP_FAULT_AFTER: i32 = 5;' 'pub const SUP_FAULT_AFTER: i32 = 4;'
mutate M4 "clear after 19 good samples" 'pub const SUP_CLEAR_AFTER: i32 = 20;' 'pub const SUP_CLEAR_AFTER: i32 = 19;'
mutate M5 "flip D-term sign" 'sub(i64::from(self.prev_pv), i64::from(measurement))?' 'sub(i64::from(measurement), i64::from(self.prev_pv))?'
mutate M6 "no PID reset on fault" '            self.pid.reset();' '            let _ = 0;'
mutate M7 "remove output clamp" 'clamp64(total, lo, hi) >> PID_Q' 'total >> PID_Q'
mutate M8 "D-term always primed" 'let d_term = if self.primed {' 'let d_term = if true {'
mutate M9 "ADC low limit 51" 'pub const SUP_ADC_MIN: i32 = 50;' 'pub const SUP_ADC_MIN: i32 = 51;'
mutate M10 "ADC high limit 4044" 'pub const SUP_ADC_MAX: i32 = 4045;' 'pub const SUP_ADC_MAX: i32 = 4044;'
