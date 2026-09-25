> Historical initial-audit snapshot. Subsequent implementation is described in README.md and PHASE_DECISIONS.md. Statements about missing pipelines below refer to the initial audit.

# CareFlow project audit

## Scope and existing work

The project contains `Dataset`, `EDA`, `README.md`, `.gitignore` and Git metadata. The EDA folder already contains `run_eda.py`, `verify_eda.py`, `analysis.sql`, `requirements.txt`, `LEARNING_GUIDE.md`, generated CSV and JSON reports, figures and a local SQLite database. A local dependency folder is excluded from the project-content inventory. Git internals are not analytical deliverables.

The file-level inventory is generated in `EDA/outputs/project_file_inventory.csv`. Raw sources consist of a Dryad XLSX workbook and six MIMIC demo CSV tables, with license and checksum documentation. The README introduction has been preserved. No folders or raw files were moved or deleted.

## Verification completed

The existing EDA pipeline and independent verifier were executed before this audit was generated. Verification checked source hashes, every parsed hourly cell, missing-date calendar, independently computed LOS and SQLite reconciliation. The existing run reports 1,876 successful reconciliation checks. New calendar outputs retain 3,067 unknown hours. No forecasting or simulation pipeline exists yet.

## What needs improvement

1. Existing README autocorrelations and future-window totals previously omitted their blank-as-zero assumption. The EDA section now labels these legacy outputs and links observed-only alternatives.
2. The source study description and workbook date coverage differ. Neither should overwrite the other until reconciled with source documentation.
3. Hospital linkage and admitted disposition disagree. Both definitions are retained; a single admission label is not yet justified.
4. The learning guide previously said Python 3.10 or newer, but the verifier uses `hashlib.file_digest`, which requires a later runtime. The reproducible minimum is Python 3.11.
5. Existing chart panels and full-period summaries must not become forecasting inputs. Baselines and transformations must be fitted only on data available at the forecast origin.
6. EDA does not identify capacity constraints or stage-specific bottlenecks. Total LOS cannot substitute for service time in a capacity intervention model.

## What remains missing

Forecast models, chronological split manifests, horizon-specific backtests, patient-cluster uncertainty, externally supported operational parameters, simulation validation, intervention comparisons, Tableau data contracts and page mockups are not complete. These must not be described as project results.

## Responsible-use review

The currently tracked patient files are the openly distributed MIMIC demo. This differs from the credentialed full dataset. License obligations still apply. The local patient-level SQLite database is Git-ignored. Current ignore rules need explicit protection before any credentialed download is placed here. No publishing or Git commit was performed. Repository-history and comprehensive secret scans have not been completed, so this audit is not publication clearance.

The requested unfinished-work search found legitimate uses of sample, temperature and resample in analysis and documentation. They do not indicate invented data. The existing zero-filling scenario is an explicit assumption and is retained as legacy sensitivity work, not promoted to observed data.

## Phase decision

What we learned: useful reproducible EDA exists, but key source interpretations are unresolved.

Evidence: raw-cell checks, generated data-quality tables, source documentation and independent LOS calculations.

Uncertainty: meaning of workbook blanks, mismatch in study dates, representativeness of the demo and absence of operational stage measurements.

Decision enabled: retain and extend the existing analysis; do not claim a validated hospital demand or congestion product.

Next: resolve or explicitly bound Dryad target missingness, then evaluate chronological seasonal baselines. Keep MIMIC descriptive. Before simulation, review the missing-input register with the project owner.

## Sources

- Dryad: https://doi.org/10.5061/dryad.q57d4g4
- MIMIC demo: https://physionet.org/content/mimic-iv-ed-demo/2.2/
- MIMIC documentation, including patient-specific date shifting: https://physionet.org/content/mimic-iv-ed/2.2/
