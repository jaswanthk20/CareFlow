"""Audit existing CareFlow outputs and generate a source-aware EDA summary.

Run after run_eda.py and verify_eda.py. No missing counts are imputed.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd


def main():
    root = Path(__file__).resolve().parents[1]
    out = root / 'EDA' / 'outputs'
    docs = root / 'Documentation'
    docs.mkdir(exist_ok=True)
    summary = json.loads((out / 'summary.json').read_text())
    dryad = summary['dryad']
    mimic = summary['mimic']
    hourly = pd.read_csv(out / 'dryad_hourly.csv', parse_dates=['timestamp'])
    grid = pd.date_range(hourly.timestamp.min(), hourly.timestamp.max(), freq='h')
    clean = hourly.set_index('timestamp').reindex(grid).rename_axis('timestamp')
    clean['status'] = np.select(
        [clean.excel_row.isna(), clean.day_has_total.eq(0), clean.arrivals_observed.isna()],
        ['absent_date_column', 'date_without_total', 'blank_hour_cell'], default='observed')
    clean[['arrivals_observed', 'status', 'excel_row', 'excel_column']].to_csv(out / 'dryad_calendar_observed.csv')
    series = clean.arrivals_observed
    calendar = pd.DataFrame({'arrivals': series, 'hour': grid.hour,
                             'weekday': grid.dayofweek, 'weekend': grid.dayofweek >= 5,
                             'month': grid.month, 'year': grid.year}, index=grid)
    for group in ['hour', 'weekday', 'weekend', 'month', 'year']:
        table = calendar.groupby(group).arrivals.agg(['size', 'count', 'mean', 'median', 'std', 'min', 'max'])
        table['missing_hours'] = table['size'] - table['count']
        table['coverage_fraction'] = table['count'] / table['size']
        table.to_csv(out / f'dryad_observed_by_{group}.csv')
    calendar.groupby(['weekday', 'hour']).arrivals.agg(['size', 'count', 'mean', 'std']).to_csv(out / 'dryad_observed_weekday_hour.csv')
    rolling = pd.DataFrame({'timestamp': grid, 'arrivals_observed': series.to_numpy(),
                            'trailing_24h_mean_complete': series.rolling(24, min_periods=24).mean().to_numpy(),
                            'trailing_168h_mean_complete': series.rolling(168, min_periods=168).mean().to_numpy()})
    rolling.to_csv(out / 'dryad_observed_rolling.csv', index=False)
    runs = series.notna().ne(series.notna().shift()).cumsum()
    lengths = series.notna().groupby(runs).sum()
    feasibility = []
    for horizon in [6, 12, 24]:
        targets = series.shift(-horizon)
        future = series.shift(-1).rolling(horizon, min_periods=horizon).sum().shift(1-horizon)
        feasibility.append({'horizon_hours': horizon,
            'origins_with_observed_point_target': int(targets.notna().sum()),
            'origins_with_complete_future_window': int(future.notna().sum()),
            'origins_with_observed_origin_and_point_target': int((series.notna() & targets.notna()).sum()),
            'point_target_with_24h_origin_history': int((series.rolling(24, min_periods=24).count().eq(24) & targets.notna()).sum()),
            'interpretation': 'Coverage only; no model trained or accuracy measured'})
    pd.DataFrame(feasibility).to_csv(out / 'dryad_observed_forecasting_coverage.csv', index=False)
    correlations = []
    for lag in [1, 6, 12, 24, 48, 168]:
        correlations.append({'lag_hours': lag, 'paired_hours': int((series.notna() & series.shift(lag).notna()).sum()),
                             'correlation_observed_pairs': series.corr(series.shift(lag))})
    pd.DataFrame(correlations).to_csv(out / 'dryad_observed_lag_correlations.csv', index=False)
    # Historical screening compares each value with its own hour and weekday.
    # This retrospective flag is not a forecast feature or evidence of a cause.
    grouped = calendar.groupby(['weekday', 'hour']).arrivals
    q1, q3 = grouped.transform(lambda x: x.quantile(.25)), grouped.transform(lambda x: x.quantile(.75))
    upper = q3 + 3 * (q3-q1)
    flags = series.gt(upper)
    screen = pd.DataFrame({'timestamp': grid, 'arrivals_observed': series.to_numpy(),
                           'upper_outer_fence': upper.to_numpy(), 'high_screen_flag': flags.to_numpy(),
                           'adjacent_hour_also_flagged': (flags.shift(1, fill_value=False) | flags.shift(-1, fill_value=False)).to_numpy()})
    screen.to_csv(out / 'dryad_retrospective_high_screen.csv', index=False)
    files = []
    for path in sorted(root.rglob('*')):
        relative = path.relative_to(root)
        if any(part in {'.git', '.packages', '.venv', '__pycache__'} for part in relative.parts):
            continue
        if path.is_file():
            files.append({'path': relative.as_posix(), 'format': path.suffix, 'bytes': path.stat().st_size})
    pd.DataFrame(files).to_csv(out / 'project_file_inventory.csv', index=False)
    los = pd.read_csv(out / 'mimic_los_distribution.csv').iloc[0]
    dispositions = pd.read_csv(out / 'mimic_by_disposition.csv').set_index('disposition')
    linkage = pd.read_csv(out / 'mimic_disposition_hadm.csv')
    linked = int(linkage.has_hadm_id.sum())
    admitted = int(dispositions.loc['ADMITTED', 'stays'])
    observed = series.dropna()
    observed_hours = int(observed.size)
    quality = {
        'calendar_hours': len(grid), 'observed_hours': observed_hours,
        'unknown_hours': int(series.isna().sum()),
        'longest_observed_run_hours': int(lengths.max()),
        'high_screen_flags': int(flags.sum()),
        'high_flags_with_adjacent_flag': int((flags & (flags.shift(1, fill_value=False) | flags.shift(-1, fill_value=False))).sum()),
        'mimic_admitted_disposition_stays': admitted, 'mimic_linked_hospital_stays': linked}
    (out / 'audit_summary.json').write_text(json.dumps(quality, indent=2) + '\n')
    eda = f'''## Exploratory Data Analysis

### Data sources

The local sources are the [Dryad arrival workbook](https://doi.org/10.5061/dryad.q57d4g4) and [MIMIC-IV-ED demo](https://physionet.org/content/mimic-iv-ed-demo/2.2/). They describe different healthcare environments and cannot be joined as a hospital cohort. Source file fingerprints are recorded in [the manifest](EDA/outputs/source_manifest.csv).

### Data grain

Dryad is a pivot workbook. The parser derives one date-hour record from each year, date column and hour row, excluding repeated subtotal columns. MIMIC `edstays` has one row per ED stay; `triage` joins at that grain. The local files contain {mimic['stays']:,} stays for {mimic['patients']:,} patients. Event tables are summarized before joining to avoid multiplying encounters. See [table inventory](EDA/outputs/table_inventory.csv).

### Data quality

The workbook has {dryad['represented_days']:,} dates with totals, from {dryad['first_date']} through {dryad['last_date']}. There are {dryad['missing_dates']:,} dates without totals inside that interval, all at month end, and {dryad['blank_hours']:,} blank hour cells within represented days. Across the full calendar, {observed_hours:,} hours have observed counts and {quality['unknown_hours']:,} are unknown. Missing dates include dates absent from the workbook columns and dates present without a daily total. The [calendar dataset](EDA/outputs/dryad_calendar_observed.csv) distinguishes these conditions. It does not impute zeros.

All {dryad['reconciliation_checks']:,} existing workbook reconciliation checks passed. Zero source counts are not explicitly recorded. Subtotal agreement alone does not establish what blanks mean. Dryad's online description ends its study period in August, whereas the workbook includes later dates in the same final year. This unresolved discrepancy prevents treating workbook coverage as verified study coverage.

The existing blank-as-zero sensitivity outputs remain available for traceability. In particular, `dryad_lag_correlations.csv`, `dryad_future_window_totals.csv`, `dryad_calendar_months.csv` and `arrival_patterns.png` use that assumption. They are not observed-only results. New `dryad_observed_*` outputs retain missing values.

### ED demand patterns

Among recorded nonblank hours, mean arrivals are {observed.mean():.3f}, median {observed.median():.3f}, standard deviation {observed.std():.3f}, and the observed range is {observed.min():.0f} to {observed.max():.0f}. These are conditional on a count being recorded. If blanks include zero-arrival hours, these summaries overstate unconditional hourly demand. Hour, weekday, weekend, month and year summaries therefore include observed coverage alongside demand.

The retrospective high-demand screen flags {quality['high_screen_flags']:,} hours using an outer fence above the within-weekday-and-hour upper quartile plus three interquartile ranges. Of these, {quality['high_flags_with_adjacent_flag']:,} have an adjacent flagged hour. These flags identify records for review, not confirmed anomalies or explanations. The rule uses full-period data and must never be reused as a fitted forecasting feature. See [screen output](EDA/outputs/dryad_retrospective_high_screen.csv).

### Patient flow characteristics

Observed ED LOS, calculated as departure minus arrival, has mean {los['mean']:.3f} hours, median {los['median']:.3f} hours and upper-decile threshold {los['p90']:.3f} hours. There are {mimic['repeat_patients']:,} patients with repeat encounters. Results are encounter-weighted, with correlated stays from the same patient. These summaries do not establish population estimates. See [LOS output](EDA/outputs/mimic_los_distribution.csv) and the acuity, disposition and arrival-transport tables.

Recorded `ADMITTED` disposition occurs in {admitted:,} of {mimic['stays']:,} stays ({100*admitted/mimic['stays']:.1f}%). A hospital identifier is present for {linked:,} stays ({100*linked/mimic['stays']:.1f}%). These definitions disagree and must be reported separately rather than silently merged into an admission label. See [disposition and hospital linkage](EDA/outputs/mimic_disposition_hadm.csv).

### Operational implications

Calendar patterns warrant investigating seasonal demand baselines. The observed LOS tail warrants investigating patient-flow differences. Neither finding identifies a resource bottleneck: these files do not provide treatment capacity, staffing, service-stage durations, waiting time or boarding duration. Longer total LOS cannot be assigned to a particular stage or interpreted as hands-on treatment time.

### Important limitations

MIMIC dates are shifted separately by patient. They support within-patient elapsed time but not simultaneous hospital occupancy across patients. The demo is a selected subset, not a representative hospital sample. Final disposition, hospital linkage, discharge diagnoses, departure time and later events are unavailable as arrival-time predictors. Triage measurements are candidate near-arrival variables, but their exact availability time is not established by a timestamp in the triage table. Clinical screening flags in the existing EDA are analyst review rules, not validated physiological limits.

### What this suggests for forecasting and simulation

The [forecast coverage table](EDA/outputs/dryad_observed_forecasting_coverage.csv) distinguishes forecasting an individual future hour from summing a complete future window. It reports eligibility, not accuracy. A prototype can evaluate recorded target hours while retaining unknown targets, but its errors would be conditional on observed hours and cannot establish all-hour performance. Resolve blank semantics and source coverage before interpreting an operational demand forecast.

Later backtests must use chronological training, validation and test periods with features available at each forecast origin. Simulation is not ready: stage times, capacity, queue discipline, starting census and downstream constraints are missing. Any hypothetical experiment requires documented, explicitly approved scenario inputs. No occupancy, waiting-time reduction, bottleneck or intervention result has been generated.

CareFlow is a research and operational decision intelligence prototype. Patient safety, privacy and interpretability take priority over a compelling dashboard.

---
'''
    readme = (root / 'README.md').read_text(encoding='utf-8')
    start = readme.index('## Exploratory Data Analysis')
    end = readme.index('## Project Idea' if '## Project Idea' in readme else '## Problem Statement', start)
    readme = readme[:start] + eda + readme[end:]
    readme = readme.replace('**Current stage: Research and problem definition**', '**Current stage: Existing EDA reproduced; data interpretation issues remain open**')
    (root / 'README.md').write_text(readme, encoding='utf-8')
    (docs / 'PROJECT_AUDIT.md').write_text(f'''# CareFlow project audit

## Scope and existing work

The project contains `Dataset`, `EDA`, `README.md`, `.gitignore` and Git metadata. The EDA folder already contains `run_eda.py`, `verify_eda.py`, `analysis.sql`, `requirements.txt`, `LEARNING_GUIDE.md`, generated CSV and JSON reports, figures and a local SQLite database. A local dependency folder is excluded from the project-content inventory. Git internals are not analytical deliverables.

The file-level inventory is generated in `EDA/outputs/project_file_inventory.csv`. Raw sources consist of a Dryad XLSX workbook and six MIMIC demo CSV tables, with license and checksum documentation. The README introduction has been preserved. No folders or raw files were moved or deleted.

## Verification completed

The existing EDA pipeline and independent verifier were executed before this audit was generated. Verification checked source hashes, every parsed hourly cell, missing-date calendar, independently computed LOS and SQLite reconciliation. The existing run reports {dryad['reconciliation_checks']:,} successful reconciliation checks. New calendar outputs retain {quality['unknown_hours']:,} unknown hours. No forecasting or simulation pipeline exists yet.

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
''', encoding='utf-8')
    print(json.dumps(quality, indent=2))


if __name__ == '__main__':
    main()
