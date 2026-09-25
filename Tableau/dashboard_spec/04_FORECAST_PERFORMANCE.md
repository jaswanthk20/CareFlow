# Forecast performance

Purpose: Evaluate trust, systematic bias and difficult target periods.

## Charts and field mapping

| Chart | Source | Field mapping | Tableau type |
| --- | --- | --- | --- |
| Primary horizon MAE cards | model_metrics plus selected_models | split = test; model matches selected model; horizons 6,12,24; mae; n | Text |
| Actual versus forecast | forecast_backtest | split = test; horizon parameter; target_time; actual and forecast | Two lines, retaining gaps |
| Model comparison | model_metrics | split = test; horizon parameter; model; mae | Horizontal bars; highlight declared selection |
| Optional error inspection | forecast_errors | dimension = target_hour or target_weekday; value; mae; bias; n | Bar or dot replacing one panel, not adding clutter |

## Filters and parameters

Horizon and test-target date range. Keep selection, calibration, test and coverage_supplement explicitly separate. Filtering a date range requires recalculation from forecast_backtest rather than fixed model_metrics.

## Interactions and tooltips

Select a difficult target window to highlight the errors. Tooltip includes issue time, actual, forecast, signed error and target availability. Model comparison must not relabel the best test model as selected.

## Calculated fields

MAE, RMSE and interval coverage calculations are in the common guide. Show only observed targets in error denominators; retain unknown targets on the time axis.

## Layout

Fixed 1600 by 1000. Follow the matching PNG and common build guide. Header and filters occupy roughly the top fifth; KPI row roughly one eighth; main chart area about one third; supporting interpretation uses the lower fifth. Keep generous gutters and a visible research-use footer. Tooltip content complements the chart but must not hide essential assumptions.

## Evidence and validation

Reconcile displayed values to their source rows. Keep observed, derived, predicted and simulated content explicitly labeled. This specification describes a manual Tableau build and does not imply a connected live dashboard.
