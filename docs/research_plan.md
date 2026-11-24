# What Makes a City Flood?

**Multi-Source Analysis of Urban Flooding Drivers, Risk Prediction, and Spatial Vulnerability in New York City**

纽约市内涝影响因素、风险预测与空间脆弱性的多源数据分析

资料整理日期：2026-11-24

## 1. 研究目标与范围

以纽约市降雨引发的城市内涝（pluvial / street flooding）为核心，研究降水、地形、城市建设、排水系统、绿化及社会环境如何共同关联内涝发生、严重程度和空间分布；建立可解释的风险预测模型，并用真实传感器观测验证。

- **研究区域：** NYC 五个行政区；有条件时扩展至跨城市比较。
- **建议时间：** 2021–2025 年（以实际数据重叠期为准）；可扩展至 2010–2025 年进行历史趋势分析。
- **空间单位：** 500 m 网格（全市分析）；FloodNet 传感器及周围缓冲区（局部实测分析）；Census Tract（社会脆弱性分析）。
- **时间单位：** 小时（全市风险预测）；分钟或 5–15 分钟（传感器积水动态）。
- **研究主线：** Where → Why → Interactions → Prediction → Validation → Adaptation。

将沿海潮汐洪水与降雨内涝分开，必要时单独分析二者的复合影响。注意区别**灾害危险性（hazard）、人口/资产暴露（exposure）、社会脆弱性（vulnerability）与综合风险（risk）**。

## 2. Research Questions：候选研究问题全集

以下是可供选择的问题库，不要求全部完成。**核心**为建议优先研究；**扩展**可在数据充足时增加；**条件**表示需要额外数据或更严格的研究设计。

### A. 内涝时空规律

| ID | Research Question | 优先级 |
| --- | --- | --- |
| RQ01 | 内涝报告和实测积水是否呈现空间聚集性？热点区域在哪里？ | 核心 |
| RQ02 | 五个行政区的内涝频率、严重程度与分布有何差异？ | 核心 |
| RQ03 | 内涝在不同季节、月份、时段是否具有显著差异？ | 核心 |
| RQ04 | 多年内涝报告频率和热点位置是否发生变化？ | 扩展 |
| RQ05 | 是否存在反复发生内涝的长期热点？这些热点有何共同特征？ | 核心 |
| RQ06 | 不同空间尺度（250 m、500 m、1 km、社区）是否改变研究结论？ | 扩展 |
| RQ07 | 不同暴雨事件的积水空间分布和演变过程有何差异？ | 核心 |

### B. 降水与气象因素

| ID | Research Question | 优先级 |
| --- | --- | --- |
| RQ08 | 降水强度与内涝发生概率之间是否存在非线性关系或临界阈值？ | 核心 |
| RQ09 | 短时强降雨和长时间持续降雨，哪一种与更高内涝风险相关？ | 核心 |
| RQ10 | 过去 1、3、6、12、24、72 小时累计降水量中，哪个最有预测价值？ | 核心 |
| RQ11 | 从降雨开始、达到峰值到积水出现、达到峰值分别存在多长滞后？ | 核心 |
| RQ12 | 前期降水或土壤湿润程度是否与后续积水风险相关？ | 扩展 |
| RQ13 | 雷达网格降水是否比少数气象站观测更能解释局地内涝？ | 扩展 |
| RQ14 | 极端降雨、高频短历时暴雨及普通降雨的风险关系是否不同？ | 核心 |
| RQ15 | 潮位、风暴潮和降雨共同出现时是否会增加沿海地区积水？ | 扩展 |

### C. 地形与水文环境

| ID | Research Question | 优先级 |
| --- | --- | --- |
| RQ16 | 海拔、坡度、相对高程与内涝发生概率有何关系？ | 核心 |
| RQ17 | 局部低洼地形、洼地深度、地形起伏能否解释反复积水？ | 核心 |
| RQ18 | 汇流面积、流向、流量累积或地形湿度指数（TWI）能否提高风险预测能力？ | 核心 |
| RQ19 | 距河流、海岸和其他水体的距离是否与内涝风险相关？ | 扩展 |
| RQ20 | 土壤类型、渗透能力及地下水条件是否关联积水发生或消退？ | 条件 |
| RQ21 | 不同 DEM 分辨率或地形特征提取尺度对结果有何影响？ | 扩展 |

### D. 城市建设、土地利用与交通形态

| ID | Research Question | 优先级 |
| --- | --- | --- |
| RQ22 | 建筑覆盖率、建筑密度、容积率和建筑类型与内涝风险有何关联？ | 核心 |
| RQ23 | 不透水地面比例是否与积水概率、深度和持续时间相关？ | 核心 |
| RQ24 | 工业、商业、住宅、公共绿地等土地用途之间是否存在风险差异？ | 核心 |
| RQ25 | 道路密度、道路宽度和交叉口密度是否关联内涝分布？ | 扩展 |
| RQ26 | 道路网络拓扑、低洼路段与地下通道是否与积水热点相关？ | 扩展 |
| RQ27 | 建设强度或土地覆盖变化是否伴随长期内涝风险变化？ | 条件 |
| RQ28 | 建筑环境、地形和排水特征中，哪类变量对解释空间差异贡献更大？ | 核心 |

### E. 排水设施与排水方式

| ID | Research Question | 优先级 |
| --- | --- | --- |
| RQ29 | 排水口密度、距离最近排水口的距离与内涝风险有何关系？ | 核心 |
| RQ30 | 排水口空间分布是否与内涝热点匹配？哪些区域可能存在配置缺口？ | 核心 |
| RQ31 | 已知 MS4 分流排水覆盖区与非 MS4 区域的内涝风险是否不同？ | 核心 |
| RQ32 | 已确认的合流制与分流制排水系统之间是否存在风险差异？ | 条件：须有可靠服务区分类 |
| RQ33 | 排水口堵塞、下水道回流、井盖溢流等历史报告能否帮助识别积水风险？ | 扩展 |
| RQ34 | 排水设施分布与积水消退速度、持续时间有何关系？ | 核心 |
| RQ35 | 管径、管道坡度、设计流量、泵站和维护状态是否关联排水表现？ | 条件：需管网工程及运行数据 |
| RQ36 | 不同区域在极端降雨下是否表现出不同的排水饱和迹象？ | 扩展：仅作间接推断 |

### F. 绿化与自然基础设施

| ID | Research Question | 优先级 |
| --- | --- | --- |
| RQ37 | 植被覆盖率、树冠率、草地比例是否与较低内涝风险相关？ | 核心 |
| RQ38 | 绿地面积、连通性和空间布局是否比绿化总量更有解释价值？ | 扩展 |
| RQ39 | 雨水花园、生物滞留设施、绿色屋顶等绿色基础设施与内涝风险有何关联？ | 核心 |
| RQ40 | 不同类型绿色基础设施周围的积水深度或持续时间是否不同？ | 扩展 |
| RQ41 | 绿色基础设施建成前后内涝是否改善？ | 条件：需建设日期、对照区域和可比降雨 |

### G. 真实积水动态与观测偏差

| ID | Research Question | 优先级 |
| --- | --- | --- |
| RQ42 | 降雨和局地环境与最大积水深度、积水持续时间及上升/消退速度有何关系？ | 核心 |
| RQ43 | NYC 311 积水报告与 FloodNet 实测积水在时间、位置和严重程度上是否一致？ | 核心 |
| RQ44 | 哪些实测积水事件没有居民报告？漏报与积水深度、时段、人口密度是否相关？ | 核心 |
| RQ45 | 311 投诉量能否作为真实积水严重程度的代理指标？ | 核心 |
| RQ46 | 不同社会经济背景区域在相似实测积水条件下是否有不同报告倾向？ | 扩展 |
| RQ47 | 传感器布设偏向已知高风险区域，是否影响模型空间代表性？ | 核心 |
| RQ48 | 不同积水阈值、空间匹配半径和时间容差会怎样影响一致性结论？ | 核心 |

### H. 社会公平、暴露与城市韧性

| ID | Research Question | 优先级 |
| --- | --- | --- |
| RQ49 | 高内涝危险区是否与高人口密度、低收入或高社会脆弱性社区重叠？ | 核心 |
| RQ50 | 老年人、残障人士、无车家庭等群体的潜在内涝暴露是否存在空间差异？ | 扩展 |
| RQ51 | 医院、学校、地铁站等关键设施位于高内涝危险区的比例是多少？ | 扩展 |
| RQ52 | 内涝风险与排水、绿化设施配置之间是否存在空间不均衡？ | 核心 |
| RQ53 | 哪些区域应优先进行排水设施维护、绿色基础设施建设或预警部署？ | 核心 |
| RQ54 | 极端降雨情景下，关键服务设施的潜在受影响范围是否扩大？ | 扩展 |
| RQ55 | 不同降雨或海平面情景下，高风险与高脆弱性区域的重叠如何变化？ | 扩展 |

### I. 风险预测、泛化与可解释性

| ID | Research Question | 优先级 |
| --- | --- | --- |
| RQ56 | 多源数据是否比仅使用降水或仅使用静态地理特征更有预测价值？ | 核心 |
| RQ57 | LR、Random Forest、XGBoost、LightGBM 等模型的预测表现有何差异？ | 核心 |
| RQ58 | 哪些变量及变量组合对模型预测贡献最大？是否存在可解释的非线性关系？ | 核心 |
| RQ59 | 模型在未见城区、未见传感器或未来暴雨事件中是否具有泛化能力？ | 核心 |
| RQ60 | 模型在极端降雨下是否出现明显误报或漏报？ | 核心 |
| RQ61 | 15、30、60、120 分钟等不同提前量的预测准确性如何变化？ | 扩展 |
| RQ62 | 能否直接预测传感器积水深度、峰值或持续时间，而不仅预测报告发生？ | 核心 |
| RQ63 | 模型预测的风险分数是否校准良好，能否作为预警优先级？ | 核心 |
| RQ64 | 数据缺失、降水估计误差或空间分辨率变化是否显著降低预测性能？ | 扩展 |
| RQ65 | 模型风险地图与官方 Stormwater Flood Maps 有多大程度的空间一致性？ | 核心 |
| RQ66 | 跨城市或不同气候背景下模型是否仍然有效？ | 条件：需要可比标签与数据 |

## 3. 联合研究问题：建议突出为项目特色

单变量分析用于建立基础认知，联合问题用于解释为何相同降雨在不同城区产生不同积水后果。以下均为待验证假设，不是既有结论。

| ID | 联合因素 | Research Question |
| --- | --- | --- |
| J01 | 降水 × 地形 | 相同降雨条件下，低洼区域与高地的风险差异是否更大？ |
| J02 | 降水 × 排水口密度 | 排水口密度与风险的关联是否随降雨强度改变？是否出现饱和迹象？ |
| J03 | 降水 × 绿化 | 普通降雨和极端暴雨下，绿化与较低内涝风险的关联是否不同？ |
| J04 | 降水 × 不透水率 | 高硬化地面比例是否放大强降雨下的内涝风险？ |
| J05 | 降水强度 × 持续时间 | 哪些强度—持续时间组合与高风险相关？ |
| J06 | 降水 × 前期降水 | 相同当前雨强下，前期累计降水更高的地区是否风险更高？ |
| J07 | 降水 × 潮位 | 高潮位是否放大沿海区域的降雨内涝？ |
| J08 | 降水 × 排水方式 | 不同已知排水服务区在不同雨强下的风险响应是否不同？ |
| J09 | 地形 × 不透水率 | 低洼且高度硬化区域是否构成更明显的积水热点？ |
| J10 | 地形 × 土地利用 | 同为低洼区域，工业、商业、住宅和绿地的风险有何差异？ |
| J11 | 地形 × 排水设施 | 相近低洼程度下，排水设施分布与风险是否相关？ |
| J12 | 建筑密度 × 排水设施 | 更高排水口密度是否与高密度建设区域较低的风险相关？ |
| J13 | 不透水率 × 排水方式 | 不同排水服务区内，硬化地面与风险的关系是否不同？ |
| J14 | 绿化 × 排水设施 | 自然与人工排水设施是否呈现互补的风险关联？ |
| J15 | 绿化 × 不透水率 | 高硬化区域中的局部绿地是否与较低积水风险相关？ |
| J16 | 道路拓扑 × 排水方式 × 降水 | 道路结构与排水类型是否共同改变暴雨下的积水分布？ |
| J17 | 降水 × 地形 × 排水 | 是否能识别局地差异化的降雨风险阈值？ |
| J18 | 地形 × 排水 × 积水深度 | 低洼程度和排水设施是否共同解释峰值水深及消退速度？ |
| J19 | 风险 × 人口 × 收入 | 哪些区域同时具有高危险性、高人口暴露和高社会脆弱性？ |
| J20 | 风险 × 人口 × 排水设施 | 哪些高风险、高暴露区域可能存在排水设施配置缺口？ |
| J21 | 风险 × 绿化 × 社会脆弱性 | 绿色基础设施是否与高风险脆弱社区的需求匹配？ |
| J22 | 实测水深 × 人口 × 投诉 | 在相似实测水深下，不同人口特征区域的报告概率是否不同？ |
| J23 | 实测水深 × 时段 × 投诉 | 夜间与白天相同深度的积水被报告的概率是否不同？ |
| J24 | 风险 × 交通 × 关键设施 | 哪些内涝区域可能同时影响交通及关键公共服务？ |

**优先选择：J01、J02、J03、J04、J08、J14、J19、J22。** 使用分层统计、带交互项的回归、二维 ALE/PDP 或 SHAP interaction；高度相关特征下谨慎解释。除非具备可靠因果识别设计，否则不将关联表述为设施建设的因果效果。

## 4. References：公开数据集与下载链接

### 4.1 核心标签与预处理数据

| ID | Dataset / Reference | 数据与用途 | 获取方式 |
| --- | --- | --- | --- |
| D01 | [NYC 311 Service Requests (2020–present)](https://data.cityofnewyork.us/d/erm2-nwe9) | 全市投诉时间、位置、类别；构造积水报告标签 | 官方开放 CSV/API；按日期和类别筛选 |
| D02 | [NYC 311 Service Requests (2010–2019)](https://data.cityofnewyork.us/d/76ig-c548) | 历史长期趋势 | 官方开放 CSV/API |
| D03 | [311 Street Flooding and Sewer Backups](https://data.cityofnewyork.us/d/9qq5-d465) | 已筛选的积水和回流报告入口 | 社区创建视图；以 D01 为正式来源并核对筛选逻辑 |
| D04 | [FloodNet: Street Flooding Events Measured by Sensors](https://data.cityofnewyork.us/d/aq7i-eu5q) / [联邦目录](https://catalog.data.gov/dataset/floodnet-street-flooding-events-measured-by-floodnet-sensors) | 质控后的实测积水事件摘要，事件定义涉及水深超过 10 mm | 官方开放 CSV；仅事件表，不代表完整连续负样本 |
| D05 | [FloodNet Data Downloads](https://www.floodnet.nyc/data-downloads) / [Methodology](https://www.floodnet.nyc/methodology) / [Data Request](https://www.floodnet.nyc/contact) | 分钟级实测水深、在线状态；传感器动态预测及无积水时段确认 | 事件摘要公开；完整分钟序列可免费申请 API/CSV |
| D06 | [OTTER-NYC Paper](https://doi.org/10.1038/s41597-026-08642-w) / [GitHub](https://github.com/jinwork00/OTTER-NYC) / [Zenodo DOI](https://doi.org/10.5281/zenodo.22732056) | 分钟级传感器水深、降水、地形与排水口特征；2020.10–2025.08，最多 293 个传感器 | 论文 2026-11-17 发布；论文给出 Zenodo DOI，但本次未能访问该下载页；代码库说明 DEM 派生特征需本地生成 |
| D07 | [NYC Stormwater Flood Maps](https://data.cityofnewyork.us/d/9i7c-xyvv) / [交互地图](https://www.nyc.gov/stormwater-map) | 四种降雨/海平面情景的官方模拟洪涝范围或等级；空间对照与暴露分析 | 官方 GIS ZIP；模拟结果不是实测标签 |

**优先 D01 + D04 + D08/D10 + D13 + D15 + D17/D18。** D06 若可获取，可快速建立传感器级分支；若不可下载，先用公开 FloodNet 事件摘要开展验证，或申请 D05 原始数据。不要把同源 OTTER-NYC 与 FloodNet 当成两个独立观测网络。

### 4.2 气象与水文

| ID | Dataset | 数据与用途 | 获取方式 |
| --- | --- | --- | --- |
| D08 | [IEM ASOS Hourly Precipitation](https://mesonet.agron.iastate.edu/request/hourlyprecip.phtml) | 小时降水；适合基础实验 | CSV；站点观测 |
| D09 | [IEM ASOS One Minute Data](https://mesonet.agron.iastate.edu/request/asos/1min.phtml) | 分钟降水及事件动态 | CSV；注意累积量定义和缺测 |
| D10 | [NOAA MRMS QPE / Precipitation Time Series Explorer](https://www.ncei.noaa.gov/products/precipitation-time-series-explorer) / [MRMS 数据使用指南](https://www.hec.usace.army.mil/confluence/hmsdocs/hmsguides/gridded-boundary-condition-data/importing-and-using-multi-radar-multi-sensor-mrms-precipitation-data) | 约 1 km 小时网格降水，较适合全市局地降雨差异分析 | 历史网格/时间序列入口；批量 GRIB 处理成本较高 |
| D11 | [NOAA Climate Data Online](https://www.ncei.noaa.gov/cdo-web/) | 历史气象站降水、温度及其他气象记录 | 官方查询下载 |
| D12 | [NOAA Tides & Currents – The Battery](https://tidesandcurrents.noaa.gov/stationhome.html?id=8518750) / [CO-OPS API](https://api.tidesandcurrents.noaa.gov/api/prod/) | 潮位、水位；用于排除或研究复合洪涝 | 官方站点及 API |
| D26 | [USGS Water Data](https://waterdata.usgs.gov/) | 水位、地下水等站点观测（视 NYC 覆盖而定） | 官方数据入口；非全市连续覆盖 |
| D27 | [USDA Web Soil Survey](https://websoilsurvey.nrcs.usda.gov/) | 土壤类型与水文土壤组等 | 官方入口；城市填土与微尺度渗透率需谨慎解释 |
| D28 | [NOAA Storm Events Database](https://www.ncei.noaa.gov/stormevents/) | 极端天气事件与历史灾情 | 官方事件库；非逐网格积水记录 |

### 4.3 地形、建筑、绿化与道路

| ID | Dataset | 数据与用途 | 获取方式 |
| --- | --- | --- | --- |
| D13 | [NYC 1-foot DEM](https://data.cityofnewyork.us/d/dpc8-z3jc) | 2010 LiDAR 裸地高程；坡度、洼地、汇流特征 | 官方栅格；整数版压缩约 3.3 GB；注意高程单位为英尺 |
| D14 | [USGS 3DEP / National Map](https://apps.nationalmap.gov/downloader/) | 可选更新或更易处理的 DEM | 官方下载入口；确认 NYC 年份与分辨率 |
| D15 | [NYC PLUTO](https://data.cityofnewyork.us/d/64uk-42ks) / [MapPLUTO](https://www.nyc.gov/site/planning/data-maps/open-data/dwn-pluto-mappluto.page) | 地块属性、土地用途、建筑面积、容积率等；MapPLUTO 提供地块几何 | 官方 CSV/GIS；选取与研究年份匹配的历史版本 |
| D16 | [NYC Land Cover Raster 2017](https://catalog.data.gov/dataset/land-cover-raster-data-2017-6in-resolution) / [COG 镜像](https://source.coop/betanyc/nyc-land-cover-2017) | 6 英寸土地覆盖；树冠、草地、道路、建筑、水体等 | 官方 ZIP；镜像便于栅格窗口读取；树冠可能遮盖下方硬化地面 |
| D17 | [DEP Citywide Parcel-Based Impervious Area GIS Study](https://catalog.data.gov/dataset/deps-citywide-parcel-based-impervious-area-gis-study) | 地块透水与不透水面积及比例 | 官方 GIS；可分区下载 |
| D29 | [NYC Citywide Street Centerline metadata](https://github.com/CityOfNewYork/nyc-geo-metadata/blob/main/Metadata/CSCL_Pub.md) | 道路网络、交叉口、拓扑 | 官方元数据及数据入口 |
| D30 | [OpenStreetMap Geofabrik](https://download.geofabrik.de/north-america/us/new-york.html) | 道路、设施、POI、水系；道路网络及关键设施暴露 | PBF/SHP；注意历史快照和 ODbL 许可 |
| D31 | [NYC Parks GIS Data](https://www.nycgovparks.org/about/doing-business-with-parks/parks-data) | 公园及绿地数据入口 | 官方入口；核对各图层年份 |

### 4.4 排水与绿色基础设施

| ID | Dataset | 数据与用途 | 获取方式 |
| --- | --- | --- | --- |
| D18 | [NYCDEP Citywide Catch Basins](https://data.cityofnewyork.us/d/2w2g-fk3i) | 约 15.4 万个排水口点位；密度、最近距离、服务覆盖代理变量 | 官方 CSV/GeoJSON；不含实际容量、运行状态 |
| D19 | [Municipal Separate Storm Sewer System (MS4) Data](https://data.cityofnewyork.us/d/j57c-rqtq) / [ArcGIS FeatureServer](https://services.arcgis.com/at3rDjch5X7i9Bag/arcgis/rest/services/MS42020_DrainageAreas/FeatureServer) | 已知分流排水区域与排放口等 GIS 数据 | 官方 GDB/服务；非 MS4 区域不能直接标记为合流制 |
| D20 | [DEP MS4 官方说明](https://www.nyc.gov/site/dep/water/municipal-separate-storm-sewer-system.page) | 排水类型定义、城市排水管理信息 | 官方背景及地图 |
| D21 | [DEP Green Infrastructure Point Layer](https://data.cityofnewyork.us/d/df32-vzax) | 绿色设施位置、类型及建设状态 | 官方点数据；仅保留研究时期已建成且可确认的设施 |
| D22 | [DEP Green Infrastructure Regulated Projects](https://data.cityofnewyork.us/d/fm4z-qud6) | 绿色基础设施项目范围及属性 | 官方面数据；确认状态和时间 |
| D23 | [NYC Cloudburst Management](https://www.nyc.gov/site/dep/environment/cloudburst.page) | 暴雨治理项目、策略和建设背景 | 官方项目资料；用于案例与治理讨论 |
| D32 | [CEQR Data Hub – Water and Sewer Infrastructure](https://nycplanning.github.io/ceqr-data-hub/pages/chapters.html) | 洪涝地图、硬化地面及其他城市规划 GIS 入口 | NYC Planning 数据目录 |

**排水数据限制：** 本次核实到的是排水口位置和 MS4 服务区等公开数据，尚未确认全市完整合流/分流分类、管径、设计流量或实时运行数据可公开下载。不能把排水口数量直接当作实际排水能力。历史堵塞等 311 记录也可能受报告偏差影响。

### 4.5 社会经济、行政边界与关键设施

| ID | Dataset | 数据与用途 | 获取方式 |
| --- | --- | --- | --- |
| D24 | [US Census ACS](https://data.census.gov/) / [ACS API](https://www.census.gov/data/developers/data-sets/acs-5year.html) | 人口、收入、年龄、残障、车辆拥有、住房等 | Census Tract / Block Group；使用对应年份 5-year estimates |
| D25 | [CDC/ATSDR Social Vulnerability Index](https://svi.cdc.gov/dataDownloads/data-download.html) | 社会脆弱性指标及分位数 | 官方 CSV/GDB；区分州内与全国排名 |
| D33 | [US Census TIGER/Line](https://www.census.gov/geographies/mapping-files/time-series/geo/tiger-line-file.html) | Census Tract、Block Group 等边界 | 官方 GIS；与 ACS 地理年份匹配 |
| D34 | [NYC Department of City Planning Open Data](https://www.nyc.gov/site/planning/data-maps/open-data.page) | 行政边界、社区、土地使用与设施数据入口 | 官方目录；具体图层需进一步筛选 |
| D35 | [MTA Developer Resources](https://www.mta.info/developers) | 交通站点、线路、GTFS；关键交通设施暴露 | 官方数据入口；历史服务状况需另行确认 |
| D36 | [FEMA National Flood Hazard Layer](https://www.fema.gov/flood-maps/national-flood-hazard-layer) | 河流及沿海等官方洪水危险区，用于区分风险类型 | 官方入口；本次访问受限；不替代 NYC 内涝图 |

### 4.6 其他城市 / 外部验证（可选）

- [Chicago Data Portal](https://data.cityofchicago.org/)：可查找 311、排水和环境相关数据。跨城市比较前须审核积水投诉分类、历史覆盖及坐标可用性。
- [Toronto Open Data](https://open.toronto.ca/)：可查找 311、地形、城市设施等数据；不保证与 NYC 标签同质。
- [Google Earth Engine Data Catalog](https://developers.google.com/earth-engine/datasets)：可用于遥感绿化、地表覆盖及外部灾害数据检索；城市短时积水通常不能直接由卫星洪水产品完整识别。

以上是广覆盖的候选来源目录；核心条目已检索到公开页面或官方目录，但未逐个下载文件验证完整性、许可、字段或研究期重叠。扩展条目部分为官方检索入口，并非已经确认可直接拼接的训练集。

## 5. References：论文与官方报告

### 5.1 NYC 内涝及其驱动因素（优先阅读）

| ID | Year / Venue | Reference | 与本项目的关系 |
| --- | --- | --- | --- |
| P01 | 2017 · Water | Smith & Rodriguez. [Spatial Analysis of High-Resolution Radar Rainfall and Citizen-Reported Flash Flood Data in Ultra-Urban New York City](https://doi.org/10.3390/w9100736) | 雷达降雨、居民报告、排水类型与地理差异；适合复现和延伸 RQ08–19、RQ32 |
| P02 | 2022 · Journal of Hydrology | Agonafir et al. [Understanding New York City street flooding through 311 complaints](https://doi.org/10.1016/j.jhydrol.2021.127300) / [开放存档](https://repository.library.noaa.gov/view/noaa/62328) | 降雨、堵塞、回流、溢流投诉与街道内涝；LASSO 与计数模型基线 |
| P03 | 2022 · Computers, Environment and Urban Systems | Agonafir et al. [A machine learning approach to evaluate the spatial variability of New York City's 311 street flooding complaints](https://doi.org/10.1016/j.compenvurbsys.2022.101854) | NYC 空间异质性与机器学习；建筑、排水、地形等特征参考 |
| P04 | 2024 · Journal of Hydrology | Zuo et al. [The influence of road network topology on street flooding in New York City—A social media data approach](https://www.sciencedirect.com/science/article/pii/S0022169424008679) | 道路网络、排水方式及降雨交互；J16 的直接参考 |
| P05 | 2024 · Natural Hazards | [Compounding effects of changing sea level and rainfall regimes on pluvial flooding in New York City](https://doi.org/10.1007/s11069-024-06466-8) | 降雨与海平面复合影响；模型和 311 对照 |
| P06 | 2026 · City and Environment Interactions | Lau et al. [Anticipating street-flooding complaints through rainfall data: a Value-at-Risk approach for urban operations](https://doi.org/10.1016/j.cacint.2026.100511) | 基于降水预测投诉数量、风险阈值与校准；检索页面列入 2026 年 12 月卷期，已可查到文章页面 |

### 5.2 真实传感器与数据集

| ID | Year / Venue | Reference | 与本项目的关系 |
| --- | --- | --- | --- |
| P07 | 2022 · Water Research | Silverman et al. [Making Waves: Uses of real-time, hyperlocal flood sensor data for emergency management, resiliency planning, and flood impact mitigation](https://doi.org/10.1016/j.watres.2022.118648) | 高频实测积水的城市治理应用 |
| P08 | 2024 · Water Resources Research | Mydlarz et al. [FloodNet: Low-Cost Ultrasonic Sensors for Real-Time Measurement of Hyperlocal, Street-Level Floods in New York City](https://doi.org/10.1029/2023WR036806) | FloodNet 核心引用；理解传感器原理、质控、部署偏差 |
| P09 | 2026 · Scientific Data | Jin et al. [OTTER-NYC: A Minute-Scale Multimodal Dataset for Urban Flood Event Dynamics and Forecasting](https://doi.org/10.1038/s41597-026-08642-w) | 预处理多模态数据；积水深度预测、事件质控与基线 |
| P10 | 2026 · Journal of Participatory Research Methods | Ignace et al. [At the intersection of science, policy, and community: The FloodNet NYC community engagement strategy](https://doi.org/10.35844/001c.162371) | 社区参与、传感器布设与观测代表性 |
| P11 | Project resources | [FloodNet Research Publications](https://www.floodnet.nyc/research) / [Documentation](https://floodnet-nyc.github.io/) / [Event Summaries](https://www.floodnet.nyc/flood-event-summaries) | 研究文献、质控、实际暴雨与潮汐案例 |

### 5.3 报告偏差、社会脆弱性与韧性

| ID | Year / Venue | Reference | 与本项目的关系 |
| --- | --- | --- | --- |
| P12 | 2025 · Annals of Applied Statistics | Boxer et al. [Estimating reporting bias in 311 complaint data](https://doi.org/10.1214/24-AOAS2003) | 311 报告偏差的统计方法；原研究对象是供暖/热水投诉，非内涝 |
| P13 | 2026 · Research article | [Expanding frameworks: Integrating vulnerability, exposure, and critical infrastructure to assess pluvial flood risks in New York City](https://pmc.ncbi.nlm.nih.gov/articles/PMC13598209/) | 人口暴露、社会脆弱性、关键基础设施与情景风险地图 |
| P14 | 2024 · Annals of the New York Academy of Sciences | [NPCC4: Climate change and New York City's flood risk](https://doi.org/10.1111/nyas.15175) | NYC 不同洪涝类型、暴雨、风险管理及 Ida 案例 |
| P15 | 2019 · Annals of the New York Academy of Sciences | [NPCC 2019: New Methods for Assessing Extreme Temperatures, Heavy Downpours, and Drought](https://doi.org/10.1111/nyas.14007) | 历史降雨、排水方式及气候背景 |
| P16 | 2021 · NYC official plan | [NYC Stormwater Resiliency Plan](https://www1.nyc.gov/assets/orr/pdf/publications/stormwater-resiliency-plan.pdf) | 官方内涝模拟情景及治理策略；可从 D07 官方页面进入 |
| P17 | Official program | [NYC Cloudburst Management](https://www.nyc.gov/site/dep/environment/cloudburst.page) | 灰色和绿色基础设施联合治理背景 |

**文献定位：** P01–P04 已经研究过 NYC 内涝与降雨、排水或建筑因素。不能声称首次研究这些关系。课程项目较有价值的延伸是组合多因素交互、按未来事件/空间区域严格验证、以实测积水检验报告代理标签，并探讨观测偏差。P09 和 P13 也已涉及实测预测及综合风险，研究创新需以具体实验比较为准。

### 5.4 方法、代码与工具参考

| ID | Reference | 用途 |
| --- | --- | --- |
| M01 | [PySAL / ESDA](https://pysal.org/esda/) | Moran's I、局部空间聚集分析 |
| M02 | [GeoPandas](https://geopandas.org/en/stable/) / [Rasterio](https://rasterio.readthedocs.io/) | 矢量空间连接、栅格统计、坐标变换 |
| M03 | [WhiteboxTools](https://www.whiteboxgeo.com/manual/wbt_book/intro.html) | 洼地、流向、汇流及水文地形指标 |
| M04 | [Scikit-learn](https://scikit-learn.org/stable/) / [XGBoost](https://xgboost.readthedocs.io/) / [LightGBM](https://lightgbm.readthedocs.io/) | 分类、回归、预测校准和基线 |
| M05 | Lundberg & Lee (2017). [A Unified Approach to Interpreting Model Predictions](https://arxiv.org/abs/1705.07874) / [SHAP](https://shap.readthedocs.io/) | 特征贡献与交互解释 |
| M06 | [Statsmodels](https://www.statsmodels.org/stable/) | Logistic、负二项回归、显式交互项 |
| M07 | Roberts et al. (2017). [Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure](https://doi.org/10.1111/ecog.02881) | 时空阻断验证，避免相邻样本泄漏 |
| M08 | [EPA Storm Water Management Model (SWMM)](https://www.epa.gov/water-research/storm-water-management-model-swmm) | 水文水动力模拟及绿色/灰色设施分析；可选，需工程参数 |
| M09 | [QGIS](https://qgis.org/) / [Folium](https://python-visualization.github.io/folium/) / [Plotly](https://plotly.com/python/) | GIS 风险地图及交互式展示 |
| M10 | [Socrata API documentation](https://dev.socrata.com/) | NYC Open Data 分页及服务端筛选 |

## 6. 推荐实现方案

### 6.1 两条互补数据分支

| 分支 | 样本 | 标签 | 目的 |
| --- | --- | --- | --- |
| A：全市风险 | 500 m 网格 × 小时（可优先取降雨事件窗口） | 下一小时是否出现 311 街道积水报告；可增加投诉数量 | 全市风险分布、影响因素与空间泛化 |
| B：真实积水 | FloodNet 传感器 × 时间；静态特征以缓冲区提取 | 有效运行期实测水深、是否超过阈值、峰值/持续时间 | 实测验证、报告偏差、局地积水动态预测 |

若只能获得 FloodNet 事件摘要，B 分支先做事件匹配、实测严重程度统计和有条件的一致性验证；不要把未列在事件表中的时段直接视为无积水。获取完整运行状态和原始时间序列后，才构建可靠的传感器分类负样本。

### 6.2 处理流程

1. 下载 D01 并核对 `complaint_type`、`descriptor` 的实际取值，单独提取街道积水报告；下水道回流/堵塞作为独立变量或次级标签。通过 API 服务端筛选，避免整表下载。
2. 统一坐标系统（使用适合纽约的投影坐标系，确认单位后构建 500 m 网格）；统一 UTC 和纽约当地时间，处理夏令时。
3. 提取降水特征：过去 1/3/6/12/24 小时累计雨量、峰值雨强、持续时间；使用 MRMS 或最近站点降水。
4. 提取静态特征：海拔、相对高程、坡度、洼地、汇流、建筑覆盖、不透水率、绿化率、排水口密度、MS4 覆盖及绿色设施密度。
5. 按网格与小时构建数据；分别定义有雨无报告、无雨对照和报告发生样本。无报告仅为无报告，不是无内涝。
6. 实施空间统计、分层关联分析、交互模型与预测。将预测数据与 FloodNet 在空间和时间上匹配，使用多种匹配半径和时间容差开展敏感性分析。
7. 叠加 Census 和官方模拟图层，生成危险性、暴露、脆弱性与治理优先级地图。

**预测设置：** 预测时刻 t 只能使用 t 及之前已知的信息；若加入未来降水，应使用当时可获得的历史归档预报，或明确标注为理想化已知降雨情景，不得把未来实测降水作为真实预警输入。避免使用同一时刻目标投诉或事后结案信息作为预测特征。设施、土地利用等静态特征尽量采用研究时段对应版本。

### 6.3 实验清单

| Experiment | 实验 | 建议方法 / 指标 |
| --- | --- | --- |
| E01 | 内涝时空统计与热点 | 频率、暴雨事件对比、Moran's I、局部热点 |
| E02 | 单因素关联 | 分层统计、Logistic / Negative Binomial、非线性曲线 |
| E03 | 联合因素交互 | 分组风险曲线、回归交互项、二维 ALE/PDP、SHAP interaction |
| E04 | 模型比较 | 历史频率、仅降雨 LR、RF、XGBoost、LightGBM |
| E05 | 多源数据消融 | 降雨 → +地形 → +建成环境 → +排水 → +绿化；补充逐组移除 |
| E06 | 时间与空间泛化 | 按年份、完整暴雨事件、空间块或行政区划分；传感器留出 |
| E07 | 极端降雨与校准 | 极端雨强分层 AUPRC/Recall、Brier Score、可靠性曲线 |
| E08 | 传感器验证与报告偏差 | 事件匹配率、实测峰值深度分层、未报告事件比例；有完整运行数据时评估真实分类 |
| E09 | 实测积水动态（可选） | Persistence、线性/树模型；MAE、RMSE、峰值误差 |
| E10 | 风险暴露与治理优先级 | 人口/设施暴露、SVI 分层、官方模拟图对照 |
| E11 | 稳健性 | 网格尺寸、降水数据源、匹配容差、静态变量年份和样本策略敏感性 |

分类指标：AUPRC（稀有事件优先）、AUROC、F1、Precision、Recall、Brier Score。深度回归指标：MAE、RMSE；另报告事件峰值误差。所有模型使用一致的数据划分；阈值在验证集确定；不要随机拆分同一暴雨或相邻网格作为唯一验证方式。若负样本下采样，需在自然发生率的测试集上评估校准。

### 6.4 五人分工建议

| Module | 工作 | 主要成果 |
| --- | --- | --- |
| 1 | 数据收集、降水及内涝时空分析 | 数据表、热点与降雨响应图 |
| 2 | 地形、建筑、土地覆盖分析 | 地形与建成环境特征、多因素关联 |
| 3 | 排水方式、排水设施、绿化交互 | 分区对比、交互曲线 |
| 4 | 多源预测、消融与泛化 | 实验表、校准与风险地图 |
| 5 | FloodNet 验证、观测偏差和社会脆弱性 | 实测对照、暴露与治理优先级地图 |

## 7. 建议最终聚焦的五个主要研究问题

- **Main RQ1 – Spatial and temporal patterns:** Where and when does urban flooding occur, and how does it respond to rainfall intensity and duration?
- **Main RQ2 – Environmental drivers:** How are topography, impervious surfaces, buildings, and vegetation associated with urban flooding?
- **Main RQ3 – Infrastructure and interactions:** How do drainage infrastructure and green infrastructure interact with rainfall and urban form in explaining flooding risk?
- **Main RQ4 – Explainable prediction:** Can multi-source data improve calibrated short-term flood-report prediction and generalization to unseen locations and storm events?
- **Main RQ5 – Observation and vulnerability:** How consistent are citizen reports with sensor-measured flooding, and which communities face overlapping flood hazard, exposure, and social vulnerability?

## 8. 最终成果与边界

- 一份统一时空尺度的多源数据集（遵守各来源许可；保存下载日期、版本和处理脚本）。
- 历史内涝热点、典型暴雨案例和影响因素交互图。
- 具备时间/空间泛化验证的内涝报告预测模型及风险地图。
- 真实传感器对照和报告偏差分析；数据足够时补充实测水深预测。
- 危险性、人口暴露、社会脆弱性及潜在治理优先区地图。

**最低可行版本：** D01、D08 或 D10、D13、D15/D17、D18、D04，完成 E01–E06 和事件级 E08；再逐步加入 MS4、绿色设施及人口数据。核心实验普通 CPU 可完成，不必训练复杂深度学习模型。

**解释边界：** 居民报告概率不是物理内涝概率；传感器点位并非全市随机抽样；官方模拟图不是历史实测；排水口密度不是实际排水容量；人口暴露地图不等同实际经济损失；观察性关系不直接证明因果。研究内容及创新程度最终以实际数据和实验结果为准。
