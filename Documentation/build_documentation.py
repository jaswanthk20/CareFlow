"""Generate the case study, Tableau instructions from saved results."""
import json
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT/'Documentation'


def table(frame):
    columns = list(frame.columns)
    def cell(value):
        return f'{value:.3f}' if isinstance(value, float) else str(value)
    return '\n'.join(['| '+' | '.join(columns)+' |', '| '+' | '.join(['---']*len(columns))+' |']+
                     ['| '+' | '.join(cell(value) for value in row)+' |' for row in frame.itertuples(index=False, name=None)])


def main():
    DOC.mkdir(exist_ok=True)
    summary = json.loads((ROOT/'EDA/outputs/summary.json').read_text())
    audit = json.loads((ROOT/'EDA/outputs/audit_summary.json').read_text())
    metrics = pd.read_csv(ROOT/'Forecasting/outputs/model_metrics.csv')
    selected = pd.read_csv(ROOT/'Forecasting/outputs/selected_models.csv')
    test = metrics[metrics.split.eq('test')].merge(selected[['horizon_hours','model']], on=['horizon_hours','model'])
    test = test[test.horizon_hours.isin([6,12,24])]
    patient = pd.read_csv(ROOT/'EDA/outputs/mimic_cluster_uncertainty.csv')
    overall = patient[patient.dimension.eq('all')].iloc[0]
    simulation = pd.read_csv(ROOT/'Simulation/outputs/scenario_summary.csv')
    simcheck = json.loads((ROOT/'Simulation/outputs/validation.json').read_text())
    comparison = simulation[simulation.metric.eq('mean_wait_hours') & simulation.scenario.isin(
        ['baseline','treatment_capacity_20','triage_capacity_3','boarding_duration_half','treatment_duration_minus20pct'])].copy()
    comparison = comparison[['scenario','mean','mean_lower95','mean_upper95','change_vs_baseline']]
    for c in comparison.columns[1:]: comparison[c] *= 60
    comparison.columns = ['Scenario','Mean wait minutes','Lower95 minutes','Upper95 minutes','Change minutes']
    forecast_table = test[['horizon_hours','model','n','mae','rmse','bias']].copy()
    forecast_table.columns = ['Horizon hours','Selected model','Scored targets','MAE','RMSE','Bias']
    readme = (ROOT/'README.md').read_text(encoding='utf-8')
    # Preserve the original introduction and the substantial generated EDA section.
    prefix = readme.split('## Project Idea')[0] if '## Project Idea' in readme else readme.split('## Problem Statement')[0]
    prefix = prefix.replace('Later backtests must use chronological training, validation and test periods with features available at each forecast origin. Simulation is not ready: stage times, capacity, queue discipline, starting census and downstream constraints are missing. Any hypothetical experiment requires documented, explicitly approved scenario inputs. No occupancy, waiting-time reduction, bottleneck or intervention result has been generated.',
        'Backtests now use chronological periods with features available at each forecast origin. The simulation uses explicitly documented hypothetical inputs because stage times, capacity and downstream constraints are missing. Its occupancy, queues and intervention comparisons are model outputs, not observations of either hospital.')
    prefix = prefix.replace('The [forecast coverage table](EDA/outputs/dryad_observed_forecasting_coverage.csv)',
        'The [forecast coverage table](EDA/outputs/dryad_observed_forecasting_coverage.csv)')
    body = f'''## Problem Statement

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

{table(forecast_table)}

Source: `Forecasting/outputs/model_metrics.csv`, joined to `selected_models.csv`; primary test and primary horizons only. MAE and RMSE are arrivals per hourly target. Bias is forecast minus actual. Evaluation excludes unknown targets, so the result does not estimate accuracy over all hospital hours.

The selected model underpredicts on average. Regression candidates have lower errors on the test period, but did not meet the selection rule. This supports investigating drift and a new validation design using fresh data, not declaring the test-winning model validated. Error tables cover hour, weekday, high-demand targets and month. The high-demand threshold comes from initial training data. Peak strata are retrospective evaluation labels, not prediction inputs.

Prediction bands use absolute residuals from a separate calibration period and the frozen selected model. Their empirical coverage is in `interval_coverage.csv`; temporal dependence and drift prevent a guaranteed coverage claim. A day-block bootstrap compares paired errors, but does not capture all longer-term dependence. Similar errors across horizons are expected for a calendar-only forecast and are not evidence that longer-horizon forecasting is intrinsically easy.

## Patient Flow Analysis

The demo contains {summary['mimic']['stays']} stays for {summary['mimic']['patients']} distinct patients. Mean LOS is {overall.mean_los_hours:.3f} hours; its patient-cluster bootstrap interval is {overall.mean_los_lower95:.3f} to {overall.mean_los_upper95:.3f} hours. This describes uncertainty within the selected demo, not representativeness of the hospital population. Intervals for very small patient groups are suppressed.

Empirical acuity-disposition probabilities, LOS bands and group summaries are generated without fitting a clinical prediction model. The joint distribution preserves the observed relationship between acuity and final disposition. Final disposition is descriptive or an assigned simulation route, not an arrival-time predictor. Total LOS is never used as treatment-service time. Arrival transport and near-arrival triage fields are documented in the EDA; exact triage recording availability is not established.

## Simulation

The simulation is an explicitly hypothetical FIFO queueing experiment. The owner authorized continuation after the missing-input review. `Simulation/scenario_inputs.json` lists every operational value, unit, support and influence. No numerical service or resource parameter is claimed to come from hospital measurements or literature.

Arrivals use a Poisson process based on an archival forecast profile. That profile is repeated during warmup, which is a scenario construction, not a forecast of subsequent days. The model starts empty before warmup. Triage has generic servers; treatment resources remain occupied through an assumed boarding stage on the admitted route. The route probability is transferred from the MIMIC demo, so it may fit neither hospital. Acuity does not alter priority or service duration in this architecture.

Metrics reconcile arrivals, exits and remaining census. Queue, occupancy and resource use are time-weighted over the measurement window. Waiting and total time in system follow window-arrival patients through completion, including after the window ends. Exits include patients present at the start of measurement, so arrivals and exits need not be equal during the window.

## Intervention Experiments

{table(comparison)}

Source: `Simulation/outputs/scenario_summary.csv`, waiting-time metric converted from hours to minutes. These are hypothetical outcomes from {simcheck['replications']} runs per scenario. Mean intervals quantify Monte Carlo uncertainty only. Run quantiles are separately available. Parameter, population, forecast and structural uncertainty are not included in these intervals; scenario and warmup sensitivity outputs expose some of those dependencies.

Adding treatment capacity and reducing assumed stage durations are experiments, not operational recommendations. Resource costs, staffing feasibility, safety and treatment effectiveness are unmeasured. More capacity can lower utilization while reducing waiting. Adding triage capacity can reorder arrivals at the next queue: total wait increased in {simcheck['triage_total_wait_increase_runs']} individual paired runs even though triage waiting did not increase. This illustrates why stage-specific behavior matters.

Within this model, treatment and boarding share a constrained resource. The stage timeline and controlled parameter changes support that mechanism. `scenario_load.csv` compares expected offered workload with resource capacity. The lowest-capacity sensitivity exceeds average capacity, so its queue does not have a periodic steady state under these assumptions; its finite-window result depends on initialization and warmup. Results from that scenario must not be described as an equilibrium estimate. These mechanisms do not identify the bottleneck at a real ED. A fast-track experiment is deliberately omitted because routing and service-time information are unavailable and the low-acuity demo group is too sparse to estimate it defensibly.

## Dashboard

Seven reproducible page images and detailed manual build specifications are in `Tableau/mockups` and `Tableau/dashboard_spec`. The pages cover ED command center, demand patterns, patient flow, forecast performance, bottleneck intelligence, intervention lab, and data and methodology. The command center is an archival replay. No Tableau workbook was created.

`Tableau/dashboard_data/dataset_manifest.csv` defines each file's grain and source. `field_catalog.csv` records fields and missingness. Use separate logical data sources for incompatible grains. Patient identifiers and clinical free text are excluded from the dashboard extracts.

## Key Findings

- Reporting completeness is part of the analytical problem: {audit['unknown_hours']:,} calendar hours have unknown counts. Nonblank-only demand summaries cannot establish unconditional demand.
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
'''
    (ROOT/'README.md').write_text(prefix+body, encoding='utf-8')
    (DOC/'METHODS.md').write_text('''# Analytical decisions

## Demand targets and timestamp availability

An origin represents an issue time at an hour boundary. The count for the immediately preceding hour is assumed available then, with no reporting delay. Real deployment would require a measured reporting-latency policy. Horizon is the offset to the start of the target hour, not a rolling sum. Forecast paths include separate hourly targets; their individual intervals must not be added to obtain an interval for a cumulative total.

## Why the chronological split has four periods

Training fits candidates. Selection chooses model class using later data. Final candidates refit through the selection cutoff and remain fixed. Calibration sets prediction bands without fitting coefficients. Testing evaluates the frozen pipeline. Origin and target boundaries are separately enforced so a horizon does not bridge into a fitting period. Workbook months beyond the source's stated coverage are a supplemental evaluation, not pooled into the primary test. This conservative cutoff does not resolve the underlying discrepancy.

## Feature decisions

Calendar means are fitted on available historical observations. Cyclical hour terms represent smooth repeating patterns with a small interpretable basis; annual terms are exploratory. Weekday indicators permit non-sinusoidal weekday differences. Trend permits gradual change. The lag model uses completed-hour, previous-day, previous-week and complete trailing-day features. It trains on complete feature rows and falls back to the calendar regression when a required lag is unavailable. Fallback is a prediction route, not a replacement of missing observations. Momentum and rolling standard deviation were not added without validation evidence that the simpler features were insufficient.

The regression penalty is a fixed candidate choice applied after feature scaling learned on training rows. Only the intercept is unpenalized. Negative model predictions are clipped at zero. Model estimates remain fractional expected counts; they are not rounded before error scoring. The fixed relative improvement rule favors simplicity but is not a clinical threshold. No test-period winner is promoted after inspecting test results.

## EDA screening and inference

High-demand screening uses within-weekday-hour outer interquartile fences, retrospectively. These screens neither prove anomalous records nor identify causes. Missing dates break continuity and rolling windows. Full-period EDA statistics never become fitted forecasting baselines. Daily and weekly totals are only complete where all constituent hours are observed. A nonblank sum is labeled as observed arrivals, not total hospital volume.

LOS is outtime minus intime. No outlier is removed solely because it is long. Nonpositive durations fail a validity check. Administrative censoring and stage decomposition cannot be established from these tables alone. Bootstrap resampling selects patients with replacement and keeps their encounter clusters; encounter-weighted estimates are then recomputed. A selected educational demo does not become population-representative through bootstrapping. Sparse groups retain descriptive counts, with intervals suppressed below the documented patient-count threshold.

## Simulation behavior and estimands

The model uses FCFS/FIFO queues and non-preemptive resources. Triage completions are ordered before entry into the treatment queue, since variable service times allow overtaking. A treatment resource remains held during the assumed boarding stage. No finite admission-bed queue exists. There are no acuity priority effects, abandonment, staff schedules or clinical decisions. Empirical final disposition supplies a latent simulation route; it is not used as an observed real-time predictor.

Occupancy and queue lengths integrate time spent within the observation window. Resource use divides occupied resource-hours by available resource-hours. Throughput counts exits in the window, including warmup arrivals. Wait and time-in-system summarize patients arriving in the window and follow them to exit, avoiding artificial end-window censoring. Initial census plus arrivals minus exits equals ending census in every run.

Interventions share arrivals and underlying duration draws with baseline where possible. Arrival-rate sensitivity draws are different point processes and are labeled accordingly. Mean bootstrap intervals quantify simulation sampling uncertainty conditional on the inputs. Replication quantiles describe run variability. Warmup sensitivity explores empty-start dependence; it does not prove steady state. The independent low- and high-demand experiments examine direction of mean waiting, while exact conservation and feasible utilization are checked in every run.

Increasing triage capacity can alter the order of service jobs at treatment. Therefore total waiting is not required to decrease in every finite paired run; triage wait itself is checked. Treatment-capacity and duration interventions preserve treatment entry ordering and are checked for nonincreasing wait under shared inputs. This distinction was identified during validation and retained in the model documentation.

## Use and limitations

No chart is a clinical risk score. No regression coefficient is a causal effect. No intervention ranking measures clinical safety, cost effectiveness or hospital feasibility. A real pilot requires secure event ingestion, reporting-latency measurement, representative patient data, calibrated resources and workflow, a hospital validation team, prospective error monitoring and approval for the intended operational use.
''', encoding='utf-8')
    phase = '''# Phase decisions

| Phase | What we learned and evidence | Uncertainty | Decision enabled and next step |
| --- | --- | --- | --- |
| Audit | Existing Python, SQL and independent source checks were reusable | Provenance of extracted archives and source coverage remain incomplete | Preserve structure; extend existing scripts |
| EDA | Missingness differs by hour; demo LOS is heterogeneous; generated observed summaries and cluster intervals provide evidence | Blank semantics, selection and repeated encounters limit inference | Carry missingness into reporting; request source clarification |
| Analytical dataset | Complete calendar retains source coordinates and unknowns | Counts may arrive late in a real feed | Use explicit issue-time features; measure reporting delay before a pilot |
| Forecasting | Validation selects the calendar baseline; test shows bias and better regression results | One time split and drift limit generalization | Retain declared selection; evaluate updates on new data |
| Patient flow | Empirical joint distributions and patient-cluster intervals are reproducible | Demo is not representative and groups are sparse | Prefer descriptive modeling; seek larger representative data |
| Simulation | Conservation, stage constraints and sensitivity checks pass | Parameters and cross-hospital transfer are hypothetical | Use the experiment to understand mechanisms, not recommend staffing |
| Bottlenecks | Treatment and boarding share a constrained resource in the model | Architecture cannot attribute hospital congestion or acuity effects | Inspect stage measurements in a real setting |
| Interventions | Repeated comparisons show waiting and utilization tradeoffs | Costs, safety and implementation feasibility are absent | Do not name an operational optimum |
| Tableau | Aggregate contracts and seven reproducible images map each chart to data | Tableau workbook remains the owner's manual build | Recreate the pages with separate logical data sources |
| Validation | Rebuild, reconciliation, timing, disclosure and format checks are automated | Local pattern scans are not security certification | Review the validation report before sharing |
'''
    (DOC/'PHASE_DECISIONS.md').write_text(phase, encoding='utf-8')
    initial = (DOC/'PROJECT_AUDIT.md').read_text(encoding='utf-8')
    if not initial.startswith('> Historical'):
        initial = '> Historical initial-audit snapshot. Subsequent implementation is described in README.md and PHASE_DECISIONS.md. Statements about missing pipelines below refer to the initial audit.\n\n'+initial
    (DOC/'PROJECT_AUDIT.md').write_text(initial, encoding='utf-8')
    review = (DOC/'SIMULATION_INPUT_REVIEW.md').read_text(encoding='utf-8')
    if not review.startswith('> Historical'):
        review = '> Historical pre-experiment review. The owner subsequently requested the full build. The implemented hypothetical inputs are in Simulation/scenario_inputs.json; none is claimed as an observed hospital parameter.\n\n'+review
    (DOC/'SIMULATION_INPUT_REVIEW.md').write_text(review, encoding='utf-8')
    create_specs()
    print('Case study, methods, phase decisions, Tableau specifications generated.')


def create_specs():
    directory = ROOT/'Tableau/dashboard_spec'
    directory.mkdir(exist_ok=True)
    common = '''# Tableau implementation guide

Dashboard size: fixed 1600 by 1000 pixels. Use tiled horizontal and vertical containers, an approximately 56-pixel outer margin and 24-pixel gutters. Header uses the upper 180 pixels, KPI row the next 120 pixels, main charts approximately 355 pixels, and interpretation cards approximately 115 pixels near the bottom. Refer to the corresponding PNG for exact proportions. Pages use four KPI cards and two primary chart panels, with one small supporting chart only where useful.

Palette: background #F2F6F7, card white, text #173448, muted text #657985, teal #087F8C, secondary blue #4178B0, caution #BB7733, border #DCE5E8. Use Tableau Book or a comparable sans-serif; page titles about 27 points, KPIs 25 points, chart titles 12 points, body 10 or 11 points. Use restrained chart marks, light horizontal gridlines and consistent axis units. Cautions remain text, never decorative risk scores.

CSV files live in dashboard_data. Set dates and numeric fields explicitly using field_catalog.csv. All files are independent logical tables unless a relationship is declared. Model metrics may relate to selected_models by horizon_hours AND model where appropriate; do not multiply model metrics by joining to raw predictions. Patient summaries must be filtered to one dimension before display. Do not sum medians, percentiles or patient counts across groups. Use ATTR or MIN for a precomputed single-row KPI after its filter is set.

Primary horizon parameter: integer values 6, 12, 24, default 24. Scenario parameter: list of implemented scenario names, default baseline. These select precomputed data; moving a control does not run the simulator. Date filters on preaggregated month, hour or patient tables cannot recalculate results from another grain. Use the hourly_demand data source to build date-responsive demand worksheets and display the selected date denominator explicitly. The supplied demand aggregates support the fixed full-workbook mockup view.

Common calculations, using the matching data source:

```tableau
// hourly_demand
[Observed Hour] = IF ISNULL([arrivals_observed]) THEN 0 ELSE 1 END
[Observed Coverage] = SUM([Observed Hour]) / COUNT([timestamp])
[Observed Mean] = AVG([arrivals_observed])
// forecast_backtest
[Horizon Filter] = [horizon_hours] = [Horizon parameter]
[Error] = [forecast] - [actual]
[Absolute Error] = ABS([Error])
[MAE] = AVG([Absolute Error])
[RMSE] = SQRT(AVG([Error] * [Error]))
[Covered] = IF ISNULL([actual]) THEN NULL ELSE
  INT([actual] >= [lower90] AND [actual] <= [upper90]) END
[Interval Height] = [upper90] - [lower90]
// simulation_scenarios
[Wait Minutes] = IF [metric] = 'mean_wait_hours' THEN [mean] * 60 END
[Wait Lower Minutes] = IF [metric] = 'mean_wait_hours' THEN [mean_lower95] * 60 END
[Wait Upper Minutes] = IF [metric] = 'mean_wait_hours' THEN [mean_upper95] * 60 END
[Scenario Filter] = [scenario] = [Scenario parameter]
```

Create each named calculation as its own Tableau field. The bracketed field name at the left is the field's name, not part of the formula pasted into Tableau. Never use ZN on unknown arrivals or suppressed patient intervals. Format rates as percentages. Build uncertainty ribbons with a lower-bound Gantt mark sized by interval height and a synchronized dual-axis forecast line, or use reference bands for a selected target. Individual hourly bands do not define a cumulative-window band.

Navigation buttons link the seven pages. Dashboard filter actions apply only to compatible worksheets. Highlight actions can preserve comparison context instead of removing other scenarios. Include an always-visible source and evidence-type subtitle, and a tooltip reminder when a value is simulated or based on incomplete coverage. Never show MIMIC patient timestamps as a hospital calendar or occupancy timeline.

Acceptance checks: all figures reconcile with the CSVs; missing values remain unknown; horizon filters select hourly targets; scenario labels and intervals remain visible; axes retain units; source-specific filters never imply a cross-hospital join. No workbook is supplied because the owner will build it manually.
'''
    (directory/'00_BUILD_GUIDE.md').write_text(common, encoding='utf-8')
    pages = [
      ('01_ED_COMMAND_CENTER', 'ED command center', 'Identify the timing of forecast arrival demand in an archival replay.',
       [('Hourly KPI cards', 'forecast_path', 'horizon_hours = 6, 12 or 24; forecast; lower90; upper90', 'Text KPI; use separate fixed-horizon sheets'),
        ('Forecast curve and uncertainty', 'forecast_path', 'horizon_hours on columns; forecast on rows; lower90 and upper90 for band', 'Line and Gantt interval ribbon, synchronized axes'),
        ('Recent observed demand', 'hourly_demand', 'timestamp before origin; arrivals_observed', 'Line with gaps for unknown counts')],
       'Origin is the fixed archival replay. Display all hourly path targets; the three cards are point targets, not rolling sums. A different origin needs regenerated path data.',
       'Hover reports issue time, target start time, horizon, forecast, band and archival status. Selecting a target highlights the line and opens its detail tooltip. Link to forecast performance.',
       'Peak target: filter to the maximum forecast within the selected origin, retaining tied peaks. Expected peak is a model output, not a congestion threshold.'),
      ('02_DEMAND_PATTERNS', 'Demand patterns', 'Inspect recurring patterns alongside reporting completeness.',
       [('Weekday-hour heatmap', 'demand_heatmap', 'weekday rows; hour columns; mean_arrivals color; observed_hours and calendar_hours detail', 'Square heatmap, weekdays ordered Monday through Sunday'),
        ('Hour and coverage', 'demand_hour', 'hour columns; mean_arrivals and coverage_fraction on separate labeled axes', 'Dual-axis lines with unsynchronized units and explicit labels'),
        ('Monthly pattern', 'demand_month', 'month as date; mean_arrivals rows; coverage_fraction detail', 'Line')],
       'Full-workbook aggregates support the mockup. To enable date, weekend or year filters, recreate aggregations from hourly_demand and apply the same filter to every demand worksheet.',
       'Heatmap selection highlights the corresponding hour. Tooltip reports mean per recorded hour, observed hours, calendar hours and coverage. Link to data quality.',
       'Weekday: DATEPART(weekday, [timestamp], monday) - 1. Weekend: weekday >= 5. Use coverage as an accompanying denominator, not an operational risk category.'),
      ('03_PATIENT_FLOW', 'Patient flow', 'Describe LOS and patient mix without implying causal or population effects.',
       [('LOS distribution', 'los_histogram', 'los_band_hours ordered as provided; stays', 'Bar histogram with documented variable-width bins; bar height is count, not density'),
        ('Mean LOS by acuity', 'patient_flow', 'dimension = acuity; group; mean_los_hours; mean_los_lower95; mean_los_upper95; stays; patients', 'Dot and interval plot'),
        ('Disposition mix', 'patient_flow', 'dimension = disposition; group; stays', 'Bar; optionally group non-ADMITTED/non-HOME as Other recorded')],
       'Dimension selector can switch the dot plot between acuity, disposition and arrival_transport. Do not filter LOS histogram by acuity: that cross-tabulated histogram is not supplied. No calendar-date filter.',
       'Group highlights preserve all comparison groups. Tooltip reports stays, distinct patients, LOS metric, interval_status and selected-demo caveat. Sparse groups keep counts; do not draw missing intervals at zero.',
       'Overall KPIs use dimension = all. Percent admitted is admitted_disposition_rate. Do not substitute hospital-ID presence or average group medians.'),
      ('04_FORECAST_PERFORMANCE', 'Forecast performance', 'Evaluate trust, systematic bias and difficult target periods.',
       [('Primary horizon MAE cards', 'model_metrics plus selected_models', 'split = test; model matches selected model; horizons 6,12,24; mae; n', 'Text'),
        ('Actual versus forecast', 'forecast_backtest', 'split = test; horizon parameter; target_time; actual and forecast', 'Two lines, retaining gaps'),
        ('Model comparison', 'model_metrics', 'split = test; horizon parameter; model; mae', 'Horizontal bars; highlight declared selection'),
        ('Optional error inspection', 'forecast_errors', 'dimension = target_hour or target_weekday; value; mae; bias; n', 'Bar or dot replacing one panel, not adding clutter')],
       'Horizon and test-target date range. Keep selection, calibration, test and coverage_supplement explicitly separate. Filtering a date range requires recalculation from forecast_backtest rather than fixed model_metrics.',
       'Select a difficult target window to highlight the errors. Tooltip includes issue time, actual, forecast, signed error and target availability. Model comparison must not relabel the best test model as selected.',
       'MAE, RMSE and interval coverage calculations are in the common guide. Show only observed targets in error denominators; retain unknown targets on the time axis.'),
      ('05_BOTTLENECK_INTELLIGENCE', 'Bottleneck intelligence', 'Inspect stage contributions inside the hypothetical architecture.',
       [('Queue timeline', 'simulation_timeline', 'scenario parameter; hour; triage_queue and treatment_queue', 'Two lines'),
        ('Treatment resource occupation', 'simulation_timeline', 'scenario parameter; hour; treatment_in_service and boarding_in_resource', 'Stacked area'),
        ('State KPI cards', 'simulation_scenarios', 'scenario parameter; metric mean_queue, treatment_utilization, triage_utilization, mean_wait_hours; mean', 'Text')],
       'Scenario selector chooses precomputed experiments. The timeline hour is relative to the measured synthetic cycle, not a hospital clock. No patient or acuity filter.',
       'Hour selection highlights both stage panels. Tooltip states time-weighted mean, scenario, evidence type and number of runs. Navigation leads to the intervention comparison.',
       'Do not create a causal attribution percentage, clinical risk score or acuity contribution. Stage resource occupancy sums to treatment resource occupation within the architecture.'),
      ('06_INTERVENTION_LAB', 'Intervention lab', 'Compare waiting, queue, throughput and utilization tradeoffs.',
       [('Wait comparison', 'simulation_scenarios', 'metric = mean_wait_hours; scenario; mean, mean_lower95 and mean_upper95 multiplied by 60', 'Dot and interval'),
        ('Utilization comparison', 'simulation_scenarios', 'metric = treatment_utilization; scenario; mean and interval limits', 'Dot and interval, percentage axis'),
        ('Metric selector alternative', 'simulation_scenarios', 'metric parameter: mean_queue, exits, mean_occupancy or mean_time_in_system_hours', 'Replace utilization panel with selected metric'),
        ('Change detail', 'simulation_scenarios', 'change_vs_baseline; change_lower95; change_upper95; comparison', 'Tooltip or compact detail table')],
       'Scenario highlight selector and metric selector operate on existing rows. Baseline remains visible. Hypothetical capacity or duration sliders must not imply on-demand simulation; they require a new run.',
       'Highlight a scenario across the two plots. Tooltip states mean, mean interval, run_p05/run_p95, paired change and assumptions. Keep cost and safety unmeasured rather than giving them zero values.',
       'Difference is precomputed from paired runs when comparison = paired_common_inputs. Do not subtract confidence limits to construct a change interval. Baseline change is exactly zero.'),
      ('07_DATA_AND_METHODOLOGY', 'Data and methodology', 'Make provenance, limitations, timing and assumptions visible.',
       [('Source KPI cards', 'table_inventory and documented audit outputs', 'edstays row count; audit recorded hours; documented grain', 'Text'),
        ('Evaluation sequence', 'Forecasting/outputs/split_manifest.csv', 'split; first_origin; last_target; fit_target_cutoff', 'Gantt or clearly labeled text stages'),
        ('Missingness details', 'column_quality', 'table; column; missing; missing_pct', 'Text table or horizontal bar replacing one narrative panel'),
        ('Assumption summary', 'Simulation/scenario_inputs.json', 'name; baseline; unit; support; influence', 'Text panel; enter documented values only')],
       'Data-source selector can switch the missingness table. Show the record type and dataset grain for every source. No unsupported refresh-time badge.',
       'Source links open the original Dryad and PhysioNet pages. Documentation links open the methods and assumption register. Every other page links back here.',
       'No calculated risk or data-quality score. Counts and percentages retain their stated denominators. Display that MIMIC dates cannot define a concurrent hospital census.')]
    for filename, title, purpose, charts, filters, actions, calculations in pages:
        mapping = pd.DataFrame(charts, columns=['Chart','Source','Field mapping','Tableau type'])
        text = f'''# {title}

Purpose: {purpose}

## Charts and field mapping

{table(mapping)}

## Filters and parameters

{filters}

## Interactions and tooltips

{actions}

## Calculated fields

{calculations}

## Layout

Fixed 1600 by 1000. Follow the matching PNG and common build guide. Header and filters occupy roughly the top fifth; KPI row roughly one eighth; main chart area about one third; supporting interpretation uses the lower fifth. Keep generous gutters and a visible research-use footer. Tooltip content complements the chart but must not hide essential assumptions.

## Evidence and validation

Reconcile displayed values to their source rows. Keep observed, derived, predicted and simulated content explicitly labeled. This specification describes a manual Tableau build and does not imply a connected live dashboard.
'''
        (directory/f'{filename}.md').write_text(text, encoding='utf-8')




if __name__ == '__main__':
    main()
