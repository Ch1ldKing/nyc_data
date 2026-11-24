# NYC Urban Pluvial Flooding — Multi-source Data Analysis: Findings

*Generated 2026-11-24 by the pipeline in `src/urban_flooding/` (`make full`). All numbers below are read from `outputs/full/tables/*_stats.json`; figures are in `docs/figures/` (PNG) and `outputs/full/figures/` (PNG/PDF/SVG).*

## 1. Data actually used

| Source (plan ID) | What was obtained | Coverage / notes |
|---|---|---|
| NYC 311 (D01, D02) | 405,897 flood-related Sewer requests: street flooding 45,932; catch basin clogged/flooding 126,980; sewer backup 213,255; manhole overflow 11,682; highway flooding 687 | 2010-01 → 2026-10; 2010–19 from the `76ig-c548` archive, 2020+ from `erm2-nwe9`; 98.2% geocoded |
| FloodNet events + sensors (D04) | 3,611 QC'd events with depth profiles; 496 sensors (2,440 events at tidally influenced sensors) | 2020-11 → 2026-11 |
| OTTER-NYC (D06) | Code only. The dataset is not published yet (README: "link will be added"), so its plotting code could not be reused | QC logic referenced |
| IEM ASOS hourly + 1-min (D08, D09) | NYC, LGA, JFK, EWR, TEB hourly 2010–2026; 1-min precip NYC, LGA, JFK (2020+) | 2010–12 gaps filled from METAR p01i; 99% hourly coverage |
| NOAA tides, The Battery (D12) | Hourly observed + predicted water level (NAVD88) | 2010–2026 |
| USGS 3DEP DEM (D14 instead of D13) | 5 m bare-earth DEM → 10 m depression depth, slope, TPI, TWI, flow accumulation (pysheds) | Chosen over the 3.3 GB 1-ft DEM for disk/time |
| NYC Land Cover 2017 (D16) | 8 ft overview of the 6-inch raster: canopy, grass, impervious, buildings, roads | COG mirror |
| PLUTO (D15) | 857k lots: land use, FAR, floors, year built | current release |
| Catch basins (D18), MS4 (D19), GI points (D21) | 154k basins; MS4 drainage areas; constructed GI assets | — |
| Stormwater Flood Maps (D07) | Moderate-2050 and Extreme-2080 scenarios | The "Limited" GDB uses CDF compression and cannot be read by GDAL OpenFileGDB |
| CDC SVI 2022 (D25) + 2020 tracts (D33) | SVI ranks plus ACS 2018–22 estimates (population, poverty, no-vehicle, 65+, minority) | **The Census API returned HTTP 403**, so ACS variables come from SVI's E_* fields |
| Facilities DB, MTA stations (D34, D35) | Hospitals, schools, underground and open-cut subway stations | — |

Not used: MRMS radar (D10; costly GRIB processing), soil/groundwater (D26–27), street-network topology (D29–30; J16 not done), FEMA NFHL (D36).

**Analysis units:** 3,472 land cells of 500 m (EPSG:26918); 1,138 storm events (wet hours separated by ≥6 dry hours, city total ≥2.5 mm); a 3.95M-row storm × cell panel (target: ≥1 street-flooding report from storm start to storm end + 12 h). Figures 5–11 restrict to 2,404 **urban street cells** (≥50% land, ≥8% road, ≥200 residents). Without this filter, marsh, park and airport cells make low-lying ground look *safer*, because reports need streets and people (see §3.5).

## 2. Figures and the questions they answer

| Fig | Title | Questions |
|---|---|---|
| 1 | Where and when flooding is reported | seasonality, time of day, boroughs, trends |
| 2 | Hotspots, recurrence, sensor validation | spatial clustering, recurring hotspots, what they have in common |
| 3 | Rainfall controls | non-linear threshold, intense vs long rain, 1–72 h windows, J05, J06, J07 |
| 4 | Storm case studies | how footprints differ between storms, report vs sensor timing |
| 5 | Topography × rainfall × drainage | RQ16–17, J01, J09, J11, J17 |
| 6 | Built form, land use, greenness | RQ22–24, RQ37, J03, J04, J10, J15, multivariable model |
| 7 | Drainage infrastructure | RQ29–31, J02, J08, J12, J13, J14, coverage gaps |
| 8 | FloodNet ponding dynamics | RQ42 (depth, duration, rise and recession), J18, J07 |
| 9 | Reporting bias | RQ43–48, J22, J23 |
| 10 | Prediction, ablation, SHAP | multi-source vs single-source, RQ28, design-storm hazard |
| 11 | Exposure, equity, priorities | RQ49–53, J19–J21, J24 |

## 3. Key findings

### 3.1 Timing (Fig. 1)
- Reports are strongly seasonal and diurnal (month χ² = 1,496; hour vs rainfall-timing χ² = 26,580; both p≈0). Rain falls almost evenly across the day, but **reports pile up between 08:00 and 17:00 and almost vanish overnight**. This is a reporting effect, not a hydrological one (confirmed by sensors in Fig. 9).
- Reports per 100 mm of rain peak in May and September–October (≈255–275) and bottom out in March (≈186).
- Only 58% of street-flooding reports fall inside a storm window. For sewer backups it is 31% and for manhole overflows 22%, so those descriptors are mostly not rainfall-driven.
- Boroughs differ significantly (Kruskal–Wallis p = 2×10⁻³²). Brooklyn has the highest per-area rate and storm hit probability (4.2 reports km⁻² yr⁻¹; 2.4% of cells hit per heavy storm). Staten Island has the highest per-capita rate (9.3 per 10k residents per year). FloodNet median peaks are highest in Queens (100 mm) and the Bronx (92 mm).

### 3.2 Hotspots (Fig. 2)
- Clustering is significant every year: global Moran's I averages 0.14 for street flooding and 0.24 for catch-basin complaints, all p < 0.01.
- Gi* finds 65 FDR-significant hot cells (in Queens, Staten Island and Brooklyn).
- **178 persistent hotspots** (top decile in ≥8 of 16 years) cover 5.4% of land but receive **26.5% of storm-period reports**.
- Persistent hotspots are flatter (Cohen's d = −0.65 for slope), lower, less tree-covered and more impervious. They also have more depressions and more catch basins per road hectare (d = +0.65), which likely reflects DEP adding inlets where flooding recurs.
- Independent check: FloodNet sensors inside 311 hotspots record more events (median 1.6 vs 0.9 per sensor-year; Mann–Whitney p = 0.017).

### 3.3 Rainfall (Fig. 3)
- **The storm response is non-linear, with a break at ≈8 mm h⁻¹** (95% CI 5.1–9.4). Below the break, log reports rise 0.24 per mm h⁻¹; above it, only 0.04. Past this point extra intensity adds fewer reports, which is consistent with saturation, and storm total takes over.
- **Short intense vs long rain:** in a joint negative-binomial model, storm total has the largest effect (IRR 1.78 per SD), then peak 1-h intensity (1.29), antecedent 7-day rain (1.15) and duration (1.14). The intensity–duration matrix (J05) shows the most reports for intense storms that are also long (≥15 mm h⁻¹ over 12–72 h: medians of 88–178 reports per storm).
- **Accumulation window:** for hour-level prediction of ≥3 reports in the next 3 h, 24-h accumulation predicts best (AUC 0.727). 72 h is worse (0.696), as are 1 h (0.662) and the 15-min peak (0.619, 2020+ only).
- Antecedent wetness (J06) gives a modest, consistent uplift (IRR 1.15 per SD) but no clean shift across every intensity class.
- Tide (J07): storms with high tide at the Battery bring 2.8–2.9× more reports in low coastal cells but only 1.65–1.7× in inland cells. That gap fits a compound tide–rain effect, but high-tide storms are often nor'easters, so storm type confounds it.
- Reporting rises over time (IRR 1.17 per SD of year), even after controlling for rainfall.

### 3.4 Storm footprints (Fig. 4)
- Sensors start flooding within ≈0–1 h of the city rainfall peak. 311 reports lag by **1.5–4 h** (median report time 17–20 h after storm start vs a rainfall peak at ≈16 h).
- Footprints differ a lot between storms: the median Spearman ρ of cell counts across the 14 largest storms is only 0.08. Each big storm floods its own places, set by where its rain fell.
- The share of a storm's reports landing in chronic hotspots does not depend on intensity (ρ = 0.03, p = 0.62). It is highest for the Dec 2022 coastal storm (56%) and lowest for the convective events (16%).

### 3.5 Topography (Fig. 5)
- Among urban cells, the low-lying third reports **1.2–1.46×** more than high ground, a gap that grows slightly with intensity (J01; interaction p = 0.46). The **many-depression third reports 1.4×** more at light rain and **1.74×** more at ≥20 mm h⁻¹.
- Flat terrain is the strongest terrain signal (slope β = −0.39 per SD, p < 10⁻²¹).
- J17 local thresholds, as the rain rate at which P(report) reaches 2%: about **10 mm h⁻¹ for low-lying cells with dense catch basins**, 13.5 for higher ground with dense basins, 16 for low-lying with sparse basins and 20 for higher ground with sparse basins. Dense basins mark known problem areas, so read "dense basins" as "historically flood-prone".

### 3.6 Built form and greenness (Fig. 6)
- Taken alone, high imperviousness carries 5–20% higher report probability (J04) and high greenness 5–17% lower (J03). Neither effect changes significantly with rainfall class (interaction p = 0.22 and 0.30).
- Canopy *within highly impervious cells* (J15) shows no detectable benefit, and canopy there ranges only 1–22%.
- In the multivariable NB model (borough fixed effects, 2-km clustered SEs), imperviousness, building cover and canopy all become non-significant. What remains: population (IRR 1.23), depression share (1.18), catch basins per road ha (1.17, reverse causality likely), slope (0.84), distance to shore (0.90), FAR (0.89), GI density (0.93) and SVI (0.93).
- Land use (J10): among low-lying cells, residential (2.1%) and mixed-use cells report most per heavy storm. Industrial and transport cells report least, which probably reflects few reporters as much as real hazard.

### 3.7 Drainage (Fig. 7)
- Dense-basin cells report 1.8–2.0× more than sparse-basin cells at ordinary intensities, falling to **1.4× at ≥20 mm h⁻¹** (J02). MS4 vs non-MS4 areas: 1.2–1.3×, falling to **1.0× at ≥20 mm h⁻¹** (J08). Both convergences fit **infrastructure-independent saturation in extreme storms**: every system is overwhelmed.
- Imperviousness matters more inside MS4 areas than in non-MS4 areas (J13).
- High building density does not change the catch-basin pattern (J12). Green-infrastructure presence does not offset sparse basins (J14).
- Reports sit closer to catch basins than random road points do (median 21 vs 34 m; KS D = 0.17). People report flooding at inlets.
- **59 hotspot cells with below-median basin coverage** are candidate gaps (23 in Staten Island, 14 in Brooklyn, 13 in Queens): `outputs/full/tables/fig07_coverage_gap_cells.csv`.

### 3.8 Measured ponding (Fig. 8)
- Events rise fast and recede slowly: depth peaks about 35% of the way through an event (median onset 13 min, drain 27 min, peak 66 mm).
- 68% of FloodNet events come from tidally influenced sensors, and only 31% of those coincide with ≥2 mm of rain. Most tidal-sensor events are tide-driven, starting at Battery levels above the 90th percentile.
- Peak depth scales with nearby 1-h rain (ρ = 0.41; median quantile slope 0.38).
- Sensors farther from a catch basin rise and recede more slowly (ρ = −0.35 and −0.37). Sensors in sinks flood more often and deeper (ρ = +0.21 and +0.25). Higher-elevation sites are flashier.
- J18: after controlling for depth, sink depth, TPI and rain, the number of catch basins within 100 m shortens drain time, but not significantly (β = −0.14, p = 0.26).

### 3.9 Reporting bias (Fig. 9)
- Only **27% of measured ≥100 mm non-tidal floods get any 311 flood report** within 250 m (from 18% at 100 m/+1 h to 55% at 1 km/+12 h).
- **Night-onset floods are almost never reported:** 3.6% vs 31% by day for ≥100 mm (OR 0.11, 95% CI 0.03–0.34). Weekend floods are also under-reported (OR 0.35).
- With depth held equal, reporting rises with depth (OR 2.9 per SD) and population (OR 1.8 per SD). **SVI and minority share show no significant effect** (OR 0.91 and 0.84; J22).
- Storm-level 311 volume correlates only weakly with the share of sensors flooding (ρ = 0.22). 311 is a biased, noisy proxy for severity.

### 3.10 Prediction and source contributions (Fig. 10)
- Task: will a 500 m urban cell produce ≥1 street-flooding report in a given storm? LightGBM was trained on 2010 – Jun 2022 storms (early stopping on a random 20% of those storms) and tested on the 284 later storms (687,564 cell-storms; prevalence 0.87%).
- **Multi-source data beat rainfall alone**:
  - Temporal test AP: 0.041 with all sources vs 0.033 rain-only (lift 4.7× vs 3.8×). Static features alone reach only 0.017. The storm-bootstrap CIs overlap widely, because a handful of extreme storms dominate the test period.
  - The clearest gain is in **ranking cells within a storm**: within-storm AUC is 0.53 for rain-only (gauges only resolve 5 zones), 0.66 for rain + physical features and 0.66 for all sources.
  - 5-km spatial-block CV (unseen neighbourhoods): lift 5.0× for rain-only vs 6.95× for rain + physical features and 6.7× with population added. Physical features carry the gain, not population.
- **Contributions (mean |SHAP|, RQ28):** rainfall/storm 47%, topography 18%, built form 15%, population/reporting 10%, drainage 8%, greenness 3%. Top single static feature: local relief (low relief means higher risk). Next come distance to the nearest catch basin and residential land share.
- Design-storm hazard (30 mm h⁻¹ peak, 60 mm total) agrees moderately with DEP's Extreme stormwater-flood-map area share (Spearman ρ = 0.57). Two independent methods, one statistical from complaints and one hydraulic, point to similar places.

### 3.11 Exposure, equity and priorities (Fig. 11)
- Composite hazard = mean percentile of (i) the empirical-Bayes heavy-storm report rate, (ii) model design-storm risk and (iii) DEP Extreme-map flood share. The three agree at ρ = 0.36–0.75.
- **Hazard does not rise monotonically with social vulnerability (J19).** For all three measures it peaks in SVI deciles 4–7 (hazard percentile ≈ 55–60) and is lowest in the most vulnerable decile (≈ 34–38). That decile is dominated by dense, elevated parts of the Bronx and upper Manhattan, which are also places where floods are reported less.
- Still, **221 cells with ≈1.0 M residents are both high-hazard and high-SVI** (top tercile of each).
- Green infrastructure (J21) is concentrated where hazard is mid to high and SVI is mid to high (31–39 assets km⁻²), and is scarce in low-SVI areas whatever their hazard (7–8 km⁻²). That matches the combined-sewer-focused GI program more than flood need.
- Critical facilities in top-decile hazard cells (J24): schools 11.7% (395, about proportional to area), underground subway stations 7.0% (22), hospitals 2.9% (13, under-represented).
- **Priority cells** (hazard × population × SVI × catch-basin gap; `outputs/full/tables/fig11_priority_cells.csv`) cluster in Bensonhurst, Borough Park and Gravesend in south Brooklyn; Soundview, Hunts Point and Concourse in the Bronx; and East Harlem.

## 4. Answers to the plan's questions (short form)

| Question | Answer (figure) |
|---|---|
| Seasonal / monthly / diurnal differences? | Yes. Report yield peaks in May and Sep–Oct; reports are strongly daytime-biased (1, 9) |
| Spatial clustering, hotspots? | Yes. Moran's I 0.14 (street flooding) and 0.24 (catch basin); 65 Gi* hot cells; 178 persistent cells hold 26.5% of reports (2) |
| Borough differences? | Brooklyn highest per area, Staten Island per capita, Queens deepest measured ponding (1) |
| Recurring hotspots and what they share? | Flat, low, depression-rich, less canopy, more impervious, more catch basins (2) |
| Storm-to-storm differences? | Footprints barely overlap between storms (median ρ 0.08) (4) |
| Non-linear threshold? | Break at 8 mm h⁻¹ (5.1–9.4) (3) |
| Short intense vs long? | Storm total > peak intensity > duration; worst is intense *and* long (3) |
| Best accumulation window? | 24 h (AUC 0.727); 15 min and 1 h weakest (3) |
| Elevation, slope, relief? | Low and flat means higher risk; relief is the top static SHAP feature (5, 10) |
| Depressions explain recurrence? | Yes. 1.4–1.74× more reports, and more so with heavier rain; sensors in sinks flood more (5, 8) |
| Distance to water? | Closer to shore means more reports (IRR 0.90 per SD of distance) (6) |
| Soil / groundwater | Not analysed (data not acquired) |
| Building cover, FAR, type? | Weak; FAR slightly protective in the multivariable model (6) |
| Vegetation lower risk? | Bivariate yes (−5 to −17%); not after adjustment (6) |
| Land use differences? | Residential and mixed highest among low-lying cells (6) |
| Catch-basin density and distance? | Positively associated (reverse causality); reports cluster near inlets; sensors far from basins recede slower (7, 8) |
| Coverage gaps? | 59 hotspot cells with below-median basins (7) |
| Drainage vs recession? | Faster recession nearer basins (ρ −0.37); not significant after controls (8) |
| Which category explains most? | Rainfall ≫ topography > built form > population > drainage > greenness (10) |
| Rain/environment vs depth, duration, rates? | Depth ~ rain^0.38; rise/recession set by elevation, TPI and basin distance (8) |
| Multi-source better than rain-only or static-only? | Yes, especially for spatial ranking (within-storm AUC 0.66 vs 0.53) (10) |
| Hazard overlaps population / low income / SVI? | Inverted-U with SVI; 1.0 M residents in high–high cells (11) |
| Critical infrastructure in high-hazard areas? | Schools 11.7%, subway 7%, hospitals 2.9% of each class (11) |
| J01–J24 | J01 ✓5, J02 ✓7, J03 ✓6, J04 ✓6, J05 ✓3, J06 ✓3, J07 ✓3 and 8, J08 ✓7, J09 ✓5, J10 ✓6, J11 ✓5 (via J17 types), J12 ✓7, J13 ✓7, J14 ✓7, J15 ✓6, **J16 not done** (no street topology), J17 ✓5, J18 ✓8, J19 ✓11, J20 ✓7 and 11, J21 ✓11, J22 ✓9, J23 ✓9, J24 ✓11 |

## 5. Limitations
- **311 measures reports, not floods.** Fig. 9 shows only about a quarter of deep measured floods are reported, almost none at night. Population, time of day and history of complaints shape the label. All associations are observational.
- **Catch-basin density is endogenous:** DEP adds inlets where flooding was reported. Its positive association is not evidence that basins cause flooding.
- **Rain comes from 3–5 gauges.** Convective storms are poorly resolved (Fig. 4a–d), which limits rain-only models. MRMS radar would be the most valuable addition.
- DEM is 3DEP at 5 m, resampled to 10 m, rather than the 1-ft city DEM, so curb-scale sinks are not resolved. Land cover is the 8-ft overview of the 6-inch raster.
- ACS variables come via CDC SVI (Census API blocked). The DEP "Limited" stormwater scenario could not be read (CDF-compressed FileGDB).
- FloodNet sensors are placed purposefully in known trouble spots. 68% of their events are at tidal sensors and mostly tide-driven. OTTER-NYC minute-level data were unavailable.
- The temporal test is dominated by a few extreme storms (wide AP CIs), and reporting drifts upward over time (IRR 1.17 per SD of year).

## 6. Reproduce
```bash
uv sync --extra full
make full          # acquire -> build -> 11 figures (about 1 h, mostly downloads and LightGBM)
```
Code: `src/urban_flooding/acquire.py` (downloads and provenance in `data/raw/full/manifest.jsonl`), `build.py` (grid, DEM hydrology, static features, storms, panel), `figs/fig01…fig11_*.py` (each writes PNG/PDF/SVG plus tables and `*_stats.json` to `outputs/full/`).

