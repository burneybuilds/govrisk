# Model Card — Logistic Regression: y_cost_overrun

**Task:** binary classification, L2-regularised, FULL feature set (37 columns after encoding) — a genuine conventional-ML competitor to Phase 4's tree ensembles, not a sector-only toy.

**Evaluation:** out-of-fold via GroupKFold(project_id, n_splits=5).

| Metric | Value |
|---|---|
| PR-AUC | 0.7209 |
| ROC-AUC | 0.9115 |
| Brier score | 0.0826 |
| F1 @ best threshold (0.304) | 0.6557 |
| Base rate | 0.1709 |
| n | 34,414 |
