# Tableau data contract

Use each aggregate file as a separate logical data source. Do not physically join aggregate tables at incompatible grains. The manifest defines one row in each file. The field catalog records types and missingness. No patient identifiers or clinical free text are included.

Blank CSV cells mean unknown or intentionally suppressed. Never convert missing arrivals or confidence limits to zero. Timestamp is a source wall-clock label without a verified timezone. Forecast origin is an archival issue time, not today. Hourly target counts become available only after their hour ends.

Patient-flow summaries describe the selected demo. Confidence intervals resample patient clusters, and intervals for fewer than ten distinct patients are suppressed. A patient can contribute to several groups. Group patient counts cannot be added into an overall unique count.

Simulation files contain hypothetical model outputs. Mean confidence limits describe Monte Carlo uncertainty; run quantiles describe variation across runs. Neither includes parameter, forecast, selection or structural uncertainty. Scenario metrics must not be summed across scenarios. Means of precomputed means require appropriate weights; use the overall row when available.

Rebuild with python Tableau/prepare_data.py after the analytical pipelines. The page specifications define filters and interactions. No Tableau workbook is included.
