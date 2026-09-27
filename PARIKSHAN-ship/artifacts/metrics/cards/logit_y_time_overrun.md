# Model Card — Logistic Regression: y_time_overrun

**Task:** binary classification, L2-regularised, FULL feature set (37 columns after encoding) — a genuine conventional-ML competitor to Phase 4's tree ensembles, not a sector-only toy.

**Evaluation:** out-of-fold via GroupKFold(project_id, n_splits=5).

| Metric | Value |
|---|---|
| PR-AUC | 0.7991 |
| ROC-AUC | 0.7625 |
| Brier score | 0.2001 |
| F1 @ best threshold (0.279) | 0.7437 |
| Base rate | 0.5436 |
| n | 34,414 |
