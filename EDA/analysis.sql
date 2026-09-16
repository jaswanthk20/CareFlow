-- SQLite queries executed by run_eda.py. Each result is saved as an aggregate CSV.
-- Join triage once per stay. Never join all event tables directly: doing so
-- multiplies rows and silently weights LOS toward heavily documented encounters.
-- name: sql_los_by_acuity
SELECT COALESCE(CAST(t.acuity AS TEXT), 'Missing') AS acuity,
       COUNT(*) AS stays,
       COUNT(DISTINCT e.subject_id) AS patients,
       AVG((julianday(e.outtime)-julianday(e.intime))*24) AS mean_los_hours,
       SUM(CASE WHEN e.disposition='ADMITTED' THEN 1 ELSE 0 END) AS admitted
FROM edstays e LEFT JOIN triage t USING (subject_id, stay_id)
GROUP BY t.acuity ORDER BY t.acuity;

-- name: sql_event_coverage
WITH event_counts AS (
  SELECT 'diagnosis' AS source, stay_id, COUNT(*) AS records FROM diagnosis GROUP BY stay_id
  UNION ALL SELECT 'medrecon', stay_id, COUNT(*) FROM medrecon GROUP BY stay_id
  UNION ALL SELECT 'pyxis', stay_id, COUNT(*) FROM pyxis GROUP BY stay_id
  UNION ALL SELECT 'vitalsign', stay_id, COUNT(*) FROM vitalsign GROUP BY stay_id
)
SELECT source, COUNT(*) AS stays_with_records, SUM(records) AS records,
       AVG(records) AS mean_records_per_documented_stay, MAX(records) AS max_records
FROM event_counts GROUP BY source;

-- name: sql_arrivals_by_hour
SELECT hour, COUNT(*) AS represented_hours, COUNT(arrivals_observed) AS nonblank_hours,
       AVG(arrivals_observed) AS mean_nonblank_only,
       AVG(arrivals_zero_assumption) AS mean_if_blank_is_zero,
       SUM(blank_cell) AS blank_hours
FROM arrivals WHERE day_has_total=1 GROUP BY hour ORDER BY hour;

-- name: sql_integrity
SELECT 'edstays_duplicate_stay_id' AS check_name, COUNT(*)-COUNT(DISTINCT stay_id) AS failures FROM edstays
UNION ALL SELECT 'triage_duplicate_stay_id', COUNT(*)-COUNT(DISTINCT stay_id) FROM triage
UNION ALL SELECT 'triage_orphan_stay', COUNT(*) FROM triage t LEFT JOIN edstays e USING(stay_id) WHERE e.stay_id IS NULL
UNION ALL SELECT 'nonpositive_los', COUNT(*) FROM edstays WHERE julianday(outtime)<=julianday(intime);
