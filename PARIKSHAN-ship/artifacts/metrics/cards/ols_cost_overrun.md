# Model Card — OLS: log(cost ratio) ~ sector fixed effects

**Task:** regression, target `cost_overrun_pct` (via `log(1 + cost_overrun_pct/100)`)

**Scope:** sector fixed effects ONLY (PRD §6.3) — a simple, interpretable conventional baseline, not the full feature set. Evaluated out-of-fold via GroupKFold(project_id, n_splits=5); the summary table below is a full-sample in-sample fit for interpretability, not the evaluation.

**Out-of-fold R2 (original scale):** 0.0062
**Out-of-fold MAE:** 47.66 pp

**Note on back-transformation:** predictions are back-transformed from log-scale using Duan's (1983) smearing estimator (mean of exp(training-fold residuals)), not a plain `exp()`. A plain exp() back-transform is biased downward by Jensen's inequality and, uncorrected, made this model score WORSE than the naive sector-mean baseline it should beat — not because sector carries no signal, but purely from retransformation bias. Fixed during Phase 3; see HANDOFF.md.

**Honest read of the R2 itself:** it is small (a few tenths of a percent to ~3% in-sample). Sector alone is a genuinely weak predictor of an individual project's cost overrun in this dataset — by design (PRD §4.3.5), most of the variance is project- and agency-level idiosyncratic risk, not sector membership. This is the correct, PRD-scoped conventional baseline (sector fixed effects only); the fairer full-feature-set conventional comparison against Phase 4's ML models is the logistic regression cards below, not this one.

**Caveat:** fit only on completed (non-censored) projects — cost_overrun_pct is undefined for still-executing projects. If completed projects are systematically different from ongoing ones (e.g. faster-moving, lower-risk), this is a selection effect worth keeping in mind when interpreting the coefficients below.

## statsmodels summary (full-sample fit)

```
                            OLS Regression Results                            
==============================================================================
Dep. Variable:         log_cost_ratio   R-squared:                       0.032
Model:                            OLS   Adj. R-squared:                  0.032
Method:                 Least Squares   F-statistic:                     54.93
Date:                Sat, 12 Sep 2026   Prob (F-statistic):          4.67e-227
Time:                        14:27:17   Log-Likelihood:                -17785.
No. Observations:               34414   AIC:                         3.561e+04
Df Residuals:                   34392   BIC:                         3.580e+04
Df Model:                          21                                         
Covariance Type:            nonrobust                                         
===========================================================================================================
                                              coef    std err          t      P>|t|      [0.025      0.975]
-----------------------------------------------------------------------------------------------------------
Intercept                                   0.1201      0.007     16.477      0.000       0.106       0.134
C(sector)[T.Road Transport & Highways]     -0.0855      0.009     -9.166      0.000      -0.104      -0.067
C(sector)[T.Petroleum]                     -0.1401      0.013    -10.820      0.000      -0.166      -0.115
C(sector)[T.Power]                         -0.0100      0.010     -0.969      0.333      -0.030       0.010
C(sector)[T.Coal]                          -0.0199      0.013     -1.503      0.133      -0.046       0.006
C(sector)[T.Atomic Energy]                 -0.0101      0.021     -0.475      0.635      -0.052       0.032
C(sector)[T.Civil Aviation]                 0.0135      0.014      0.963      0.335      -0.014       0.041
C(sector)[T.Telecommunications]            -0.0093      0.012     -0.748      0.454      -0.034       0.015
C(sector)[T.Steel]                         -0.1619      0.014    -11.167      0.000      -0.190      -0.133
C(sector)[T.Mines]                         -0.0790      0.015     -5.415      0.000      -0.108      -0.050
C(sector)[T.Shipping & Ports]               0.0884      0.013      6.834      0.000       0.063       0.114
C(sector)[T.Water Resources]               -0.0192      0.011     -1.705      0.088      -0.041       0.003
C(sector)[T.Health & Family Welfare]       -0.1388      0.014     -9.720      0.000      -0.167      -0.111
C(sector)[T.Urban Development]             -0.1556      0.011    -13.767      0.000      -0.178      -0.133
C(sector)[T.Fertilizers]                    0.0252      0.013      1.894      0.058      -0.001       0.051
C(sector)[T.Chemicals & Petrochemicals]     0.0149      0.016      0.933      0.351      -0.016       0.046
C(sector)[T.Heavy Industries]              -0.1937      0.013    -14.747      0.000      -0.219      -0.168
C(sector)[T.Defence]                       -0.1724      0.013    -13.716      0.000      -0.197      -0.148
C(sector)[T.Higher Education]              -0.0608      0.015     -4.148      0.000      -0.089      -0.032
C(sector)[T.Information & Broadcasting]    -0.0573      0.017     -3.348      0.001      -0.091      -0.024
C(sector)[T.Textiles]                       0.0110      0.018      0.619      0.536      -0.024       0.046
C(sector)[T.Food & Public Distribution]    -0.1621      0.015    -10.638      0.000      -0.192      -0.132
==============================================================================
Omnibus:                    17208.851   Durbin-Watson:                   0.073
Prob(Omnibus):                  0.000   Jarque-Bera (JB):            85622.228
Skew:                           2.504   Prob(JB):                         0.00
Kurtosis:                       8.884   Cond. No.                         17.1
==============================================================================

Notes:
[1] Standard Errors assume that the covariance matrix of the errors is correctly specified.
```
