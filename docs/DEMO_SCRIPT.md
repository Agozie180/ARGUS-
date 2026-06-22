# Argus — Judge Demo Script

A tight, repeatable walkthrough. Total runtime ~4 minutes. Every scenario is
deterministic, so it lands the same way every time.

**Setup:** `streamlit run frontend/Home.py` → open `http://localhost:8501`.
No credentials needed — Argus runs on simulated data.

---

## 0. The hook (15s)

> "Most trading bots compete to give you *more* signals. The problem is, most
> trades shouldn't be taken. Argus is an AI Trading Guardian — it's built to
> tell you when **not** to trade. Its motto: **NO TRADE IS ALPHA**."

---

## 1. Home — capital protection at a glance (30s)

- Point to the four headline metrics: decisions made, trades rejected,
  rejection rate, **capital saved**.
- "Argus treats a rejected bad trade as a *win* — and it keeps score."

---

## 2. The WOW moment — Demo Mode → FOMO setup (90s)  ⭐

This is the unforgettable beat. Open **Demo Mode → FOMO setup (Scenario D)**
(or hit `GET /wow`).

> "Here's SOLUSDT: up 40% on the week, every short-term timeframe green,
> momentum screaming. **Any normal bot flashes BUY.**"

Reveal Argus's verdict: **NO TRADE.** Read its reasoning:

- RSI **86** — exhausted, this is late-cycle chasing
- ATR **4.6%** — a normal wiggle stops you out
- Reward:risk is upside-down this late in the move

> "And here's the kicker — Argus shows the capital that decision just protected.
> **Standing aside *is* the trade.**"

---

## 3. Contrast — Demo Mode → Excellent trade (30s)

- Run **Scenario A**. Argus returns **TAKE TRADE / HIGH QUALITY SETUP**.
- "Argus isn't just cautious — when the setup is genuinely good, it says so,
  with a full thesis, entry zone, invalidation, and laddered targets."

---

## 4. The honesty engine — Demo Mode → Low-liquidity trap & Missing data (45s)

- **Scenario C (Low-liquidity trap):** pretty chart, thin book → **REJECT**.
  "A beautiful chart on no liquidity is a slippage trap."
- **Scenario E (Missing data):** "If Argus can't trust the inputs, it won't
  pretend. Data Quality drops, and it refuses to guess. It *never* fabricates
  confidence."

---

## 5. Judge Mode + Explainability (30s)

- Go to **Trade Analysis**, analyze any symbol, toggle **Beginner ↔ Professional**.
- "Every verdict comes with a bull case, a bear case, why it could fail, and why
  it might be rejected — in plain language or full technical detail. Argus
  argues *against itself* before it argues for a trade."

---

## 6. Close (15s)

> "Argus is not an oracle that predicts the future. It's a guardian that helps
> traders avoid bad trades, understand risk, and preserve capital. Most bots
> help you enter trades. **Argus helps you survive them.**"

---

### Backup: API path (if the UI misbehaves)

```bash
curl localhost:8000/wow            # the NO-TRADE moment
curl localhost:8000/demo/A         # excellent trade
curl localhost:8000/demo/C         # low-liquidity trap
curl localhost:8000/journal        # capital-saved report
```
