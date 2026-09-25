# Demand patterns

Purpose: Inspect recurring patterns alongside reporting completeness.

## Charts and field mapping

| Chart | Source | Field mapping | Tableau type |
| --- | --- | --- | --- |
| Weekday-hour heatmap | demand_heatmap | weekday rows; hour columns; mean_arrivals color; observed_hours and calendar_hours detail | Square heatmap, weekdays ordered Monday through Sunday |
| Hour and coverage | demand_hour | hour columns; mean_arrivals and coverage_fraction on separate labeled axes | Dual-axis lines with unsynchronized units and explicit labels |
| Monthly pattern | demand_month | month as date; mean_arrivals rows; coverage_fraction detail | Line |

## Filters and parameters

Full-workbook aggregates support the mockup. To enable date, weekend or year filters, recreate aggregations from hourly_demand and apply the same filter to every demand worksheet.

## Interactions and tooltips

Heatmap selection highlights the corresponding hour. Tooltip reports mean per recorded hour, observed hours, calendar hours and coverage. Link to data quality.

## Calculated fields

Weekday: DATEPART(weekday, [timestamp], monday) - 1. Weekend: weekday >= 5. Use coverage as an accompanying denominator, not an operational risk category.

## Layout

Fixed 1600 by 1000. Follow the matching PNG and common build guide. Header and filters occupy roughly the top fifth; KPI row roughly one eighth; main chart area about one third; supporting interpretation uses the lower fifth. Keep generous gutters and a visible research-use footer. Tooltip content complements the chart but must not hide essential assumptions.

## Evidence and validation

Reconcile displayed values to their source rows. Keep observed, derived, predicted and simulated content explicitly labeled. This specification describes a manual Tableau build and does not imply a connected live dashboard.
