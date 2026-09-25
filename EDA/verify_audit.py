"""Check the observed calendar using standard-library calculations."""
import csv
import json
from datetime import datetime, timedelta
from pathlib import Path


def rows(path):
    with path.open(newline='', encoding='utf-8') as stream:
        return list(csv.DictReader(stream))


def main():
    root = Path(__file__).resolve().parents[1]
    out = root / 'EDA' / 'outputs'
    calendar = rows(out / 'dryad_calendar_observed.csv')
    timestamps = [datetime.fromisoformat(row['timestamp']) for row in calendar]
    assert all(b-a == timedelta(hours=1) for a, b in zip(timestamps, timestamps[1:]))
    source = {row['timestamp']: row['arrivals_observed'] for row in rows(out / 'dryad_hourly.csv')}
    for row in calendar:
        assert row['arrivals_observed'] == source.get(row['timestamp'], '')
        assert (row['status'] == 'observed') == bool(row['arrivals_observed'])
    valid = [bool(row['arrivals_observed']) for row in calendar]
    for row in rows(out / 'dryad_observed_forecasting_coverage.csv'):
        horizon = int(row['horizon_hours'])
        point = sum(valid[horizon:])
        complete = sum(all(valid[i+1:i+horizon+1]) for i in range(len(valid)-horizon))
        assert point == int(row['origins_with_observed_point_target'])
        assert complete == int(row['origins_with_complete_future_window'])
    total = sum(float(row['arrivals_observed']) for row in calendar if row['arrivals_observed'])
    original = json.loads((out / 'summary.json').read_text())
    assert total == original['dryad']['total_arrivals']
    audit = json.loads((out / 'audit_summary.json').read_text())
    assert sum(valid) == audit['observed_hours']
    assert len(valid) - sum(valid) == audit['unknown_hours']
    for path in [root/'README.md', root/'Documentation/PROJECT_AUDIT.md', root/'Documentation/SIMULATION_INPUT_REVIEW.md']:
        content = path.read_text(encoding='utf-8')
        assert '\u2014' not in content
        assert '\ue200' not in content
    print('PASS: hourly continuity, unchanged counts and missing values, all forecast coverage windows, totals and document formatting.')


if __name__ == '__main__':
    main()
