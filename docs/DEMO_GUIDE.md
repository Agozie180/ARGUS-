# Argus — Demo Guide (Self-Guided)

A hands-on tour you can follow at your own pace. For the timed, spoken judge
walkthrough, see [`DEMO_SCRIPT.md`](DEMO_SCRIPT.md).

## Start it

```bash
pip install -r requirements.txt
streamlit run frontend/Home.py      # → http://localhost:8501
# optional API: uvicorn backend.main:app --reload → http://localhost:8000/docs
```

No API keys required — Argus runs on deterministic simulated data.

---

## 1. Dashboard (Home)

What you see:
- **Capital Protection Score™ (CPS)** — Argus' signature metric (Grade A, ~85).
  This is the headline number: value created by *avoiding* bad trades.
- **CPS breakdown** — losses avoided, exposure avoided, FOMO blocked, liquidity traps avoided.
- **Watchlist** — live decision badges across the majors.
- **Session summary** — decisions made, trades rejected, rejection rate, capital saved.

Try: type a symbol (e.g. `BTCUSDT`) → **Analyze** → read the full Judge Mode verdict.

---

## 2. Demo Mode — the heart of the demo

Run the scenarios in order and watch how Argus reasons:

| Scenario | Expected verdict | What it teaches |
|----------|------------------|-----------------|
| Excellent trade | TAKE TRADE | What a genuinely good setup looks like |
| Weak trade | WATCH | Mediocre signals aren't opportunities |
| Low-liquidity trap | REJECT | A pretty chart on a thin book is a slippage trap |
| **FOMO setup** ⭐ | **NO TRADE** | Chasing an overbought parabola is how accounts die |
| Missing data | NO TRADE | If you can't trust inputs, you can't trust the trade |
| Trend exhaustion | WATCH | Strong trends end — momentum divergence is the tell |

⭐ **The WOW moment** is the FOMO setup — see below.

---

## 3. The WOW moment

Open **Demo Mode → FOMO setup** (or `GET /wow`).

- The chart looks *great*: +40% on the week, every short-term signal green.
- Most bots would say **BUY**.
- Argus says **NO TRADE** and shows **Capital Protection Impact**: the dollars of
  downside it just avoided, plus the exact dangers caught (FOMO chase, exhausted RSI).

This is the "Argus protects traders from themselves" beat.

---

## 4. Trade Analysis — Judge Mode in full

Pick any symbol and read the complete verdict:
- Trade thesis · Market structure · Liquidity · Volatility
- Bull case / Bear case
- Confidence / Risk / Data Quality / Trade Quality meters
- Entry zone · Invalidation · Take-profit ladder
- Why it exists / could fail / should be rejected
- **Capital Protection Impact**

Toggle **Beginner ↔ Professional** to see the same verdict in plain language vs.
full technical detail.

---

## 5. Risk Guardian, Journal, Analytics

- **Risk Guardian** — position sizing, drawdown, portfolio health.
- **Journal** — every decision logged, lessons extracted, capital saved.
- **Analytics** — decision distribution, confidence-vs-risk map, CPS panel,
  Accepted / Rejected / Capital Saved / Mistakes Avoided.

---

## API quick tour

```bash
curl localhost:8000/cps                       # Capital Protection Score
curl localhost:8000/wow                        # the NO-TRADE moment
curl localhost:8000/demo/A                     # excellent trade
curl localhost:8000/scan                       # grade the universe
curl localhost:8000/journal                    # learning report (incl. live CPS)
curl -X POST localhost:8000/execute/BTCUSDT    # paper-execute (only if TAKE TRADE)
curl localhost:8000/positions                  # open + closed paper positions
```

## Executing a paper trade

On the **Trade Analysis** page, analyze a symbol Argus approves (decision
**TAKE TRADE**) and click **🚀 Execute paper trade**. The position appears on the
**Risk Guardian** page under *Paper portfolio*, where you can close it at a price
and see realized P&L plus the post-trade review. If the decision is anything
other than TAKE TRADE, Argus refuses to execute — *NO TRADE IS ALPHA™*.
