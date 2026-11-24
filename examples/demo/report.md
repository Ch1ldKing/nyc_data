# Analysis run — DEMO

**SYNTHETIC DEMONSTRATION ONLY. No empirical conclusions.**

## Data summary
```text
mode  grid_hours  reports  positive_hours  report_rate  cells
demo       10080      592             592      0.05873     30
```

## Model results
```text
        feature_set         model  validation_ap  test_ap  test_auroc  test_f1  test_precision  test_recall  test_brier  threshold  test_prevalence
       weather_time      logistic       0.042511 0.068659    0.424222 0.105324        0.057233     0.659420    0.064598   0.033976         0.067647
       weather_time random_forest       0.050399 0.070047    0.476455 0.098639        0.064444     0.210145    0.067291   0.115979         0.067647
       weather_time    prevalence       0.043284 0.067647    0.500000 0.126722        0.067647     1.000000    0.063117   0.060862         0.067647
weather_time_static      logistic       0.054959 0.076023    0.456183 0.102503        0.061341     0.311594    0.064431   0.066676         0.067647
weather_time_static random_forest       0.054810 0.078597    0.501109 0.114173        0.078378     0.210145    0.065261   0.112441         0.067647
```

## Model selection
Selected on validation AP: logistic / weather_time_static.

## Limitations
- Target is a recorded street-flooding report, not confirmed flooding.
- Historical weather is city-scale reanalysis, not a live forecast.
- Conditional rates and SHAP are not causal.
- Independent sensor validation, spatial generalization and complete infrastructure coverage remain future tasks.

## Figures
- [historical_reports_map](figures/historical_reports_map.png)
- [hourly_rainfall_reports](figures/hourly_rainfall_reports.png)
- [interaction_catch_basin_count](figures/interaction_catch_basin_count.png)
- [interaction_elevation_m](figures/interaction_elevation_m.png)
- [interaction_green_fraction](figures/interaction_green_fraction.png)
- [interaction_impervious_fraction](figures/interaction_impervious_fraction.png)
- [precision_recall](figures/precision_recall.png)
- [spearman](figures/spearman.png)
- [test_mean_risk_map](figures/test_mean_risk_map.png)
