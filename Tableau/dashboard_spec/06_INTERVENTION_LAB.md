# Intervention lab

Purpose: Compare waiting, queue, throughput and utilization tradeoffs.

## Charts and field mapping

| Chart | Source | Field mapping | Tableau type |
| --- | --- | --- | --- |
| Wait comparison | simulation_scenarios | metric = mean_wait_hours; scenario; mean, mean_lower95 and mean_upper95 multiplied by 60 | Dot and interval |
| Utilization comparison | simulation_scenarios | metric = treatment_utilization; scenario; mean and interval limits | Dot and interval, percentage axis |
| Metric selector alternative | simulation_scenarios | metric parameter: mean_queue, exits, mean_occupancy or mean_time_in_system_hours | Replace utilization panel with selected metric |
| Change detail | simulation_scenarios | change_vs_baseline; change_lower95; change_upper95; comparison | Tooltip or compact detail table |

## Filters and parameters

Scenario highlight selector and metric selector operate on existing rows. Baseline remains visible. Hypothetical capacity or duration sliders must not imply on-demand simulation; they require a new run.

## Interactions and tooltips

Highlight a scenario across the two plots. Tooltip states mean, mean interval, run_p05/run_p95, paired change and assumptions. Keep cost and safety unmeasured rather than giving them zero values.

## Calculated fields

Difference is precomputed from paired runs when comparison = paired_common_inputs. Do not subtract confidence limits to construct a change interval. Baseline change is exactly zero.

## Layout

Fixed 1600 by 1000. Follow the matching PNG and common build guide. Header and filters occupy roughly the top fifth; KPI row roughly one eighth; main chart area about one third; supporting interpretation uses the lower fifth. Keep generous gutters and a visible research-use footer. Tooltip content complements the chart but must not hide essential assumptions.

## Evidence and validation

Reconcile displayed values to their source rows. Keep observed, derived, predicted and simulated content explicitly labeled. This specification describes a manual Tableau build and does not imply a connected live dashboard.
