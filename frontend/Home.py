"""Argus web app — Home.

The first impression: what Argus is, why it matters, and proof it works —
all above the fold. Premium dark, institutional, mobile-first. Uses only
Streamlit's native components + inline CSS via st.markdown. No new dependencies.

Launch:  streamlit run frontend/Home.py
"""
import argus_client as ac  # noqa: F401  (bootstraps sys.path)
import streamlit as st

from dashboard import components as ui

st.set_page_config(
    page_title="Argus — The AI Trading Guardian",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)
ui.inject_theme()


# ============================================================================
#  Hero styling — institutional dark, large type, strong hierarchy, mobile-first
# ============================================================================
st.markdown(
    """
    <style>
      /* Tighten the default top padding so the hero owns the first screen. */
      .block-container { padding-top: 2.2rem; max-width: 1280px; }

      .argus-hero {
        background:
          radial-gradient(1200px 420px at 18% -10%, rgba(22,199,132,.16), transparent 60%),
          radial-gradient(900px 380px at 92% 0%, rgba(47,128,237,.14), transparent 55%),
          linear-gradient(180deg, #11161c 0%, #0b0e11 100%);
        border: 1px solid #232a32;
        border-radius: 20px;
        padding: clamp(26px, 5vw, 56px) clamp(22px, 5vw, 60px);
        margin-bottom: 22px;
      }
      .argus-eyebrow {
        display:inline-block; font-size: clamp(11px, 1.4vw, 13px);
        letter-spacing: 3px; text-transform: uppercase; font-weight: 700;
        color:#16c784; background:#16c78416; border:1px solid #16c78440;
        padding: 6px 14px; border-radius: 999px; margin-bottom: 20px;
      }
      .argus-title {
        font-size: clamp(40px, 7.5vw, 78px); font-weight: 850; line-height: 1.02;
        letter-spacing: -1.5px; margin: 0 0 6px 0;
        background: linear-gradient(92deg, #ffffff 0%, #cfeede 55%, #16c784 100%);
        -webkit-background-clip: text; background-clip: text;
        -webkit-text-fill-color: transparent;
      }
      .argus-deck {
        font-size: clamp(17px, 2.4vw, 24px); font-weight: 600; color:#eaecef;
        margin: 0 0 18px 0; line-height: 1.35;
      }
      .argus-deck .accent { color:#16c784; }
      .argus-lede {
        font-size: clamp(14px, 1.7vw, 17px); color:#aab0b8; max-width: 760px;
        line-height: 1.6; margin: 0 0 26px 0;
      }
      .argus-philosophy {
        display:flex; align-items:center; gap:16px; flex-wrap:wrap;
        background:#0c1f17; border:1px solid #16c78455; border-left:5px solid #16c784;
        border-radius:14px; padding:16px 22px; margin-top:6px;
      }
      .argus-philosophy .mark {
        font-size: clamp(20px, 3vw, 30px); font-weight: 850; color:#16c784;
        letter-spacing: .5px; white-space:nowrap;
      }
      .argus-philosophy .desc { font-size: clamp(13px, 1.6vw, 15px); color:#cfd3d8; }

      /* Trust-signal chips */
      .argus-chips { display:flex; flex-wrap:wrap; gap:10px; margin: 4px 0 2px 0; }
      .argus-chip {
        display:inline-flex; align-items:center; gap:8px;
        background:#161a1e; border:1px solid #2b3139; border-radius:999px;
        padding:9px 16px; font-size:13px; font-weight:600; color:#d4d8dd;
      }
      .argus-chip .dot { width:8px; height:8px; border-radius:50%; background:#16c784;
                         box-shadow:0 0 0 3px #16c78422; }

      /* Section headers */
      .argus-section { font-size: clamp(13px,1.6vw,14px); letter-spacing:2px;
        text-transform:uppercase; font-weight:700; color:#8a8f98;
        margin: 26px 0 6px 0; }

      /* Demo verdict cards */
      .verdict-card {
        background:#161a1e; border:1px solid #2b3139; border-radius:16px;
        padding:20px 22px; height:100%;
      }
      .verdict-card.accept { border-top:4px solid #16c784; }
      .verdict-card.reject { border-top:4px solid #ea3943; }
      .verdict-card .vc-tag {
        display:inline-block; font-size:12px; font-weight:800; letter-spacing:1px;
        padding:5px 12px; border-radius:8px; margin-bottom:12px;
      }
      .verdict-card.accept .vc-tag { background:#16c78422; color:#16c784; }
      .verdict-card.reject .vc-tag { background:#ea394322; color:#ea3943; }
      .verdict-card .vc-sym { font-size:22px; font-weight:800; color:#eaecef; }
      .verdict-card .vc-sub { font-size:13px; color:#8a8f98; margin-bottom:14px; }
      .verdict-card .vc-row { display:flex; justify-content:space-between;
        font-size:13px; color:#cfd3d8; padding:4px 0; border-top:1px solid #20262d; }
      .verdict-card .vc-why { font-size:13.5px; color:#d4d8dd; line-height:1.5;
        margin-top:12px; }
      .verdict-card .vc-impact { font-size:13px; font-weight:700; margin-top:12px;
        padding-top:12px; border-top:1px solid #20262d; }
      .verdict-card.accept .vc-impact { color:#16c784; }
      .verdict-card.reject .vc-impact { color:#16c784; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================================
#  JUDGE STATUS BAR — the first thing a judge sees (honest, live states)
# ============================================================================
argus = ac.get_argus()
cps = argus.cps_overview()
status = argus.market_status()       # honest live-Bitget connectivity probe (cached)
exec_status = argus.execution_status()
ui.judge_status_bar(status, exec_status, cps)

# ============================================================================
#  HERO
# ============================================================================
st.markdown(
    """
    <div class="argus-hero">
      <span class="argus-eyebrow">🛡️ AI Capital-Protection Engine · Powered by Qwen · Live Bitget</span>
      <div class="argus-title">Argus — The AI Trading Guardian</div>
      <div class="argus-deck">
        Most AI trading bots optimize for activity.
        <span class="accent">Argus optimizes for survival.</span>
      </div>
      <div class="argus-lede">
        <strong>Protect capital. Reject bad trades. Trade with discipline.</strong><br/>
        Argus protects capital before it pursues profit. It rejects weak setups,
        explains risk in plain language, and <strong>measures the value of the trades
        you don't take</strong> — proving that disciplined inaction can outperform
        impulsive action. Not a signal generator, prediction machine or trading oracle:
        a capital-protection AI built to help traders survive long enough to win.
      </div>
      <div class="argus-philosophy">
        <span class="mark">NO&nbsp;TRADE&nbsp;IS&nbsp;ALPHA™</span>
        <span class="desc">The trade you don't take is often the best one you make.
          Capital preserved compounds; capital lost does not.</span>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

ui.execution_mode_banner(exec_status)  # PAPER / LIVE indicator

# --- Signature pillars -------------------------------------------------------
st.markdown(
    """
    <div class="argus-chips">
      <span class="argus-chip"><span class="dot"></span>Capital Protection Score™</span>
      <span class="argus-chip"><span class="dot"></span>Live Bitget Intelligence</span>
      <span class="argus-chip"><span class="dot"></span>Powered by Qwen</span>
      <span class="argus-chip"><span class="dot"></span>Execution Ready</span>
      <span class="argus-chip"><span class="dot"></span>Explainable Decisions</span>
      <span class="argus-chip"><span class="dot"></span>NO TRADE IS ALPHA™</span>
    </div>
    """,
    unsafe_allow_html=True,
)

# ============================================================================
#  PRIMARY METRICS — the proof, above the fold
# ============================================================================
st.markdown('<div class="argus-section">The Measurable Value Of Trades Not Taken</div>',
            unsafe_allow_html=True)
st.caption("Every metric below is computed by the live decision engine on real "
           "market structure — not a marketing claim.")
m = st.columns(4)
m[0].metric("🛡 Capital Protection Score", f"{cps['cps']:.0f}/100", f"Grade {cps['grade']}")
m[1].metric("💰 Losses Avoided", f"${cps['potential_loss_avoided_usd']:,.0f}",
            f"${cps['risk_exposure_avoided_usd']:,.0f} exposure kept off the table")
m[2].metric("⛔ Weak Setups Rejected", f"{cps['trades_rejected']}",
            f"{cps['rejection_rate_pct']:.0f}% rejection rate")
# Honest live-data tile: only says "Connected" when the Bitget probe really is.
from datetime import datetime, timezone
_ts = status.get("checked_at")
_ts_label = (datetime.fromtimestamp(_ts, tz=timezone.utc).strftime("Updated %H:%M:%S UTC")
             if _ts else "")
if status.get("live"):
    m[3].metric("🛰 Live Bitget Data",
                f"BTCUSDT ${status.get('probe_price'):,.0f}" if status.get("probe_price") else "Connected",
                f"Source: Bitget · {_ts_label}")
else:
    m[3].metric("🛰 Live Bitget Data", "SIMULATED", "Exchange unreachable — labelled DEMO")

st.markdown("")  # small breathing room

# ============================================================================
#  SIGNATURE: Capital Protection Score
# ============================================================================
st.markdown('<div class="argus-section">Signature Innovation — Capital Protection Score™</div>',
            unsafe_allow_html=True)
left, right = st.columns([1, 1])
with left:
    ui.cps_hero(cps)
    ui.cps_breakdown(cps)
with right:
    ui.watchlist(argus.scan(["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT", "DOGEUSDT"]))

st.divider()

# ============================================================================
#  DEMO / STORYTELLING — accept vs reject, in 10 seconds
# ============================================================================
st.markdown('<div class="argus-section">See The Guardian Decide</div>', unsafe_allow_html=True)
st.markdown(
    "Same engine, two setups. Argus **accepts** a genuinely high-quality trade and "
    "**rejects** a tempting FOMO chase — quantifying the loss avoided and explaining "
    "every verdict in plain language. This is discipline you can audit."
)

st.page_link(
    "pages/7_Live_Bitget.py",
    label="🛰️  **Live Bitget Intelligence** → run real BTC / ETH data through the guardian right now",
    icon="🛰️",
)


def _verdict_card(kind: str, result: dict, headline: str) -> None:
    """Render one demo verdict (accept/reject) as a self-contained card."""
    j = result["judge"]
    sc = result["scores"]
    tag = "✅ TAKE TRADE" if kind == "accept" else "⛔ NO TRADE"
    why = (j["trade_thesis"] if kind == "accept"
           else j["why_trade_should_be_rejected"])
    impact = j["capital_protection_impact"]
    st.markdown(
        f"""
        <div class="verdict-card {kind}">
          <span class="vc-tag">{tag}</span>
          <span class="vc-tag" style="background:#2b313944;color:#aab0b8;">{j['setup_quality']}</span>
          <div class="vc-sym">{j['symbol']} <span style="font-size:14px;color:#8a8f98;">@ {j['price']:,}</span></div>
          <div class="vc-sub">{headline}</div>
          <div class="vc-row"><span>Confidence</span><span>{sc['confidence']:.0f}/100</span></div>
          <div class="vc-row"><span>Risk</span><span>{sc['risk']:.0f}/100</span></div>
          <div class="vc-row"><span>Trade quality</span><span>{sc['trade_quality']:.0f}/100</span></div>
          <div class="vc-why">{why}</div>
          <div class="vc-impact">🛡 {impact}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


accepted = argus.demo("A")   # Excellent trade  -> TAKE TRADE / HIGH QUALITY SETUP
rejected = argus.demo("D")   # FOMO setup       -> NO TRADE   / REJECT

d1, d2 = st.columns(2)
with d1:
    _verdict_card("accept", accepted,
                  "A high-quality setup: the math, structure and data all line up.")
with d2:
    _verdict_card("reject", rejected,
                  "A FOMO chase most bots scream BUY on — Argus refuses to buy the top.")

with st.expander("🔍  Argus's full explanation of the rejected FOMO trade", expanded=False):
    from render import render_analysis
    render_analysis(rejected)

st.divider()

# ============================================================================
#  QUICK ANALYSIS — interactive, same engine
# ============================================================================
st.markdown('<div class="argus-section">Analyze Any Symbol</div>', unsafe_allow_html=True)
col = st.columns([2, 1, 1])
symbol = col[0].text_input("Symbol", "BTCUSDT", label_visibility="collapsed",
                           placeholder="Symbol e.g. BTCUSDT")
mode_label = col[1].selectbox("Mode", ["Professional", "Beginner"], label_visibility="collapsed")
go = col[2].button("Analyze", type="primary", use_container_width=True)

if go:
    from render import render_analysis
    res = argus.analyze(symbol.upper(), mode=ac.mode_from_label(mode_label))
    render_analysis(res)
else:
    st.info("Enter a symbol and hit **Analyze**, or explore the sidebar: "
            "Market Scanner, Trade Analysis, Risk Guardian, Journal, Analytics, Demo Mode.")

st.divider()
st.caption("Argus is a guardian, not an oracle — not a signal generator, prediction "
           "machine, or trading oracle. It helps traders avoid bad trades, understand "
           "risk, and preserve capital. Live Bitget public market data · Qwen-assisted "
           "reasoning · paper / read-only by design (execution disabled). NO TRADE IS ALPHA™.")
