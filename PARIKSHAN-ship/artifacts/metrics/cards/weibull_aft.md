# Model Card — Weibull AFT: time-to-commissioning

**Task:** survival analysis on `months_to_completion`, right-censored for still-ongoing projects. Project grain (one row per project), static covariates only (sector, cost_band, funding_mode, original_cost_cr, original_duration_months).

**Evaluation:** temporal split, sanctioned before 2018 = train, on/after = test — the honest simulation-of-deployment backtest (PRD §6.2.2).

| Metric | Value |
|---|---|
| Concordance index (train) | 0.9164 |
| Concordance index (test) | 0.9455 |
| n train / events | 1,250 / 1,105 |
| n test / events | 731 / 225 |

**Interpretive note, not a leakage concern:** `original_duration_months` is a legitimate at-sanction covariate, but absolute months-to-completion is mechanically dominated by a project's planned SCALE — a 200-month project takes longer in absolute terms than a 20-month one almost regardless of relative overrun risk. Concordance drops from **0.9455** to **0.7575** when that one covariate is excluded, showing how much of the headline number is "the model knows the project's size" rather than genuine risk discrimination. This is exactly why `y_time_overrun`/`time_overrun_months` (relative to plan) are the harder, more decision-relevant Phase 4 targets, not raw time-to-completion.
