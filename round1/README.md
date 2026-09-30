# Round 1 — Traffic Demand Forecasting

Predict traffic demand for a given location and time. The score is `max(0, 100 × R²)`.

## Final model

CatBoost and XGBoost are trained with 5-fold out-of-fold predictions. A Bayesian Ridge model combines those predictions. The target is trained as `log1p(demand)` and clipped at zero after `expm1`.

Out-of-fold **R² = 0.9589** (about 95.89 local score).

## Files

| File | What it is |
| --- | --- |
| `Team_Flipgrid_Code.ipynb` | Final training notebook |
| `Team_Flipgrid_Approach.pdf` | Written approach |
| `research_stacking_submission.csv` | Test predictions (`Index`, `demand`), 41,778 rows |
