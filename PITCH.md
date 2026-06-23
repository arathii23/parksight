# ParkSight — Pitch Deck & Demo Script

**Team:** Flipgrid.STAR (IIT Kanpur)
**Members:** Aaditya Rathi · Ankit Kumar · Priyanshi Agarwal · Shivesh Shukla
**Problem statement:** Poor Visibility on Parking-Induced Congestion
**Built on data from:** Bengaluru Traffic Police (ASTraM) · **Road geometry:** OpenStreetMap (ready for MapmyIndia drop-in)
**Live app:** https://parksight-87cceloqd3hdappsp4asjvb.streamlit.app  ·  **Code:** github.com/arathii23/parksight

> All figures below are computed from the actual dataset (292,768 Bengaluru traffic-police citations) and are reproducible from `Flipgrid.ipynb`.

---

## PART A — SLIDE-BY-SLIDE DECK (10 slides)

### Slide 1 — Title
**ParkSight**
*Parking-Induced Congestion Intelligence*
Detect illegal-parking hotspots · Quantify their traffic-flow impact · Deploy enforcement where & when it matters.

Team Flipgrid.STAR (IIT Kanpur) — Aaditya Rathi, Ankit Kumar, Priyanshi Agarwal, Shivesh Shukla

*Visual: the dark dashboard hero + the Bengaluru hotspot map.*

---

### Slide 2 — The Problem
- Illegal on-street parking is a **leading, invisible cause of urban congestion** — a single car blocking a lane throttles a whole corridor.
- Cities have **citation data but no visibility**: they can't see *where* parking actually chokes traffic, or *when*.
- Enforcement today is **reactive and untargeted** — patrols roam; hotspots recur unaddressed.

**One line:** *We can ticket parking, but we can't see its congestion footprint — so we can't fix it.*

---

### Slide 3 — The Opportunity (Why now)
- Bengaluru Traffic Police generate **rich, geocoded citation records** (292,768 in this dataset).
- That data, fused with **road geometry**, can pinpoint exactly which spots and time-windows hurt traffic most.
- Turn a passive log into an **operational, scheduled enforcement plan**.

---

### Slide 4 — Our Solution: ParkSight  (Detect → Quantify → **Predict** → Act)
A spatial–temporal decision-support system that turns raw citations into a **ranked, time-stamped enforcement plan**, with an ML risk forecast for the upcoming week.

Four questions it answers:
1. **WHERE** are the congestion-causing hotspots? → Gi* hotspot map
2. **HOW BAD** is each one for traffic? → % carriageway capacity removed (OSM road geometry)
3. **WHAT'S NEXT?** → ML ranker predicts each hotspot's high-pressure windows for the **next week** (High/Medium/Low risk)
4. **WHEN to act?** → peak day-of-week × hour for every zone, surfaced as a downloadable patrol schedule

---

### Slide 5 — How It Works (Method)
1. **Impact score per violation** = vehicle footprint × severity × time-of-day demand
2. Aggregate onto **~65 m Uber H3 hexagons** (6,805 cells)
3. **Getis-Ord Gi\*** local statistic (z-score + p-value) → statistically-significant **Critical (99%)** and **High (95%)** hotspot tiers — *not just "where there are lots of tickets," but where clustering is real*
4. **Traffic-flow anchor:** match each hotspot to its **OpenStreetMap road class / lane count** → estimate **% of carriageway capacity removed** (single-lane blockages penalised more than arterials)
5. **Gradient-boosted classifier ("the AI")** predicts per slot the **probability that a hotspot × day-of-week × hour combination will be a top-quartile congestion-impact event**. Inputs: temporal (hour, dow, weekend), seasonal climatology, and structural features (Gi\*, lane count, capacity loss, junction proximity). It is not a CCTV detector — it is a **predictive prioritisation model** for shift planning.
6. **Next-week risk forecast:** apply the classifier to every (Critical/High hotspot × 7 days × 24 hours) — **168 future slots × 505 hotspots = 84,840 predictions / week** — and aggregate to a per-hotspot **High / Medium / Low** risk tier + predicted peak window.

*Visual: pipeline arrow Citations → H3 → Gi\* → OSM capacity → ML ranker → Next-week risk forecast → Ranked plan.*

---

### Slide 6 — Key Findings (the punchline)
- **Impact is hyper-concentrated:** the **top 5% of locations carry ~60%** of all congestion impact (top 1% ≈ 30%). → *You don't need to be everywhere — just the right 5%.*
- **505 statistically-significant hotspots** (412 Critical + 93 High) cover the bulk of the problem.
- A single blocked hotspot can remove up to **98%** of a road's capacity; Critical zones average **~48%**.
- **For the upcoming week**, the ML ranker flags **169 zones as High-risk**, 168 Medium-risk, 168 Low-risk — converting analytics into a forward-looking, prioritised target list.
- **#1 hotspot: Safina Plaza Junction** — followed by Sagar Theatre, KR Market, Elite, Subbanna.

---

### Slide 7 — It maps to the problem statement
ParkSight directly surfaces the congestion contexts named in the brief:
- **Intersections:** ranked named junctions (Safina Plaza, KR Market, …)
- **Commercial areas / markets:** 9.0% of impact
- **Institutional (hospitals/schools/courts):** 5.9%
- **Transit (metro/bus/rail):** 1.2%  ·  **Events/hospitality:** 0.5%

*Visual: bar charts of top junctions + place-type shares.*

---

### Slide 8 — The Product (Demo)
Interactive dashboard with:
- **Hotspot map** (H3 cells, Critical/High tiers) + impact heatmap
- **"Where to send a patrol first"** — top zones with plain-English recommended actions & time windows
- **Time-window targeting** — pick a day/hour, see which zones light up
- **Enforcement targets** tab with ranked list + **CSV download** for field teams

*Visual: 2–3 dashboard screenshots.*

---

### Slide 9 — Rigor & Honesty (why judges should trust it)
- **Real statistics, not heuristics:** Getis-Ord Gi\* with p-values; OSM-grounded capacity loss.
- **Explicit AI role:** a gradient-boosted classifier predicts the per-slot probability of a top-quartile congestion-impact event, using temporal + spatial + road-geometry features. Output → next-week High/Medium/Low risk forecast per hotspot. Beats naive baseline by **+7% ROC-AUC** on a held-out future period.
- **Honest negative result:** plain regression does **not** beat a seasonal-naive weekly mean — the recurring weekly pattern *is* the signal. So the model is correctly framed as a **ranker** for prioritisation, not a magical time-series forecaster.
- **Transparent limitations:** enforcement data is a **proxy** (patrol selection bias); timestamps are anonymised but hour-of-day is internally consistent. Documented in-app.

**"Where exactly is the AI?" answer (for judge Q&A):**
> "Our AI is a gradient-boosted classifier that predicts the probability each hotspot × day × hour slot will be a high-pressure congestion event. We apply it to all 84,840 future slots in the upcoming week and aggregate into per-zone risk tiers and predicted peak windows. Spatial statistics identify the clusters; the ML model predicts the future enforcement-pressure within them. It's not a CCTV detector — it's a predictive prioritisation model, which is what shift planning actually needs."

---

### Slide 10 — Impact & Scalability / Close
- **Impact:** shift enforcement from reactive patrolling → **targeted, scheduled deployment**; clear the top 5% and you address most of the congestion footprint.
- **Scalable:** pipeline is city-agnostic — any city with geocoded citations + OpenStreetMap can run it; H3 + Gi\* + OSM all scale.
- **Next:** live data feed, before/after enforcement A/B, integrate camera/sensor feeds.

**Close line:** *ParkSight gives cities the missing eyes on parking-induced congestion — and tells them exactly where and when to act.*

---

## PART B — 2–3 MINUTE DEMO VIDEO SCRIPT (~430 words)

**[0:00–0:20 — Hook + problem]**
"Picture one car parked illegally on a busy Bengaluru street. It doesn't just take a spot — it removes an entire lane, and the whole corridor backs up. Cities issue thousands of parking tickets, but they have almost no visibility into which of those violations are actually choking traffic, or when. Enforcement ends up reactive and scattered. We're Team Flipgrid.STAR, and we built ParkSight to fix exactly that."

**[0:20–0:40 — What ParkSight is]**
"ParkSight turns raw traffic-police citation data into a ranked, time-stamped enforcement plan with an ML risk forecast for the upcoming week. It follows a clear pipeline: **Detect, Quantify, Predict, Act** — *where* are the congestion hotspots, *how badly* each one hurts traffic flow, *what's coming* next week, and *when* to send a patrol."

**[0:40–1:20 — How it works (show pipeline / methodology tab)]**
"We start from 292,768 real citations. Each violation gets an impact score from vehicle footprint, severity, and time-of-day demand. We aggregate onto 65-metre hexagons, then run the Getis-Ord Gi-star statistic — so we flag hotspots only where clustering is *statistically real*, not just busy. That gives 505 significant Critical and High zones. Then the key step: we match every hotspot to its actual road in OpenStreetMap and estimate the percentage of carriageway capacity it removes — a single-lane blockage is penalised far more than an arterial."

**[1:20–2:10 — Live demo (screen-record the app)]**
"Here's the dashboard. This is the hotspot map of Bengaluru — Critical zones in red. Up top, the headline: the top 5% of locations carry about 60% of all congestion impact. So we tell the city exactly where to focus. 'Where to send a patrol first' ranks the worst zones — number one is Safina Plaza Junction — each with a recommended action, a peak time window, and a **next-week risk forecast** from our ML model. Jump to Enforcement Targets — every hotspot now has a predicted risk tier and its single most likely peak hour next week — 169 zones flagged High-risk. Over here in time-window targeting, I pick a day and hour, and watch which zones light up — enforcement becomes *scheduled*, not random. And the whole ranked list downloads as a CSV for field teams."

**[2:10–2:40 — Rigor + honesty]**
"On the AI side, we were rigorous and honest. Our gradient-boosted classifier predicts the probability of a top-quartile congestion event for every hotspot × day × hour slot — and beats the naive seasonal baseline by 7% ROC-AUC on a held-out future period. We also transparently show that plain regression doesn't beat the recurring weekly pattern — because that pattern *is* the signal. So we frame the model honestly: spatial statistics find the clusters, the ML model predicts and prioritises within them. And we flag the limitation that enforcement data reflects where patrols go, not a perfect census."

**[2:40–3:00 — Impact + close]**
"ParkSight is city-agnostic — any city with geocoded citations and OpenStreetMap can run it. It shifts enforcement from reactive patrolling to targeted, scheduled deployment. Clear the top 5%, and you've addressed most of the congestion footprint. ParkSight gives cities the missing eyes on parking-induced congestion — and tells them exactly where and when to act. Thank you."

---

### Recording tips
- Keep the live demo segment as a real screen-recording of the deployed app (smooth, pre-loaded).
- Practice once to land under 3:00 — the demo block is where you can trim if needed.
- Have the app already loaded on the hotspot-map view before you hit record (avoids cold-start lag).

---

## PART C — JUDGING-CRITERIA CHEAT SHEET (for live Q&A at Flipkart HQ)

Use these one-liners when a judge presses on a specific dimension.

| Judging dimension | One-line answer |
|---|---|
| **Problem understanding** | "We answer the brief's three core questions — *detect, quantify, target* — *and* surface the four named contexts: commercial areas, metro/bus/rail, events, intersections. Each is quantified with real impact share." |
| **Solution robustness** | "Real statistics, not heuristics: Getis-Ord Gi\* with p-values for hotspot significance, OSM-grounded carriageway capacity loss, and an ML ranker validated on a **held-out future period** (+7% ROC-AUC over a seasonal-naive baseline). We also honestly report a *negative* result — plain regression doesn't beat the recurring weekly pattern — so we frame the model as a ranker, not a magic forecaster." |
| **Innovation** | "First pipeline we know of to fuse three approaches: **spatial statistics (Gi\*) + OSM road-geometry capacity-loss anchor + ML next-week per-hotspot risk forecast**. Together they shift enforcement from reactive patrolling to a forward-looking, time-resolved deployment plan." |
| **Prototype clarity** | "Live deployed dashboard with five tabs that walk the judge through Detect → Quantify → Predict → Act. Every metric is explainable in plain English in the sidebar." |
| **Scalability** | "Pipeline is city- and **map-provider-agnostic**. We run on OpenStreetMap today; a drop-in upgrade to **MapmyIndia's** proprietary lane graph requires zero model retraining. The whole pipeline runs on a standard laptop in under 20 minutes per city." |
| **Real-world viability** | "Outputs are downloadable CSV schedules at the per-hour, per-day cadence **ASTraM** already operates on. A patrol commander can read the next-week risk forecast and drop it straight into their roster. No bespoke infra required." |
| **AI / ML sophistication** | "Gradient-boosted classifier that predicts, for every hotspot × day-of-week × hour slot, the probability of a top-quartile congestion-impact event. We apply it to 84,840 future slots per week and aggregate to per-zone risk tiers + predicted peak windows. Inputs: temporal, seasonal climatology, spatial Gi\*, road geometry. **Not** a CCTV detector — a predictive prioritisation model, which is what shift planning actually needs." |
| **"Where exactly is the AI?"** | Same answer as AI/ML row above. The forecast in Enforcement Targets is the visible AI output. |
| **"What about MapmyIndia data?"** | "Our pipeline only needs a road-class + lane-count attribute per nearest road segment, so it's map-provider-agnostic. MapmyIndia's proprietary lane graph would be a drop-in upgrade with higher-resolution Indian road data — code-level swap of the geometry source." |
| **"Live traffic feeds?"** | "Out of scope tonight but architected for it: probe-vehicle or ASTraM live speed feeds would calibrate the OSM capacity-loss estimate against *observed* flow degradation. We flag this transparently as future work in the Methodology tab." |

---

## PART D — DELIVERABLES CHECKLIST

- ☑ Live app (private, going public tomorrow evening) — https://parksight-87cceloqd3hdappsp4asjvb.streamlit.app
- ☑ Source code (private repo, going public tomorrow evening) — github.com/arathii/parksight
- ☑ Submission zip — `parksight_source.zip` (900 KB, well under 50 MB limit)
- ☐ Pitch deck (build from Part A in this file)
- ☐ Demo video (record using script in Part B)
