# ⚠️ Process Safety Console

An adversarial AI stress-testing platform for two-tank process control systems, with a P&ID intelligence analyser powered by Gemini Vision.

Built as a research and educational tool demonstrating how AI can be used both to **attack** and **defend** industrial control systems — aligned with ISA-84 / IEC 61511 process safety standards.

---

## 🎬 What It Does

The app has three tabs:

### ⚙️ Tab 1 — Two-Tank Red Team Console
A digital twin of a two-tank liquid level control system is simulated using SciPy ODEs with a PID controller. An adversarial AI agent (Optuna TPE sampler) stress-tests the system by searching for the worst-case combination of faults — valve clogging, sensor bias, pump surges, and leaks — that causes overflow or setpoint deviation. A Gemini remedial agent then streams a full ISA-84 aligned engineering remediation report.

### 🏭 Tab 2 — P&ID Intelligence Analyser
Upload any Piping & Instrumentation Diagram (PNG, JPEG, TIFF, PDF). Gemini Vision reads the diagram and generates structured engineering insights across five analysis modes: Full Review, Failure Mode Analysis, SIS/Safety Gaps, Control Loop Inventory, and Instrumentation Audit. Output includes prioritised findings with `[CRITICAL]` / `[HIGH]` / `[MEDIUM]` / `[LOW]` labels and downloadable Markdown reports.

### ☢️ Tab 3 — Chaos Panel
A live fault injection simulator. Slide disturbance parameters in real time and watch the PID controller respond. Includes a disturbance rejection scoring system (Gold / Silver / Bronze) and plain-English explanations of what each fault does to the control loop.

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────┐
│                   app.py                        │
│         Streamlit Unified Dashboard             │
│   Tab 1: Red Team │ Tab 2: P&ID │ Tab 3: Chaos  │
└────────┬──────────┴──────┬──────┴───────────────┘
         │                 │
    ┌────▼─────┐     ┌─────▼──────┐
    │simulation│     │pid_analyser│
    │  .py     │     │   .py      │
    │ (SciPy)  │     │(Gemini     │
    │  + PID   │     │ Vision)    │
    └────┬─────┘     └────────────┘
         │
    ┌────▼──────┐    ┌────────────┐    ┌──────────┐
    │adversarial│    │ remedial   │    │tank_     │
    │   .py     │    │   .py      │    │visual.py │
    │ (Optuna)  │    │ (Gemini)   │    │(SVG anim)│
    └───────────┘    └────────────┘    └──────────┘
         │                 │
    ┌────▼─────────────────▼──────────┐
    │            config.py            │
    │   Tank dims · PID gains ·       │
    │   Attack space · .env loader    │
    └─────────────────────────────────┘
```

---

## 📁 File Structure

```
two_tank_redteam/
│
├── app.py              # Streamlit dashboard — unified 3-tab UI
├── simulation.py       # SciPy digital twin with physical overflow clamping
├── adversarial.py      # Optuna TPE adversarial search agent
├── remedial.py         # Gemini remediation report generator
├── pid_analyser.py     # Gemini Vision P&ID analysis engine
├── tank_visual.py      # Animated SVG two-tank visualiser (HTML)
├── config.py           # All constants — loads .env via python-dotenv
│
├── .env.example        # Template — copy to .env and add your API key
├── requirements.txt    # Python dependencies
└── README.md
```

---

## ⚙️ Tech Stack

| Component | Library | Role |
|---|---|---|
| Physics Engine | `scipy` + `numpy` | Euler ODE integration for tank dynamics |
| PID Controller | `simple-pid` | Controls inlet pump to track setpoint |
| Adversarial Agent | `optuna` | TPE sampler — finds worst-case fault combo |
| Remedial Agent | `google-genai` | Streams ISA-84 engineering report |
| P&ID Vision | `google-genai` | Multimodal analysis of uploaded diagrams |
| Dashboard | `streamlit` | Web UI with live charts and animated tanks |
| Charts | `plotly` | Interactive time-series, tornado, importance charts |
| Data | `pandas` | Top-5 attack tables, comparison tables |

---

## 🚀 Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/process-safety-console.git
cd process-safety-console
```

### 2. Install dependencies

```bash
pip install streamlit scipy optuna simple-pid plotly pandas numpy google-genai python-dotenv
```

### 3. Set up your API key

```bash
cp .env.example .env
```

Open `.env` and fill in your Gemini API key:

```dotenv
GEMINI_API_KEY=AIza...your_key_here
GEMINI_MODEL_NAME=gemini-2.0-flash-lite
```

Get a free key at [aistudio.google.com](https://aistudio.google.com) → **Get API Key**.

### 4. Run the app

```bash
streamlit run app.py
```

The app opens automatically at `http://localhost:8501`.

---

## 🔬 How the Red Team Works

The adversarial agent (Optuna TPE sampler) explores a 6-dimensional fault space:

| Parameter | Range | What It Simulates |
|---|---|---|
| `valve1_clog` | 0 – 90% | Inter-tank valve mechanical degradation |
| `valve2_clog` | 0 – 90% | Outlet valve blockage |
| `leak_rate` | 0 – 0.02 m³/s | Uncontrolled drain from Tank 1 |
| `sensor_bias` | ±0.30 m | Sensor calibration drift |
| `sensor_noise` | 0 – 0.15 m σ | Measurement noise / interference |
| `inlet_surge` | 1× – 3× | Pump runaway / actuator fault |

**Objective:** maximise `RMSE + max_setpoint_error + 1000 × (overflow events)`

The worst-case parameter set is then fed to Gemini, which generates a structured remediation report covering root cause analysis, corrective actions, SIS recommendations, and monitoring KPIs.

---

## 🏭 Physics Model

The two-tank system follows Torricelli's law (gravity-driven flow):

```
dh₁/dt = (Q_in − Q₁₂ − leak) / A₁
dh₂/dt = (Q₁₂ − Q_out)       / A₂

Q₁₂  = CV₁ · √max(h₁ − h₂, 0)     [inter-tank flow]
Q_out = CV₂ · √max(h₂, 0)           [outlet flow]
```

**Overflow is physically modelled** — once a tank reaches its maximum height, excess water spills out and the level stays at the rim. Spill volume is tracked in m³.

| Parameter | Value |
|---|---|
| Tank 1 max height | 2.0 m |
| Tank 2 max height | 1.5 m |
| Tank 1 area (A₁) | 1.0 m² |
| Tank 2 area (A₂) | 0.8 m² |
| CV₁ (inter-tank valve) | 0.08 m³/s/√m |
| CV₂ (outlet valve) | 0.035 m³/s/√m |
| PID output limits | 0 – 0.032 m³/s |

---

## 🛡️ P&ID Analysis Modes

| Mode | What Gemini Analyses |
|---|---|
| 🔍 Full Review | Equipment inventory, control loops, flow summary, concerns |
| ⚠️ Failure Modes | Single points of failure, valve fail positions, utility failures |
| 🛡️ SIS Gaps | ISA-84 compliance, missing SIFs, common-cause failures, SIL targets |
| 🔄 Control Loops | Full loop register, cascade/feedforward structures, interlock logic |
| 📡 Instrumentation | Sensor coverage, alarm gaps, redundancy audit |

All outputs use `[CRITICAL]` / `[HIGH]` / `[MEDIUM]` / `[LOW]` priority labels and can be downloaded as Markdown.

---

## 🗝️ Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `GEMINI_API_KEY` | ✅ Yes | — | Your Google Gemini API key |
| `GEMINI_MODEL` or `GEMINI_MODEL_NAME` | No | `gemini-2.0-flash-lite` | Gemini model to use |

---

## ⚠️ Rate Limits

The free Gemini tier has daily and per-minute quotas. If you hit a `429 RESOURCE_EXHAUSTED` error:

- Switch to `gemini-2.0-flash-lite` in your `.env` (higher free quota)
- Wait 15–60 seconds and retry
- Or enable billing at [aistudio.google.com](https://aistudio.google.com) for higher limits

---

## 📖 Standards Referenced

- **ISA-84 / IEC 61511** — Functional Safety: Safety Instrumented Systems
- **ISA 5.1** — Instrumentation Symbols and Identification
- **ISO 10628** — Flow diagrams for process plants
- **HAZOP** — Hazard and Operability Study methodology
- **LOPA** — Layer of Protection Analysis

---

## 🧪 Project Context

This project was built as a demonstration of:

1. **Adversarial AI for process safety** — using optimisation to find failure modes before they happen in real plants
2. **Multimodal AI for engineering** — applying vision-language models to interpret industrial diagrams
3. **AI-assisted HAZOP** — automating preliminary hazard identification from P&IDs

It is intended for educational and research purposes. For real SIS design, always consult a certified functional safety engineer.

---

## 📄 License

MIT License — free to use, modify, and distribute with attribution.
