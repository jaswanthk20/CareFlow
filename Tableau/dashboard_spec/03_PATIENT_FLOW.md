# Patient flow

Purpose: Describe LOS and patient mix without implying causal or population effects.

## Charts and field mapping

| Chart | Source | Field mapping | Tableau type |
| --- | --- | --- | --- |
| LOS distribution | los_histogram | los_band_hours ordered as provided; stays | Bar histogram with documented variable-width bins; bar height is count, not density |
| Mean LOS by acuity | patient_flow | dimension = acuity; group; mean_los_hours; mean_los_lower95; mean_los_upper95; stays; patients | Dot and interval plot |
| Disposition mix | patient_flow | dimension = disposition; group; stays | Bar; optionally group non-ADMITTED/non-HOME as Other recorded |

## Filters and parameters

Dimension selector can switch the dot plot between acuity, disposition and arrival_transport. Do not filter LOS histogram by acuity: that cross-tabulated histogram is not supplied. No calendar-date filter.

## Interactions and tooltips

Group highlights preserve all comparison groups. Tooltip reports stays, distinct patients, LOS metric, interval_status and selected-demo caveat. Sparse groups keep counts; do not draw missing intervals at zero.

## Calculated fields

Overall KPIs use dimension = all. Percent admitted is admitted_disposition_rate. Do not substitute hospital-ID presence or average group medians.

## Layout

Fixed 1600 by 1000. Follow the matching PNG and common build guide. Header and filters occupy roughly the top fifth; KPI row roughly one eighth; main chart area about one third; supporting interpretation uses the lower fifth. Keep generous gutters and a visible research-use footer. Tooltip content complements the chart but must not hide essential assumptions.

## Evidence and validation

Reconcile displayed values to their source rows. Keep observed, derived, predicted and simulated content explicitly labeled. This specification describes a manual Tableau build and does not imply a connected live dashboard.
