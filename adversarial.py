import optuna
from simulation import run_simulation
from config import (
    ATTACK_SPACE, N_OPTUNA_TRIALS,
    OVERFLOW_PENALTY, TANK1_MAX_HEIGHT, TANK2_MAX_HEIGHT,
)

# Silence Optuna's default verbose logging
optuna.logging.set_verbosity(optuna.logging.WARNING)


def _objective(trial: optuna.Trial, setpoint: float) -> float:
    """
    Optuna minimises this, so we return the NEGATIVE of badness.
    Higher badness = more damage to the system.
    """
    # ── Sample disturbance parameters ─────────────────────────
    params = {
        "valve1_clog"  : trial.suggest_float("valve1_clog",  *ATTACK_SPACE["valve1_clog"]),
        "valve2_clog"  : trial.suggest_float("valve2_clog",  *ATTACK_SPACE["valve2_clog"]),
        "leak_rate"    : trial.suggest_float("leak_rate",    *ATTACK_SPACE["leak_rate"]),
        "sensor_bias"  : trial.suggest_float("sensor_bias",  *ATTACK_SPACE["sensor_bias"]),
        "sensor_noise" : trial.suggest_float("sensor_noise", *ATTACK_SPACE["sensor_noise"]),
        "inlet_surge"  : trial.suggest_float("inlet_surge",  *ATTACK_SPACE["inlet_surge"]),
    }

    result = run_simulation(setpoint=setpoint, **params)

    # ── Objective: maximise damage score ──────────────────────
    damage = result["rmse"] + result["max_setpt_err"]
    if result["overflow_t1"]:
        damage += OVERFLOW_PENALTY
    if result["overflow_t2"]:
        damage += OVERFLOW_PENALTY

    return -damage   # Optuna minimises → flip sign


def run_red_team(setpoint: float, progress_callback=None) -> dict:
    """
    Run the adversarial search.

    Returns:
        worst_params  — the disturbance combo that caused most damage
        worst_result  — full simulation output for that combo
        study         — the Optuna study object (for inspection)
        all_damages   — list of damage scores per trial (for plotting)
    """
    study = optuna.create_study(
        direction="minimize",
        sampler=optuna.samplers.TPESampler(seed=0),
    )

    all_damages = []

    def _cb(study, trial):
        score = -trial.value          # flip back to positive damage
        all_damages.append(score)
        if progress_callback:
            progress_callback(len(all_damages), N_OPTUNA_TRIALS, score)

    study.optimize(
        lambda t: _objective(t, setpoint),
        n_trials=N_OPTUNA_TRIALS,
        callbacks=[_cb],
    )

    worst_params = study.best_params
    worst_result = run_simulation(setpoint=setpoint, **worst_params)

    # ── Build human-readable failure report ───────────────────
    failure_modes = []
    if worst_result["overflow_t1"]:
        failure_modes.append(
            f"TANK 1 OVERFLOW  (peak {worst_result['max_h1']:.3f} m, limit {TANK1_MAX_HEIGHT} m)"
        )
    if worst_result["overflow_t2"]:
        failure_modes.append(
            f"TANK 2 OVERFLOW  (peak {worst_result['max_h2']:.3f} m, limit {TANK2_MAX_HEIGHT} m)"
        )
    if worst_result["steady_err"] > 0.1:
        failure_modes.append(
            f"STEADY-STATE DEVIATION  ({worst_result['steady_err']:.3f} m from setpoint)"
        )
    if not failure_modes:
        failure_modes.append("Degraded performance — elevated RMSE without hard overflow")

    report = {
        "worst_params"  : worst_params,
        "worst_result"  : worst_result,
        "failure_modes" : failure_modes,
        "damage_score"  : -study.best_value,
        "all_damages"   : all_damages,
        "study"         : study,
    }
    return report
