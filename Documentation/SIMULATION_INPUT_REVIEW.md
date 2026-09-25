> Historical pre-experiment review. The owner subsequently requested the full build. The implemented hypothetical inputs are in Simulation/scenario_inputs.json; none is claimed as an observed hospital parameter.

# Simulation input review

Status: not ready to parameterize. No simulation assumptions have been approved in this review.

The available files establish arrival counts where recorded and elapsed ED stay durations. They do not establish the operational stages required for a capacity-sensitive queueing model. This is the stopping point required by the project's working principles before introducing simulation assumptions.

| Missing input | Why required | Available support | How an assumption could change results |
| --- | --- | --- | --- |
| Triage service duration and resources | Creates a triage queue and resource utilization | Neither dataset measures this stage | Longer assumed duration or fewer resources can create a bottleneck by construction |
| Treatment service duration | Determines treatment resource occupation | Total ED LOS is observed, but includes other unmeasured stages | Using total LOS as service time can double-count waiting and exaggerate capacity requirements |
| Staff and treatment-space capacity by time | Defines resource constraints | Not provided in either local dataset | Chosen capacity largely determines simulated waits and utilization |
| Queue discipline and routing | Determines patient priority and pathways | Acuity and transport categories exist, but routing rules do not | Priority rules redistribute delays across groups |
| Boarding duration and admission capacity | Represents downstream delays | Final disposition exists; decision-to-admit and bed-ready times do not | Invented boarding delays can manufacture downstream admission pressure |
| Initial census and elapsed stay | Initializes a nonempty system | Cross-patient MIMIC timestamps cannot reconstruct simultaneous occupancy | Starting empty can understate early congestion |
| Arrival process within an hour | Schedules individual arrivals | Dryad has hourly counts only | Uniform or Poisson timing changes burstiness and queues |
| Cross-dataset transferability | Couples Iowa demand with Boston patient profiles | Different hospitals and a selected MIMIC demo | The resulting mix may represent neither site |
| Intervention magnitude and resource cost | Defines operationally comparable experiments | No staffing or cost data supplied | Arbitrary changes can determine the preferred scenario |

No literature-supported values have been selected. Source documentation supports the interpretation of the data, not numerical values for these missing inputs. Literature ranges would remain external assumptions, not observed CareFlow hospital facts.

The next decision is whether to obtain hospital operational measurements or authorize a clearly hypothetical teaching experiment with reviewed parameter ranges. Before execution, record each value or range, unit, source, rationale, sensitivity range and approval. Empirical total-LOS sampling alone can illustrate time in system, but cannot justify treatment-capacity, fast-track or staffing claims.

## Forecasting source questions

- Does a blank Dryad hour mean zero arrivals or unavailable information? Reconciliation suggests compatibility with zero, but the source page does not explicitly establish that interpretation.
- Why does the workbook contain dates beyond the study period stated online?
- Are very low daily totals complete days or incomplete reporting? Keep them until a documented exclusion rule is justified.
- What timezone and daylight-saving convention produced the source hour labels?

Recorded-target-only backtesting is possible without filling blanks. Its accuracy would apply to recorded hours, and its selection bias would remain unresolved. It should not be described as verified all-hour hospital forecasting.
