.PHONY: setup setup_full test demo download_datasets audit_datasets preprocess_datasets exploratory_data_analysis risk_prediction generate_all_figures generate_report run_all static_features shap_analysis
CONFIG ?= configs/pilot.yaml
RUN = uv run python -m urban_flooding --config $(CONFIG)
setup:
	uv sync
setup_full:
	uv sync --extra full
test:
	uv run pytest -q
demo:
	uv run python -m urban_flooding --config configs/demo.yaml all
download_datasets:
	$(RUN) download
audit_datasets:
	$(RUN) audit
static_features:
	$(RUN) static
preprocess_datasets:
	$(RUN) preprocess
exploratory_data_analysis:
	$(RUN) analyze
risk_prediction:
	$(RUN) train
shap_analysis:
	$(RUN) explain
generate_all_figures:
	$(RUN) figures
generate_report:
	$(RUN) report
run_all:
	$(RUN) all

# ---- full multi-source analysis (data/raw/full -> outputs/full) ----
.PHONY: full_acquire full_build full_figures full
FIGS = fig01_overview fig02_hotspots fig03_rainfall fig04_storms fig05_topography fig06_built_green fig07_drainage fig08_floodnet fig09_reporting fig10_model fig11_equity
full_acquire:
	uv run python -m urban_flooding.acquire
full_build:
	uv run python -m urban_flooding.build grid hydro static rain storms reports panel floodnet
full_figures:
	for f in $(FIGS); do uv run python -m urban_flooding.figs.$$f || exit 1; done
full: full_acquire full_build full_figures
