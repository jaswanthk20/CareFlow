# Analytical decisions

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
