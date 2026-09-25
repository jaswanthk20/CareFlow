# Data and methodology

Purpose: Make provenance, limitations, timing and assumptions visible.

## Charts and field mapping

| Chart | Source | Field mapping | Tableau type |
| --- | --- | --- | --- |
| Source KPI cards | table_inventory and documented audit outputs | edstays row count; audit recorded hours; documented grain | Text |
| Evaluation sequence | Forecasting/outputs/split_manifest.csv | split; first_origin; last_target; fit_target_cutoff | Gantt or clearly labeled text stages |
| Missingness details | column_quality | table; column; missing; missing_pct | Text table or horizontal bar replacing one narrative panel |
| Assumption summary | Simulation/scenario_inputs.json | name; baseline; unit; support; influence | Text panel; enter documented values only |

## Filters and parameters

Data-source selector can switch the missingness table. Show the record type and dataset grain for every source. No unsupported refresh-time badge.

## Interactions and tooltips

Source links open the original Dryad and PhysioNet pages. Documentation links open the methods and assumption register. Every other page links back here.

## Calculated fields

No calculated risk or data-quality score. Counts and percentages retain their stated denominators. Display that MIMIC dates cannot define a concurrent hospital census.

## Layout

Fixed 1600 by 1000. Follow the matching PNG and common build guide. Header and filters occupy roughly the top fifth; KPI row roughly one eighth; main chart area about one third; supporting interpretation uses the lower fifth. Keep generous gutters and a visible research-use footer. Tooltip content complements the chart but must not hide essential assumptions.

## Evidence and validation

Reconcile displayed values to their source rows. Keep observed, derived, predicted and simulated content explicitly labeled. This specification describes a manual Tableau build and does not imply a connected live dashboard.
