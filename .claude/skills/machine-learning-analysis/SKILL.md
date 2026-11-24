---
name: machine-learning-analysis
description: Train, evaluate, ablate and explain flooding-report prediction models.
---

# machine-learning-analysis

Start with prevalence and logistic baselines; compare RF, optional boosting; chronological and storm/spatial holdouts. Fit preprocessing on train, tune threshold on validation, never test. Use past-only features and assess AP relative to prevalence, AUROC, F1, precision, recall and calibration. Use SHAP with training background and held-out samples. Treat historical reanalysis as retrospective. Save configs, splits, metrics and predictions.

Read `CLAUDE.md` and `docs/research_plan.md` before acting. Follow `docs/implementation.md` and save artifacts under the configured run directory.
