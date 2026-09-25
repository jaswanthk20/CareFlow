"""Chronological hourly forecasts. Unknown arrival counts stay unknown."""
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Forecasting' / 'outputs'
MODELS = ['historical_mean', 'hour_mean', 'weekday_hour_mean', 'weekly_naive',
          'calendar_linear', 'calendar_ridge', 'lag_ridge']


def design(calendar, counts, horizon):
    target = calendar + pd.Timedelta(hours=horizon)
    # Calendar features are known at issue time. All observed lags precede issue time.
    features = {'intercept': np.ones(len(calendar)),
                'trend_years': (target - pd.Timestamp('2014-01-01')).total_seconds() / (365.25*86400)}
    for k in [1, 2, 3]:
        features[f'hour_sin_{k}'] = np.sin(2*np.pi*k*target.hour/24)
        features[f'hour_cos_{k}'] = np.cos(2*np.pi*k*target.hour/24)
    for day in range(1, 7):
        features[f'weekday_{day}'] = (target.dayofweek == day).astype(float)
    features['annual_sin'] = np.sin(2*np.pi*target.dayofyear/365.25)
    features['annual_cos'] = np.cos(2*np.pi*target.dayofyear/365.25)
    x = pd.DataFrame(features, index=calendar)
    lag = pd.DataFrame({'previous_hour': counts.shift(1), 'previous_day': counts.shift(24),
                        'previous_week': counts.shift(168),
                        'trailing_day_mean': counts.shift(1).rolling(24, min_periods=24).mean()}, index=calendar)
    return x, pd.concat([x, lag], axis=1), target


def linear_predict(x, y, train, penalty):
    complete = x.notna().all(axis=1)
    fit = train & y.notna() & complete
    a = x.loc[fit].to_numpy()
    scale = a.std(axis=0)
    scale[scale == 0] = 1
    a = a / scale
    regularizer = np.eye(a.shape[1]) * penalty
    regularizer[0, 0] = 0
    beta = np.linalg.lstsq(a.T @ a + regularizer, a.T @ y.loc[fit].to_numpy(), rcond=None)[0]
    prediction = pd.Series(np.nan, index=x.index)
    prediction.loc[complete] = np.maximum(0, (x.loc[complete].to_numpy()/scale) @ beta)
    return prediction, beta/scale, int(fit.sum())


def predict_all(calendar, counts, horizon, cutoff):
    x, lag, target = design(calendar, counts, horizon)
    y = counts.shift(-horizon)
    train = target <= cutoff
    historical = counts.loc[:cutoff]
    mean = historical.mean()
    hours = historical.groupby(historical.index.hour).mean()
    week = historical.groupby([historical.index.dayofweek, historical.index.hour]).mean()
    prediction = pd.DataFrame(index=calendar)
    prediction['historical_mean'] = mean
    prediction['hour_mean'] = [hours.get(t.hour, mean) for t in target]
    prediction['weekday_hour_mean'] = [week.get((t.dayofweek, t.hour), hours.get(t.hour, mean)) for t in target]
    # For all supported horizons, the previous-week target lies before issue time.
    assert horizon < 168
    seasonal = counts.shift(168-horizon)
    prediction['weekly_naive'] = seasonal.fillna(prediction.weekday_hour_mean)
    coefficients = []
    for name, matrix, penalty in [('calendar_linear', x, 0), ('calendar_ridge', x, 10), ('lag_ridge', lag, 10)]:
        result, beta, n = linear_predict(matrix, y, train, penalty)
        prediction[name] = result
        coefficients.extend({'horizon_hours': horizon, 'model': name, 'feature': feature,
                             'coefficient': value, 'training_rows': n, 'fit_target_cutoff': str(cutoff)}
                            for feature, value in zip(matrix.columns, beta))
    lag_fallback = prediction.lag_ridge.isna()
    prediction['lag_ridge'] = prediction.lag_ridge.fillna(prediction.calendar_ridge)
    return prediction, y, target, coefficients, lag_fallback, seasonal.isna()


def scores(actual, forecast):
    error = forecast-actual
    return {'n': int(error.notna().sum()), 'mae': float(error.abs().mean()),
            'rmse': float(np.sqrt((error**2).mean())), 'bias': float(error.mean())}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    raw = pd.read_csv(ROOT/'EDA/outputs/dryad_calendar_observed.csv', parse_dates=['timestamp'])
    series = raw.set_index('timestamp').arrivals_observed
    calendar = series.index
    series.to_csv(ROOT/'Dataset/processed/dryad_observed_hourly.csv')
    selection_end = pd.Timestamp('2016-06-30 23:00')
    train_end = pd.Timestamp('2015-12-31 23:00')
    split_rows, metrics, selected, predictions, coefs, daily_path, modeling_rows = [], [], [], [], [], [], []
    for h in range(1, 25):
        candidate, actual, target, _, _, _ = predict_all(calendar, series, h, train_end)
        selection = (calendar >= '2016-01-01') & (target <= selection_end) & actual.notna()
        ranking = []
        for name in MODELS:
            score = scores(actual[selection], candidate.loc[selection, name])
            ranking.append((name, score['mae']))
            metrics.append({'horizon_hours': h, 'split': 'selection', 'model': name, **score})
        baseline, base_mae = min(ranking[:4], key=lambda pair: pair[1])
        advanced, advanced_mae = min(ranking[4:], key=lambda pair: pair[1])
        winner = advanced if advanced_mae < base_mae*.98 else baseline
        # Refit through selection, then freeze. Calibration and test never fit coefficients.
        candidate, actual, target, coefficients, lag_fallback, naive_fallback = predict_all(calendar, series, h, selection_end)
        coefs.extend(coefficients)
        calibration = (calendar >= '2016-07-01') & (target <= pd.Timestamp('2016-12-31 23:00')) & actual.notna()
        test = (calendar >= '2017-01-01') & (target <= pd.Timestamp('2017-08-31 23:00'))
        supplement = (calendar >= '2017-09-01') & (target <= calendar.max())
        residual = (candidate.loc[calibration, winner]-actual[calibration]).abs()
        level = min(1, np.ceil((len(residual)+1)*.9)/len(residual))
        width = float(residual.quantile(level, interpolation='higher'))
        selected.append({'horizon_hours': h, 'model': winner, 'best_baseline': baseline,
                         'selection_baseline_mae': base_mae, 'selection_advanced_mae': advanced_mae,
                         'calibration_absolute_error_q90': width,
                         'selection_rule': 'Advanced must reduce validation MAE by more than 2 percent'})
        for label, mask in [('calibration', calibration), ('test', test), ('coverage_supplement', supplement)]:
            for name in MODELS:
                metrics.append({'horizon_hours': h, 'split': label, 'model': name,
                                **scores(actual[mask], candidate.loc[mask, name])})
            split_rows.append({'horizon_hours': h, 'split': label,
                               'first_origin': str(calendar[mask].min()), 'last_origin': str(calendar[mask].max()),
                               'first_target': str(target[mask].min()), 'last_target': str(target[mask].max()),
                               'eligible_origins': int(mask.sum()), 'observed_targets': int(actual[mask].notna().sum()),
                               'fit_target_cutoff': str(selection_end)})
        for label, mask in [('selection', selection)]:
            split_rows.append({'horizon_hours': h, 'split': label, 'first_origin': str(calendar[mask].min()),
                               'last_origin': str(calendar[mask].max()), 'first_target': str(target[mask].min()),
                               'last_target': str(target[mask].max()), 'eligible_origins': int(mask.sum()),
                               'observed_targets': int(actual[mask].notna().sum()), 'fit_target_cutoff': str(train_end)})
        if h in [6, 12, 24]:
            _, features, _ = design(calendar, series, h)
            features = features.copy()
            features['origin'] = calendar
            features['target_time'] = target
            features['horizon_hours'] = h
            features['target_arrivals'] = actual.to_numpy()
            features['split'] = np.select([target <= train_end,
                (calendar >= '2016-01-01') & (target <= selection_end),
                (calendar >= '2016-07-01') & (target <= pd.Timestamp('2016-12-31 23:00')),
                test, supplement], ['train','selection','calibration','test','coverage_supplement'],
                default='boundary_excluded')
            modeling_rows.append(features.reset_index(drop=True))
            for label, mask in [('calibration', calibration), ('test', test), ('coverage_supplement', supplement)]:
                frame = pd.DataFrame({'origin': calendar[mask], 'target_time': target[mask], 'horizon_hours': h,
                    'split': label, 'actual': actual[mask].to_numpy(), 'forecast': candidate.loc[mask, winner].to_numpy(),
                    'baseline_forecast': candidate.loc[mask, baseline].to_numpy(), 'model': winner,
                    'baseline_model': baseline, 'lower90': np.maximum(0, np.floor(candidate.loc[mask, winner]-width)),
                    'upper90': np.ceil(candidate.loc[mask, winner]+width),
                    'lag_fallback': lag_fallback[mask].to_numpy(), 'weekly_naive_fallback': naive_fallback[mask].to_numpy()})
                predictions.append(frame.reset_index(drop=True))
        origin = pd.Timestamp('2017-08-30 00:00')
        value = float(candidate.loc[origin, winner])
        daily_path.append({'origin': origin, 'target_time': origin+pd.Timedelta(hours=h),
                           'horizon_hours': h, 'forecast': value, 'lower90': max(0, np.floor(value-width)),
                           'upper90': np.ceil(value+width), 'model': winner,
                           'actual': actual.loc[origin], 'record_type': 'archival_prediction'})
        print(f'Horizon {h}: {winner}', flush=True)
    pd.DataFrame(metrics).to_csv(OUT/'model_metrics.csv', index=False)
    pd.DataFrame(selected).to_csv(OUT/'selected_models.csv', index=False)
    pd.DataFrame(split_rows).to_csv(OUT/'split_manifest.csv', index=False)
    pd.DataFrame(coefs).to_csv(OUT/'coefficients.csv', index=False)
    pd.DataFrame(daily_path).to_csv(OUT/'archival_forecast_path.csv', index=False)
    pd.concat(modeling_rows, ignore_index=True).to_csv(ROOT/'Dataset/processed/forecast_modeling_rows.csv.gz', index=False)
    predictions = pd.concat(predictions, ignore_index=True)
    predictions['error'] = predictions.forecast-predictions.actual
    predictions['absolute_error'] = predictions.error.abs()
    predictions['target_hour'] = predictions.target_time.dt.hour
    predictions['target_weekday'] = predictions.target_time.dt.dayofweek
    peak = series.loc[:train_end].quantile(.9)
    predictions['demand_group'] = np.where(predictions.actual.isna(), 'unknown',
        np.where(predictions.actual >= peak, 'at_or_above_training_p90', 'below_training_p90'))
    predictions.to_csv(OUT/'predictions.csv', index=False)
    test = predictions[predictions.split.eq('test') & predictions.actual.notna()].copy()
    errors = []
    for dimension in ['target_hour', 'target_weekday', 'demand_group']:
        for (h, value), group in test.groupby(['horizon_hours', dimension]):
            errors.append({'horizon_hours': h, 'dimension': dimension, 'value': value, **scores(group.actual, group.forecast)})
    pd.DataFrame(errors).to_csv(OUT/'error_segments.csv', index=False)
    intervals, blocks, month_rows = [], [], []
    for h, group in test.groupby('horizon_hours'):
        intervals.append({'horizon_hours': h, 'n': len(group),
                          'empirical_coverage': float(group.actual.between(group.lower90, group.upper90).mean()),
                          'mean_width': float((group.upper90-group.lower90).mean())})
        group = group.copy()
        group['day'] = group.target_time.dt.floor('D')
        group['month'] = group.target_time.dt.to_period('M').astype(str)
        for month, part in group.groupby('month'):
            month_rows.append({'horizon_hours': h, 'month': month, **scores(part.actual, part.forecast)})
        group['improvement'] = (group.baseline_forecast-group.actual).abs()-group.absolute_error
        daily = group.groupby('day').improvement.agg(['sum', 'count']).to_numpy()
        rng = np.random.default_rng(2718+h)
        bootstrap = []
        # Day blocks retain within-day error dependence; longer dependence remains a limitation.
        for _ in range(1000):
            draw = daily[rng.integers(0, len(daily), len(daily))]
            bootstrap.append(draw[:, 0].sum()/draw[:, 1].sum())
        blocks.append({'horizon_hours': h, 'mae_reduction_vs_baseline': group.improvement.mean(),
                       'bootstrap_lower95': np.quantile(bootstrap, .025),
                       'bootstrap_upper95': np.quantile(bootstrap, .975), 'resamples': 1000})
    pd.DataFrame(intervals).to_csv(OUT/'interval_coverage.csv', index=False)
    pd.DataFrame(blocks).to_csv(OUT/'paired_error_comparison.csv', index=False)
    pd.DataFrame(month_rows).to_csv(OUT/'monthly_test_metrics.csv', index=False)
    metadata = {'target': 'count in hour beginning origin plus horizon',
        'latest_available_count': 'hour beginning origin minus one hour',
        'primary_test': '2017-01-01 through 2017-08-31; later workbook coverage is supplemental',
        'unknown_policy': 'Keep counts missing. Score only recorded targets. No zero imputation.',
        'lag_policy': 'Complete-case lag regression; explicit calendar regression fallback. No lag imputation.',
        'interval_policy': 'Frozen-model calibration absolute residual quantile; empirical temporal coverage, not guaranteed coverage.',
        'model_policy': 'Validation MAE; advanced model requires more than 2 percent improvement over best baseline.',
        'refit_policy': 'Fit final candidates through June 2016; no calibration or test fitting.',
        'primary_horizons': [6, 12, 24], 'path_horizons': list(range(1, 25)),
        'high_demand_threshold_training_p90': float(peak),
        'limitations': ['Observed targets exclude all unknown hours', 'Blank semantics unresolved',
                       'Source date-range discrepancy', 'Single hospital and limited years',
                       'No real-time ingestion or clinical deployment validation']}
    (OUT/'methodology.json').write_text(json.dumps(metadata, indent=2)+'\n')


if __name__ == '__main__':
    (ROOT/'Dataset/processed').mkdir(parents=True, exist_ok=True)
    main()
