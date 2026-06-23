# ParkSight — Parking-Induced Congestion Intelligence
Detects illegal-parking hotspots and quantifies their congestion impact from Bengaluru traffic-police
citation data, to enable proactive, targeted enforcement.

## Approach
- Per-violation impact = vehicle footprint × violation severity × time-of-day demand
- Aggregated on ~65 m Uber H3 hexagons (resolution 10)
- **Real Getis-Ord Gi\*** local statistic (z-score + p-value) → significant Critical/High hotspot tiers
- **Traffic-flow anchor:** each hotspot matched to its OpenStreetMap road class / lane count to estimate
  **% carriageway capacity removed** (single-lane blockages penalised more than arterials)
- Two validations on a temporal split: (1) regression does **not** beat the seasonal-naive weekly mean —
  the recurring pattern is the signal; (2) a gradient-boosted **high-pressure ranker** that adds spatial (Gi\*)
  and road-geometry features **beats** the naive ranker (+~6% ROC-AUC) for prioritisation

## Run locally
1. `pip install -r requirements.txt`
2. `streamlit run app.py`

The app only reads the small pre-computed files in `data/` (`dashboard_cells.csv`, `dashboard_cell_time.csv`,
`violation_summary.csv`, `vehicle_summary.csv`, `model_eval.json`, `kpis.json`).

## Pipeline (`Flipgrid.ipynb`)
Cell 0 EDA → Cell 1 clean + feature-engineer (`master_tickets.csv`) → Cell 2 aggregate + initial tiers →
Cell 3 regression benchmark → Cells 4–5 summaries + location/junction enrichment →
**Cell 6 Getis-Ord Gi\*** → **Cell 7 OSM capacity loss** → **Cell 8 gradient-boosted ranker** → Cell 9 exports.