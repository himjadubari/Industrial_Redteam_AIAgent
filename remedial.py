# ─────────────────────────────────────────────
#  remedial.py  —  Gemini Remedial Agent
#
#  Improvements applied:
#   1. "Role" passed as system_instruction (not inside user prompt)
#   2. Prompt requests Markdown tables for Corrective Actions
#   3. Priority labels [CRITICAL] / [HIGH] / [MEDIUM] on every action
#   4. Real engineering constraints baked into prompt
#   5. Guard against missing worst_result
#   6. API key + model pulled from config (env-backed), never hardcoded
# ─────────────────────────────────────────────
from google import genai
from google.genai import types
from config import GEMINI_API_KEY, GEMINI_MODEL


# ── System instruction (keeps model "in character") ────────────────────────
_SYSTEM_INSTRUCTION = """\
You are a senior process-safety and control-systems engineer with 20+ years of \
experience in liquid-level control for chemical and water-treatment plants.
You are deeply familiar with ISA-84 / IEC 61511 functional-safety standards, \
PID tuning, cascade and feedforward control, and Safety Instrumented Systems (SIS).
You communicate in precise engineering language, always citing units, \
referencing standards by clause where relevant, and organising output for \
operations and instrumentation teams to act on immediately.
"""


def _check_report(red_team_report: dict) -> bool:
    """Return True only if the report has the data we need to build a prompt."""
    return (
        red_team_report is not None
        and "worst_params"  in red_team_report
        and "worst_result"  in red_team_report
        and red_team_report["worst_result"] is not None
        and "failure_modes" in red_team_report
    )


def build_prompt(red_team_report: dict, setpoint: float) -> str:
    """
    Build the user-turn prompt.
    The 'role' context lives in system_instruction, NOT here.
    """
    if not _check_report(red_team_report):
        return (
            "The Red-Team agent did not return a valid failure report. "
            "Please describe generic best-practice remediation steps for a "
            "two-tank coupled level-control system with PID control."
        )

    p  = red_team_report["worst_params"]
    r  = red_team_report["worst_result"]
    fm = red_team_report["failure_modes"]

    lines = [
        "## Incident Report — Two-Tank Level Control System",
        "",
        "### System Constraints (nonlinear coupled-tank rig)",
        "- Tank maximum height        : 1.0 m (hard mechanical limit)",
        "- Safe operating range       : 0.2 m – 0.8 m",
        "- Overflow is a CRITICAL safety hazard (spill, pump cavitation risk)",
        "- Flow between tanks is gravity-driven (Torricelli's law — nonlinear)",
        "- Valves exhibit known nonlinearities (hysteresis, dead-band, clogging)",
        "- Sensor susceptible to bias drift and Gaussian noise",
        "",
        f"### Operating Setpoint  :  h₂ = {setpoint:.2f} m",
        "",
        "### Worst-Case Attack Parameters (found by AI adversarial search)",
        f"| Parameter          | Value                        |",
        f"|--------------------|-----------------------------|",
        f"| Valve-1 clogging   | {p['valve1_clog']*100:.1f} %              |",
        f"| Valve-2 clogging   | {p['valve2_clog']*100:.1f} %              |",
        f"| Tank-1 leak rate   | {p['leak_rate']:.5f} m³/s          |",
        f"| Sensor bias (h₂)   | {p['sensor_bias']:+.4f} m              |",
        f"| Sensor noise σ     | {p['sensor_noise']:.4f} m               |",
        f"| Inlet pump surge   | {p['inlet_surge']:.3f}×                |",
        "",
        "### Observed Failure Modes",
    ]
    for fm_item in fm:
        lines.append(f"- ❌ {fm_item}")

    lines += [
        "",
        "### Simulation Performance Metrics Under Attack",
        f"| Metric              | Value                   |",
        f"|---------------------|------------------------|",
        f"| Peak Tank-1 level   | {r['max_h1']:.3f} m               |",
        f"| Peak Tank-2 level   | {r['max_h2']:.3f} m               |",
        f"| Max setpoint error  | {r['max_setpt_err']:.3f} m               |",
        f"| RMSE               | {r['rmse']:.4f} m              |",
        f"| Tank-1 overflow?    | {'YES' if r['overflow_t1'] else 'No'}                    |",
        f"| Tank-2 overflow?    | {'YES' if r['overflow_t2'] else 'No'}                    |",
        "",
        "---",
        "## Required Output Format",
        "",
        "Produce a structured remediation report with exactly these six sections.",
        "Use Markdown headings (##, ###). Write for both operators and engineers.",
        "",
        "### 1. Root Cause Analysis",
        "Identify the primary failure mode, its coupling to secondary modes, and "
        "the nonlinear dynamics that amplified the fault.",
        "",
        "### 2. Immediate Corrective Actions",
        "Present as a Markdown table with columns: "
        "| Priority | Action | Rationale | Expected Outcome |",
        "Label each row Priority as one of: [CRITICAL], [HIGH], or [MEDIUM].",
        "Include 4-6 rows.",
        "",
        "### 3. Engineering Design Fixes",
        "Present as a Markdown table with columns: "
        "| Priority | Fix | Component Affected | Standard Reference |",
        "Include 4-5 rows with [CRITICAL] / [HIGH] / [MEDIUM] labels.",
        "",
        "### 4. Control System Tuning Recommendations",
        "Cover PID retuning (suggest specific Kp, Ki, Kd direction of change), "
        "cascade control strategy, and feedforward compensation for the inlet surge.",
        "",
        "### 5. SIS / Safety Instrumented System Recommendations",
        "Specify: recommended SIL level (per IEC 61511), required SIF architecture "
        "(e.g., 1oo2 voting), proof-test interval, and independent high-high level switch spec.",
        "",
        "### 6. Monitoring KPIs",
        "List 5-7 key process variables to trend continuously, "
        "with alarm setpoints in engineering units.",
        "",
        "Be concise but technically precise. Use engineering units throughout.",
    ]
    return "\n".join(lines)


def _make_client() -> genai.Client:
    """Instantiate the Gemini client using the env-backed API key."""
    if not GEMINI_API_KEY:
        raise EnvironmentError(
            "GEMINI_API_KEY is not set. "
            "Add it to your .env file or export it as a shell variable."
        )
    return genai.Client(api_key=GEMINI_API_KEY)


def get_remediation(red_team_report: dict, setpoint: float) -> str:
    """Non-streaming call — returns full report string."""
    client = _make_client()
    prompt = build_prompt(red_team_report, setpoint)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_INSTRUCTION,
            temperature=0.3,
        ),
    )
    return response.text


def get_remediation_stream(red_team_report: dict, setpoint: float):
    """
    Generator — yields text chunks for Streamlit streaming.
    API key is read from config (env), never passed by caller.
    """
    client = _make_client()
    prompt = build_prompt(red_team_report, setpoint)

    for chunk in client.models.generate_content_stream(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            system_instruction=_SYSTEM_INSTRUCTION,
            temperature=0.3,
        ),
    ):
        if chunk.text:
            yield chunk.text