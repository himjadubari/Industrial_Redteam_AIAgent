# ─────────────────────────────────────────────
#  simulation.py  —  Digital Twin (Euler + PID)
# ─────────────────────────────────────────────
import numpy as np
from simple_pid import PID
from config import (
    TANK1_AREA, TANK2_AREA,
    CV1_NOMINAL, CV2_NOMINAL,
    PID_KP, PID_KI, PID_KD, PID_OUTPUT_MAX,
    SIM_DURATION, SIM_DT,
    TANK1_MAX_HEIGHT, TANK2_MAX_HEIGHT,
)


def run_simulation(
    setpoint:     float,
    valve1_clog:  float = 0.0,
    valve2_clog:  float = 0.0,
    leak_rate:    float = 0.0,
    sensor_bias:  float = 0.0,
    sensor_noise: float = 0.0,
    inlet_surge:  float = 1.0,
) -> dict:
    """
    Simulate the two-tank system.

    PID limits are simply (0, PID_OUTPUT_MAX) — the hardware ceiling.
    The integrator will wind up to exactly Q_out_at_setpoint naturally.
    DO NOT scale limits by setpoint — that guarantees wrong steady-state.
    """
    t_span = np.arange(0, SIM_DURATION + SIM_DT, SIM_DT)
    n      = len(t_span)

    cv1 = CV1_NOMINAL * (1.0 - valve1_clog)
    cv2 = CV2_NOMINAL * (1.0 - valve2_clog)

    h1_arr     = np.zeros(n)
    h2_arr     = np.zeros(n)
    q_in_arr   = np.zeros(n)
    q12_arr    = np.zeros(n)
    q_out_arr  = np.zeros(n)
    err_arr    = np.zeros(n)
    spill1_arr = np.zeros(n)
    spill2_arr = np.zeros(n)

    # Start below setpoint so PID ramps up naturally
    h1 = min(0.5, setpoint * 0.6)
    h2 = min(0.4, setpoint * 0.5)

    overflow_t1, overflow_t2           = False, False
    overflow_t1_time, overflow_t2_time = None, None
    total_spill1, total_spill2         = 0.0, 0.0

    # ── PID: hardware limits only — DO NOT scale by setpoint ──
    pid = PID(PID_KP, PID_KI, PID_KD, setpoint=setpoint)
    pid.output_limits = (0.0, PID_OUTPUT_MAX)
    pid.sample_time = None   # FIX 1: decouple from wall-clock; we pass dt explicitly

    rng = np.random.default_rng(42)

    for i, t in enumerate(t_span):
        h2_measured = h2 + sensor_bias + rng.normal(0, sensor_noise)
        q_in = pid(h2_measured, dt=SIM_DT) * inlet_surge   # FIX 1: use simulation dt

        h1 = max(h1, 0.0)
        h2 = max(h2, 0.0)

        q12   = cv1 * np.sqrt(max(h1 - h2, 0.0))
        q_out = cv2 * np.sqrt(max(h2, 0.0))

        dh1_dt = (q_in - q12 - leak_rate) / TANK1_AREA
        dh2_dt = (q12  - q_out)           / TANK2_AREA

        h1 += dh1_dt * SIM_DT
        h2 += dh2_dt * SIM_DT

        # Physical overflow clamping
        spill1 = 0.0
        if h1 > TANK1_MAX_HEIGHT:
            spill1 = (h1 - TANK1_MAX_HEIGHT) * TANK1_AREA
            h1 = TANK1_MAX_HEIGHT
            total_spill1 += spill1
            if not overflow_t1:
                overflow_t1 = True
                overflow_t1_time = float(t)

        spill2 = 0.0
        if h2 > TANK2_MAX_HEIGHT:
            spill2 = (h2 - TANK2_MAX_HEIGHT) * TANK2_AREA
            h2 = TANK2_MAX_HEIGHT
            total_spill2 += spill2
            if not overflow_t2:
                overflow_t2 = True
                overflow_t2_time = float(t)

        h1_arr[i]     = h1
        h2_arr[i]     = h2
        q_in_arr[i]   = q_in
        q12_arr[i]    = q12
        q_out_arr[i]  = q_out
        err_arr[i]    = h2_measured - setpoint
        spill1_arr[i] = spill1
        spill2_arr[i] = spill2

    max_h1        = float(np.max(h1_arr))
    max_h2        = float(np.max(h2_arr))
    max_setpt_err = float(np.max(np.abs(h2_arr - setpoint)))
    rmse          = float(np.sqrt(np.mean((h2_arr - setpoint) ** 2)))
    steady_err    = float(np.mean(np.abs(h2_arr[-30:] - setpoint)))

    return {
        "time"      : t_span,
        "h1"        : h1_arr,
        "h2"        : h2_arr,
        "q_in"      : q_in_arr,
        "q12"       : q12_arr,
        "q_out"     : q_out_arr,
        "error"     : err_arr,
        "spill1"    : spill1_arr,
        "spill2"    : spill2_arr,
        "overflow_t1"      : overflow_t1,
        "overflow_t2"      : overflow_t2,
        "overflow_t1_time" : overflow_t1_time,
        "overflow_t2_time" : overflow_t2_time,
        "total_spill1_m3"  : total_spill1,
        "total_spill2_m3"  : total_spill2,
        "max_h1"       : max_h1,
        "max_h2"       : max_h2,
        "max_setpt_err": max_setpt_err,
        "rmse"         : rmse,
        "steady_err"   : steady_err,
    }