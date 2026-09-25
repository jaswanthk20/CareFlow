-- name: demand_heatmap
SELECT (CAST(strftime('%w', timestamp) AS INTEGER)+6)%7 AS weekday,
       CAST(strftime('%H', timestamp) AS INTEGER) AS hour,
       COUNT(*) AS calendar_hours, COUNT(arrivals_observed) AS observed_hours,
       AVG(arrivals_observed) AS mean_arrivals,
       1.0*COUNT(arrivals_observed)/COUNT(*) AS coverage_fraction
FROM observed_calendar GROUP BY weekday, hour ORDER BY weekday, hour;

-- name: demand_hour
SELECT CAST(strftime('%H', timestamp) AS INTEGER) AS hour,
       COUNT(*) AS calendar_hours, COUNT(arrivals_observed) AS observed_hours,
       SUM(arrivals_observed) AS observed_arrivals, AVG(arrivals_observed) AS mean_arrivals,
       1.0*COUNT(arrivals_observed)/COUNT(*) AS coverage_fraction
FROM observed_calendar GROUP BY hour ORDER BY hour;

-- name: demand_month
SELECT strftime('%Y-%m', timestamp) AS month,
       COUNT(*) AS calendar_hours, COUNT(arrivals_observed) AS observed_hours,
       SUM(arrivals_observed) AS observed_arrivals, AVG(arrivals_observed) AS mean_arrivals,
       1.0*COUNT(arrivals_observed)/COUNT(*) AS coverage_fraction
FROM observed_calendar GROUP BY month ORDER BY month;

-- name: demand_week
SELECT date(timestamp, '-' || ((CAST(strftime('%w', timestamp) AS INTEGER)+6)%7) || ' days') AS week_start,
       COUNT(*) AS calendar_hours, COUNT(arrivals_observed) AS observed_hours,
       AVG(arrivals_observed) AS mean_arrivals,
       CASE WHEN COUNT(arrivals_observed)=168 THEN SUM(arrivals_observed) END AS complete_week_total,
       1.0*COUNT(arrivals_observed)/COUNT(*) AS coverage_fraction
FROM observed_calendar GROUP BY week_start ORDER BY week_start;
