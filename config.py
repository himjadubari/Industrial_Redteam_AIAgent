import os
from dotenv import load_dotenv

load_dotenv()

# ── Gemini ──────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = (
    os.getenv("GEMINI_MODEL")
    or os.getenv("GEMINI_MODEL_NAME")
    or "gemini-2.0-flash-lite"
)

# ── Tank Geometry ──────────────────────────────
TANK1_MAX_HEIGHT = 2.0
TANK2_MAX_HEIGHT = 1.5
TANK1_AREA       = 1.0
TANK2_AREA       = 0.8

# ── Nominal Flow / Valve coefficients ─────────
# CV2 tuned so Q_out=CV2*sqrt(h2) matches PID output at any typical setpoint.
# At h2=1.0m: Q_out = 0.032*1.0 = 0.032 m³/s (matches PID_OUTPUT_MAX)
INLET_FLOW_NOMINAL  = 0.02
CV1_NOMINAL         = 0.15   # wider inter-tank valve (was 0.08)
CV2_NOMINAL         = 0.032  # tuned for setpoint balance

# ── PID ────────────────────────────────────────
# FIX 2 — Kp scaled to actuator range:
#   P = Kp * err. At err=0.2m (20cm off), P = 0.05*0.2 = 0.01 m3/s — gentle ramp.
#   At err=1.0m,  P = 0.05*1.0 = 0.05 m3/s — still under PID_OUTPUT_MAX.
#   Old Kp=2.0 would redline the pump at just 4cm error (bang-bang behaviour).
# FIX 3 — Ki much lower to prevent integral windup through the 2-tank lag:
#   Old Ki=0.50 accumulated aggressively before water even reached Tank 2.
#   Ki=0.05 lets the integrator trim slowly once the level is close.
# Kd small — derivative on noisy sensor signal; keep it minimal.
PID_KP = 0.10
PID_KI = 0.05
PID_KD = 0.01
PID_OUTPUT_MAX    = 0.08     # hardware ceiling
PID_OUTPUT_LIMITS = (0.0, PID_OUTPUT_MAX)

# ── Simulation ─────────────────────────────────
SIM_DURATION   = 600         # seconds (was 300)
SIM_DT         = 1.0
SETPOINT_H2    = 0.8

# ── Adversarial Search Space ───────────────────
ATTACK_SPACE = {
    "valve1_clog"   : (0.0, 0.90),
    "valve2_clog"   : (0.0, 0.90),
    "leak_rate"     : (0.0, 0.02),
    "sensor_bias"   : (-0.3, 0.3),
    "sensor_noise"  : (0.0, 0.15),
    "inlet_surge"   : (1.0, 3.0),
}

N_OPTUNA_TRIALS = 60

# ── Failure Thresholds ─────────────────────────
OVERFLOW_PENALTY   = 1000.0
SETPOINT_TOLERANCE = 0.05