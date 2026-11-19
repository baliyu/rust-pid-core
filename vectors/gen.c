/* gen.c: dumps replay vectors from the real C controller (core/ of stm32-pid-control-lab). */
#include <stdio.h>
#include <stdint.h>
#include "control.h"
#include "gains.h"

static uint32_t rng_state;
static uint32_t rnd(void)
{
    rng_state = rng_state * 1664525u + 1013904223u;
    return rng_state >> 8;
}

typedef struct { int32_t kp, ki, kd; int steps; int mode; } cfg_t;

int main(void)
{
    static const cfg_t cfgs[] = {
        { CONTROL_KP_Q16, CONTROL_KI_Q16, CONTROL_KD_Q16, 2000, 0 },
        { CONTROL_KP_Q16, CONTROL_KI_Q16, CONTROL_KD_Q16, 4000, 1 },
        { 17309, 1735, 65536, 1000, 0 },
        { 16711680, 16711680, 16711680, 1000, 2 },
        { 0, 0, 0, 500, 2 },
        { 65536, 0, 0, 500, 3 },
        { 16711680, 65536, 16711680, 1000, 3 },
        { -17309, -1735, -100, 500, 2 },
        { CONTROL_KP_Q16, CONTROL_KI_Q16, CONTROL_KD_Q16, 180, 4 },
    };
    static const int32_t sps[3] = { 1000, 2048, 3000 };
    const int n = (int)(sizeof cfgs / sizeof cfgs[0]);
    rng_state = 12345u;
    puts("scenario,step,kp,ki,kd,setpoint,adc,out,fault");
    for (int s = 0; s < n; s++) {
        control_t c;
        int32_t sp = 2048, adc = 2048;
        int burst = 0;
        control_init_with(&c, cfgs[s].kp, cfgs[s].ki, cfgs[s].kd);
        for (int t = 0; t < cfgs[s].steps; t++) {
            if (cfgs[s].mode == 0) {
                if (t % 200 == 0) { sp = sps[(t / 200) % 3]; }
                adc += (int32_t)(rnd() % 41u) - 20;
                if (adc < 100) { adc = 100; }
                if (adc > 4000) { adc = 4000; }
            } else if (cfgs[s].mode == 1) {
                sp = 2048;
                if (burst > 0) { adc = (rnd() & 1u) ? 0 : 4090; burst--; }
                else if (rnd() % 20u == 0) { burst = (int)(rnd() % 8u); adc = 0; }
                else { adc = 1000 + (int32_t)(rnd() % 2001u); }
            } else if (cfgs[s].mode == 2) {
                sp = (int32_t)(rnd() % 4096u);
                adc = (int32_t)(rnd() % 4096u);
            } else if (cfgs[s].mode == 3) {
                sp = (int32_t)(rnd() % 65536u);
                adc = (int32_t)(rnd() % 65536u);
            } else {
                static const int32_t bv[6] = { 49, 50, 51, 4044, 4045, 4046 };
                sp = 2048;
                adc = (t % 30 < 5) ? bv[t / 30] : 2000;
            }
            int32_t out = control_step(&c, sp, adc);
            printf("%d,%d,%d,%d,%d,%d,%d,%d,%d\n", s, t, (int)cfgs[s].kp, (int)cfgs[s].ki, (int)cfgs[s].kd,
                   (int)sp, (int)adc, (int)out, sup_fault(&c.sup) ? 1 : 0);
        }
    }
    return 0;
}
