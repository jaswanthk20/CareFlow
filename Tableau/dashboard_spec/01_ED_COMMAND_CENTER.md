# ED command center

Purpose: Identify the timing of forecast arrival demand in an archival replay.

## Charts and field mapping

| Chart | Source | Field mapping | Tableau type |
| --- | --- | --- | --- |
| Hourly KPI cards | forecast_path | horizon_hours = 6, 12 or 24; forecast; lower90; upper90 | Text KPI; use separate fixed-horizon sheets |
| Forecast curve and uncertainty | forecast_path | horizon_hours on columns; forecast on rows; lower90 and upper90 for band | Line and Gantt interval ribbon, synchronized axes |
| Recent observed demand | hourly_demand | timestamp before origin; arrivals_observed | Line with gaps for unknown counts |

## Filters and parameters

Origin is the fixed archival replay. Display all hourly path targets; the three cards are point targets, not rolling sums. A different origin needs regenerated path data.

## Interactions and tooltips

Hover reports issue time, target start time, horizon, forecast, band and archival status. Selecting a target highlights the line and opens its detail tooltip. Link to forecast performance.

## Calculated fields

Peak target: filter to the maximum forecast within the selected origin, retaining tied peaks. Expected peak is a model output, not a congestion threshold.

## Layout

Fixed 1600 by 1000. Follow the matching PNG and common build guide. Header and filters occupy roughly the top fifth; KPI row roughly one eighth; main chart area about one third; supporting interpretation uses the lower fifth. Keep generous gutters and a visible research-use footer. Tooltip content complements the chart but must not hide essential assumptions.

## Evidence and validation

Reconcile displayed values to their source rows. Keep observed, derived, predicted and simulated content explicitly labeled. This specification describes a manual Tableau build and does not imply a connected live dashboard.
