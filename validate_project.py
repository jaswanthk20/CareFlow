"""Validate timing, reconciliation, simulation mechanics and disclosure boundaries."""
import hashlib
import importlib.util
import json
import platform
from pathlib import Path
import re
import subprocess

import matplotlib
import numpy as np
import pandas as pd
from PIL import Image

ROOT = Path(__file__).resolve().parent


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, ROOT/path)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


def main():
    checks = {}
    source = pd.read_csv(ROOT/'EDA/outputs/source_manifest.csv')
    for row in source.itertuples():
        assert 'processed' not in Path(row.path).parts
        with (ROOT/row.path).open('rb') as stream:
            assert hashlib.file_digest(stream, 'sha256').hexdigest() == row.sha256
    checks['source_hashes_unchanged'] = True
    forecasts = pd.read_csv(ROOT/'Forecasting/outputs/predictions.csv', parse_dates=['origin','target_time'])
    hourly = pd.read_csv(ROOT/'EDA/outputs/dryad_calendar_observed.csv', parse_dates=['timestamp']).set_index('timestamp').arrivals_observed
    assert forecasts[['origin','horizon_hours','split']].duplicated().sum() == 0
    assert ((forecasts.target_time-forecasts.origin).dt.total_seconds()/3600 == forecasts.horizon_hours).all()
    expected = hourly.reindex(forecasts.target_time).to_numpy()
    assert np.allclose(expected, forecasts.actual, equal_nan=True)
    assert (forecasts.forecast >= 0).all()
    checks['forecast_targets_match_source_and_horizon'] = True
    split = pd.read_csv(ROOT/'Forecasting/outputs/split_manifest.csv')
    assert (pd.to_datetime(split.first_origin) > pd.to_datetime(split.fit_target_cutoff)).all()
    assert pd.to_datetime(split.loc[split.split.eq('calibration'),'last_target']).max() < forecasts.loc[forecasts.split.eq('test'),'origin'].min()
    for h in [6,12,24]:
        part = forecasts[forecasts.horizon_hours.eq(h) & forecasts.split.eq('test')]
        metrics = pd.read_csv(ROOT/'Forecasting/outputs/model_metrics.csv')
        row = metrics[(metrics.horizon_hours.eq(h)) & metrics.split.eq('test') & metrics.model.eq(part.model.iloc[0])].iloc[0]
        assert np.isclose(row.mae, (part.forecast-part.actual).abs().mean())
        assert np.isclose(row.rmse, np.sqrt(((part.forecast-part.actual)**2).mean()))
    checks['chronological_boundaries_and_error_metrics'] = True
    modeling = pd.read_csv(ROOT/'Dataset/processed/forecast_modeling_rows.csv.gz', parse_dates=['origin','target_time'])
    assert not modeling[['origin','horizon_hours']].duplicated().any()
    assert set(modeling.horizon_hours) == {6,12,24}
    assert np.allclose(hourly.reindex(modeling.target_time).to_numpy(), modeling.target_arrivals, equal_nan=True)
    assert np.allclose(hourly.reindex(modeling.origin-pd.Timedelta(hours=1)).to_numpy(), modeling.previous_hour, equal_nan=True)
    assert modeling.loc[modeling.split.eq('train'),'target_time'].max() < modeling.loc[modeling.split.eq('selection'),'origin'].min()
    checks['saved_modeling_rows_and_available_lags_reconcile'] = True
    forecast_module = module('careflow_forecasting', 'Forecasting/run_forecasting.py')
    origin = pd.Timestamp('2017-03-10 00:00')
    changed = hourly.copy()
    changed.loc[origin:] = 1000
    for h in [6,12,24]:
        before = forecast_module.predict_all(hourly.index, hourly, h, pd.Timestamp('2016-06-30 23:00'))[0].loc[origin]
        after = forecast_module.predict_all(changed.index, changed, h, pd.Timestamp('2016-06-30 23:00'))[0].loc[origin]
        assert np.allclose(before, after)
    checks['future_perturbation_does_not_change_prior_origin_predictions'] = True
    simulation = module('careflow_simulation', 'Simulation/run_simulation.py')
    toy = (np.array([0.,0.]), np.array([1.,1.]), np.array([2.,2.]), np.array([0.,0.]))
    result, _ = simulation.simulate(toy, treatment_capacity=1, triage_capacity=1, warmup_days=0)
    assert result['exits'] == 2 and result['ending_census'] == 0
    assert np.isclose(result['mean_wait_hours'], 1)
    assert np.isclose(result['mean_time_in_system_hours'], 4)
    assert np.isclose(result['treatment_utilization'], 4/24)
    checks['hand_calculated_two_patient_queue'] = True
    runs = pd.read_csv(ROOT/'Simulation/outputs/simulation_runs.csv')
    assert (runs.initial_census+runs.arrivals-runs.exits == runs.ending_census).all()
    # Summing clipped floating-point durations can exceed one by machine precision.
    assert runs.treatment_utilization.between(-1e-12,1+1e-12).all() and runs.triage_utilization.between(-1e-12,1+1e-12).all()
    scenario_summary = pd.read_csv(ROOT/'Simulation/outputs/scenario_summary.csv')
    for row in scenario_summary.itertuples():
        assert np.isclose(row.mean, runs.loc[runs.scenario.eq(row.scenario), row.metric].mean())
    checks['all_simulation_runs_conserve_patients_and_reconcile'] = True
    manifest = pd.read_csv(ROOT/'Tableau/dashboard_data/dataset_manifest.csv')
    for row in manifest.itertuples():
        frame = pd.read_csv(ROOT/f'Tableau/dashboard_data/{row.dataset}.csv')
        assert len(frame) == row.rows
        keys = [column.strip() for column in row.grain.split(',')]
        assert frame[keys].duplicated().sum() == 0, row.dataset
        assert not {'subject_id','stay_id','hadm_id','chiefcomplaint','intime','outtime'}.intersection(frame.columns)
        if row.source.endswith('.csv'):
            pd.testing.assert_frame_equal(frame, pd.read_csv(ROOT/row.source), check_dtype=False)
    demand = pd.read_csv(ROOT/'Tableau/dashboard_data/demand_hour.csv')
    assert demand.observed_hours.sum() == hourly.notna().sum()
    assert demand.calendar_hours.sum() == len(hourly)
    assert np.isclose(demand.observed_arrivals.sum(), hourly.sum())
    checks['tableau_extracts_reconcile_and_exclude_patient_fields'] = True
    images = sorted((ROOT/'Tableau/mockups').glob('*.png'))
    assert len(images) == 7
    for image in images:
        with Image.open(image) as opened:
            assert opened.size == (1600,1000)
    checks['seven_mockup_images_with_specifications'] = len(list((ROOT/'Tableau/dashboard_spec').glob('0[1-7]_*.md'))) == 7
    assert checks['seven_mockup_images_with_specifications']
    readme = (ROOT/'README.md').read_text(encoding='utf-8')
    assert '## Exploratory Data Analysis' in readme and '## How to Reproduce' in readme
    selected = pd.read_csv(ROOT/'Forecasting/outputs/selected_models.csv')
    chosen = pd.read_csv(ROOT/'Forecasting/outputs/model_metrics.csv').merge(selected[['horizon_hours','model']], on=['horizon_hours','model'])
    for row in chosen[chosen.split.eq('test') & chosen.horizon_hours.isin([6,12,24])].itertuples():
        assert f'{row.mae:.3f}' in readme and f'{row.rmse:.3f}' in readme and f'{row.bias:.3f}' in readme
    checks['readme_forecast_numbers_match_generated_outputs'] = True
    paths = [p for p in ROOT.rglob('*') if p.is_file() and not any(part in {'.git','.packages','.venv','__pycache__'} for part in p.relative_to(ROOT).parts)]
    unfinished, secrets, bad_format = [], [], []
    scan = re.compile(r'TODO|FIXME|placeholder|dummy|sample|fake|hardcoded|temp', re.I)
    secret = re.compile(r'gh[pousr]_[A-Za-z0-9]{30,}|AKIA[0-9A-Z]{16}|-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----|sk-[A-Za-z0-9]{32,}')
    for path in paths:
        if path.suffix.lower() not in {'.py','.sql','.md','.json','.txt','.toml','.yml','.yaml','.env','.csv'}:
            continue
        content = path.read_text(encoding='utf-8', errors='replace')
        if secret.search(content): secrets.append(str(path.relative_to(ROOT)))
        if path.relative_to(ROOT).parts[0] != 'Dataset' and path.suffix != '.csv' and ('\u2014' in content or '\ue200' in content):
            bad_format.append(str(path.relative_to(ROOT)))
        if path.suffix == '.csv' or path.name in {'VALIDATION.json','SEARCH_REVIEW.csv'}: continue
        for line, text in enumerate(content.splitlines(), 1):
            for found in scan.finditer(text):
                term = found.group(0).lower()
                if term == 'sample': rationale = 'Sampling, resampling or selected-demo terminology; inspect context for empirical versus hypothetical use.'
                elif term == 'temp': rationale = 'Temperature, temporal terminology or variable text; not a temporary deliverable.'
                else: rationale = 'Search-pattern definition or explicit prohibition; inspect file and line.'
                unfinished.append({'file': str(path.relative_to(ROOT)), 'line': line, 'term': term, 'review': rationale})
    assert not secrets, f'Potential secrets found in {secrets}'
    assert not bad_format, f'Forbidden formatting found in {bad_format}'
    checks['text_scan_no_matching_secret_patterns_or_forbidden_format'] = True
    pd.DataFrame(unfinished, columns=['file','line','term','review']).to_csv(ROOT/'Documentation/SEARCH_REVIEW.csv', index=False)
    tracked = subprocess.check_output(['git','ls-files'], cwd=ROOT, text=True).splitlines()
    assert not any(p.endswith(('.sqlite','.sqlite3','.db','.env')) for p in tracked)
    tracked_mimic = [p for p in tracked if 'mimic' in p.lower() and p.lower().endswith(('.csv','.csv.gz')) and '/outputs/' not in p]
    assert all('demo' in p.lower() for p in tracked_mimic)
    # Inspect historical names without printing raw data or credentials.
    historical = subprocess.check_output(['git','log','--all','--format=','--name-only'], cwd=ROOT, text=True).splitlines()
    suspicious_history = sorted({p for p in historical if (p.endswith(('.sqlite','.sqlite3','.env')) or
        ('mimic' in p.lower() and 'demo' not in p.lower() and ('Dataset' in p or 'Datasets' in p)))})
    objects = subprocess.check_output(['git','rev-list','--objects','--all'], cwd=ROOT, text=True).splitlines()
    text_objects = {}
    for line in objects:
        if ' ' not in line: continue
        oid, name = line.split(' ', 1)
        if Path(name).suffix.lower() in {'.py','.sql','.md','.json','.txt','.toml','.yml','.yaml','.env','.csv'} or Path(name).name == '.gitignore':
            text_objects[oid] = name
    history_secret_paths = []
    historical_blobs_scanned = 0
    if text_objects:
        batch = subprocess.run(['git','cat-file','--batch'], input=('\n'.join(text_objects)+'\n').encode(),
                               cwd=ROOT, stdout=subprocess.PIPE, check=True).stdout
        position = 0
        for oid, name in text_objects.items():
            newline = batch.index(b'\n', position)
            header = batch[position:newline].decode().split()
            size = int(header[2])
            content = batch[newline+1:newline+1+size].decode('utf-8', errors='replace')
            # The source extraction includes directories whose names end in .csv.
            if header[1] == 'blob':
                historical_blobs_scanned += 1
                if secret.search(content): history_secret_paths.append(name)
            position = newline+1+size+1
    checks['historical_text_blobs_no_matching_secret_patterns'] = not history_secret_paths
    checks['tracked_raw_mimic_is_named_demo_only'] = True
    checks['history_filename_scan_no_restricted_data_indicators'] = not suspicious_history
    result = {'checks': checks, 'all_passed': all(checks.values()),
        'search_occurrences_reviewed': len(unfinished), 'potential_secret_files': secrets,
        'historical_text_blobs_scanned': historical_blobs_scanned, 'historical_potential_secret_paths': history_secret_paths,
        'history_paths_for_review': suspicious_history,
        'privacy_scope': 'Working-tree text and CSV pattern scan, historical text/CSV blob pattern scan and history filename review; not a security certification or binary-content review.',
        'simulation_scope': 'Hypothetical experiment; structural and parameter validity not established for a hospital.'}
    (ROOT/'Documentation/VALIDATION.json').write_text(json.dumps(result, indent=2)+'\n')
    (ROOT/'Documentation/runtime_versions.json').write_text(json.dumps({'python': platform.python_version(),
        'pandas': pd.__version__, 'numpy': np.__version__, 'matplotlib': matplotlib.__version__}, indent=2)+'\n')
    assert result['all_passed'], result
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
