# PARIKSHAN — 5-Minute Demo Script

A beat-by-beat run sheet for demoing the live system. Every number below was
pulled from the actual cached artifacts at the time this was written (see
each beat) — say them with confidence, and if a live number differs slightly
after a re-run, that's expected (the underlying data/models weren't
regenerated between writing this and demo day) — don't panic, just narrate
what's on screen.

**Before you start:** `streamlit run src/paimana/app/Home.py`, and — for the
LLM assistant beat — `ollama serve` running in the background with
`qwen2.5:7b-instruct` pulled (`ollama list` to confirm). If Ollama isn't
running, the assistant still works via the deterministic fallback — that's
a deliberate feature, not a failure, and worth calling out if it happens.

---

## 0. The one-sentence pitch (30s)

> "PAIMANA tracks 1,981 infrastructure projects over ₹150 crore. Today it can
> tell you a project is *already* late or over budget. PARIKSHAN tells you
> it's *about to be* — weeks or quarters before anyone would otherwise
> notice — and explains why, in plain language, entirely offline."

Say clearly, once, up front: **the dataset is synthetic**, generated to match
published PAIMANA aggregate statistics (not a real CUF export — none is
public in ML-ready form). Every screen repeats this; it's not something to
downplay.

---

## 1. Portfolio Overview (45s)

Open the app (defaults to this screen).

Point at the KPI tiles and say the real numbers:
- **1,981 projects**, **₹21.3 lakh crore** total approved outlay
- **585 projects (29.5%) flagged at risk** (Amber or Red band)
- Risk-band split: **1,396 Green / 473 Amber / 112 Red**
- Average predicted cost overrun across the portfolio: **19.5%**

Point at the sector risk heatmap and state breakdown — this is the same data
the LLM assistant will narrate later, so it's worth the audience seeing the
ground truth on screen first.

---

## 2. Early Warning Centre (45s)

Click through to the alert queue.

- **265 Critical-severity alerts** are currently open portfolio-wide.
- Filter by severity, show the reason codes and recommended actions columns
  — these come from SHAP explanations, not templated text.
- Click one alert's project to show the drill-down link into Deep-Dive.

Message: this isn't a black-box score — every alert says *why*, in terms an
official can act on ("reconcile disbursed funds against verified physical
progress").

---

## 3. Project Deep-Dive (45s)

Pick a Red-band project (or use the one just clicked through from the alert
queue).

- Predicted-vs-approved cost chart with the uncertainty band.
- Risk trajectory over time, colour-banded Green/Amber/Red.
- SHAP waterfall — point at the top 2-3 contributing features.
- Delay-reason timeline.

Message: this is what a single project's story looks like when the system
flags it — not just a score, a narrative.

---

## 4. Model Lab — the rigour slide (45s)

This is the screen for anyone who asks "why should I trust an ML model over
what MoSPI already does?"

Say the honest headline, not a marketing one:
- For **cost overrun magnitude** (regression): ML (Random Forest) reaches
  **R²=0.53** vs. a sector-fixed-effects OLS baseline's **R²=0.006** — a
  bootstrap 95% CI of **[0.49, 0.56]** on the R² gap, clearly excluding zero.
- For **time overrun magnitude**: ML reaches **R²=0.46** vs. a naive
  sector-mean baseline's **R²=-0.02** — CI **[0.45, 0.51]**.
- For **binary cost-overrun classification**, ML did **not** significantly
  beat logistic regression (PR-AUC 0.716 vs. 0.721 — a bootstrap CI of
  **[-0.024, 0.014] that includes zero**). **Say this one out loud, plainly**
  — it's the honest negative result the methodology is built to surface, not
  hide.
- For **severe-overrun classification**, ML (Random Forest) *did*
  significantly beat logistic regression (PR-AUC 0.702 vs. 0.664, CI
  **[0.013, 0.064]**, excludes zero).

Message: the system reports wins **and** non-wins from the same rigorous
bootstrap methodology — that honesty is the point, not a weakness to
minimize.

---

## 5. LLM Assistant (60-90s) — the finale

Go to the Assistant tab. Ask, live, in this order:

1. **"How many projects are at risk?"** → expect ~1,981 projects, 585 at
   risk. Point out the tool name shown under the answer (`portfolio_summary`)
   and open the raw-data expander — the number wasn't computed by the LLM,
   it was handed to it.
2. **"What is the riskiest sector?"** → Shipping & Ports, mean risk score
   35.7.
3. **"How early would we have caught eventual severe overruns?"** → out of
   237 eventually-severe projects historically, 206 were flagged by at least
   one signal, with a median lead time of **18 quarters** — 193 of those
   early enough (≥4 quarters ahead) to actually act on, for a recall of
   **81.4%** at that threshold. This is the money slide: retrospectively,
   the system would have given officials years of runway, not weeks.

**Then, live, kill Ollama** (`Ctrl+C` on the `ollama serve` terminal, or
`taskkill /IM ollama.exe /F`) and ask a 4th question — the screen keeps
answering, now via the deterministic fallback template, with **identical
numbers**, clearly labelled "📋 Deterministic fallback" instead of "🤖
Ollama." This is the anti-hallucination architecture made visible: the
prose narrator can die and the numbers never change.

---

## 6. Close (15s)

> "Every number in this demo traces back to a pandas computation the LLM
> never touched. It's honest about what it doesn't know — a null result on
> cost-overrun classification, an unverified calibration anchor — and it
> runs entirely on this laptop, no API key, no cloud, no bill."

Point at the synthetic-data banner one more time before ending — repetition
here is a feature of the demo, not an oversight.
