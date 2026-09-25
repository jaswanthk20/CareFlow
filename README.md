# CareFlow

**CareFlow** is an in-progress research project exploring how emergency department data can be used to better understand and eventually predict short-term ED pressure.

The project is currently in the **problem-definition and data-understanding stage**.

The main idea is to investigate whether historical ED arrival patterns and patient-level ED information can be used to estimate how busy an emergency department may become over the next **6–24 hours**, while also considering patients who are already present in the department.

---

## Exploratory Data Analysis

### Data sources

The local sources are the [Dryad arrival workbook](https://doi.org/10.5061/dryad.q57d4g4) and [MIMIC-IV-ED demo](https://physionet.org/content/mimic-iv-ed-demo/2.2/). They describe different healthcare environments and cannot be joined as a hospital cohort. Source file fingerprints are recorded in [the manifest](EDA/outputs/source_manifest.csv).

### Data grain

Dryad is a pivot workbook. The parser derives one date-hour record from each year, date column and hour row, excluding repeated subtotal columns. MIMIC `edstays` has one row per ED stay; `triage` joins at that grain. The local files contain 222 stays for 64 patients. Event tables are summarized before joining to avoid multiplying encounters. See [table inventory](EDA/outputs/table_inventory.csv).

### Data quality

The workbook has 1,416 dates with totals, from 2014-01-01 through 2017-12-30. There are 44 dates without totals inside that interval, all at month end, and 2,011 blank hour cells within represented days. Across the full calendar, 31,973 hours have observed counts and 3,067 are unknown. Missing dates include dates absent from the workbook columns and dates present without a daily total. The [calendar dataset](EDA/outputs/dryad_calendar_observed.csv) distinguishes these conditions. It does not impute zeros.

All 1,876 existing workbook reconciliation checks passed. Zero source counts are not explicitly recorded. Subtotal agreement alone does not establish what blanks mean. Dryad's online description ends its study period in August, whereas the workbook includes later dates in the same final year. This unresolved discrepancy prevents treating workbook coverage as verified study coverage.

The existing blank-as-zero sensitivity outputs remain available for traceability. In particular, `dryad_lag_correlations.csv`, `dryad_future_window_totals.csv`, `dryad_calendar_months.csv` and `arrival_patterns.png` use that assumption. They are not observed-only results. New `dryad_observed_*` outputs retain missing values.

### ED demand patterns

Among recorded nonblank hours, mean arrivals are 4.441, median 4.000, standard deviation 2.581, and the observed range is 1 to 19. These are conditional on a count being recorded. If blanks include zero-arrival hours, these summaries overstate unconditional hourly demand. Hour, weekday, weekend, month and year summaries therefore include observed coverage alongside demand.

The retrospective high-demand screen flags 26 hours using an outer fence above the within-weekday-and-hour upper quartile plus three interquartile ranges. Of these, 0 have an adjacent flagged hour. These flags identify records for review, not confirmed anomalies or explanations. The rule uses full-period data and must never be reused as a fitted forecasting feature. See [screen output](EDA/outputs/dryad_retrospective_high_screen.csv).

### Patient flow characteristics

Observed ED LOS, calculated as departure minus arrival, has mean 8.096 hours, median 5.842 hours and upper-decile threshold 15.720 hours. There are 35 patients with repeat encounters. Results are encounter-weighted, with correlated stays from the same patient. These summaries do not establish population estimates. See [LOS output](EDA/outputs/mimic_los_distribution.csv) and the acuity, disposition and arrival-transport tables.

Recorded `ADMITTED` disposition occurs in 150 of 222 stays (67.6%). A hospital identifier is present for 172 stays (77.5%). These definitions disagree and must be reported separately rather than silently merged into an admission label. See [disposition and hospital linkage](EDA/outputs/mimic_disposition_hadm.csv).

### Operational implications

Calendar patterns warrant investigating seasonal demand baselines. The observed LOS tail warrants investigating patient-flow differences. Neither finding identifies a resource bottleneck: these files do not provide treatment capacity, staffing, service-stage durations, waiting time or boarding duration. Longer total LOS cannot be assigned to a particular stage or interpreted as hands-on treatment time.

### Important limitations

MIMIC dates are shifted separately by patient. They support within-patient elapsed time but not simultaneous hospital occupancy across patients. The demo is a selected subset, not a representative hospital sample. Final disposition, hospital linkage, discharge diagnoses, departure time and later events are unavailable as arrival-time predictors. Triage measurements are candidate near-arrival variables, but their exact availability time is not established by a timestamp in the triage table. Clinical screening flags in the existing EDA are analyst review rules, not validated physiological limits.

### What this suggests for forecasting and simulation

The [forecast coverage table](EDA/outputs/dryad_observed_forecasting_coverage.csv) distinguishes forecasting an individual future hour from summing a complete future window. It reports eligibility, not accuracy. A prototype can evaluate recorded target hours while retaining unknown targets, but its errors would be conditional on observed hours and cannot establish all-hour performance. Resolve blank semantics and source coverage before interpreting an operational demand forecast.

Backtests now use chronological periods with features available at each forecast origin. The simulation uses explicitly documented hypothetical inputs because stage times, capacity and downstream constraints are missing. Its occupancy, queues and intervention comparisons are model outputs, not observations of either hospital.

CareFlow is a research and operational decision intelligence prototype. Patient safety, privacy and interpretability take priority over a compelling dashboard.

---
## Problem Statement

Can an analyst forecast hourly ED arrival demand, describe patient flow, and use a transparent hypothetical model to investigate congestion mechanisms? The preserved introduction records the original project stage. The current implementation includes EDA, forecasting, patient-flow distributions, simulation experiments, Tableau extracts and page designs. It is not a live hospital system.

## Research Questions

- When does recorded ED demand occur, and where is reporting incomplete?
- How do observed stay durations and dispositions differ across the demo cohort?
- How accurately can future recorded hourly counts be predicted?
- Which constraints generate queues inside the hypothetical model?
- How do intervention effects trade off against resource utilization?

## Data Sources

The [Dryad workbook](https://doi.org/10.5061/dryad.q57d4g4) supports demand analysis. The [MIMIC-IV-ED demo](https://physionet.org/content/mimic-iv-ed-demo/2.2/) supports patient-level descriptions. The [source documentation](https://physionet.org/content/mimic-iv-ed/2.2/) explains patient-specific date shifting and table meanings. These are separate hospitals. The local source manifest records hashes. The supplied MIMIC archive checksums cannot authenticate extracted CSVs without the corresponding compressed files.

## Methodology

Evidence types remain separate: observed values, derived summaries, model predictions, hypothetical simulation outputs, assumptions and recommendations. The source discrepancy and unresolved blank semantics remain visible. Counts are not silently filled. Every table below is generated from saved analytical outputs by `Documentation/build_documentation.py`.

## Data Engineering

The Dryad pivot is unpivoted with source-cell coordinates and subtotal reconciliation. A complete hourly calendar distinguishes observed counts, blank cells and absent dates. `Dataset/processed/forecast_modeling_rows.csv.gz` stores features, target labels, origin and target times, and chronological split assignments for the primary horizons. Boundary exclusions are explicit. Target labels are never predictor columns. Stay-to-triage joins are one-to-one. Event-table aggregation avoids row multiplication. SQLite implements joins, group summaries and calendar transformations; Python handles workbook parsing, statistical analysis and models. See `EDA/analysis.sql` and `Tableau/dashboard_queries.sql`.

## Forecasting

The target is the number of arrivals in the hour beginning at forecast origin plus the stated horizon. The last count available at issue time belongs to the preceding hour. An hourly target is different from the cumulative arrivals over a future window. All models use that same timing convention.

Chronological design: initial training uses the earlier workbook years; selection uses the first half of the following year; final fitting ends at selection; calibration uses its second half; primary testing uses the first eight months of the final year. Exact timestamps and horizon boundaries are in `Forecasting/outputs/split_manifest.csv`. Later workbook dates are reported separately because they exceed the period stated by the source. Random splitting would let later demand patterns influence earlier predictions.

Candidates include a historical mean, hour mean, weekday-hour mean, previous-week target with a calendar fallback, calendar linear regression, calendar ridge regression and complete-case lag ridge regression with an explicit calendar fallback. Fourier terms represent cyclical time; weekday indicators and a linear trend stay interpretable. Lag features use only previous hours, a previous-day value, a previous-week value and a complete trailing-day mean. Unknown counts are not imputed. Fallback flags are retained.

A regression model must improve selection MAE over the best baseline by more than the documented relative threshold. This is an analyst complexity rule, not a healthcare tolerance. The selection chose the weekday-hour mean at the primary horizons. Test results do not retroactively select a different model.

| Horizon hours | Selected model | Scored targets | MAE | RMSE | Bias |
| --- | --- | --- | --- | --- | --- |
| 6 | weekday_hour_mean | 5410 | 1.778 | 2.380 | -0.860 |
| 12 | weekday_hour_mean | 5404 | 1.776 | 2.378 | -0.859 |
| 24 | weekday_hour_mean | 5392 | 1.773 | 2.375 | -0.857 |

Source: `Forecasting/outputs/model_metrics.csv`, joined to `selected_models.csv`; primary test and primary horizons only. MAE and RMSE are arrivals per hourly target. Bias is forecast minus actual. Evaluation excludes unknown targets, so the result does not estimate accuracy over all hospital hours.

The selected model underpredicts on average. Regression candidates have lower errors on the test period, but did not meet the selection rule. This supports investigating drift and a new validation design using fresh data, not declaring the test-winning model validated. Error tables cover hour, weekday, high-demand targets and month. The high-demand threshold comes from initial training data. Peak strata are retrospective evaluation labels, not prediction inputs.

Prediction bands use absolute residuals from a separate calibration period and the frozen selected model. Their empirical coverage is in `interval_coverage.csv`; temporal dependence and drift prevent a guaranteed coverage claim. A day-block bootstrap compares paired errors, but does not capture all longer-term dependence. Similar errors across horizons are expected for a calendar-only forecast and are not evidence that longer-horizon forecasting is intrinsically easy.

## Patient Flow Analysis

The demo contains 222 stays for 64 distinct patients. Mean LOS is 8.096 hours; its patient-cluster bootstrap interval is 6.782 to 9.595 hours. This describes uncertainty within the selected demo, not representativeness of the hospital population. Intervals for very small patient groups are suppressed.

Empirical acuity-disposition probabilities, LOS bands and group summaries are generated without fitting a clinical prediction model. The joint distribution preserves the observed relationship between acuity and final disposition. Final disposition is descriptive or an assigned simulation route, not an arrival-time predictor. Total LOS is never used as treatment-service time. Arrival transport and near-arrival triage fields are documented in the EDA; exact triage recording availability is not established.

## Simulation

The simulation is an explicitly hypothetical FIFO queueing experiment. The owner authorized continuation after the missing-input review. `Simulation/scenario_inputs.json` lists every operational value, unit, support and influence. No numerical service or resource parameter is claimed to come from hospital measurements or literature.

Arrivals use a Poisson process based on an archival forecast profile. That profile is repeated during warmup, which is a scenario construction, not a forecast of subsequent days. The model starts empty before warmup. Triage has generic servers; treatment resources remain occupied through an assumed boarding stage on the admitted route. The route probability is transferred from the MIMIC demo, so it may fit neither hospital. Acuity does not alter priority or service duration in this architecture.

Metrics reconcile arrivals, exits and remaining census. Queue, occupancy and resource use are time-weighted over the measurement window. Waiting and total time in system follow window-arrival patients through completion, including after the window ends. Exits include patients present at the start of measurement, so arrivals and exits need not be equal during the window.

## Intervention Experiments

| Scenario | Mean wait minutes | Lower95 minutes | Upper95 minutes | Change minutes |
| --- | --- | --- | --- | --- |
| baseline | 38.145 | 30.876 | 46.513 | 0.000 |
| treatment_capacity_20 | 6.049 | 3.922 | 8.586 | -32.096 |
| triage_capacity_3 | 37.778 | 30.666 | 46.047 | -0.368 |
| boarding_duration_half | 7.879 | 5.492 | 10.794 | -30.266 |
| treatment_duration_minus20pct | 15.179 | 11.140 | 19.721 | -22.966 |

Source: `Simulation/outputs/scenario_summary.csv`, waiting-time metric converted from hours to minutes. These are hypothetical outcomes from 80 runs per scenario. Mean intervals quantify Monte Carlo uncertainty only. Run quantiles are separately available. Parameter, population, forecast and structural uncertainty are not included in these intervals; scenario and warmup sensitivity outputs expose some of those dependencies.

Adding treatment capacity and reducing assumed stage durations are experiments, not operational recommendations. Resource costs, staffing feasibility, safety and treatment effectiveness are unmeasured. More capacity can lower utilization while reducing waiting. Adding triage capacity can reorder arrivals at the next queue: total wait increased in 8 individual paired runs even though triage waiting did not increase. This illustrates why stage-specific behavior matters.

Within this model, treatment and boarding share a constrained resource. The stage timeline and controlled parameter changes support that mechanism. `scenario_load.csv` compares expected offered workload with resource capacity. The lowest-capacity sensitivity exceeds average capacity, so its queue does not have a periodic steady state under these assumptions; its finite-window result depends on initialization and warmup. Results from that scenario must not be described as an equilibrium estimate. These mechanisms do not identify the bottleneck at a real ED. A fast-track experiment is deliberately omitted because routing and service-time information are unavailable and the low-acuity demo group is too sparse to estimate it defensibly.

## Dashboard

Seven reproducible page images and detailed manual build specifications are in `Tableau/mockups` and `Tableau/dashboard_spec`. The pages cover ED command center, demand patterns, patient flow, forecast performance, bottleneck intelligence, intervention lab, and data and methodology. The command center is an archival replay. No Tableau workbook was created.

`Tableau/dashboard_data/dataset_manifest.csv` defines each file's grain and source. `field_catalog.csv` records fields and missingness. Use separate logical data sources for incompatible grains. Patient identifiers and clinical free text are excluded from the dashboard extracts.

## Key Findings

- Reporting completeness is part of the analytical problem: 3,067 calendar hours have unknown counts. Nonblank-only demand summaries cannot establish unconditional demand.
- The selected seasonal baseline is explainable but biased downward in the primary test period. Model simplicity does not remove the need to monitor drift.
- Patient flow is heterogeneous in the demo. Repeat patients and small groups limit inference; neither longer LOS nor final disposition explains a causal bottleneck.
- Hypothetical queue results depend strongly on resource and service assumptions. They are useful for understanding mechanisms and specifying needed data.

## Limitations

Source date coverage and blank semantics are unresolved. The Dryad timezone and daylight-saving convention are unverified. The selected MIMIC demo has shifted dates, repeat patients and small groups. No simultaneous hospital census is reconstructed. No treatment-stage measurements, staff roster, bed capacity, boarding decisions, costs or outcomes establish a real operational model. Absence of a clinical timestamp or abnormal flag is not evidence that a value is valid. No causality, patient benefit, live forecast reliability or staffing optimum is established.

## Responsible Use

CareFlow is a research and operational decision intelligence prototype. It is not clinical decision support and is not ready for hospital operational use. Raw sources remain local. The checked-in demo is publicly distributed, but its license still applies. Credentialed MIMIC data must never be committed. New raw datasets, patient databases, environments and credential files are ignored. Validation and a local secret-pattern scan do not constitute a security certification or permission to publish restricted data.

## Future Research

Resolve workbook metadata with the source owner. Obtain a representative patient cohort and hospital stage timestamps, capacity and roster data. Validate baseline updates on fresh periods, test interval stability and specify acceptable operational error. Calibrate service distributions and routing before testing real interventions. Review fairness, patient safety, workflow fit and privacy with hospital partners before any deployment.

## Technical Stack

Python, pandas, NumPy, matplotlib, openpyxl and SQLite. Regression uses small transparent numerical routines. The discrete-event model uses a priority queue of server availability times. Tableau is the intended manually authored presentation layer. Deep learning is not justified by the unresolved target interpretation, short historical span and limited incremental need.

## Repository Structure

```text
CareFlow/
  README.md
  run_all.py
  validate_project.py
  requirements.txt
  Dataset/                 source files and regenerated processed demand
  EDA/                     Python, SQL, profiles and distributions
  Forecasting/             models, split manifest, predictions and evaluation
  Simulation/              hypothetical parameters, experiments and checks
  Tableau/                 aggregate data, manual specifications and page images
  Documentation/           audit, methodology, phase decisions
```

## How to Reproduce the Analysis

Use Python compatible with the declared dependencies. From the project folder:

```powershell
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
.venv/Scripts/python run_all.py
```

Raw sources must already exist in `Dataset`. The pipeline discovers the supplied workbook and each ED table; it will fail rather than silently choose among duplicate sources. It does not download healthcare data. Existing generated outputs are regenerated in place. The README introduction remains preserved; generated sections are rebuilt from results. `Documentation/VALIDATION.json` records final checks and `Documentation/runtime_versions.json` records the libraries used. All paths resolve from script locations rather than a personal absolute path.
