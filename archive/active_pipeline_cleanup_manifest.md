# Active Pipeline Cleanup Manifest

This file records legacy modules that are no longer part of the active
`run_auto_analysis.py` pipeline after the whitelist consolidation.

## Active Runtime Chain

- `run_auto_analysis.py`
- `src/agent/dataset_selector_service.py`
- `src/agent/disease_analysis_agent.py`
- `src/agent/llm_client.py`
- `src/agent/runtime_config.py`
- `src/agent/whitelist_repository.py`
- `src/agent/prompts.py`
- `src/agent/plot_generator.py`
- `src/data_extraction/geo_downloader.py`
- `data/geo_whitelist.csv`

## Legacy Files Safe To Archive

Move these into `archive/active_pipeline_legacy/` when convenient:

- `src/agent/llm_integration.py`
- `src/agent/disease_selector.py`
- `src/agent/config.py`
- `src/agent/analysis_strategies.py`
- `src/agent/logger.py`

## Legacy Files To Review Before Archiving

These are not part of the active auto-analysis path. `geo_validator.py` remains
in the active tree for lightweight dataset validation, while the others below
have now been archived under `archive/src_legacy/`:

- `src/agent/geo_validator.py`
- `src/data_extraction/download_go_annotations.py`
- `src/data_extraction/download_kegg_mappings.py`
- `src/data_extraction/download_gse50425_platform.py`
- `src/analysis/`
- `src/classification/`
- `src/visualization/`
- `src/models/`
- `src/preprocessing/`
- `src/config/`

## Documentation To Update

- `README.md`
- `fetch_geo_whitelist.py` comments that still mention updating `src/agent/config.py`
