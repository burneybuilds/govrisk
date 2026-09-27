# Model Card — Cox Proportional Hazards: time-to-commissioning

**Task:** survival analysis on `months_to_completion`, right-censored for still-ongoing projects. Project grain (one row per project), static covariates only (sector, cost_band, funding_mode, original_cost_cr, original_duration_months).

**Evaluation:** temporal split, sanctioned before 2018 = train, on/after = test — the honest simulation-of-deployment backtest (PRD §6.2.2).

| Metric | Value |
|---|---|
| Concordance index (train) | 0.9170 |
| Concordance index (test) | 0.9469 |
| n train / events | 1,250 / 1,105 |
| n test / events | 731 / 225 |
