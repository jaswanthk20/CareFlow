# Phase decisions

| Phase | What we learned and evidence | Uncertainty | Decision enabled and next step |
| --- | --- | --- | --- |
| Audit | Existing Python, SQL and independent source checks were reusable | Provenance of extracted archives and source coverage remain incomplete | Preserve structure; extend existing scripts |
| EDA | Missingness differs by hour; demo LOS is heterogeneous; generated observed summaries and cluster intervals provide evidence | Blank semantics, selection and repeated encounters limit inference | Carry missingness into reporting; request source clarification |
| Analytical dataset | Complete calendar retains source coordinates and unknowns | Counts may arrive late in a real feed | Use explicit issue-time features; measure reporting delay before a pilot |
| Forecasting | Validation selects the calendar baseline; test shows bias and better regression results | One time split and drift limit generalization | Retain declared selection; evaluate updates on new data |
| Patient flow | Empirical joint distributions and patient-cluster intervals are reproducible | Demo is not representative and groups are sparse | Prefer descriptive modeling; seek larger representative data |
| Simulation | Conservation, stage constraints and sensitivity checks pass | Parameters and cross-hospital transfer are hypothetical | Use the experiment to understand mechanisms, not recommend staffing |
| Bottlenecks | Treatment and boarding share a constrained resource in the model | Architecture cannot attribute hospital congestion or acuity effects | Inspect stage measurements in a real setting |
| Interventions | Repeated comparisons show waiting and utilization tradeoffs | Costs, safety and implementation feasibility are absent | Do not name an operational optimum |
| Tableau | Aggregate contracts and seven reproducible images map each chart to data | Tableau workbook remains the owner's manual build | Recreate the pages with separate logical data sources |
| Validation | Rebuild, reconciliation, timing, disclosure and format checks are automated | Local pattern scans are not security certification | Review the validation report before sharing |
