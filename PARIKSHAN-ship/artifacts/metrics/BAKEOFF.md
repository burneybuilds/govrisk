# PARIKSHAN — Phase 4 Bake-Off: Conventional Statistics vs. Machine Learning

**Headline:** ML significantly beat the conventional baseline on 4/5 targets, significantly lost on 0, and showed no significant difference on 1.

| Target | Task | Conventional | ML (best) | Conventional score | ML score | Bootstrap 95% CI (ML - conv) | Significant? |
|---|---|---|---|---|---|---|---|
| cost_overrun_pct | regression | ols_sector_fe | random_forest | 0.0062 | 0.5324 | [0.4868, 0.5604] | YES |
| time_overrun_months | regression | naive_sector_mean | random_forest | -0.0207 | 0.4601 | [0.4541, 0.5073] | YES |
| y_cost_overrun | classification | logistic_regression | random_forest | 0.7209 | 0.7162 | [-0.0236, 0.0141] | no |
| y_time_overrun | classification | logistic_regression | xgboost | 0.7991 | 0.8624 | [0.0505, 0.0779] | YES |
| y_severe | classification | logistic_regression | random_forest | 0.6644 | 0.7019 | [0.0128, 0.0635] | YES |

## DeLong test (ROC-AUC significance, classification targets only)

| Target | AUC (ML) | AUC (conventional) | z | p-value |
|---|---|---|---|---|
| y_cost_overrun | 0.9128 | 0.9115 | 1.054 | 0.2921 |
| y_time_overrun | 0.8295 | 0.7625 | 31.345 | 0 |
| y_severe | 0.8809 | 0.8582 | 13.314 | 0 |

## Prediction interval coverage (XGBoost quantile models, 10th-90th percentile)

| Target | Target coverage | Observed coverage (temporal test) | Mean interval width |
|---|---|---|---|
| cost_overrun_pct | 80% | 71.0% | 61.48 |
| time_overrun_months | 80% | 69.6% | 13.02 |

## Full per-family metrics

### cost_overrun_pct
| Family | r2 |
|---|---|
| random_forest | 0.5324 |
| xgboost | 0.4079 |
| lightgbm | 0.4449 |

### time_overrun_months
| Family | r2 |
|---|---|
| random_forest | 0.4601 |
| xgboost | 0.4440 |
| lightgbm | 0.4344 |

### y_cost_overrun
| Family | pr_auc |
|---|---|
| random_forest | 0.7162 |
| xgboost | 0.6763 |
| lightgbm | 0.6514 |

### y_time_overrun
| Family | pr_auc |
|---|---|
| random_forest | 0.8580 |
| xgboost | 0.8624 |
| lightgbm | 0.8608 |

### y_severe
| Family | pr_auc |
|---|---|
| random_forest | 0.7019 |
| xgboost | 0.6631 |
| lightgbm | 0.6590 |

## Calibration curves

Reliability-curve data (predicted vs. observed frequency, 10 bins) for each classification target's best ML model is cached at `artifacts/metrics/calibration_curves.json` for the Phase 6 dashboard's Model Lab screen to render.

## Plain-English verdict

- **cost_overrun_pct**: ML (**random_forest**) SIGNIFICANTLY beats the conventional baseline (**ols_sector_fe**).
- **time_overrun_months**: ML (**random_forest**) SIGNIFICANTLY beats the conventional baseline (**naive_sector_mean**).
- **y_cost_overrun**: NO statistically significant difference between ML (**random_forest**) and the conventional baseline (**logistic_regression**).
- **y_time_overrun**: ML (**xgboost**) SIGNIFICANTLY beats the conventional baseline (**logistic_regression**).
- **y_severe**: ML (**random_forest**) SIGNIFICANTLY beats the conventional baseline (**logistic_regression**).