import os, json
import streamlit as st
import pandas as pd, numpy as np
import pydeck as pdk, altair as alt

# Cohesive chart styling: transparent background + readable light text on the dark theme
@alt.theme.register("parksight", enable=True)
def _parksight_theme():
    ink, grid = "#c9cdd6", "rgba(255,255,255,0.08)"
    return {"config": {
        "background": "transparent",
        "view": {"stroke": "transparent"},
        "axis": {"labelColor": ink, "titleColor": ink, "gridColor": grid,
                 "domainColor": "rgba(255,255,255,0.18)", "tickColor": "rgba(255,255,255,0.18)",
                 "labelFontSize": 11, "titleFontSize": 12, "titleFontWeight": 600},
        "legend": {"labelColor": ink, "titleColor": ink},
        "title": {"color": "#e8e8e8", "fontSize": 13},
    }}

st.set_page_config(page_title="ParkSight — Parking-Congestion Intelligence", page_icon="🅿️",
                   layout="wide", initial_sidebar_state="expanded")
DATA_DIR = "data"
DAY_ORDER = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
PERIOD = "November 2023 – April 2024"
SOURCE = "Bengaluru Traffic Police on-street parking enforcement"
TIER_COLOR = {"CRITICAL":[176,58,46,205], "HIGH":[214,137,16,170], "NORMAL":[120,130,140,70]}

def _swatch(rgb, label):
    return (f"<span style='display:inline-flex;align-items:center;margin-right:16px;'>"
            f"<span style='width:12px;height:12px;border-radius:3px;margin-right:6px;"
            f"background:rgb({rgb[0]},{rgb[1]},{rgb[2]});'></span>{label}</span>")

def tier_legend():
    return ("<div style='font-size:0.9rem;margin:2px 0 8px;'>"
            + _swatch(TIER_COLOR["CRITICAL"], "Critical &nbsp;<span style='opacity:.7'>(99% Gi*)</span>")
            + _swatch(TIER_COLOR["HIGH"], "High &nbsp;<span style='opacity:.7'>(95% Gi*)</span>")
            + _swatch(TIER_COLOR["NORMAL"], "Normal")
            + "</div>")

@st.cache_data
def load():
    cells = pd.read_csv(os.path.join(DATA_DIR,"dashboard_cells.csv"))
    ct    = pd.read_csv(os.path.join(DATA_DIR,"dashboard_cell_time.csv"))
    opt = {}
    try: opt["model_eval.json"] = json.load(open(os.path.join(DATA_DIR,"model_eval.json")))
    except Exception: opt["model_eval.json"] = {}
    for n in ("violation_summary.csv","vehicle_summary.csv","junction_summary.csv","context_summary.csv"):
        try: opt[n] = pd.read_csv(os.path.join(DATA_DIR,n))
        except Exception: opt[n] = None
    return cells, ct, opt

try:
    cells, ct, opt = load()
except FileNotFoundError:
    st.error("Place dashboard_cells.csv and dashboard_cell_time.csv inside a data/ folder next to app.py."); st.stop()

# graceful fallbacks if an enrichment step wasn't run
if "location_name" not in cells.columns: cells["location_name"] = "(unnamed segment)"
if "near_junction" not in cells.columns: cells["near_junction"] = False
if "capacity_loss_pct" not in cells.columns: cells["capacity_loss_pct"] = np.nan
if "road_class" not in cells.columns: cells["road_class"] = "n/a"
if "gi_z" not in cells.columns: cells["gi_z"] = np.nan
cells["place"] = cells["location_name"].astype(str).str.split(",").str[:2].str.join(",").str.strip()
cells["fill_color"] = cells["tier"].map(TIER_COLOR)
cells["w_heat"] = np.sqrt(cells["total_impact"].clip(lower=0))
ev = opt["model_eval.json"]

# derived stats
s = cells["total_impact"].sort_values(ascending=False).reset_index(drop=True)
cum_impact = (s.cumsum()/s.sum()).values
top5_share = cum_impact[min(max(int(len(s)*0.05),1)-1, len(s)-1)]*100
hourly = ct.groupby("hour")["impact"].sum().reindex(range(24), fill_value=0)
busiest_hour = int(hourly.idxmax())
busiest_day = ct.groupby("dow")["impact"].sum().reindex(DAY_ORDER).fillna(0).idxmax()
crit_jx = 100*cells.loc[cells.tier=="CRITICAL","near_junction"].mean() if cells["near_junction"].any() else None
crit_caploss = cells.loc[cells.tier=="CRITICAL","capacity_loss_pct"].mean()

# default map framing: open centred on the impact-weighted hotspot cluster (Critical+High), with safe fallbacks
_disp = cells[cells.tier.isin(["CRITICAL","HIGH"])]
_disp = _disp if len(_disp) else cells
_wc = _disp["total_impact"].clip(lower=0)
MAP_LAT = float((_disp.lat*_wc).sum()/_wc.sum()) if _wc.sum() else 12.97
MAP_LON = float((_disp.lon*_wc).sum()/_wc.sum()) if _wc.sum() else 77.59

# extra in-app insights (no reprocessing needed)
PEAK_HOURS = [8,9,10,11,17,18,19,20]
peak_share = 100*ct.loc[ct.hour.isin(PEAK_HOURS),"impact"].sum()/max(ct["impact"].sum(),1)
approved_overall = (100*(cells["approved_share"]*cells["tickets"]).sum()/max(cells["tickets"].sum(),1)
                    if "approved_share" in cells.columns else None)
vio_sum, veh_sum = opt["violation_summary.csv"], opt["vehicle_summary.csv"]
junc_sum, ctx_sum = opt["junction_summary.csv"], opt["context_summary.csv"]
top_violation_name = vio_sum.iloc[0]["primary_violation"].title() if vio_sum is not None and len(vio_sum) else "—"
top_vehicle_name   = veh_sum.iloc[0]["veh"].title() if veh_sum is not None and len(veh_sum) else "—"
top_junction_name  = str(junc_sum.iloc[0]["junction"]) if junc_sum is not None and len(junc_sum) else None

# ---- Appearance / theme ----
THEMES = {
    "Civic Red": {"accent": "#e2483d", "basemap": "Light"},
    "Midnight":  {"accent": "#6aa8ff", "basemap": "Dark"},
    "Teal":      {"accent": "#0ea5a4", "basemap": "Streets"},
    "Amber":     {"accent": "#f59e0b", "basemap": "Light"},
    "Forest":    {"accent": "#34d399", "basemap": "Streets"},
}
BASEMAP_URL = {
    "Light":   "https://basemaps.cartocdn.com/gl/positron-gl-style/style.json",
    "Dark":    "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json",
    "Streets": "https://basemaps.cartocdn.com/gl/voyager-gl-style/style.json",
}
st.sidebar.header("Appearance")
theme_name = st.sidebar.selectbox("Theme", list(THEMES), index=0,
    help="Recolours the dashboard accent and switches the map basemap.")
ACCENT = THEMES[theme_name]["accent"]
basemap_choice = st.sidebar.radio("Map basemap", list(BASEMAP_URL),
    index=list(BASEMAP_URL).index(THEMES[theme_name]["basemap"]), horizontal=True)
BASEMAP = BASEMAP_URL[basemap_choice]
st.markdown(f"""<style>
.block-container {{ padding-top: 2.2rem; max-width: 1280px; }}
[data-testid="stMetric"] {{ background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08);
  border-left: 4px solid {ACCENT}; border-radius: 10px; padding: 10px 14px; transition: border-color .15s ease; }}
[data-testid="stMetric"]:hover {{ border-color: rgba(255,255,255,0.18); }}
[data-testid="stMetricValue"] {{ font-size: 1.55rem; }}
[data-testid="stMetricLabel"] {{ opacity: 0.85; }}
section[data-testid="stSidebar"] {{ border-right: 1px solid rgba(255,255,255,0.06); }}
.stTabs [data-baseweb="tab-list"] {{ gap: 30px; border-bottom: 1px solid rgba(255,255,255,0.10); margin-bottom: 16px; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 600; font-size: 1.03rem; padding: 12px 2px; letter-spacing: 0.005em; }}
.stTabs [data-baseweb="tab"]:hover {{ color: rgba(255,255,255,0.92); }}
.stTabs [aria-selected="true"] {{ color: {ACCENT} !important; }}
.stTabs [data-baseweb="tab-highlight"] {{ background-color: {ACCENT}; height: 3px; border-radius: 3px; }}
[data-testid="stExpander"] details {{ border-radius: 10px; border-color: rgba(255,255,255,0.08); }}
[data-testid="stVerticalBlockBorderWrapper"] {{ border-radius: 10px; }}
hr {{ margin: 0.7rem 0; border-color: rgba(255,255,255,0.08); }}
h1, h2, h3, h4, h5 {{ letter-spacing: -0.01em; }}
a {{ color: {ACCENT}; }}
</style>""", unsafe_allow_html=True)

st.markdown(
    f"<h1 style='margin-bottom:0;'>ParkSight</h1>"
    f"<div style='font-size:1.18rem; font-weight:600; margin:2px 0 0;'>Parking-Induced Congestion Intelligence</div>"
    f"<div style='color:{ACCENT}; font-weight:600; font-size:0.98rem; margin:3px 0 8px;'>"
    f"Detect illegal-parking hotspots · Quantify their traffic-flow impact · Deploy enforcement where &amp; when it matters</div>",
    unsafe_allow_html=True)
st.markdown("A spatial–temporal decision-support system that turns on-street parking-enforcement records into a "
            "prioritised, time-resolved map of congestion-impact hotspots — shifting enforcement from reactive "
            "patrolling to targeted, scheduled deployment.")
st.caption(f"Source: {SOURCE}  ·  Period: {PERIOD}  ·  {int(cells.tickets.sum()):,} citations  ·  "
           f"{len(cells):,} analysis cells (~65 m H3)  ·  Bengaluru")

k = st.columns(5)
k[0].metric("Citations analysed", f"{int(cells.tickets.sum()):,}")
k[1].metric("Critical hotspot zones", int((cells.tier=="CRITICAL").sum()))
k[2].metric("Top 5% of cells (by impact)", f"{top5_share:.0f}% of impact")
k[3].metric("Mean capacity loss (Critical)", f"{crit_caploss:.0f}%" if pd.notna(crit_caploss) else "n/a",
            help="Estimated share of carriageway capacity removed at a Critical cell, from OSM road class × vehicle footprint × junction spillback.")
k[4].metric("Aggregate peak window", f"{busiest_day}, {busiest_hour:02d}:00")

st.sidebar.header("Map controls")
map_mode = st.sidebar.radio("Map style", ["Hotspot cells (H3)","Impact heatmap"], index=0)
tiers = st.sidebar.multiselect("Tiers to display", ["CRITICAL","HIGH","NORMAL"], default=["CRITICAL","HIGH"])
mapdf = cells[cells.tier.isin(tiers)] if tiers else cells
with st.sidebar.expander("How to read this", expanded=False):
    st.markdown(
        "- **Critical / High** — statistically significant impact clusters (Getis-Ord Gi\\*).\n"
        "- **Impact** — vehicle footprint × violation severity × time-of-day demand.\n"
        "- **Capacity loss** — estimated % of carriageway a parked vehicle blocks, from OSM lane counts.\n"
        "- **Enforcement targets** — the deployable, time-stamped patrol schedule.")
st.sidebar.divider()
st.sidebar.caption("**Team Flipgrid.STAR** (IIT Kanpur)\n\n"
                   "Aaditya Rathi · Ankit Kumar · Priyanshi Agarwal · Shivesh Shukla")

tab_o, tab_s, tab_t, tab_e, tab_m = st.tabs(
    ["Overview","Spatial distribution","Temporal demand","Enforcement targets","Methodology & validation"])

with tab_o:
    _tot = int(cells.tickets.sum()); _ncrit = int((cells.tier=="CRITICAL").sum())
    _maxcap = cells["capacity_loss_pct"].max()
    st.markdown(
        f"<div style='border-left:5px solid {ACCENT}; background:rgba(127,127,127,0.09); "
        f"padding:14px 18px; border-radius:8px; margin-bottom:10px;'>"
        f"<b>Executive summary.</b> ParkSight turns <b>{_tot:,}</b> parking citations into a ranked, time-stamped "
        f"enforcement plan. Congestion impact is highly concentrated — the <b>top 5% of locations carry "
        f"{top5_share:.0f}%</b> of it — so just <b>{_ncrit} Critical zones</b> (statistically significant clusters) "
        f"cover most of the problem. A single blocked hotspot can remove up to "
        f"<b>{_maxcap:.0f}% of a carriageway's capacity</b>; ParkSight pinpoints <b>where and when</b> to act.</div>",
        unsafe_allow_html=True)

    st.markdown("##### How it works")
    cstep = st.columns(3)
    steps = [
        ("1  ·  Detect",    "Find statistically significant illegal-parking hotspots across the city (Getis-Ord Gi\\*)."),
        ("2  ·  Quantify",  "Estimate the road capacity each hotspot removes, from real OpenStreetMap lane geometry."),
        ("3  ·  Prioritise","Output a ranked, time-stamped patrol schedule — exactly where and when to act."),
    ]
    for col,(t,d) in zip(cstep, steps):
        with col.container(border=True):
            st.markdown(f"**{t}**"); st.caption(d)

    st.markdown("##### Where to send a patrol first")
    top3 = cells.sort_values("total_impact", ascending=False).head(3)
    for i, (_, r) in enumerate(top3.iterrows(), 1):
        cap = f"~{r['capacity_loss_pct']:.0f}% capacity loss" if pd.notna(r['capacity_loss_pct']) else "high impact"
        window = f"{r['peak_dow']} {int(r['peak_hour']):02d}:00–{int(r['peak_hour'])+1:02d}:00"
        jx = bool(r.get("near_junction", False))
        action = ("Station a patrol **" + window + "**"
                  + (" and keep the junction approach clear to stop spillback" if jx else " to clear the corridor") + ".")
        with st.container(border=True):
            st.markdown(f"**{i}. {r['place']}** — {str(r['top_violation']).title()}  ·  est. **{cap}**  ·  peak **{window}**")
            st.caption(f"↳ Recommended action: {action}")
    st.caption("Full ranked list, live time-window targeting and CSV downloads are in the **Enforcement targets** tab.")

    st.markdown("##### Why targeting works")
    lor = pd.DataFrame({"cum_cells_pct": np.arange(1,len(s)+1)/len(s)*100, "cum_impact_pct": cum_impact*100})
    area = alt.Chart(lor).mark_area(opacity=0.5, color=ACCENT).encode(
        x=alt.X("cum_cells_pct:Q", title="Cumulative share of locations (%)"),
        y=alt.Y("cum_impact_pct:Q", title="Cumulative share of impact (%)"))
    diag = alt.Chart(pd.DataFrame({"x":[0,100],"y":[0,100]})).mark_line(strokeDash=[4,4], color="gray").encode(x="x", y="y")
    st.altair_chart(area+diag, width='stretch')
    st.caption(f"The top **5%** of locations carry **{top5_share:.0f}%** of all congestion impact — so a small team can cover most of the problem.")

    with st.expander("Dataset at a glance"):
        g = st.columns(4)
        g[0].metric("Citations", f"{int(cells.tickets.sum()):,}")
        g[1].metric("Peak-hour share", f"{peak_share:.0f}%", help="Share of impact in the 08–11 and 17–20 windows.")
        g[2].metric("Top violation", top_violation_name)
        g[3].metric("Top vehicle", top_vehicle_name)
        st.caption(f"Source: {SOURCE} · {PERIOD} · Bengaluru. "
                   + (f"~{approved_overall:.0f}% of citations are validated-approved; " if approved_overall is not None else "")
                   + "the remainder are unvalidated or rejected — rankings are best re-checked on the approved subset (see Methodology).")

    with st.expander("How this maps to the problem statement"):
        st.markdown(
            "- **Detect illegal-parking hotspots** — spatial map + Critical/High tiers (*Spatial distribution*).\n"
            "- **Chokes carriageways & intersections** — hotspots are ranked against real OSM road geometry and the "
            "named-junction field, surfacing the worst **intersections, commercial areas, transit & event** clusters "
            "(*Spatial distribution → intersections & place types*).\n"
            "- **Quantify impact on traffic flow** — a blocked lane is converted to an estimated **% of carriageway "
            "capacity removed** (OSM road class × lane count × vehicle footprint, amplified at junctions for spillback), "
            "on top of an impact score (vehicle footprint × violation severity × time-of-day demand) (*Methodology*).\n"
            "- **Prioritise enforcement zones** — a ranked, downloadable patrol schedule (*Enforcement targets*).\n"
            "- **Reactive → proactive** — the validated recurring weekly pattern drives scheduled deployment (*Temporal demand*).\n"
            "- **Scales beyond Bengaluru** — the pipeline is city-agnostic: any city with geocoded parking citations + "
            "OpenStreetMap runs it unchanged, no model retraining required.")
        wknd = busiest_day in ("Saturday","Sunday")
        peak_note = ("a **weekend-morning** peak (market/commercial activity, not the weekday commute)" if wknd
                     else "aligned with the weekday commute on commercial corridors")
        jx_line = (f" Around **{crit_jx:.0f}%** of Critical zones sit at or beside a mapped intersection." if crit_jx is not None else "")
        jname_line = (f" The single worst intersection is **{top_junction_name}**." if top_junction_name else "")
        st.markdown(f"**Key findings.** Impact is highly concentrated (top 5% → {top5_share:.0f}%); pressure peaks "
                    f"**{busiest_day} ~{busiest_hour:02d}:00** — {peak_note}; **{int((cells.tier=='CRITICAL').sum())}** Critical zones."
                    + jname_line
                    + jx_line)

with tab_s:
    st.subheader("Spatial distribution of congestion impact")
    st.caption("Use the sidebar to switch between a smooth impact heatmap and discrete ~65 m hotspot cells, and to filter by tier.")
    if map_mode == "Impact heatmap":
        layer = pdk.Layer("HeatmapLayer", mapdf, get_position="[lon, lat]",
                          get_weight="w_heat", radius_pixels=45, aggregation="SUM"); tooltip=None
    else:
        layer = pdk.Layer("H3HexagonLayer", mapdf, get_hexagon="h3", get_fill_color="fill_color",
                          pickable=True, extruded=False, stroked=True, filled=True, opacity=0.55)
        tooltip = {"html":"<b>{place}</b><br/><b>Impact:</b> {total_impact}<br/><b>Citations:</b> {tickets}"
                          "<br/><b>Dominant violation:</b> {top_violation}"
                          "<br/><b>Road:</b> {road_class} · <b>Est. capacity loss:</b> {capacity_loss_pct}%"
                          "<br/><b>Gi* z-score:</b> {gi_z}"
                          "<br/><b>Recurring peak:</b> {peak_dow} {peak_hour}:00<br/><b>Tier:</b> {tier}"}
    st.pydeck_chart(pdk.Deck(layers=[layer],
        initial_view_state=pdk.ViewState(latitude=MAP_LAT, longitude=MAP_LON, zoom=10.7, pitch=0),
        map_style=BASEMAP, tooltip=tooltip))
    if map_mode == "Impact heatmap":
        st.caption("Warmer colour = higher congestion-impact density. Switch to **Hotspot cells (H3)** in the sidebar for clickable, tier-coded zones.")
    else:
        st.markdown(tier_legend(), unsafe_allow_html=True)
        st.caption("Each hexagon is a ~65 m zone, coloured by significance tier. Click a cell for its road class, capacity loss, Gi\\* score and recurring peak.")
    with st.expander("What this map does and doesn't show"):
        st.markdown("This map shows enforcement-**observed** pressure — *where* officers issue citations — which is a "
                    "**proxy** for, not a direct measurement of, where illegal parking is actually worst. Patrol-based "
                    "enforcement carries spatial selection bias: a lightly-patrolled street can look quiet even if "
                    "violations are common (see Methodology → Limitations).")
    st.subheader("Hotspot tier composition")
    tier_sum = (cells.groupby("tier").agg(cells=("h3","count"), citations=("tickets","sum"),
                impact=("total_impact","sum")).reindex(["CRITICAL","HIGH","NORMAL"]).reset_index())
    tier_sum["share"] = 100*tier_sum.impact/tier_sum.impact.sum()
    st.dataframe(pd.DataFrame({
        "Tier": tier_sum.tier, "Cells": tier_sum.cells.map("{:,}".format),
        "Citations": tier_sum.citations.map("{:,}".format),
        "Total impact": tier_sum.impact.map("{:,.0f}".format),
        "Impact share": tier_sum.share.map("{:.1f}%".format)}),
        width='stretch', hide_index=True)
    st.caption("Tiers rank cells by *statistically significant local concentration* (Getis-Ord Gi\\*), which differs slightly from a cell's own raw impact.")

    if junc_sum is not None or ctx_sum is not None:
        st.divider()
        st.subheader("Where congestion concentrates: intersections & place types")
        st.caption("Tying hotspots back to the problem statement — illegal parking that chokes **intersections** and "
                   "clusters near **commercial areas, transit and events**.")
        jc1, jc2 = st.columns([3, 2])
        if junc_sum is not None and len(junc_sum):
            with jc1:
                st.markdown("**Top congestion intersections** — named Bengaluru Traffic Police junctions")
                topj = junc_sum.head(10)
                st.altair_chart(alt.Chart(topj).mark_bar(color=ACCENT).encode(
                    x=alt.X("impact:Q", title="Total congestion impact"),
                    y=alt.Y("junction:N", sort="-x", title=""),
                    tooltip=[alt.Tooltip("junction:N", title="junction"),
                             alt.Tooltip("impact:Q", title="impact", format=",.0f"),
                             alt.Tooltip("tickets:Q", title="citations", format=",")]
                    ).properties(height=300), width='stretch')
        if ctx_sum is not None and len(ctx_sum):
            with jc2:
                st.markdown("**Impact by place type**")
                st.altair_chart(alt.Chart(ctx_sum).mark_bar(color="#7f8c8d").encode(
                    x=alt.X("impact_share:Q", title="Share of impact (%)"),
                    y=alt.Y("context:N", sort="-x", title=""),
                    tooltip=[alt.Tooltip("context:N", title="place type"),
                             alt.Tooltip("impact_share:Q", title="impact share %", format=".1f"),
                             alt.Tooltip("tickets:Q", title="citations", format=",")]
                    ).properties(height=300), width='stretch')
        st.caption("Place type is inferred from the citation address text, so the commercial / transit / event shares are a "
                   "**lower bound** (many addresses don't name the nearby POI). Intersection ranking uses the dataset's "
                   "structured junction field — *“No Junction”* records are excluded.")

    vio, veh = opt["violation_summary.csv"], opt["vehicle_summary.csv"]
    if vio is not None or veh is not None:
        st.divider()
        st.subheader("What drives the impact")
        st.caption("Which violation types and vehicle classes contribute most to total congestion impact.")
        d1, d2 = st.columns(2)
        if vio is not None:
            with d1:
                st.markdown("**By violation type**")
                st.altair_chart(alt.Chart(vio.head(8)).mark_bar(color=ACCENT).encode(
                    x=alt.X("impact:Q", title="Total impact"), y=alt.Y("primary_violation:N", sort="-x", title="")
                    ).properties(height=260), width='stretch')
        if veh is not None:
            with d2:
                st.markdown("**By vehicle class**")
                st.altair_chart(alt.Chart(veh.head(8)).mark_bar(color="#7f8c8d").encode(
                    x=alt.X("impact:Q", title="Total impact"), y=alt.Y("veh:N", sort="-x", title="")
                    ).properties(height=260), width='stretch')

with tab_t:
    st.subheader("Recurring weekly demand profile")
    st.caption("When is parking pressure recorded? Hour-of-day reflects citation/enforcement timing "
               "(morning-concentrated, and corroborated by the record's modify timestamp — see Methodology). "
               "These stable weekly patterns are what make proactive scheduling possible.")
    full = pd.MultiIndex.from_product([DAY_ORDER, range(24)], names=["dow","hour"]).to_frame(index=False)
    piv = full.merge(ct.groupby(["dow","hour"])["impact"].sum().reset_index(), on=["dow","hour"], how="left").fillna({"impact":0})
    st.altair_chart(alt.Chart(piv).mark_rect().encode(
        x=alt.X("hour:O", title="Hour of day"), y=alt.Y("dow:O", sort=DAY_ORDER, title=""),
        color=alt.Color("impact:Q", scale=alt.Scale(scheme="reds"), legend=alt.Legend(title="Impact")),
        tooltip=["dow","hour", alt.Tooltip("impact:Q", format=",.0f")]).properties(height=240), width='stretch')
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Hourly impact (city-wide)**")
        hr = hourly.reset_index(); hr.columns=["hour","impact"]
        st.altair_chart(alt.Chart(hr).mark_area(opacity=0.6, color=ACCENT).encode(
            x=alt.X("hour:O", title="Hour"), y=alt.Y("impact:Q", title="Impact")).properties(height=240), width='stretch')
    with c2:
        st.markdown("**Weekday vs weekend (mean per day)**")
        prof = ct.groupby(["dow","hour"])["impact"].sum().reset_index()
        prof["Day type"] = np.where(prof.dow.isin(["Saturday","Sunday"]),"Weekend","Weekday")
        prof2 = prof.groupby(["Day type","hour"])["impact"].mean().reset_index()
        st.altair_chart(alt.Chart(prof2).mark_line(point=True).encode(
            x=alt.X("hour:O", title="Hour"), y=alt.Y("impact:Q", title="Mean impact"),
            color=alt.Color("Day type:N", scale=alt.Scale(range=[ACCENT,"#1f77b4"]))).properties(height=240), width='stretch')

with tab_e:
    st.subheader("Recommended enforcement schedule")
    st.caption("The prioritised, deployable output: the highest-impact zones with the recurring window when each is worst. "
               "Download it as a patrol worklist.")
    sched = cells[cells.tier.isin(["CRITICAL","HIGH"])].sort_values("total_impact", ascending=False).head(30).reset_index(drop=True)
    sched["priority"] = sched.index + 1
    sched["recommended window"] = sched.apply(lambda r: f"{r.peak_dow} {int(r.peak_hour):02d}:00–{int(r.peak_hour)+1:02d}:00", axis=1)
    sched["map"] = sched.apply(lambda r: f"https://www.google.com/maps?q={r.lat:.5f},{r.lon:.5f}", axis=1)
    sched_view = sched[["priority","place","tier","total_impact","capacity_loss_pct","road_class","top_violation","recommended window","map"]]
    st.dataframe(sched_view, width='stretch', hide_index=True,
        column_config={"place": st.column_config.TextColumn("location"),
                       "total_impact": st.column_config.NumberColumn("impact", format="%.0f"),
                       "capacity_loss_pct": st.column_config.NumberColumn("est. capacity loss", format="%.0f%%"),
                       "road_class": st.column_config.TextColumn("road class"),
                       "top_violation": st.column_config.TextColumn("dominant violation"),
                       "map": st.column_config.LinkColumn("map", display_text="view")})
    st.download_button("Download enforcement schedule (CSV)",
        sched_view.to_csv(index=False), "enforcement_schedule.csv", "text/csv")

    st.divider()
    st.subheader("Targets for a specific time window")
    c1, c2 = st.columns(2)
    sel_day = c1.selectbox("Day", DAY_ORDER, index=DAY_ORDER.index(busiest_day))
    sel_hour = c2.slider("Hour of day", 0, 23, busiest_hour)
    slot = (ct[(ct.dow==sel_day)&(ct.hour==sel_hour)]
            .merge(cells[["h3","lat","lon","place","top_violation","tier"]], on="h3", how="left")
            .sort_values("impact", ascending=False).head(25).reset_index(drop=True))
    if len(slot)==0:
        st.info("No recorded violations in this window. Select another hour or day.")
    else:
        slot["rank"] = slot.index + 1
        slot["map"] = slot.apply(lambda r: f"https://www.google.com/maps?q={r.lat:.5f},{r.lon:.5f}", axis=1)
        w = st.columns(3)
        w[0].metric("Zones active in this window", len(slot))
        w[1].metric("Impact in this window", f"{slot['impact'].sum():,.0f}")
        w[2].metric("Highest-impact zone", f"{slot.iloc[0]['impact']:,.0f}")
        # clean, minimal frame for pydeck (list/object columns can make deck.gl ignore the view → world zoom)
        pts = pd.DataFrame({
            "lon": slot["lon"].astype(float), "lat": slot["lat"].astype(float),
            "radius": (80 + 12*np.sqrt(slot["impact"].clip(lower=0))).astype(float),
            "place": slot["place"].astype(str), "impact": slot["impact"].round(1),
            "tickets": slot["tickets"].astype(int),
            "top_violation": slot["top_violation"].astype(str), "tier": slot["tier"].astype(str)})
        pts[["r","g","b"]] = pd.DataFrame(
            pts["tier"].map(lambda t: TIER_COLOR.get(t, TIER_COLOR["NORMAL"])[:3]).tolist(), index=pts.index)
        clat = float(slot["lat"].dropna().mean()) if slot["lat"].notna().any() else MAP_LAT
        clon = float(slot["lon"].dropna().mean()) if slot["lon"].notna().any() else MAP_LON
        st.pydeck_chart(pdk.Deck(
            layers=[pdk.Layer("ScatterplotLayer", pts, get_position="[lon, lat]", get_radius="radius",
                              get_fill_color="[r, g, b, 205]", pickable=True, opacity=0.8, stroked=True,
                              get_line_color=[255,255,255], line_width_min_pixels=1,
                              radius_min_pixels=4, radius_max_pixels=42)],
            initial_view_state=pdk.ViewState(latitude=clat, longitude=clon, zoom=11, pitch=0),
            map_style=BASEMAP,
            tooltip={"html":"<b>{place}</b><br/>Impact: {impact}<br/>Citations: {tickets}<br/>{top_violation} · {tier}"}))
        st.markdown(tier_legend(), unsafe_allow_html=True)
        st.caption(f"Where to deploy on **{sel_day}** at **{sel_hour:02d}:00** — marker size scales with impact, colour shows "
                   f"tier. Change the day or hour above and this map updates live.")
        slot_view = slot[["rank","place","impact","tickets","top_violation","tier","map"]]
        st.dataframe(slot_view, width='stretch', hide_index=True,
            column_config={"place": st.column_config.TextColumn("location"),
                           "impact": st.column_config.NumberColumn("impact score", format="%.1f"),
                           "tickets": st.column_config.NumberColumn("citations"),
                           "top_violation": st.column_config.TextColumn("dominant violation"),
                           "map": st.column_config.LinkColumn("map", display_text="view")})
        st.download_button(f"Download {sel_day} {sel_hour:02d}:00 worklist (CSV)",
            slot_view.to_csv(index=False), f"worklist_{sel_day}_{sel_hour:02d}.csv", "text/csv")

with tab_m:
    st.subheader("Methodology and validation")
    st.markdown(f"""
**Data and provenance.** {int(cells.tickets.sum()):,} on-street parking citations issued by the {SOURCE}
({PERIOD}), each geocoded with a vehicle class, a multi-label violation type, and a timestamp converted from UTC
to IST before any temporal analysis. About **1.8% of records were duplicate *captures of one event*** —
multiple tickets (distinct IDs) sharing the same vehicle, exact location and timestamp-to-the-second, emitted in
bursts ~7 s apart with at most one ever validated-approved; these were collapsed to a single event so one parked
vehicle isn't counted 2–15× in the impact surface. Validation status (approved / rejected / unvalidated) is
retained and discussed under limitations.
*Timestamp integrity was checked directly:* the citation second-field is constant (a logging/rounding artifact),
but the hour-of-day distribution is independently corroborated by the record's modify timestamp (which carries
genuine sub-minute precision and shows the same morning-concentrated profile). Day-of-week and hour-of-day are
therefore reliable scheduling signals — they reflect when enforcement records pressure — even though absolute
sub-minute precision is not.

**Congestion-impact model.** Each citation receives a score
`impact = vehicle_footprint × violation_severity × time_demand`, where footprint proxies the lane-length a
stationary vehicle obstructs, severity encodes how disruptive the parking configuration is, and time_demand
up-weights peak hours.
""")
    m1, m2 = st.columns(2)
    m1.markdown("""**Vehicle footprint**

| Class | Weight |
|---|---|
| Two-wheeler / moped | 1.0 |
| Passenger / goods auto | 2.0–2.5 |
| Car / jeep | 4.0 |
| Van / tempo / maxi-cab | 5.0 |
| LGV / mini-lorry / school | 6.0 |
| Bus | 8.0 |
| Lorry | 9.0 |
| Tanker / HGV | 10.0 |""")
    m2.markdown("""**Violation severity**

| Configuration | Weight |
|---|---|
| Parking in main road / double parking | 2.0 |
| Near road crossing | 1.8 |
| Near bus-stop / school / hospital | 1.6 |
| Opposite a parked vehicle | 1.5 |
| Generic wrong / no parking | 1.0 |
| Time demand (peak 08–11, 17–20) | ×1.3 |""")
    st.markdown(f"""
**Traffic-flow anchor (OpenStreetMap).** To move from a relative score toward a physical traffic-flow quantity,
each cell is matched to its nearest road in OpenStreetMap (≈168k road vertices for the city) to recover the real
**road class and lane count**. We then estimate the **share of carriageway capacity removed** by a stationary
vehicle as `blocked_lanes / total_lanes`, where blocked-lanes scales with vehicle footprint and is amplified at
junctions (spillback). The same blockage is far more damaging on a single-lane street than on a six-lane arterial —
which is exactly what the estimate captures.

**Spatial aggregation.** Citations are binned into Uber H3 hexagons at resolution 10 (~65 m edge) — an equal-area
tessellation chosen over a latitude/longitude grid to avoid boundary and area-distortion artifacts (the modifiable
areal unit problem) and to match the ~5–10 m positional uncertainty of field-logged coordinates and the
street-segment scale at which enforcement acts.

**Hotspot delineation.** We compute the **Getis-Ord Gi\\*** local statistic for every cell, using native H3
adjacency (a 2-ring, ~130 m neighbourhood) as the spatial weights, to obtain a z-score and p-value per cell. Cells
significant at **99% confidence** (z ≥ 2.58) are labelled **Critical** and those at **95%** (z ≥ 1.96) **High** —
i.e. statistically significant *clusters* of high congestion-impact, not merely individually high-value cells.

**Predictive validation.** All models use a **temporal** train/test split (fit on the earlier record, evaluate on a
held-out later period) to avoid leakage. *(1) Regression —* forecasting a cell-hour's raw impact, a RandomForest does
**not** beat the seasonal-naive weekly mean (lift {ev.get('lift_pct',0):+.1f}%); the recurring weekly mean carries
~0.97 of feature importance, so the predictable component of pressure is essentially the recurring pattern.
*(2) Ranking —* the operational question is which cell-hours will be **high-pressure** (top quartile). A histogram
gradient-boosting classifier given the seasonal mean *plus* spatial structure (Gi\\* z-score) and road geometry
(lane count, estimated capacity loss) raises ranking quality to **ROC-AUC {ev.get('model_auc',0):.3f}** against the
naive ranker's **{ev.get('baseline_auc',0):.3f}** (**{ev.get('auc_lift_pct',0):+.1f}%**). Conclusion: the validated
recurring pattern sets the *schedule*, while the learned model adds value for *prioritising within* it.

**Relationship to the problem statement.** The system delivers the three requested capabilities — hotspot
detection, an impact quantification, and zone prioritisation — and converts reactive patrolling into a scheduled,
evidence-based plan. It also ties hotspots to the exact congestion sources named in the brief — **intersections**
(via the dataset's named-junction field) and **commercial / transit / event** areas (via the citation address text).
The impact figure is a **proxy** for traffic-flow degradation, not a direct measurement.

**Scalability.** The pipeline is city-agnostic and uses no city-specific tuning: H3 binning, the Getis-Ord Gi\\*
statistic, and the OpenStreetMap capacity-loss anchor apply to any geocoded parking-citation feed worldwide, and the
ranking model is retrained per city without code changes — so the same dashboard generalises beyond Bengaluru.

**Limitations.** (1) These are enforcement records, so the surface reflects *observed* pressure — where and when
officers ticket — and is a proxy for, not a measurement of, where illegal parking is worst; patrol-based
enforcement introduces spatial selection bias (visible, for example, in the weekend-morning citation peak).
(2) No *live* traffic-flow signal (speed, volume, travel time) is present; impact is anchored to static OSM road
geometry to estimate capacity loss, but actual flow degradation is modelled, not directly measured.
(3) Citations carry no dwell time, the strongest physical determinant of impact. (4) A material share of records
are unvalidated or rejected; rankings should be re-checked on the approved-only subset.

**Future work.** Fuse probe-vehicle / Google–TomTom speed feeds to calibrate the OSM-based capacity-loss estimate
against *observed* flow degradation; normalise impact by patrol exposure (per police-station beat) to debias the
enforcement-selection surface; and evaluate enforcement interventions causally (difference-in-differences around
deployment changes).
""")

st.divider()
st.markdown(
    "<div style='text-align:center; opacity:0.85; padding:6px 0;'>"
    "<b>ParkSight</b> &nbsp;·&nbsp; Team <b>Flipgrid.STAR (IIT Kanpur)</b><br/>"
    "<span style='opacity:0.75; font-size:0.9em;'>Aaditya Rathi &nbsp;·&nbsp; Ankit Kumar "
    "&nbsp;·&nbsp; Priyanshi Agarwal &nbsp;·&nbsp; Shivesh Shukla</span></div>",
    unsafe_allow_html=True)