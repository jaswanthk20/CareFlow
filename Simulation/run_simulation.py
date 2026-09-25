"""Hypothetical FIFO ED experiment. Operational inputs are assumptions, not hospital estimates."""
import heapq
import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'Simulation/outputs'


def overlap(start, end, left, right):
    return np.maximum(0, np.minimum(end, right)-np.maximum(start, left))


def lognormal(rng, mean, cv, n):
    sigma = np.sqrt(np.log(1+cv**2))
    return rng.lognormal(np.log(mean)-sigma**2/2, sigma, n)


def inputs(seed, rates, admitted_rate, warmup_days, stage_parameters):
    rng = np.random.default_rng(seed)
    hours = (warmup_days+1)*24
    arrivals = []
    for hour in range(hours):
        # Homogeneous Poisson within each hourly interval is a scenario assumption.
        count = rng.poisson(rates[hour % 24])
        arrivals.extend(hour+rng.uniform(0, 1, count))
    arrivals = np.sort(arrivals)
    n = len(arrivals)
    triage, treatment, boarding = [stage_parameters[name] for name in ['triage_duration','treatment_duration','boarding_duration']]
    return (arrivals, lognormal(rng, triage['baseline']/60, triage['cv'], n),
            lognormal(rng, treatment['baseline'], treatment['cv'], n),
            lognormal(rng, boarding['baseline'], boarding['cv'], n)*(rng.uniform(0, 1, n) < admitted_rate))


def simulate(data, treatment_capacity=16, triage_capacity=2, treatment_scale=1,
             boarding_scale=1, warmup_days=7):
    arrival, triage_duration, treatment_duration, boarding_duration = data
    n = len(arrival)
    triage_start, triage_end = np.zeros(n), np.zeros(n)
    servers = [0.0]*triage_capacity
    for i in range(n):
        free = heapq.heappop(servers)
        triage_start[i] = max(arrival[i], free)
        triage_end[i] = triage_start[i]+triage_duration[i]
        heapq.heappush(servers, triage_end[i])
    treatment_start, exit_time = np.zeros(n), np.zeros(n)
    servers = [0.0]*treatment_capacity
    for i in np.argsort(triage_end, kind='stable'):
        free = heapq.heappop(servers)
        treatment_start[i] = max(triage_end[i], free)
        exit_time[i] = treatment_start[i]+treatment_duration[i]*treatment_scale+boarding_duration[i]*boarding_scale
        heapq.heappush(servers, exit_time[i])
    left, right = warmup_days*24, (warmup_days+1)*24
    measured = (arrival >= left) & (arrival < right)
    count_arrivals = int(measured.sum())
    departures = int(((exit_time >= left) & (exit_time < right)).sum())
    initial = int(((arrival < left) & (exit_time >= left)).sum())
    remaining = int(((arrival < right) & (exit_time >= right)).sum())
    assert initial+count_arrivals-departures == remaining
    wait = triage_start-arrival+treatment_start-triage_end
    assert (wait >= -1e-12).all() and (exit_time >= treatment_start).all()
    result = {'arrivals': count_arrivals, 'exits': departures, 'initial_census': initial, 'ending_census': remaining,
        'mean_triage_wait_hours': (triage_start-arrival)[measured].mean(),
        'mean_treatment_wait_hours': (treatment_start-triage_end)[measured].mean(),
        'mean_wait_hours': wait[measured].mean(), 'p90_wait_hours': np.quantile(wait[measured], .9),
        'mean_time_in_system_hours': (exit_time-arrival)[measured].mean(),
        'mean_queue': (overlap(arrival, triage_start, left, right).sum()+overlap(triage_end, treatment_start, left, right).sum())/24,
        'mean_occupancy': overlap(arrival, exit_time, left, right).sum()/24,
        'treatment_utilization': overlap(treatment_start, exit_time, left, right).sum()/(24*treatment_capacity),
        'triage_utilization': overlap(triage_start, triage_end, left, right).sum()/(24*triage_capacity),
        'reconciliation_error': initial+count_arrivals-departures-remaining}
    assert 0 <= result['treatment_utilization'] <= 1+1e-12
    assert 0 <= result['triage_utilization'] <= 1+1e-12
    timeline = []
    for h in range(24):
        a, b = left+h, left+h+1
        timeline.append({'hour': h+1, 'mean_occupancy': overlap(arrival, exit_time, a, b).sum(),
            'mean_queue': overlap(arrival, triage_start, a, b).sum()+overlap(triage_end, treatment_start, a, b).sum(),
            'triage_queue': overlap(arrival, triage_start, a, b).sum(),
            'treatment_queue': overlap(triage_end, treatment_start, a, b).sum(),
            'treatment_in_service': overlap(treatment_start, treatment_start+treatment_duration*treatment_scale, a, b).sum(),
            'boarding_in_resource': overlap(treatment_start+treatment_duration*treatment_scale, exit_time, a, b).sum()})
    return result, timeline


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    registry = json.loads((ROOT/'Simulation/scenario_inputs.json').read_text())
    assert registry['status'] == 'hypothetical_experiment'
    assert registry['measured_hours'] == 24
    warmup = registry['warmup_days']
    parameters_by_name = {row['name']: row for row in registry['parameters']}
    baseline_parameters = {'treatment_capacity': parameters_by_name['treatment_capacity']['baseline'],
                           'triage_capacity': parameters_by_name['triage_capacity']['baseline'], 'warmup_days': warmup}
    path = pd.read_csv(ROOT/'Forecasting/outputs/archival_forecast_path.csv')
    rates = path.forecast.to_numpy()
    disposition = pd.read_csv(ROOT/'EDA/outputs/mimic_by_disposition.csv')
    admitted_rate = float(disposition.loc[disposition.disposition.eq('ADMITTED'), 'stays'].sum()/disposition.stays.sum())
    scenarios = registry['scenarios']
    loads = []
    for name, settings in list(scenarios.items())+[(f'arrival_multiplier_{factor}', {'arrival_multiplier': factor}) for factor in registry['arrival_multipliers']]:
        rate = rates.mean()*settings.get('arrival_multiplier', 1)
        work = parameters_by_name['treatment_duration']['baseline']*settings.get('treatment_scale', 1)+admitted_rate*parameters_by_name['boarding_duration']['baseline']*settings.get('boarding_scale', 1)
        capacity = settings.get('treatment_capacity', baseline_parameters['treatment_capacity'])
        ratio = rate*work/capacity
        loads.append({'scenario': name, 'mean_hourly_arrival_rate': rate,
            'expected_treatment_resource_hours_per_arrival': work, 'treatment_capacity': capacity,
            'average_offered_load_ratio': ratio,
            'interpretation': 'average_load_exceeds_capacity_no_periodic_steady_state' if ratio >= 1 else 'below_average_capacity_not_proof_of_short_waits',
            'record_type': 'derived_from_hypothetical_inputs'})
    pd.DataFrame(loads).to_csv(OUT/'scenario_load.csv', index=False)
    runs, timelines, validations = [], [], []
    for replication in range(registry['replications']):
        seed = 4000+replication
        data = inputs(seed, rates, admitted_rate, warmup, parameters_by_name)
        baseline, _ = simulate(data, **baseline_parameters)
        for name, parameters in scenarios.items():
            result, timeline = simulate(data, **(baseline_parameters | parameters))
            runs.append({'replication': replication, 'scenario': name, **result})
            timelines.extend({'replication': replication, 'scenario': name, **row} for row in timeline)
            if name in ['treatment_capacity_20', 'boarding_duration_half', 'treatment_duration_minus20pct']:
                # Pathwise monotonicity is checked on shared arrivals and service draws.
                assert result['mean_wait_hours'] <= baseline['mean_wait_hours']+1e-10
            if name == 'triage_capacity_3':
                # Extra triage capacity can reorder downstream arrivals and their job sizes.
                # Check the triage queue itself; total tandem-queue delay need not be pathwise monotone.
                assert result['mean_triage_wait_hours'] <= baseline['mean_triage_wait_hours']+1e-10
        for factor in registry['arrival_multipliers']:
            result, timeline = simulate(inputs(seed, rates*factor, admitted_rate, warmup, parameters_by_name), **baseline_parameters)
            name = f'arrival_multiplier_{factor}'
            runs.append({'replication': replication, 'scenario': name, **result})
            timelines.extend({'replication': replication, 'scenario': name, **row} for row in timeline)
        for days in registry['warmup_sensitivity_days']:
            result, _ = simulate(inputs(seed, rates, admitted_rate, days, parameters_by_name), **(baseline_parameters | {'warmup_days': days}))
            validations.append({'replication': replication, 'warmup_days': days, **result})
    runs = pd.DataFrame(runs)
    runs['record_type'] = 'hypothetical_simulation_output'
    runs.to_csv(OUT/'simulation_runs.csv', index=False)
    timeline = pd.DataFrame(timelines)
    columns = ['mean_occupancy', 'mean_queue', 'triage_queue', 'treatment_queue', 'treatment_in_service', 'boarding_in_resource']
    timeline.groupby(['scenario', 'hour'])[columns].mean().reset_index().to_csv(OUT/'simulation_timeline.csv', index=False)
    pd.DataFrame(validations).to_csv(OUT/'warmup_sensitivity.csv', index=False)
    summaries = []
    rng = np.random.default_rng(51)
    baseline = runs[runs.scenario.eq('baseline')].set_index('replication')
    metrics = ['mean_wait_hours', 'p90_wait_hours', 'mean_queue', 'mean_occupancy', 'exits',
               'treatment_utilization', 'triage_utilization', 'mean_time_in_system_hours', 'ending_census']
    for scenario, group in runs.groupby('scenario', sort=False):
        group = group.set_index('replication').sort_index()
        for metric in metrics:
            values = group[metric].to_numpy()
            difference = values-baseline.loc[group.index, metric].to_numpy()
            indices = rng.integers(0, len(values), (2000, len(values)))
            means = values[indices].mean(axis=1)
            changes = difference[indices].mean(axis=1)
            summaries.append({'scenario': scenario, 'metric': metric, 'mean': values.mean(),
                'mean_lower95': np.quantile(means, .025), 'mean_upper95': np.quantile(means, .975),
                'run_p05': np.quantile(values, .05), 'run_p95': np.quantile(values, .95),
                'change_vs_baseline': difference.mean(), 'change_lower95': np.quantile(changes, .025),
                'change_upper95': np.quantile(changes, .975), 'replications': len(values),
                'comparison': 'paired_common_inputs' if scenario in scenarios else 'different_arrival_processes_same_seed',
                'record_type': 'hypothetical_simulation_output'})
    pd.DataFrame(summaries).to_csv(OUT/'scenario_summary.csv', index=False)
    check = {'conservation_all_runs': bool(runs.reconciliation_error.eq(0).all()),
             'treatment_intervention_pathwise_monotonicity': True,
             'triage_queue_pathwise_monotonicity': True,
             'triage_total_wait_increase_runs': int((runs[runs.scenario.eq('triage_capacity_3')].set_index('replication').mean_wait_hours > baseline.mean_wait_hours+1e-10).sum()),
             'triage_order_effect': 'Triage server count can reorder entry to treatment; different service lengths may increase total wait in individual runs even when triage wait falls.',
             'replications': registry['replications'],
             'admitted_disposition_probability_demo': admitted_rate,
             'mean_hourly_arrival_rate_from_archival_forecast': float(rates.mean()),
             'forecast_origin': str(path.origin.iloc[0]), 'hospital_calibrated': False,
             'uncertainty_scope': 'Monte Carlo only. Parameter, forecast and population uncertainty not included.',
             'queue_priority': 'FIFO after triage; no acuity-based service effects',
             'censoring': 'Window-arrival patients followed through completion, including after window end',
             'arrival_stress_mean_wait_nondecreasing': bool(runs[runs.scenario.eq('arrival_multiplier_1.2')].mean_wait_hours.mean() >= baseline.mean_wait_hours.mean())}
    assert check['arrival_stress_mean_wait_nondecreasing']
    (OUT/'validation.json').write_text(json.dumps(check, indent=2)+'\n')
    print(json.dumps(check, indent=2))


if __name__ == '__main__':
    main()
