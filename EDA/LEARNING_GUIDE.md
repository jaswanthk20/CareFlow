# How to learn from this EDA

## Reproduce the analysis

From the CareFlow project folder, with Python 3.10 or newer:

```powershell
python -m venv EDA/.venv
EDA/.venv/Scripts/python -m pip install -r EDA/requirements.txt
EDA/.venv/Scripts/python EDA/run_eda.py
```

The script reads `Dataset/`, regenerates `EDA/outputs/`, and leaves raw files and the project README unchanged. The README is a reviewed interpretation of this run; review it again if the inputs change. `source_manifest.csv` records input sizes and SHA-256 hashes. `summary.json` records the runtime versions. Output files with the same names are replaced when rerunning.

## Reading order

1. Read `table_inventory.csv` and `column_quality.csv`. Ask what one row means before choosing a denominator. An encounter is not a patient, a medication record, or a vital-sign measurement.
2. Read `parse_dryad()` in `run_eda.py`. The spreadsheet is a pivot table. Each date has an adjacent repeated total column, and each year has 24 hour rows. Summing everything would double-count. `dryad_reconciliation.csv` verifies the parser against the source totals.
3. Compare `arrivals_observed` and `arrivals_zero_assumption` in `dryad_hourly.csv`. The first retains blanks. The second fills a blank hour only within a day that has a recorded subtotal. Entirely absent dates remain unknown. `excel_row` and `excel_column` are one-based source coordinates.
4. Inspect `dryad_missing_dates.csv`, `dryad_distributions.csv`, the calendar summaries, and `arrival_patterns.png`. A nonblank-only mean excludes possible zero-arrival hours and can overstate demand. The zero scenario is conditional, not verified truth.
5. Read `analyze_mimic()`. LOS is departure minus arrival, measured in hours. `validate='one_to_one'` protects the stay-to-triage join. Event tables are summarized separately to avoid multiplying encounters.
6. Open `analysis.sql` alongside `sql_*.csv`. Learn `LEFT JOIN`, `GROUP BY`, and the common-table expression. SQLite's `julianday()` computes the same LOS independently of Python. The script checks agreement on encounter count, mean LOS, total arrivals, and all 24 hourly arrival means.
7. Study missingness, event timing, range flags, and pain categories before deciding which variables to use. No outliers or duplicates are automatically removed. No clinical free text is exported into the README.
8. Read the README's leakage and simulation sections before building a model. The full-period EDA summaries are exploratory; they must not become fitted features in a held-out evaluation.

## Output conventions

- Counts refer to rows unless explicitly named `patients`, `stays`, or `hours`.
- `percent_stays` uses all encounters as its denominator. Missing categories are retained.
- Quantiles use pandas' default linear interpolation. Standard deviations use the sample denominator (`ddof=1`).
- LOS summaries retain the full observed tail. Small groups are descriptive and should not be ranked as reliable operational effects.
- `dryad_future_window_totals.csv` describes the sum in the next 6, 12, or 24 hours, starting at the next hour. These overlapping windows are not independent samples and are not forecast evaluation results.
- Weekday coding is Monday=0 through Sunday=6. Hours are source wall-clock labels, without a verified timezone or daylight-saving convention.
- Event records can legitimately share a timestamp. Repeated `(stay_id, charttime)` is a diagnostic, not a declaration of duplicate records.
- Vital range screens are deliberately broad analyst-defined flags. Temperature is screened on the documented Fahrenheit scale. Screening does not establish clinical validity, and values are retained for review.
- `careflow.sqlite` contains local source tables, including patient identifiers and text, and is excluded from Git. The data already present in the repository were not untracked or deleted.
- The supplied MIMIC `SHA256SUMS.txt` refers to compressed `.csv.gz` files. Those archives are not present locally, so their hashes cannot be compared to extracted CSV bytes. The run manifest fingerprints the actual local files; it does not certify archive provenance.

## Changes to raw-data organization

`Datasets/` was renamed to the requested `Dataset/`. Source files, their extraction subfolders, the license, and the supplied checksum file were preserved. Recursive discovery handles the existing `edstays.csv/edstays.csv` style paths. No downloads were necessary because both datasets were already extracted.
