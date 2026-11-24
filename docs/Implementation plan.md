**Topic:** New York City Urban Pluvial Flooding Data Analysis

**Dimensions:** Precipitation, Topography, Urban Construction, Drainage System, Vegetation/Greenness, Social Event Reports

### Univariate Questions (Analysis & Conclusions)

* Do NYC pluvial flooding events show significant differences across seasons, months, and times of day?
* Do NYC flood reports and sensor-measured ponding exhibit spatial clustering? Where are the hotspots?
* How do flood frequency, severity, and distribution differ across the five boroughs?
* Are there recurring long-term flooding hotspots? What common characteristics do they share?
* How do the spatial distribution and evolution of ponding differ across distinct rainstorm events?
* Is there a non-linear relationship or critical threshold between rainfall intensity and flood occurrence probability?
* Which is associated with higher flood risk: short-duration intense rainfall or prolonged continuous rainfall?
* Among cumulative precipitation over the past 1, 3, 6, 12, 24, and 72 hours, which has the strongest predictive value?
* How do elevation, slope, and relative relief relate to flood occurrence probability?
* Can local depressions (sinks), depression depth, and topographic relief explain recurring ponding?
* Is distance to rivers, coastlines, and other water bodies associated with flood risk?
* Do soil type, infiltration capacity, and groundwater conditions correlate with ponding onset or recession?
* How do building coverage, building density, floor area ratio (FAR), and building typology associate with flood risk?
* Are vegetation cover, tree canopy cover, and grass cover associated with lower flood risk?
* Are there risk differences across land uses such as industrial, commercial, residential, and public open space?
* How do catch basin density and distance to the nearest catch basin relate to flood risk?
* Does the spatial distribution of catch basins align with flood hotspots? Which areas may have coverage gaps?
* How does drainage infrastructure distribution relate to ponding recession speed and duration?
* Among built environment, topography, and drainage features, which category contributes more to explaining spatial variation?
* Are vegetation cover, tree canopy cover, and grass cover associated with lower flood risk?
* How do rainfall and local environment relate to maximum ponding depth, ponding duration, and rising/receding rates?
* Are multi-source data more predictive than using precipitation alone or static geographic features alone?
* Do high flood-hazard areas overlap with high population density, low-income, or high social vulnerability communities?
* What share of critical infrastructure—such as hospitals, schools, and subway stations—lies within high flood-hazard areas? Which areas should be prioritized for drainage maintenance, green infrastructure deployment, or early warning systems?

### Multivariate Questions (Primary)

| ID | Joint Factors | Research Question |
| --- | --- | --- |
| J01 | Precipitation × Topography | Under the same rainfall conditions, is the risk gap between low-lying areas and higher ground larger? |
| J02 | Precipitation × Catch Basin Density | Does the association between catch basin density and risk change with rainfall intensity? Are there signs of saturation? |
| J03 | Precipitation × Greenness | Does the association between greenness and lower flood risk differ between normal rain and extreme storms? |
| J04 | Precipitation × Imperviousness | Does a high impervious surface ratio amplify flood risk under heavy rainfall? |
| J05 | Rainfall Intensity × Duration | Which intensity–duration combinations are associated with high risk? |
| J06 | Precipitation × Antecedent Precipitation | Under the same current rainfall intensity, do areas with higher antecedent cumulative rainfall face higher risk? |
| J07 | Precipitation × Tide Level | Does high tide amplify rainfall-driven flooding in coastal areas? |
| J08 | Precipitation × Drainage Regime | Do known drainage service areas show different risk responses across rainfall intensities? |
| J09 | Topography × Imperviousness | Do low-lying, heavily impervious areas form more pronounced ponding hotspots? |
| J10 | Topography × Land Use | Among equally low-lying areas, how does risk differ across industrial, commercial, residential, and green space land uses? |
| J11 | Topography × Drainage Infrastructure | At similar levels of depression/low elevation, is drainage infrastructure distribution associated with risk? |
| J12 | Building Density × Drainage Infrastructure | Is higher catch basin density associated with lower risk in high-density built-up areas? |
| J13 | Imperviousness × Drainage Regime | Does the relationship between impervious surfaces and risk differ across drainage service areas? |
| J14 | Greenness × Drainage Infrastructure | Do natural and engineered drainage features show complementary associations with risk? |
| J15 | Greenness × Imperviousness | Within highly impervious areas, is localized green space associated with lower ponding risk? |
| J16 | Street Topology × Drainage Regime × Precipitation | Do street network structure and drainage type jointly alter ponding distribution during rainstorms? |
| J17 | Precipitation × Topography × Drainage | Can we identify locally differentiated rainfall risk thresholds? |
| J18 | Topography × Drainage × Ponding Depth | Do low elevation/depressions and drainage infrastructure jointly explain peak water depth and recession rate? |
| J19 | Risk × Population × Income | Which areas simultaneously have high hazard, high population exposure, and high social vulnerability? |
| J20 | Risk × Population × Drainage Infrastructure | Which high-risk, high-exposure areas may have catch basin / drainage coverage gaps? |
| J21 | Risk × Greenness × Social Vulnerability | Does green infrastructure align with the needs of high-risk, socially vulnerable communities? |
| J22 | Measured Water Depth × Population × 311 Reports | At similar measured water depths, does reporting probability differ across areas with different demographic profiles? |
| J23 | Measured Water Depth × Time of Day × 311 Reports | Does the probability of ponding of the same depth being reported differ between night and day? |
| J24 | Risk × Transit × Critical Infrastructure | Which flood-prone areas may simultaneously disrupt transit and critical public services? |

### Machine Learning Prediction: Flood Risk

**Primary deliverable:** Data analysis figures

* Charts cannot be overly simplistic. A single analytical figure should combine at least multi-source data to jointly analyze and address specific questions, rather than answering just one isolated question per chart.
* Figures must be produced using rigorous scientific plotting tools.
* **Primary dataset and plotting code source:** [https://github.com/jinwork00/OTTER-NYC](https://github.com/jinwork00/OTTER-NYC)

After implementing the code for this project and generating the figures, we will expand with additional figures tailored to our research questions. Note that we do not mind directly reproducing and reusing code from others' plots, while also stitching/combining them to create original composite figures.
Machine learning prediction will be implemented last.

### Other Datasets

#### 4.1 Core Labels & Preprocessed Data

| ID | Dataset / Reference | Data & Purpose | Access Method |
| --- | --- | --- | --- |
| D01 | NYC 311 Service Requests (2020–present) | Citywide complaint timestamps, locations, categories; construct flood/ponding report labels | Official open CSV/API; filter by date and category |
| D02 | NYC 311 Service Requests (2010–2019) | Historical long-term trends | Official open CSV/API |
| D03 | 311 Street Flooding and Sewer Backups | Filtered street flooding and sewer backup reports | Community-created view; use D01 as authoritative source and verify filtering logic |
| D04 | FloodNet: Street Flooding Events Measured by Sensors / Federal Catalog | QC'd measured street ponding event summaries; event definition involves water depth > 10 mm | Official open CSV; event table only, not full continuous negative samples |
| D05 | FloodNet Data Downloads / Methodology / Data Request | Minute-level measured water depth, online status; sensor dynamics and dry-period confirmation | Event summaries public; full minute series available via free API/CSV request |
| D06 | OTTER-NYC Paper / GitHub / Zenodo DOI | Minute-level sensor depth, precipitation, topography, catch basin features; 2020.10–2025.08, up to 293 sensors | Paper published 2026-11-17; Zenodo DOI provided in paper but unreachable during check; repo notes DEM-derived features must be generated locally |
| D07 | NYC Stormwater Flood Maps / Interactive Map | Official modeled flood extent/depth classes under four rainfall/sea-level scenarios; spatial benchmarking and exposure analysis | Official GIS ZIP; modeled outputs, not observed labels |

*Note: Prioritize D01 + D04 + D08/D10 + D13 + D15 + D17/D18. If D06 becomes accessible, quickly build a sensor-level branch; if not downloadable, start with public FloodNet event summaries for validation or request D05 raw data. Do not treat co-derived OTTER-NYC and FloodNet as two independent observation networks.*

#### 4.2 Meteorology & Hydrology

| ID | Dataset | Data & Purpose | Access Method |
| --- | --- | --- | --- |
| D08 | IEM ASOS Hourly Precipitation | Hourly precipitation; suited for baseline experiments | CSV; station observations |
| D09 | IEM ASOS One Minute Data | 1-minute precipitation and event dynamics | CSV; watch cumulative definitions and missing data |
| D10 | NOAA MRMS QPE / Precipitation Time Series Explorer / MRMS Guide | ~1 km hourly gridded precipitation; suited for analyzing localized citywide rainfall differences | Historical grid/time-series portal; batch GRIB processing is relatively costly |
| D11 | NOAA Climate Data Online | Historical station precipitation, temperature, and other meteorological records | Official query/download |
| D12 | NOAA Tides & Currents – The Battery / CO-OPS API | Tide and water levels; for filtering or studying compound flooding | Official station & API |
| D26 | USGS Water Data | Station water levels, groundwater, etc. (subject to NYC coverage) | Official data portal; not continuous citywide coverage |
| D27 | USDA Web Soil Survey | Soil types and hydrologic soil groups | Official portal; interpret urban fill and micro-scale infiltration cautiously |
| D28 | NOAA Storm Events Database | Extreme weather events and historical damage records | Official event database; not grid-level ponding records |

#### 4.3 Topography, Buildings, Vegetation & Streets

| ID | Dataset | Data & Purpose | Access Method |
| --- | --- | --- | --- |
| D13 | NYC 1-foot DEM | 2010 LiDAR bare-earth elevation; slope, sinks/depressions, flow accumulation features | Official raster; compressed integer version ~3.3 GB; note elevation units are in feet |
| D14 | USGS 3DEP / National Map | Optional updated or easier-to-process DEM | Official download portal; verify NYC year and resolution |
| D15 | NYC PLUTO / MapPLUTO | Tax lot attributes, land use, building floor area, FAR; MapPLUTO provides parcel geometry | Official CSV/GIS; select historical release matching study period |
| D16 | NYC Land Cover Raster 2017 / COG Mirror | 6-inch land cover; tree canopy, grass, roads, buildings, water | Official ZIP; COG mirror enables raster window reads; canopy may occlude underlying impervious surfaces |
| D17 | DEP Citywide Parcel-Based Impervious Area GIS Study | Parcel pervious and impervious area and fractions | Official GIS; downloadable by borough/zone |
| D29 | NYC Citywide Street Centerline metadata | Street network, intersections, topology | Official metadata and data portal |
| D30 | OpenStreetMap Geofabrik | Roads, facilities, POIs, waterways; street network and critical infrastructure exposure | PBF/SHP; check historical snapshot and ODbL license |
| D31 | NYC Parks GIS Data | Parks and green space data | Official portal; verify layer dates |

#### 4.4 Drainage & Green Infrastructure

| ID | Dataset | Data & Purpose | Access Method |
| --- | --- | --- | --- |
| D18 | NYCDEP Citywide Catch Basins | ~154,000 catch basin points; density, nearest-neighbor distance, service coverage proxies | Official CSV/GeoJSON; excludes actual capacity and operational status |
| D19 | Municipal Separate Storm Sewer System (MS4) Data / ArcGIS FeatureServer | Known separated storm sewer areas and outfalls | Official GDB/service; non-MS4 areas cannot be directly labeled as combined sewer |
| D20 | DEP MS4 Official Documentation | Drainage system definitions, urban drainage management context | Official background & map |
| D21 | DEP Green Infrastructure Point Layer | Green infrastructure locations, types, and construction status | Official point data; keep only facilities completed and verified within the study period |
| D22 | DEP Green Infrastructure Regulated Projects | Green infrastructure project footprints and attributes | Official polygon data; verify status and dates |
| D23 | NYC Cloudburst Management | Cloudburst management projects, strategies, and background | Official project documentation; for case studies and governance discussion |
| D32 | CEQR Data Hub – Water and Sewer Infrastructure | Flood maps, impervious surfaces, and other urban planning GIS layers | NYC Planning data catalog |

*Drainage data caveat: Public data verified so far covers catch basin locations and MS4 service areas; full citywide combined/separate classification, pipe diameters, design flows, or real-time operational data are not yet confirmed publicly downloadable. Do not treat catch basin count directly as actual drainage capacity. Historical 311 records (e.g., blockages) may also be affected by reporting bias.*

#### 4.5 Socioeconomics, Administrative Boundaries & Critical Infrastructure

| ID | Dataset | Data & Purpose | Access Method |
| --- | --- | --- | --- |
| D24 | US Census ACS / ACS API | Population, income, age, disability, vehicle ownership, housing | Census Tract / Block Group; use 5-year estimates matching study year |
| D25 | CDC/ATSDR Social Vulnerability Index | Social vulnerability indicators and quantiles | Official CSV/GDB; distinguish state vs. national rankings |
| D33 | US Census TIGER/Line | Census Tract, Block Group, and other boundaries | Official GIS; align with ACS geography year |
| D34 | NYC Department of City Planning Open Data | Administrative boundaries, neighborhoods, land use, facilities | Official portal; filter specific layers |
| D35 | MTA Developer Resources | Transit stations, lines, GTFS; critical transit infrastructure exposure | Official data portal; verify historical service status separately |
| D36 | FEMA National Flood Hazard Layer | Official riverine and coastal flood hazard zones for distinguishing flood types | Official portal; access restricted during check; does not replace NYC pluvial flood mapping |

### Recommended Tools & Software for Plotting and Analysis

| Category                    | Recommended Tools               |
| --------------------------- | ------------------------------- |
| Environment Management      | `uv`                            |
| Data Analysis               | Pandas, NumPy                   |
| Large-Scale Data Processing | Polars, PyArrow                 |
| Scientific Statistics       | SciPy, Statsmodels              |
| GIS Software                | QGIS(may with mcp or python)    |
| Geospatial Analysis         | GeoPandas, Shapely              |
| Raster Data Processing      | Rasterio, rioxarray             |
| Spatial Statistics          | PySAL                           |
| Machine Learning            | Scikit-learn, XGBoost, LightGBM |
| Explainability              | SHAP                            |
| Scientific Plotting         | Matplotlib, Seaborn             |
| Interactive Plotting        | Plotly                          |
| Map Visualization           | Folium, Contextily              |
| Workflow Automation         | `Makefile`                      |

In the end, we will select roughly **10–15 questions** and produce around **10 figures**—which must be publication-grade or composite multi-panel figures rather than simple single bar or line charts.