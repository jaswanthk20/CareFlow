"""Render Tableau-reproducible page designs using generated analytical outputs."""
import json
from pathlib import Path
import textwrap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'Tableau/dashboard_data'
OUT = ROOT/'Tableau/mockups'
INK, MUTED, TEAL, BLUE, AMBER = '#173448', '#657985', '#087f8c', '#4178b0', '#bb7733'
BG, BORDER = '#f2f6f7', '#dce5e8'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10, 'axes.labelcolor': MUTED,
                     'xtick.color': MUTED, 'ytick.color': MUTED, 'axes.edgecolor': BORDER,
                     'text.color': INK, 'axes.titlesize': 12, 'axes.titleweight': 'bold'})
PAGES = ['ED command center', 'Demand patterns', 'Patient flow', 'Forecast performance',
         'Bottleneck intelligence', 'Intervention lab', 'Data and methodology']


def read(name):
    return pd.read_csv(DATA/f'{name}.csv')


def card(fig, x, y, w, h):
    fig.add_artist(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.008,rounding_size=0.008',
                   transform=fig.transFigure, facecolor='white', edgecolor=BORDER, linewidth=.7, zorder=0))


def page(number, subtitle, filters):
    fig = plt.figure(figsize=(16, 10), dpi=100, facecolor=BG)
    fig.text(.035, .962, 'CAREFLOW', weight='bold', fontsize=15, color=TEAL)
    fig.text(.965, .963, 'RESEARCH & OPERATIONS  /  PROTOTYPE', ha='right', fontsize=9, color=MUTED)
    fig.text(.035, .905, PAGES[number-1], fontsize=27, weight='bold')
    fig.text(.035, .87, subtitle, fontsize=11, color=MUTED)
    fig.text(.035, .827, filters, fontsize=10, color=TEAL)
    fig.text(.035, .035, 'Historical research data  |  Unknown values retained  |  No clinical or operational deployment', fontsize=9, color=MUTED)
    fig.text(.965, .035, f'{number:02d} / 07', ha='right', fontsize=10, color=MUTED)
    return fig


def kpi(fig, x, label, value, note, width=.215):
    card(fig, x, .675, width, .108)
    fig.text(x+.012, .751, label.upper(), fontsize=9, color=MUTED, weight='bold')
    fig.text(x+.012, .707, value, fontsize=25, weight='bold')
    fig.text(x+.012, .683, note, fontsize=8.5, color=MUTED)


def panel(fig, bounds, title):
    x, y, w, h = bounds
    card(fig, x, y, w, h)
    fig.text(x+.014, y+h-.03, title, fontsize=12, weight='bold')
    ax = fig.add_axes([x+.04, y+.045, w-.065, h-.095], facecolor='white')
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='y', color=BORDER, alpha=.55, linewidth=.6)
    ax.set_axisbelow(True)
    return ax


def note(fig, x, y, w, title, text, color=TEAL):
    card(fig, x, y, w, .115)
    fig.text(x+.012, y+.083, title, color=color, weight='bold', fontsize=11)
    fig.text(x+.012, y+.062, textwrap.fill(text, int(w*165)), va='top', fontsize=10, color=MUTED, linespacing=1.5)


def save(fig, n):
    fig.savefig(OUT/f'{n:02d}_{PAGES[n-1].lower().replace(" ", "_")}.png', dpi=100)
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    forecast = read('forecast_path')
    hourly = read('demand_hour')
    metrics = read('model_metrics')
    patient = read('patient_flow')
    scenarios = read('simulation_scenarios')
    timeline = read('simulation_timeline')
    summary = json.loads((ROOT/'EDA/outputs/summary.json').read_text())
    audit = json.loads((ROOT/'EDA/outputs/audit_summary.json').read_text())
    n, p = summary['mimic']['stays'], summary['mimic']['patients']
    fig = page(1, 'Archival forecast replay. Each value predicts one future hour, not a cumulative window.',
               'ISSUED  30 AUG 2017, 00:00     |     VIEW  Next 24 hourly targets     |     BAND  Calibration-based 90%')
    for x, h in zip([.035, .28, .525], [6, 12, 24]):
        row = forecast[forecast.horizon_hours.eq(h)].iloc[0]
        kpi(fig, x, f'Hour at +{h}h', f'{row.forecast:.1f}', f'Arrivals / hour  |  Band {row.lower90:.0f} to {row.upper90:.0f}')
    peak = forecast.loc[forecast.forecast.idxmax()]
    kpi(fig, .77, 'Expected peak target', f'+{int(peak.horizon_hours)}h', f'{peak.forecast:.1f} predicted arrivals / hour', .195)
    ax = panel(fig, [.035, .27, .595, .355], 'Hourly forecast with calibrated uncertainty')
    ax.fill_between(forecast.horizon_hours, forecast.lower90, forecast.upper90, color=TEAL, alpha=.12, label='Calibration band')
    ax.plot(forecast.horizon_hours, forecast.forecast, color=TEAL, linewidth=2.5, label='Forecast')
    ax.set(xlabel='Hours ahead of issue time', ylabel='Arrivals in target hour', xticks=[1, 6, 12, 18, 24])
    ax.legend(loc='upper left', fontsize=9, frameon=False)
    ax = panel(fig, [.665, .27, .3, .355], 'Recent observed demand before issue')
    counts = read('hourly_demand')
    counts['timestamp'] = pd.to_datetime(counts.timestamp)
    recent = counts[(counts.timestamp >= '2017-08-28') & (counts.timestamp < '2017-08-30')]
    ax.plot(np.arange(len(recent)), recent.arrivals_observed, color=BLUE, linewidth=1.6)
    ax.set(xlabel='Hours since 28 Aug, 00:00', ylabel='Recorded arrivals')
    note(fig, .035, .09, .595, 'Decision supported', 'Identify the expected timing of arrival demand. This page does not estimate current occupancy, staffing need or clinical risk.')
    note(fig, .665, .09, .3, 'Trust boundary', 'This is a historical replay. Missing targets are not zeros and prediction bands are not capacity thresholds.', AMBER)
    save(fig, 1)

    fig = page(2, 'When recorded arrival demand occurs. Coverage is shown alongside each pattern.',
               'SOURCE  Dryad workbook     |     COVERAGE  Full workbook     |     BASIS  Nonblank hours only')
    peak_hour = hourly.loc[hourly.mean_arrivals.idxmax()]
    kpi(fig, .035, 'Recorded hours', f'{audit["observed_hours"]:,}', 'Denominator excludes unknown counts')
    kpi(fig, .28, 'Unknown hours', f'{audit["unknown_hours"]:,}', 'Across the complete hourly calendar')
    kpi(fig, .525, 'Highest hourly mean', f'{int(peak_hour.hour):02d}:00', f'{peak_hour.mean_arrivals:.2f} arrivals / recorded hour')
    kpi(fig, .77, 'Observed coverage', f'{audit["observed_hours"]/audit["calendar_hours"]:.1%}', 'Not proof of complete reporting', .195)
    ax = panel(fig, [.035, .29, .555, .335], 'Weekday and hour: mean recorded arrivals')
    heat = read('demand_heatmap').pivot(index='weekday', columns='hour', values='mean_arrivals')
    im = ax.imshow(heat, aspect='auto', cmap='YlGnBu', vmin=0, vmax=heat.to_numpy().max())
    ax.grid(False)
    ax.set(yticks=range(7), yticklabels=['Mon','Tue','Wed','Thu','Fri','Sat','Sun'], xticks=range(0,24,3), xlabel='Hour of day')
    fig.colorbar(im, ax=ax, fraction=.025, pad=.025).set_label('Mean arrivals')
    ax = panel(fig, [.625, .29, .34, .335], 'Hourly demand and coverage')
    ax.plot(hourly.hour, hourly.mean_arrivals, color=TEAL, linewidth=2)
    ax.set(xlabel='Hour', ylabel='Mean recorded arrivals', xticks=[0,6,12,18,23])
    twin = ax.twinx()
    twin.plot(hourly.hour, hourly.coverage_fraction*100, color=AMBER, linestyle='--', linewidth=1.5)
    twin.set(ylabel='Coverage %', ylim=(0,100))
    twin.spines[['top','left']].set_visible(False)
    ax = panel(fig, [.035, .09, .555, .16], 'Monthly mean: trend is conditional on reporting')
    month = read('demand_month')
    ax.plot(np.arange(len(month)), month.mean_arrivals, color=TEAL, linewidth=1.8)
    ax.set(xticks=[0,12,24,36], xticklabels=['2014','2015','2016','2017'], ylabel='Mean')
    note(fig, .625, .09, .34, 'Investigate reporting first', 'Lower overnight coverage can distort the apparent daily profile. Do not treat the heatmap as a complete-demand estimate.', AMBER)
    save(fig, 2)

    overall = patient[patient.dimension.eq('all')].iloc[0]
    fig = page(3, 'Observed patient-level flow in the selected MIMIC demo. Associations do not identify causes.',
               'SOURCE  MIMIC-IV-ED demo     |     UNIT  ED stay     |     INTERVALS  Patient-cluster bootstrap')
    kpi(fig, .035, 'ED stays', f'{n:,}', f'{p:,} distinct patients')
    kpi(fig, .28, 'Median ED LOS', f'{overall.median_los_hours:.2f} h', 'Arrival to departure, all stages combined')
    kpi(fig, .525, '90th percentile LOS', f'{overall.p90_los_hours:.2f} h', 'Observed tail retained')
    kpi(fig, .77, 'Admitted disposition', f'{overall.admitted_disposition_rate:.1%}', 'Not equivalent to hospital-ID linkage', .195)
    ax = panel(fig, [.035, .29, .42, .335], 'Length of stay: where the observed stays fall')
    histogram = read('los_histogram')
    ax.bar(range(len(histogram)), histogram.stays, color=TEAL, width=.7)
    ax.set(xticks=range(len(histogram)), xticklabels=['0–2','2–4','4–6','6–8','8–12','12–24','24–48','48+'], xlabel='ED LOS band (hours)', ylabel='ED stays')
    ax = panel(fig, [.49, .29, .475, .335], 'Mean LOS by acuity, with uncertainty and counts')
    ax.set_position([.555,.335,.385,.24])
    acuity = patient[patient.dimension.eq('acuity')].copy()
    for i, row in enumerate(acuity.itertuples()):
        ax.scatter(row.mean_los_hours, i, color=TEAL, s=45)
        if pd.notna(row.mean_los_lower95):
            ax.plot([row.mean_los_lower95,row.mean_los_upper95], [i,i], color=TEAL, linewidth=2)
    ax.set(yticks=range(len(acuity)), yticklabels=[f'{r.group}  |  n={r.stays}' for r in acuity.itertuples()], xlabel='Mean LOS (hours)')
    note(fig, .035, .09, .42, 'Time in the ED is not treatment time', 'LOS includes unmeasured stages. These data cannot separate waiting, treatment and boarding durations.')
    ax = panel(fig, [.49, .09, .475, .16], 'Disposition mix')
    mix = patient[patient.dimension.eq('disposition')].sort_values('stays', ascending=False)
    ax.bar(['Admitted','Home','Other recorded'], [mix.loc[mix.group.eq('ADMITTED'),'stays'].sum(),mix.loc[mix.group.eq('HOME'),'stays'].sum(),mix.loc[~mix.group.isin(['ADMITTED','HOME']),'stays'].sum()], color=[TEAL,BLUE,'#adbcc5'])
    ax.set(ylabel='Stays')
    save(fig, 3)

    fig = page(4, 'Frozen validation-selected model, evaluated on later recorded targets.',
               'TEST  Jan–Aug 2017     |     HORIZON  24 hours     |     TARGET  One future hour     |     MODEL  Weekday + hour mean')
    chosen = metrics[(metrics.split.eq('test')) & metrics.model.eq('weekday_hour_mean')]
    for x,h in zip([.035,.28,.525],[6,12,24]):
        row = chosen[chosen.horizon_hours.eq(h)].iloc[0]
        kpi(fig,x,f'MAE at +{h}h',f'{row.mae:.2f}',f'{int(row.n):,} recorded targets')
    interval = read('forecast_intervals').query('horizon_hours == 24').iloc[0]
    kpi(fig,.77,'90% band coverage',f'{interval.empirical_coverage:.1%}','Empirical test coverage',.195)
    ax = panel(fig,[.035,.29,.555,.335],'Actual versus forecast: final three test days')
    backtest=read('forecast_backtest')
    backtest['target_time']=pd.to_datetime(backtest.target_time)
    part=backtest[(backtest.split.eq('test')) & backtest.horizon_hours.eq(24) & (backtest.target_time >= '2017-08-29')]
    ax.plot(range(len(part)),part.actual,color=BLUE,linewidth=1.5,label='Recorded actual')
    ax.plot(range(len(part)),part.forecast,color=TEAL,linewidth=2,label='Selected forecast')
    ax.set(xlabel='Hourly targets since 29 Aug',ylabel='Arrivals')
    ax.legend(frameon=False,fontsize=9)
    ax=panel(fig,[.625,.29,.34,.335],'Test MAE: selection is not changed after test')
    ax.set_position([.77,.335,.17,.24])
    comparison=metrics[(metrics.split.eq('test')) & metrics.horizon_hours.eq(24)]
    labels={'historical_mean':'Historical mean','hour_mean':'Hour mean','weekday_hour_mean':'Weekday + hour','weekly_naive':'Weekly naive','calendar_linear':'Calendar linear','calendar_ridge':'Calendar ridge','lag_ridge':'Lag ridge + fallback'}
    ax.barh([labels[x] for x in comparison.model],comparison.mae,color=[TEAL if x=='weekday_hour_mean' else '#b6c9d4' for x in comparison.model])
    ax.set(xlabel='MAE (arrivals / hour)')
    note(fig,.035,.09,.555,'Model governance','Regression is better on this test period, but did not meet the validation improvement rule. The chosen baseline is retained; a new model requires a new evaluation period.')
    bias=chosen[chosen.horizon_hours.eq(24)].iloc[0].bias
    note(fig,.625,.09,.34,'Watch underprediction',f'Average error is {bias:.2f} arrivals per recorded hour. Forecast accuracy does not establish clinical safety or staffing adequacy.',AMBER)
    save(fig,4)

    base=scenarios[scenarios.scenario.eq('baseline')].set_index('metric')
    fig=page(5,'Congestion mechanisms inside the hypothetical simulation. These are not detected hospital bottlenecks.',
             'SCENARIO  Baseline     |     REPLICATIONS  80     |     ARCHITECTURE  FIFO triage + treatment + boarding')
    kpi(fig,.035,'Mean queue',f'{base.loc["mean_queue","mean"]:.2f}','Time-weighted patients waiting')
    kpi(fig,.28,'Treatment utilization',f'{base.loc["treatment_utilization","mean"]:.1%}','Includes simulated boarding hold')
    kpi(fig,.525,'Triage utilization',f'{base.loc["triage_utilization","mean"]:.1%}','Generic triage resources')
    kpi(fig,.77,'Mean wait',f'{base.loc["mean_wait_hours","mean"]*60:.1f} min','Window-arrival cohort; full follow-up',.195)
    ax=panel(fig,[.035,.29,.555,.335],'Where the model queues form')
    time=timeline[timeline.scenario.eq('baseline')]
    ax.plot(time.hour,time.treatment_queue,color=TEAL,linewidth=2,label='Waiting for treatment')
    ax.plot(time.hour,time.triage_queue,color=AMBER,linewidth=2,label='Waiting for triage')
    ax.set(xlabel='Hour in measured cycle',ylabel='Mean patients waiting')
    ax.legend(frameon=False,fontsize=9)
    ax=panel(fig,[.625,.29,.34,.335],'Resource occupation by stage')
    ax.stackplot(time.hour,time.treatment_in_service,time.boarding_in_resource,colors=[TEAL,'#a9c8d5'],labels=['Treatment','Boarding hold'])
    ax.set(xlabel='Hour in measured cycle',ylabel='Occupied treatment resources')
    ax.legend(loc='upper left',facecolor='white',framealpha=.95,fontsize=9)
    note(fig,.035,.09,.555,'Mechanism supported by this architecture','Treatment and boarding share a constrained resource. Changing either duration changes offered workload in the experiment. Real hospital attribution requires stage timestamps and capacity data.')
    note(fig,.625,.09,.34,'Not modeled','No acuity-dependent service, fast track, staff skills, admission bed queue or abandonment mechanism is present.',AMBER)
    save(fig,5)

    fig=page(6,'Compare operational tradeoffs under explicit scenario assumptions. No optimal staffing recommendation.',
             'COMPARISON  Shared arrivals and service draws     |     INTERVALS  95% Monte Carlo mean intervals')
    names=['baseline','treatment_capacity_20','triage_capacity_3','boarding_duration_half','treatment_duration_minus20pct']
    labels=['Baseline','20 treatment resources','3 triage resources','Boarding duration halved','Treatment duration −20%']
    for x,label,metric,fmt in [( .035,'Baseline waiting','mean_wait_hours','minutes'),(.28,'Baseline queue','mean_queue','number'),(.525,'Baseline exits','exits','number'),(.77,'Treatment utilization','treatment_utilization','percent')]:
        value=base.loc[metric,'mean']
        rendered=f'{value*60:.1f} min' if fmt=='minutes' else f'{value:.1%}' if fmt=='percent' else f'{value:.1f}'
        kpi(fig,x,label,rendered,'Hypothetical simulation mean',.195 if x==.77 else .215)
    for bounds,metric,title,scale,xlabel in [([.035,.29,.43,.335],'mean_wait_hours','Waiting time across scenarios',60,'Mean wait (minutes)'),([.505,.29,.46,.335],'treatment_utilization','Capacity use is part of the tradeoff',100,'Treatment utilization (%)')]:
        ax=panel(fig,bounds,title)
        ax.set_position([bounds[0]+.17,bounds[1]+.045,bounds[2]-.195,bounds[3]-.095])
        part=scenarios[scenarios.metric.eq(metric)].set_index('scenario').loc[names]
        for i,row in enumerate(part.itertuples()):
            ax.plot([row.mean_lower95*scale,row.mean_upper95*scale],[i,i],color=TEAL,linewidth=2)
            ax.scatter(row.mean*scale,i,color=TEAL,s=38)
        ax.set(yticks=range(len(names)),yticklabels=labels,xlabel=xlabel)
        ax.invert_yaxis()
    note(fig,.035,.09,.43,'Operational cost is unmeasured','More capacity can reduce waiting while lowering utilization. The dataset does not supply resource cost, staffing feasibility or patient-safety tradeoffs.')
    note(fig,.505,.09,.46,'Uncertainty has a boundary','Intervals capture variation across repeated runs only. They do not include uncertainty in the assumed service times, capacity, transferred patient mix or forecast.',AMBER)
    save(fig,6)

    fig=page(7,'A traceable chain from raw source files to analytical and hypothetical outputs.',
             'EVIDENCE TYPES  Observed  /  Derived  /  Prediction  /  Simulation  /  Assumption  /  Recommendation')
    kpi(fig,.035,'Dryad recorded hours',f'{audit["observed_hours"]:,}','Date-hour grain; workbook pivot parsed')
    kpi(fig,.28,'MIMIC demo stays',f'{n:,}',f'{p:,} patients; encounter grain')
    kpi(fig,.525,'Forecast horizons','6 / 12 / 24 h','Hourly targets; chronological evaluation')
    kpi(fig,.77,'Simulation status','Hypothetical','Not calibrated to a hospital',.195)
    card(fig,.035,.30,.555,.32)
    fig.text(.05,.584,'Forecast evaluation sequence',fontsize=13,weight='bold')
    stages=[('TRAIN','2014–2015'),('SELECT','Jan–Jun 2016'),('CALIBRATE','Jul–Dec 2016'),('TEST','Jan–Aug 2017')]
    for i,(title,dates) in enumerate(stages):
        x=.05+i*.133
        fig.text(x,.53,title,fontsize=9,color=TEAL,weight='bold')
        fig.text(x,.504,dates,fontsize=10)
    fig.text(.05,.45,'Key safeguards',fontsize=11,weight='bold')
    fig.text(.05,.42,'Counts remain missing where unknown. Features precede issue time.\nFinal coefficients freeze before calibration. Later workbook dates are\nreported separately because source coverage is unresolved.',fontsize=11,color=MUTED,linespacing=1.7,va='top')
    card(fig,.625,.30,.34,.32)
    fig.text(.64,.584,'Simulation assumptions to inspect',fontsize=13,weight='bold')
    fig.text(.64,.54,'Triage: 2 resources, mean 8 minutes\nTreatment: 16 resources, mean 2 hours\nBoarding: mean 2 hours on admitted path\nFIFO routing; empty start before warmup\n80 runs; warmup sensitivity assessed',fontsize=11,color=MUTED,linespacing=1.9,va='top')
    note(fig,.035,.09,.555,'Privacy and source limits','Patient timestamps cannot reconstruct concurrent occupancy across MIMIC patients. Dashboard extracts exclude patient identifiers and clinical free text. The local demo is selected and not population-representative.')
    note(fig,.625,.09,.34,'Responsible use','Research and operational decision intelligence prototype. No clinical decisions, staffing directives or patient outcome claims.',AMBER)
    save(fig,7)
    print('Rendered all seven dashboard mockups at 1600 x 1000.')


if __name__ == '__main__':
    main()
