# Argus — Technical Documentation

How the guardian actually decides. Everything here is deterministic and
explainable — Argus never shows a number it can't justify.

---

## 1. The Four Meters (`core/scoring.py`)

All scores are 0–100. Each function returns a component breakdown so the UI and
Judge Mode can explain *why*.

### Data Quality — *can we trust the inputs?*

```
data_quality = 0.30·completeness
             + 0.25·freshness
             + 0.30·liquidity
             + 0.15·spread_quality        # spread_quality = 100 − spread_bps·5
```

Wide spreads, stale feeds, and missing indicators quietly poison every other
score — so they're isolated and weighted here first.

### Confidence — *how much real, aligned edge is there?*

```
confidence = 0.35·timeframe_agreement     # share of TFs agreeing on direction
           + 0.25·trend_strength_adx      # ADX/40 · 100
           + 0.15·ema_stack_bonus         # 100 if BULL/BEAR, else 40
           + 0.15·momentum                # |momentum| · 100
           + 0.10·rsi_quality             # 90 mid-band, 35 at extremes
```

Stretched RSI (≥80 or ≤20) is penalized — chasing an extreme is *not* confidence.

### Risk — *how dangerous is this trade right now?* (higher = worse)

```
risk = 0.30·volatility
     + 0.20·atr_risk                      # ATR%/5 · 100  (5% ATR = max)
     + 0.25·illiquidity_risk              # 100 − liquidity
     + 0.10·spread_risk                   # spread_bps · 5
     + 0.15·overextension                 # stretched RSI in the bias direction
```

### Trade Quality — *the composite, gated by trust*

```
base    = confidence·0.7 + (100 − risk)·0.3
quality = base · (data_quality / 100)     # DQ is a hard multiplier
```

Data quality is a **multiplier**, not an addend: a perfect-looking signal on
untrustworthy data collapses toward zero. You cannot trade what you cannot trust.

---

## 2. The Signal Honesty Engine (`core/honesty_engine.py`)

After scoring, the snapshot is run against gates. Defaults:

```python
DATA_QUALITY_FLOOR   = 55.0    # below this we are blind
LIQUIDITY_FLOOR      = 45.0    # below this slippage eats the edge
RISK_CEILING         = 78.0    # above this, no edge is worth it
CONFIDENCE_TRADE     = 70.0    # confidence needed to TAKE
CONFIDENCE_POSSIBLE  = 55.0    # confidence to call it a setup
RR_FLOOR             = 1.5     # minimum acceptable reward:risk
TRADE_QUALITY_TAKE   = 68.0    # trade-quality for HIGH QUALITY SETUP
```

**Hard fails** (any one → `NO TRADE`, grade `REJECT`):
- data quality below floor (blind)
- liquidity below floor (slippage trap)
- risk above ceiling (too dangerous)
- **FOMO chase** — LONG with RSI≥82 into ATR≥3.5% or vol≥78 (and the SHORT mirror)

**Soft fails** (→ `WATCH`):
- reward:risk below floor
- timeframe signal conflict (bullish & bearish TFs roughly balanced)
- no directional bias

**Reward:risk** is measured entry→nearest target vs entry→invalidation, falling
back to an ATR-based 2R estimate when explicit levels are missing.

### Grading ladder

```
hard_fail                                    → REJECT            → NO TRADE
soft_fail                                    → WATCH             → WATCH
TQ≥68 and conf≥70 and RR≥1.5                  → HIGH QUALITY SETUP → TAKE TRADE
conf≥55                                       → POSSIBLE SETUP    → WATCH
otherwise                                     → WATCH             → WATCH
```

### NO TRADE IS ALPHA™

When the decision is `NO TRADE`/`REJECT`, Argus estimates the capital protected:

```
exposed   = capital · 0.10               # the position it would have taken
est_loss  = exposed · (risk / 100)       # downside avoided at this risk level
```

These accumulate into the learning report so the UI can show *capital saved*.

---

## 3. Judge Mode (`core/judge.py`)

`judge()` composes scores + honesty verdict into a `JudgeReport`:

- **Levels:** entry zone (price ± ½·ATR band), invalidation (support/resistance
  or 1.5·ATR fallback), laddered take-profits at 1.5R / 3R / 5R.
- **Narrative:** thesis, bull case, bear case — each assembled from the actual
  indicator values, never templated platitudes.
- **Three honest questions:** why the trade exists, why it could fail, why it
  should be rejected.
- **Explanation:** rendered through `core/explain.py` for the requested `Mode`.

---

## 4. Domain Types (`core/models.py`)

| Type | Role |
|------|------|
| `MarketSnapshot` | Point-in-time market read consumed by every agent |
| `Scores` | The four meters + flat component breakdown |
| `RiskAssessment` | Sizing, drawdown, R:R, portfolio health |
| `JudgeReport` | The full explainable verdict returned to UI/API |
| `Direction` / `Mode` / `SetupQuality` / `FinalDecision` | Enums |

`SetupQuality ∈ {REJECT, WATCH, POSSIBLE SETUP, HIGH QUALITY SETUP}`
`FinalDecision ∈ {TAKE TRADE, WATCH, REJECT, NO TRADE}`

---

## 5. Orchestration & Services

- `agents/orchestrator.py` (class `Argus`) is the single entry point:
  `analyze()`, `scan()`, `demo()`, `wow_moment()`, `learning_report()`.
- The Streamlit UI calls the orchestrator **in-process** by default; set
  `ARGUS_API_URL` to route through the FastAPI backend instead.
- `services/market_data.py` + `services/bitget.py` provide live Bitget data when
  credentialed and **deterministic simulated data** otherwise — so tests and
  demos are reproducible.

---

## 6. Testing

`tests/` covers the honesty engine gates and a full analysis cycle.

```bash
pytest -q
```

Because scoring and the demo scenarios are deterministic, the test suite asserts
exact decision outcomes (e.g. the FOMO scenario must return `NO TRADE`).
