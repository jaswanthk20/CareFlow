# Bottleneck intelligence

Purpose: Inspect stage contributions inside the hypothetical architecture.

## Charts and field mapping

| Chart | Source | Field mapping | Tableau type |
| --- | --- | --- | --- |
| Queue timeline | simulation_timeline | scenario parameter; hour; triage_queue and treatment_queue | Two lines |
| Treatment resource occupation | simulation_timeline | scenario parameter; hour; treatment_in_service and boarding_in_resource | Stacked area |
| State KPI cards | simulation_scenarios | scenario parameter; metric mean_queue, treatment_utilization, triage_utilization, mean_wait_hours; mean | Text |

## Filters and parameters

Scenario selector chooses precomputed experiments. The timeline hour is relative to the measured synthetic cycle, not a hospital clock. No patient or acuity filter.

## Interactions and tooltips

Hour selection highlights both stage panels. Tooltip states time-weighted mean, scenario, evidence type and number of runs. Navigation leads to the intervention comparison.

## Calculated fields

Do not create a causal attribution percentage, clinical risk score or acuity contribution. Stage resource occupancy sums to treatment resource occupation within the architecture.

## Layout

Fixed 1600 by 1000. Follow the matching PNG and common build guide. Header and filters occupy roughly the top fifth; KPI row roughly one eighth; main chart area about one third; supporting interpretation uses the lower fifth. Keep generous gutters and a visible research-use footer. Tooltip content complements the chart but must not hide essential assumptions.

## Evidence and validation

Reconcile displayed values to their source rows. Keep observed, derived, predicted and simulated content explicitly labeled. This specification describes a manual Tableau build and does not imply a connected live dashboard.
