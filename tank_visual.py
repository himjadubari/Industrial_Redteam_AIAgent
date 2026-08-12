# ─────────────────────────────────────────────
#  tank_visual.py  —  Animated SVG tank diagram
# ─────────────────────────────────────────────
import json


def build_tank_html(result: dict, setpoint: float,
                    h1_max: float = 2.0, h2_max: float = 1.5) -> str:
    h1_data  = [round(float(v), 4) for v in result["h1"]]
    h2_data  = [round(float(v), 4) for v in result["h2"]]
    sp1_data = [round(float(v), 6) for v in result.get("spill1", [0]*len(h1_data))]
    sp2_data = [round(float(v), 6) for v in result.get("spill2", [0]*len(h2_data))]
    t_data   = [round(float(v), 1) for v in result["time"]]
    n        = len(t_data)
    sp_y     = round(196 * (1 - setpoint / h2_max), 2)  # pixel Y for setpoint line

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    background: #0a0e1a;
    font-family: 'Share Tech Mono', 'Courier New', monospace;
    color: #94a3b8;
    padding: 12px;
  }}
  .title {{ font-size: 11px; letter-spacing: 3px; color: #475569; text-transform: uppercase; margin-bottom: 10px; }}
  .stage {{ display: flex; align-items: flex-end; justify-content: center; gap: 0px; margin-bottom: 12px; }}
  .tank-wrap {{ display: flex; flex-direction: column; align-items: center; gap: 4px; }}
  .tank-label {{ font-size: 10px; letter-spacing: 2px; color: #64748b; }}
  .tank-reading {{ font-size: 13px; font-weight: bold; color: #38bdf8; min-width: 70px; text-align: center; transition: color 0.3s; }}
  .overflow-badge {{ font-size: 10px; letter-spacing: 1px; color: #ef4444; opacity: 0; transition: opacity 0.2s; text-align: center; }}
  .controls {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-top: 6px; }}
  button {{ background: #1e3a5f; border: 1px solid #38bdf8; color: #38bdf8; padding: 4px 14px;
            font-family: inherit; font-size: 11px; letter-spacing: 1px; cursor: pointer; border-radius: 3px; }}
  button:hover {{ background: #2563a8; }}
  input[type=range] {{ flex: 1; accent-color: #38bdf8; min-width: 100px; }}
  .time-display {{ font-size: 11px; color: #64748b; min-width: 55px; }}
  .spill-info {{ font-size: 10px; color: #ef4444; min-width: 80px; text-align: right; }}
</style>
</head>
<body>
<div class="title">⚙ TANK SYSTEM — LIVE ANIMATION</div>

<div class="stage">

  <!-- PUMP / INLET -->
  <div style="display:flex;flex-direction:column;align-items:center;justify-content:flex-end;padding-bottom:38px;gap:4px">
    <div style="font-size:9px;color:#475569;letter-spacing:1px">PUMP</div>
    <svg width="56" height="44" viewBox="0 0 56 44">
      <circle cx="18" cy="26" r="14" fill="#0f172a" stroke="#1e3a5f" stroke-width="1.5"/>
      <circle cx="18" cy="26" r="8" fill="#1e293b"/>
      <polygon points="18,19 24,29 12,29" fill="#38bdf8" opacity="0.8"/>
      <rect x="30" y="23" width="26" height="6" fill="#1e3a5f" rx="1"/>
    </svg>
    <div id="qin-label" style="font-size:9px;color:#38bdf8">—</div>
  </div>

  <!-- TANK 1 -->
  <div class="tank-wrap" style="margin-right:0">
    <div class="tank-label">TANK 1</div>
    <div id="reading1" class="tank-reading">0.000 m</div>
    <div id="overflow1" class="overflow-badge">⚠ OVERFLOW</div>
    <svg width="120" height="200" viewBox="0 0 120 200">
      <defs>
        <clipPath id="clip1"><rect x="8" y="2" width="104" height="194" rx="3"/></clipPath>
        <linearGradient id="wgrad1" x1="0" y1="0" x2="0" y2="1">
          <stop id="g1top" offset="0%" stop-color="#60a5fa" stop-opacity="0.9"/>
          <stop id="g1bot" offset="100%" stop-color="#1d4ed8" stop-opacity="0.95"/>
        </linearGradient>
        <pattern id="ripple1" x="0" y="0" width="20" height="6" patternUnits="userSpaceOnUse">
          <path d="M0,3 Q5,0 10,3 Q15,6 20,3" fill="none" stroke="rgba(255,255,255,0.25)" stroke-width="1"/>
        </pattern>
      </defs>
      <rect x="8" y="2" width="104" height="194" rx="4" fill="#0f172a" stroke="#1e3a5f" stroke-width="1.5"/>
      <line x1="8" y1="10" x2="112" y2="10" stroke="#ef4444" stroke-width="1" stroke-dasharray="4,3"/>
      <rect id="water1" x="9" y="196" width="102" height="0" fill="url(#wgrad1)" clip-path="url(#clip1)" rx="2"/>
      <rect id="ripple1rect" x="9" y="196" width="102" height="5" fill="url(#ripple1)" clip-path="url(#clip1)" opacity="0.6"/>
      <g id="splash1" opacity="0">
        <rect x="8" y="0" width="104" height="6" fill="#ef4444" opacity="0.4"/>
        <text x="60" y="18" text-anchor="middle" font-size="9" fill="#ef4444" font-family="monospace">OVERFLOW</text>
      </g>
      <line x1="8" y1="50"  x2="16" y2="50"  stroke="#1e3a5f" stroke-width="1"/>
      <line x1="8" y1="98"  x2="16" y2="98"  stroke="#1e3a5f" stroke-width="1"/>
      <line x1="8" y1="146" x2="16" y2="146" stroke="#1e3a5f" stroke-width="1"/>
      <text x="18" y="53"  font-size="7" fill="#334155" font-family="monospace">{h1_max*0.75:.1f}m</text>
      <text x="18" y="101" font-size="7" fill="#334155" font-family="monospace">{h1_max*0.50:.1f}m</text>
      <text x="18" y="149" font-size="7" fill="#334155" font-family="monospace">{h1_max*0.25:.1f}m</text>
      <text x="18" y="197" font-size="7" fill="#334155" font-family="monospace">0.0m</text>
      <text x="65" y="9"   font-size="7" fill="#ef4444" font-family="monospace">MAX {h1_max}m</text>
    </svg>
  </div>

  <!-- CONNECTING PIPE T1→T2 -->
  <div style="display:flex;flex-direction:column;justify-content:flex-end;padding-bottom:26px;width:60px">
    <svg width="60" height="60" viewBox="0 0 60 60">
      <rect x="0" y="22" width="60" height="10" fill="#1e293b" stroke="#1e3a5f" stroke-width="1" rx="2"/>
      <polygon id="arrow12" points="28,27 38,22 38,32" fill="#fbbf24" opacity="0.8"/>
      <text x="30" y="18" text-anchor="middle" font-size="7" fill="#64748b" font-family="monospace">Q₁₂</text>
    </svg>
    <div id="q12-label" style="font-size:9px;color:#fbbf24;text-align:center;margin-top:2px">—</div>
  </div>

  <!-- TANK 2 -->
  <div class="tank-wrap">
    <div class="tank-label">TANK 2 <span style="color:#22d3ee;font-size:9px">[CV]</span></div>
    <div id="reading2" class="tank-reading">0.000 m</div>
    <div id="overflow2" class="overflow-badge">⚠ OVERFLOW</div>
    <svg width="120" height="200" viewBox="0 0 120 200">
      <defs>
        <clipPath id="clip2"><rect x="8" y="2" width="104" height="194" rx="3"/></clipPath>
        <linearGradient id="wgrad2" x1="0" y1="0" x2="0" y2="1">
          <stop id="g2top" offset="0%" stop-color="#a78bfa" stop-opacity="0.9"/>
          <stop id="g2bot" offset="100%" stop-color="#6d28d9" stop-opacity="0.95"/>
        </linearGradient>
        <pattern id="ripple2" x="0" y="0" width="20" height="6" patternUnits="userSpaceOnUse">
          <path d="M0,3 Q5,0 10,3 Q15,6 20,3" fill="none" stroke="rgba(255,255,255,0.25)" stroke-width="1"/>
        </pattern>
      </defs>
      <rect x="8" y="2" width="104" height="194" rx="4" fill="#0f172a" stroke="#1e3a5f" stroke-width="1.5"/>
      <line x1="8" y1="7" x2="112" y2="7" stroke="#ef4444" stroke-width="1" stroke-dasharray="4,3"/>
      <!-- setpoint line — updated dynamically via JS -->
      <line id="spline2" x1="8" y1="{2 + sp_y}" x2="112" y2="{2 + sp_y}" stroke="#22d3ee" stroke-width="1.5" stroke-dasharray="3,3"/>
      <rect id="water2" x="9" y="196" width="102" height="0" fill="url(#wgrad2)" clip-path="url(#clip2)" rx="2"/>
      <rect id="ripple2rect" x="9" y="196" width="102" height="5" fill="url(#ripple2)" clip-path="url(#clip2)" opacity="0.6"/>
      <g id="splash2" opacity="0">
        <rect x="8" y="0" width="104" height="6" fill="#ef4444" opacity="0.4"/>
        <text x="60" y="18" text-anchor="middle" font-size="9" fill="#ef4444" font-family="monospace">OVERFLOW</text>
      </g>
      <line x1="8" y1="50"  x2="16" y2="50"  stroke="#1e3a5f" stroke-width="1"/>
      <line x1="8" y1="98"  x2="16" y2="98"  stroke="#1e3a5f" stroke-width="1"/>
      <line x1="8" y1="146" x2="16" y2="146" stroke="#1e3a5f" stroke-width="1"/>
      <text x="18" y="53"  font-size="7" fill="#334155" font-family="monospace">{h2_max*0.75:.1f}m</text>
      <text x="18" y="101" font-size="7" fill="#334155" font-family="monospace">{h2_max*0.50:.1f}m</text>
      <text x="18" y="149" font-size="7" fill="#334155" font-family="monospace">{h2_max*0.25:.1f}m</text>
      <text x="18" y="197" font-size="7" fill="#334155" font-family="monospace">0.0m</text>
      <text x="65" y="6"   font-size="7" fill="#ef4444" font-family="monospace">MAX {h2_max}m</text>
      <text x="14" y="{max(2 + sp_y - 2, 10)}" font-size="7" fill="#22d3ee" font-family="monospace">SP={setpoint:.2f}m</text>
    </svg>
  </div>

  <!-- OUTLET PIPE -->
  <div style="display:flex;flex-direction:column;justify-content:flex-end;padding-bottom:26px;width:50px">
    <svg width="50" height="60" viewBox="0 0 50 60">
      <rect x="0" y="22" width="50" height="10" fill="#1e293b" stroke="#1e3a5f" stroke-width="1" rx="2"/>
      <polygon points="22,27 32,22 32,32" fill="#f87171" opacity="0.8"/>
      <text x="25" y="18" text-anchor="middle" font-size="7" fill="#64748b" font-family="monospace">Q_out</text>
    </svg>
    <div id="qout-label" style="font-size:9px;color:#f87171;text-align:center;margin-top:2px">—</div>
  </div>

  <!-- DRAIN -->
  <div style="display:flex;flex-direction:column;align-items:center;justify-content:flex-end;padding-bottom:30px">
    <svg width="30" height="30" viewBox="0 0 30 30">
      <circle cx="15" cy="15" r="13" fill="#0f172a" stroke="#334155" stroke-width="1.5"/>
      <line x1="9" y1="9" x2="21" y2="21" stroke="#475569" stroke-width="1.5"/>
      <line x1="21" y1="9" x2="9" y2="21" stroke="#475569" stroke-width="1.5"/>
      <circle cx="15" cy="15" r="4" fill="#1e293b" stroke="#475569" stroke-width="1"/>
    </svg>
    <div style="font-size:8px;color:#334155;letter-spacing:1px">DRAIN</div>
  </div>

</div>

<!-- CONTROLS -->
<div class="controls">
  <button id="playbtn" onclick="togglePlay()">▶ PLAY</button>
  <input type="range" id="scrub" min="0" max="{n-1}" value="0" oninput="seekTo(parseInt(this.value))"/>
  <div class="time-display" id="timelabel">t = 0 s</div>
  <div class="spill-info" id="spilllabel"></div>
</div>

<script>
const H1 = {json.dumps(h1_data)};
const H2 = {json.dumps(h2_data)};
const SP1 = {json.dumps(sp1_data)};
const SP2 = {json.dumps(sp2_data)};
const T   = {json.dumps(t_data)};
const H1MAX = {h1_max};
const H2MAX = {h2_max};
const SP    = {setpoint};
const N     = {n};

const SVG_H = 194;

// Pre-compute cumulative spill
const cumSpill1 = [], cumSpill2 = [];
let cs1=0, cs2=0;
for(let i=0;i<N;i++){{ cs1+=SP1[i]; cumSpill1.push(cs1); cs2+=SP2[i]; cumSpill2.push(cs2); }}

function levelToY(h, hmax) {{
  return Math.max(0, Math.min(SVG_H, SVG_H * (1 - h / hmax)));
}}

function applyColor(gradTop, gradBot, h, hmax) {{
  const r = h / hmax;
  if (r >= 0.98) {{ gradTop.setAttribute('stop-color','#ef4444'); gradBot.setAttribute('stop-color','#991b1b'); }}
  else if (r >= 0.80) {{ gradTop.setAttribute('stop-color','#fb923c'); gradBot.setAttribute('stop-color','#c2410c'); }}
  else if (r >= 0.60) {{ gradTop.setAttribute('stop-color','#facc15'); gradBot.setAttribute('stop-color','#92400e'); }}
  // else keep default (set at init)
}}

function resetColor(gradTop, gradBot, isT1) {{
  if(isT1) {{ gradTop.setAttribute('stop-color','#60a5fa'); gradBot.setAttribute('stop-color','#1d4ed8'); }}
  else     {{ gradTop.setAttribute('stop-color','#a78bfa'); gradBot.setAttribute('stop-color','#6d28d9'); }}
}}

function updateFrame(idx) {{
  const h1 = H1[idx], h2 = H2[idx];
  const sp1 = SP1[idx] > 0, sp2 = SP2[idx] > 0;

  // ── Tank 1 ──
  const y1 = levelToY(h1, H1MAX);
  const ht1 = Math.max(0, SVG_H - y1);
  document.getElementById('water1').setAttribute('y',      2 + y1);
  document.getElementById('water1').setAttribute('height', ht1);
  document.getElementById('ripple1rect').setAttribute('y', 2 + y1 - 3);

  const g1t = document.getElementById('g1top'), g1b = document.getElementById('g1bot');
  resetColor(g1t, g1b, true);
  applyColor(g1t, g1b, h1, H1MAX);

  document.getElementById('reading1').textContent = h1.toFixed(3)+' m';
  document.getElementById('reading1').style.color = sp1 ? '#ef4444' : (h1/H1MAX>0.8 ? '#fb923c' : '#38bdf8');
  document.getElementById('splash1').setAttribute('opacity', sp1 ? '1' : '0');
  document.getElementById('overflow1').style.opacity = sp1 ? '1' : '0';

  // ── Tank 2 ──
  const y2 = levelToY(h2, H2MAX);
  const ht2 = Math.max(0, SVG_H - y2);
  document.getElementById('water2').setAttribute('y',      2 + y2);
  document.getElementById('water2').setAttribute('height', ht2);
  document.getElementById('ripple2rect').setAttribute('y', 2 + y2 - 3);

  const g2t = document.getElementById('g2top'), g2b = document.getElementById('g2bot');
  resetColor(g2t, g2b, false);
  applyColor(g2t, g2b, h2, H2MAX);

  // Setpoint line — moves with SP (computed dynamically)
  const spY = 2 + SVG_H * (1 - SP / H2MAX);
  document.getElementById('spline2').setAttribute('y1', spY);
  document.getElementById('spline2').setAttribute('y2', spY);

  document.getElementById('reading2').textContent = h2.toFixed(3)+' m';
  document.getElementById('reading2').style.color = sp2 ? '#ef4444' : (h2/H2MAX>0.8 ? '#fb923c' : '#a78bfa');
  document.getElementById('splash2').setAttribute('opacity', sp2 ? '1' : '0');
  document.getElementById('overflow2').style.opacity = sp2 ? '1' : '0';

  // ── Labels ──
  document.getElementById('timelabel').textContent = 't = '+T[idx].toFixed(0)+' s';
  document.getElementById('scrub').value = idx;

  const c1v = cumSpill1[idx], c2v = cumSpill2[idx];
  document.getElementById('spilllabel').textContent =
    (c1v>0.0001||c2v>0.0001) ? 'Spill T1:'+c1v.toFixed(3)+'m³  T2:'+c2v.toFixed(3)+'m³' : '';
}}

// ── Animation loop ──
let frame = 0, playing = false, raf = null, lastTs = 0;
const FPS = 30;

function animate(ts) {{
  if(ts - lastTs > 1000/FPS) {{
    updateFrame(frame);
    frame++;
    if(frame >= N) {{ frame = N-1; stopPlay(); return; }}
    lastTs = ts;
  }}
  if(playing) raf = requestAnimationFrame(animate);
}}

function togglePlay() {{
  playing ? stopPlay() : startPlay();
}}
function startPlay() {{
  if(frame >= N-1) frame = 0;
  playing = true;
  document.getElementById('playbtn').textContent = '⏸ PAUSE';
  raf = requestAnimationFrame(animate);
}}
function stopPlay() {{
  playing = false;
  if(raf) cancelAnimationFrame(raf);
  document.getElementById('playbtn').textContent = '▶ PLAY';
}}
function seekTo(idx) {{ frame = idx; updateFrame(idx); }}

updateFrame(0);
</script>
</body>
</html>"""
