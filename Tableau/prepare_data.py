"""Create aggregate Tableau CSVs and a field catalog. No workbook is authored."""
import json
from pathlib import Path
import sqlite3

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'Tableau/dashboard_data'


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    exports = {
        'forecast_path': ('Forecasting/outputs/archival_forecast_path.csv', 'origin, horizon_hours', 'model prediction'),
        'forecast_backtest': ('Forecasting/outputs/predictions.csv', 'origin, horizon_hours, split', 'observed target and model prediction'),
        'model_metrics': ('Forecasting/outputs/model_metrics.csv', 'horizon_hours, split, model', 'derived evaluation'),
        'selected_models': ('Forecasting/outputs/selected_models.csv', 'horizon_hours', 'validation selection'),
        'forecast_errors': ('Forecasting/outputs/error_segments.csv', 'horizon_hours, dimension, value', 'derived evaluation'),
        'forecast_intervals': ('Forecasting/outputs/interval_coverage.csv', 'horizon_hours', 'derived evaluation'),
        'patient_flow': ('EDA/outputs/mimic_cluster_uncertainty.csv', 'dimension, group', 'derived demo distribution'),
        'los_histogram': ('EDA/outputs/mimic_los_histogram.csv', 'los_band_hours', 'derived demo distribution'),
        'acuity_disposition': ('EDA/outputs/mimic_empirical_joint_distribution.csv', 'acuity, disposition', 'derived demo distribution'),
        'simulation_scenarios': ('Simulation/outputs/scenario_summary.csv', 'scenario, metric', 'hypothetical simulation output'),
        'simulation_timeline': ('Simulation/outputs/simulation_timeline.csv', 'scenario, hour', 'hypothetical simulation output'),
        'simulation_load': ('Simulation/outputs/scenario_load.csv', 'scenario', 'derived hypothetical offered workload'),
        'table_inventory': ('EDA/outputs/table_inventory.csv', 'table', 'data quality'),
        'column_quality': ('EDA/outputs/column_quality.csv', 'table, column', 'data quality'),
        'hourly_demand': ('EDA/outputs/dryad_calendar_observed.csv', 'timestamp', 'observed count or unknown')}
    manifest, fields = [], []
    for name, (source, grain, kind) in exports.items():
        frame = pd.read_csv(ROOT/source)
        # Internal model fallback flags are retained as methodology fields, not operational KPIs.
        frame.to_csv(OUT/f'{name}.csv', index=False)
        manifest.append({'dataset': name, 'source': source, 'rows': len(frame), 'grain': grain, 'record_type': kind})
        for column in frame:
            fields.append({'dataset': name, 'field': column, 'dtype': str(frame[column].dtype),
                           'missing_rows': int(frame[column].isna().sum())})
    # SQL carries the calendar aggregation and denominators used by Tableau.
    with sqlite3.connect(ROOT/'EDA/outputs/careflow.sqlite') as db:
        pd.read_csv(OUT/'hourly_demand.csv').to_sql('observed_calendar', db, if_exists='replace', index=False)
        query = (ROOT/'Tableau/dashboard_queries.sql').read_text()
        for block in query.split('-- name: ')[1:]:
            name, sql = block.split('\n', 1)
            name = name.strip()
            frame = pd.read_sql_query(sql, db)
            frame.to_csv(OUT/f'{name}.csv', index=False)
            manifest.append({'dataset': name, 'source': 'Tableau/dashboard_queries.sql', 'rows': len(frame),
                             'grain': ', '.join(frame.columns[:2]) if name == 'demand_heatmap' else frame.columns[0],
                             'record_type': 'derived observed-only demand'})
            fields.extend({'dataset': name, 'field': column, 'dtype': str(frame[column].dtype),
                           'missing_rows': int(frame[column].isna().sum())} for column in frame)
    pd.DataFrame(manifest).to_csv(OUT/'dataset_manifest.csv', index=False)
    pd.DataFrame(fields).to_csv(OUT/'field_catalog.csv', index=False)
    (OUT/'README.md').write_text('''# Tableau data contract

Use each aggregate file as a separate logical data source. Do not physically join aggregate tables at incompatible grains. The manifest defines one row in each file. The field catalog records types and missingness. No patient identifiers or clinical free text are included.

Blank CSV cells mean unknown or intentionally suppressed. Never convert missing arrivals or confidence limits to zero. Timestamp is a source wall-clock label without a verified timezone. Forecast origin is an archival issue time, not today. Hourly target counts become available only after their hour ends.

Patient-flow summaries describe the selected demo. Confidence intervals resample patient clusters, and intervals for fewer than ten distinct patients are suppressed. A patient can contribute to several groups. Group patient counts cannot be added into an overall unique count.

Simulation files contain hypothetical model outputs. Mean confidence limits describe Monte Carlo uncertainty; run quantiles describe variation across runs. Neither includes parameter, forecast, selection or structural uncertainty. Scenario metrics must not be summed across scenarios. Means of precomputed means require appropriate weights; use the overall row when available.

Rebuild with python Tableau/prepare_data.py after the analytical pipelines. The page specifications define filters and interactions. No Tableau workbook is included.
''', encoding='utf-8')
    print(f'Prepared {len(manifest)} Tableau datasets.')


if __name__ == '__main__':
    main()
