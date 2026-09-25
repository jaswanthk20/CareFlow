"""Patient-cluster uncertainty and empirical demo distributions, without fitting a clinical model."""
from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def main():
    out = ROOT/'EDA/outputs'
    with sqlite3.connect(f'file:{(out/"careflow.sqlite").as_posix()}?mode=ro', uri=True) as db:
        cohort = pd.read_sql_query('''SELECT e.subject_id, e.stay_id, e.disposition, e.arrival_transport,
           t.acuity, (julianday(e.outtime)-julianday(e.intime))*24 AS los_hours
           FROM edstays e LEFT JOIN triage t USING(subject_id, stay_id)''', db)
    assert cohort.stay_id.is_unique and cohort.los_hours.gt(0).all()
    cohort['acuity'] = cohort.acuity.fillna('Missing').astype(str)
    histogram = pd.cut(cohort.los_hours, [0, 2, 4, 6, 8, 12, 24, 48, np.inf], right=False)
    histogram.value_counts(sort=False).rename_axis('los_band_hours').reset_index(name='stays').to_csv(out/'mimic_los_histogram.csv', index=False)
    empirical = cohort.groupby(['acuity', 'disposition'], dropna=False).agg(stays=('stay_id', 'size'), patients=('subject_id', 'nunique')).reset_index()
    empirical['joint_probability'] = empirical.stays/len(cohort)
    empirical['probability_within_acuity'] = empirical.stays/empirical.groupby('acuity').stays.transform('sum')
    empirical['record_type'] = 'derived_demo_distribution'
    empirical.to_csv(out/'mimic_empirical_joint_distribution.csv', index=False)
    rng = np.random.default_rng(914)
    patients = cohort.subject_id.unique()
    estimates = []
    groups = [('all', 'All stays', np.ones(len(cohort), dtype=bool))]
    for name in ['acuity', 'disposition', 'arrival_transport']:
        groups += [(name, value, cohort[name].eq(value)) for value in sorted(cohort[name].dropna().unique())]
    # Patient multiplicities preserve each selected patient's full encounter cluster.
    draws = [pd.Series(rng.choice(patients, len(patients), replace=True)).value_counts() for _ in range(1000)]
    for dimension, value, mask in groups:
        part = cohort.loc[mask]
        weighted_means, admitted_rates = [], []
        for counts in draws:
            weights = part.subject_id.map(counts).fillna(0).to_numpy()
            if weights.sum() > 0:
                weighted_means.append(np.average(part.los_hours, weights=weights))
                admitted_rates.append(np.average(part.disposition.eq('ADMITTED'), weights=weights))
        small = part.subject_id.nunique() < 10
        estimates.append({'dimension': dimension, 'group': value, 'stays': len(part),
            'patients': part.subject_id.nunique(), 'mean_los_hours': part.los_hours.mean(),
            'median_los_hours': part.los_hours.median(), 'p90_los_hours': part.los_hours.quantile(.9),
            'admitted_disposition_rate': part.disposition.eq('ADMITTED').mean(),
            'mean_los_lower95': np.nan if small else np.quantile(weighted_means, .025),
            'mean_los_upper95': np.nan if small else np.quantile(weighted_means, .975),
            'admitted_rate_lower95': np.nan if small else np.quantile(admitted_rates, .025),
            'admitted_rate_upper95': np.nan if small else np.quantile(admitted_rates, .975),
            'interval_status': 'suppressed_fewer_than_10_patients' if small else 'patient_cluster_percentile_bootstrap',
            'resamples': 1000})
    pd.DataFrame(estimates).to_csv(out/'mimic_cluster_uncertainty.csv', index=False)
    print('Patient-flow distributions and patient-cluster intervals generated.')


if __name__ == '__main__':
    main()
