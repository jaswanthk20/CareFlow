# Tableau implementation guide

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
