# Model Card — Logistic Regression: y_severe

**Task:** binary classification, L2-regularised, FULL feature set (37 columns after encoding) — a genuine conventional-ML competitor to Phase 4's tree ensembles, not a sector-only toy.

**Evaluation:** out-of-fold via GroupKFold(project_id, n_splits=5).

| Metric | Value |
|---|---|
| PR-AUC | 0.6644 |
| ROC-AUC | 0.8582 |
| Brier score | 0.1111 |
| F1 @ best threshold (0.320) | 0.6111 |
| Base rate | 0.2078 |
| n | 34,414 |
