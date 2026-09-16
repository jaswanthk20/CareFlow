"""Reproducible CareFlow EDA. Raw files are never modified.

Run from the project root: python EDA/run_eda.py
Read LEARNING_GUIDE.md for the order in which to explore the outputs.
The only zero filling is an explicitly labelled Dryad sensitivity scenario.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import re
import sqlite3
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def save_table(out, name, frame):
    """CSV outputs retain numeric precision; rounding happens only in Markdown."""
    frame.to_csv(out / f"{name}.csv", index=False)
    return frame


def markdown(frame):
    def cell(value):
        if pd.isna(value):
            return "NA"
        if isinstance(value, (float, np.floating)):
            return f"{value:,.3f}"
        return str(value).replace("|", "/").replace("\n", " ")
    lines = ["| " + " | ".join(map(str, frame.columns)) + " |",
             "| " + " | ".join(["---"] * len(frame.columns)) + " |"]
    lines += ["| " + " | ".join(cell(v) for v in row) + " |"
              for row in frame.itertuples(index=False, name=None)]
    return "\n".join(lines)


def distribution(series):
    values = pd.to_numeric(series, errors="coerce").dropna()
    return dict(n=len(values), mean=values.mean(), sd=values.std(), min=values.min(),
                p25=values.quantile(.25), median=values.median(), p75=values.quantile(.75),
                p90=values.quantile(.9), p95=values.quantile(.95), p99=values.quantile(.99),
                max=values.max())


def profile(tables, out):
    """Missing means empty/whitespace, not a numeric zero or a clinical category."""
    columns, rows = [], []
    for name, df in tables.items():
        rows.append(dict(table=name, rows=len(df), columns=len(df.columns),
                         exact_duplicate_rows=int(df.duplicated().sum())))
        for c in df:
            columns.append(dict(table=name, column=c, dtype=str(df[c].dtype),
                                missing=int(df[c].isna().sum()),
                                missing_pct=100 * df[c].isna().mean(),
                                distinct_nonmissing=df[c].nunique()))
    return (save_table(out, "table_inventory", pd.DataFrame(rows)),
            save_table(out, "column_quality", pd.DataFrame(columns)))


def parse_dryad(path, out):
    """Unpivot year/hour rows and day/month columns; exclude subtotal columns.

    Excel coordinates in outputs let a learner trace every derived hour back
    to its source cell. Blanks are retained even when totals suggest zeros.
    """
    book = pd.ExcelFile(path)
    if book.sheet_names != ["Sheet1"]:
        raise ValueError(f"Unexpected workbook sheets: {book.sheet_names}")
    raw = pd.read_excel(path, header=None)
    date_cols = [c for c in raw.columns if re.fullmatch(r"\d{1,2}-[A-Za-z]{3}", str(raw.iat[2, c]))]
    year_rows = [r for r in raw.index if re.fullmatch(r"20\d{2}", str(raw.iat[r, 0]))]
    grand_col = next(c for c in raw.columns if raw.iat[2, c] == "Grand Total")
    grand_row = next(r for r in raw.index if raw.iat[r, 0] == "Grand Total")
    records, daily, checks = [], [], []
    for c in date_cols:
        # The adjacent subtotal repeats the same date's values, not another day.
        same = raw.iloc[6:, c].fillna("<blank>").equals(raw.iloc[6:, c+1].fillna("<blank>"))
        checks.append(dict(check="repeated_total_column", location=str(raw.iat[2, c]),
                           failures=int(not same)))
    for r in year_rows:
        year = int(raw.iat[r, 0])
        for c in date_cols:
            label = f"{raw.iat[2, c]}-{year}"
            date = pd.to_datetime(label, format="%d-%b-%Y", errors="coerce")
            if pd.isna(date):
                # Feb 29 can exist as a shared column in a non-leap year.
                if raw.iloc[r:r+25, c].notna().any():
                    raise ValueError(f"Counts on invalid calendar date: {label}")
                continue
            cells = pd.to_numeric(raw.iloc[r+1:r+25, c], errors="raise")
            total = raw.iat[r, c]
            has_total = pd.notna(total)
            daily.append(dict(date=date, year=year, source_total=total,
                              sum_nonblank=cells.sum(min_count=1), blank_hours=int(cells.isna().sum())))
            if has_total:
                checks.append(dict(check="daily_total_reconciliation", location=str(date.date()),
                                   failures=int(cells.sum() != total)))
            elif cells.notna().any():
                raise ValueError(f"Hourly counts without daily subtotal: {date}")
            for offset in range(24):
                hour = datetime.strptime(str(raw.iat[r+1+offset, 0]), "%I %p").hour
                value = cells.iloc[offset]
                records.append(dict(timestamp=date+pd.Timedelta(hours=hour), date=date,
                                    year=year, hour=hour, arrivals_observed=value,
                                    arrivals_zero_assumption=(0 if pd.isna(value) else value) if has_total else np.nan,
                                    blank_cell=int(pd.isna(value)), day_has_total=int(has_total),
                                    excel_row=r+offset+2, excel_column=c+1))
        checks.append(dict(check="year_total_reconciliation", location=str(year),
                           failures=int(sum(d["source_total"] for d in daily if d["year"] == year and pd.notna(d["source_total"])) != raw.iat[r, grand_col])))
        for hr in range(24):
            s = pd.to_numeric(raw.iloc[r+1+hr, date_cols], errors="raise").sum()
            checks.append(dict(check="hour_by_year_total_reconciliation", location=f"{year}/{hr}",
                               failures=int(s != raw.iat[r+1+hr, grand_col])))
    arrivals = pd.DataFrame(records).sort_values("timestamp").reset_index(drop=True)
    daily = pd.DataFrame(daily).sort_values("date")
    observed_days = daily[daily.source_total.notna()]
    grid = pd.date_range(observed_days.date.min(), observed_days.date.max(), freq="D")
    absent = grid.difference(observed_days.date)
    save_table(out, "dryad_missing_dates", pd.DataFrame({"date": absent}))
    checks.append(dict(check="grand_total_reconciliation", location="workbook",
                       failures=int(observed_days.source_total.sum() != raw.iat[grand_row, grand_col])))
    checks.append(dict(check="duplicate_timestamp", location="parsed", failures=int(arrivals.timestamp.duplicated().sum())))
    numeric = arrivals.arrivals_observed.dropna()
    checks.append(dict(check="negative_or_fractional_count", location="parsed",
                       failures=int(((numeric < 0) | (numeric % 1 != 0)).sum())))
    check_df = save_table(out, "dryad_reconciliation", pd.DataFrame(checks))
    if check_df.failures.sum():
        raise ValueError("Dryad reconciliation failed; inspect dryad_reconciliation.csv")
    save_table(out, "dryad_hourly", arrivals)
    save_table(out, "dryad_daily", daily)
    suspect = observed_days[observed_days.source_total.eq(1)]
    save_table(out, "dryad_one_arrival_days", suspect)
    active = arrivals[arrivals.day_has_total.eq(1)].copy()
    active["weekday"] = active.timestamp.dt.dayofweek
    active["month"] = active.timestamp.dt.month
    groups = {}
    for key in ["hour", "weekday", "month", "year"]:
        grouped = active.groupby(key).agg(hours=("timestamp", "size"),
            nonblank_hours=("arrivals_observed", "count"), blank_hours=("blank_cell", "sum"),
            mean_nonblank_only=("arrivals_observed", "mean"),
            mean_if_blank_is_zero=("arrivals_zero_assumption", "mean"),
            total=("arrivals_observed", "sum")).reset_index()
        groups[key] = save_table(out, f"dryad_by_{key}", grouped)
    dist = pd.DataFrame([dict(series="hourly_nonblank", **distribution(active.arrivals_observed)),
                         dict(series="hourly_blank_as_zero", **distribution(active.arrivals_zero_assumption)),
                         dict(series="daily_source_total", **distribution(observed_days.source_total))])
    save_table(out, "dryad_distributions", dist)
    sensitivity=[]
    for label,subset in [("all_represented_days",active),
                         ("exclude_four_one_arrival_days",active[~active.date.isin(suspect.date)])]:
        sensitivity.append(dict(scenario=label,days=subset.date.nunique(),hours=len(subset),
            blank_hours=int(subset.blank_cell.sum()),mean_if_blank_is_zero=subset.arrivals_zero_assumption.mean(),
            mean_nonblank_only=subset.arrivals_observed.mean()))
    save_table(out,"dryad_low_day_sensitivity",pd.DataFrame(sensitivity))
    missing_monthends=int(pd.DatetimeIndex(absent).is_month_end.sum())
    # Reindex before shifting: an absent day must not turn a 48-hour gap into 24 hours.
    series = active.set_index("timestamp").arrivals_zero_assumption.reindex(
        pd.date_range(grid.min(), grid.max()+pd.Timedelta(hours=23), freq="h"))
    autocorr = pd.DataFrame([dict(lag_hours=k, paired_hours=int((series.notna() & series.shift(k).notna()).sum()),
                                   correlation=series.corr(series.shift(k))) for k in [1,6,12,24,48,168]])
    save_table(out, "dryad_lag_correlations", autocorr)
    # Future-window totals require every hour. No bridging over absent dates.
    windows = []
    for h in [6,12,24]:
        future = series.shift(-1).rolling(h, min_periods=h).sum().shift(-(h-1))
        windows.append(dict(horizon_hours=h, **distribution(future)))
    save_table(out, "dryad_future_window_totals", pd.DataFrame(windows))
    monthly = series.resample("MS").agg(["count", "mean", "sum"]).reset_index(names="month")
    save_table(out, "dryad_calendar_months", monthly)
    fig, axes = plt.subplots(2,2,figsize=(12,8), constrained_layout=True)
    axes[0,0].plot(groups["hour"].hour, groups["hour"].mean_if_blank_is_zero)
    axes[0,0].set(xlabel="Hour of day", ylabel="Arrivals/hour", title="Hourly pattern (blank = 0 scenario)", xticks=range(0,24,3))
    axes[0,1].bar(["Mon","Tue","Wed","Thu","Fri","Sat","Sun"],groups["weekday"].mean_if_blank_is_zero)
    axes[0,1].set(ylabel="Arrivals/hour", title="Weekday pattern (blank = 0 scenario)")
    axes[1,0].plot(monthly.month, monthly["mean"])
    axes[1,0].set(ylabel="Arrivals/hour",title="Monthly means; missing dates excluded")
    axes[1,0].tick_params(axis="x", rotation=30)
    axes[1,1].hist(active.arrivals_zero_assumption, bins=np.arange(0,numeric.max()+2)-.5, color="#247b91")
    axes[1,1].set(xlabel="Arrivals in one hour",ylabel="Hours",title="Hourly distribution (blank = 0 scenario)")
    fig.savefig(out/"arrival_patterns.png",dpi=160)
    plt.close(fig)
    summary = dict(sheet_shape=list(raw.shape), date_columns=len(date_cols), first_date=str(grid.min().date()),
        last_date=str(grid.max().date()), represented_days=len(observed_days), expected_days=len(grid),
        missing_dates=len(absent), missing_dates_at_month_end=missing_monthends,
        one_arrival_days=len(suspect), represented_hours=len(active), blank_hours=int(active.blank_cell.sum()),
        total_arrivals=int(numeric.sum()), workbook_grand_total=float(raw.iat[grand_row,grand_col]),
        explicit_zero_cells=int(numeric.eq(0).sum()), reconciliation_checks=len(check_df),
        checks_failed=int(check_df.failures.sum()))
    return arrivals, dist, groups, summary


def analyze_mimic(tables, out):
    stays = tables["edstays"].copy()
    triage = tables["triage"]
    quality = []
    for table, df in tables.items():
        quality.append(dict(table=table, check="missing_stay_id", failures=int(df.stay_id.isna().sum())))
        if table in ["edstays","triage"]:
            quality.append(dict(table=table, check="duplicate_stay_id", failures=int(df.stay_id.duplicated().sum())))
        linked = df.merge(stays[["stay_id","subject_id"]],on="stay_id",how="left",suffixes=("","_parent"),validate="many_to_one")
        quality.append(dict(table=table,check="orphan_stay_id",failures=int(linked.subject_id_parent.isna().sum())))
        quality.append(dict(table=table,check="subject_id_mismatch",failures=int((linked.subject_id != linked.subject_id_parent).sum())))
    for col in ["intime","outtime"]:
        stays[col] = pd.to_datetime(stays[col],errors="coerce")
        quality.append(dict(table="edstays",check=f"invalid_or_missing_{col}",failures=int(stays[col].isna().sum())))
    stays["los_hours"] = (stays.outtime-stays.intime).dt.total_seconds()/3600
    quality.append(dict(table="edstays",check="nonpositive_los",failures=int(stays.los_hours.le(0).sum())))
    cohort = stays.merge(triage,on=["subject_id","stay_id"],how="left",validate="one_to_one")
    los_dist = save_table(out,"mimic_los_distribution",pd.DataFrame([distribution(cohort.los_hours)]))
    groups = {}
    for key in ["acuity","disposition","arrival_transport","gender","race"]:
        rows=[]
        for value, subset in cohort.groupby(key,dropna=False):
            rows.append({key: value, "stays":len(subset), "patients":subset.subject_id.nunique(),
                         "percent_stays":100*len(subset)/len(cohort), "mean_los_hours":subset.los_hours.mean(),
                         "median_los_hours":subset.los_hours.median(), "p90_los_hours":subset.los_hours.quantile(.9),
                         "admitted":int(subset.disposition.eq("ADMITTED").sum())})
        groups[key]=save_table(out,f"mimic_by_{key}",pd.DataFrame(rows))
    save_table(out,"mimic_acuity_disposition",pd.crosstab(cohort.acuity.fillna("Missing"),cohort.disposition,dropna=False).reset_index())
    numeric, categories = [], []
    # These are mechanical range flags, not diagnoses or grounds for deletion.
    bounds={"temperature":(80,110),"heartrate":(20,250),"resprate":(4,80),
            "o2sat":(0,100),"sbp":(40,300),"dbp":(20,200),"acuity":(1,5),"pain":(0,10)}
    for name in ["triage","vitalsign"]:
        df=tables[name]
        for col,(low,high) in bounds.items():
            if col not in df: continue
            values=pd.to_numeric(df[col],errors="coerce")
            numeric.append(dict(table=name,column=col,**distribution(values),
                raw_missing=int(df[col].isna().sum()), nonnumeric_nonmissing=int((df[col].notna()&values.isna()).sum()),
                screening_low=low,screening_high=high, outside_screen=int(((values<low)|(values>high)).sum())))
        for col in ["pain","rhythm"]:
            if col in df:
                counts=df[col].fillna("<missing>").astype(str).value_counts()
                categories.extend(dict(table=name,column=col,value=k,records=v) for k,v in counts.items())
        quality.append(dict(table=name,check="sbp_less_than_dbp",failures=int((df.sbp<df.dbp).sum())))
    save_table(out,"mimic_numeric_profiles",pd.DataFrame(numeric))
    save_table(out,"mimic_pain_rhythm_values",pd.DataFrame(categories))
    event_rows=[]
    for name in ["diagnosis","medrecon","pyxis","vitalsign"]:
        df=tables[name]
        counts=df.groupby("stay_id").size().reindex(stays.stay_id,fill_value=0)
        row=dict(table=name,records=len(df),stays_with_records=df.stay_id.nunique(),
                 stays_without_records=len(stays)-df.stay_id.nunique(),median_records_per_stay=counts.median(),
                 max_records_per_stay=counts.max())
        if "charttime" in df:
            events=df.merge(stays[["stay_id","intime","outtime"]],on="stay_id",validate="many_to_one")
            times=pd.to_datetime(events.charttime,errors="coerce")
            lag=(times-events.intime).dt.total_seconds()/3600
            row.update(invalid_charttime=int(times.isna().sum()),before_intime=int((times<events.intime).sum()),
                       after_outtime=int((times>events.outtime).sum()),median_hours_from_arrival=lag.median(),
                       records_after_first_hour=int(lag.gt(1).sum()))
            event_dups=df.duplicated(["stay_id","charttime"]).sum()
            row["repeated_stay_charttime_rows"]=int(event_dups)
        event_rows.append(row)
    events=save_table(out,"mimic_event_coverage_timing",pd.DataFrame(event_rows))
    sentinels=[]
    for name,cols in {"medrecon":["gsn","ndc"],"pyxis":["gsn"]}.items():
        for col in cols:
            zero=pd.to_numeric(tables[name][col],errors="coerce").eq(0)
            sentinels.append(dict(table=name,column=col,zero_as_missing=int(zero.sum()),
                                 blank_or_zero=int((zero|tables[name][col].isna()).sum()),rows=len(tables[name])))
    save_table(out,"mimic_missing_code_sentinels",pd.DataFrame(sentinels))
    # Test plausible compound keys; repeated event times alone are not duplicates.
    keys={"diagnosis":["stay_id","seq_num"],
          "medrecon":["stay_id","charttime","name","etc_rn"],
          "pyxis":["stay_id","charttime","med_rn","gsn_rn"],
          "vitalsign":["stay_id","charttime"]}
    save_table(out,"mimic_candidate_keys",pd.DataFrame([
        dict(table=name,key=",".join(key),repeated_key_rows=int(tables[name].duplicated(key).sum()))
        for name,key in keys.items()]))
    med=tables["medrecon"]
    repeated=med[med.duplicated(keys["medrecon"],keep=False)]
    collisions=repeated.groupby(keys["medrecon"],dropna=False).agg(
        records=("stay_id","size"),distinct_gsn=("gsn","nunique"),distinct_ndc=("ndc","nunique"),distinct_etccode=("etccode","nunique"))
    # Export only counts of collision types, not patient-level records.
    save_table(out,"mimic_medrecon_key_collision_types",collisions.value_counts().reset_index(name="groups"))
    # Diagnosis counts use distinct stays, not raw codes per encounter.
    dx=tables["diagnosis"]
    topdx=dx.groupby(["icd_version","icd_code","icd_title"]).agg(records=("stay_id","size"),stays=("stay_id","nunique")).reset_index().sort_values("stays",ascending=False)
    save_table(out,"mimic_diagnosis_counts",topdx)
    for name in ["medrecon","pyxis"]:
        save_table(out,f"mimic_{name}_names",tables[name].groupby("name").agg(records=("stay_id","size"),stays=("stay_id","nunique")).reset_index().sort_values("stays",ascending=False))
    repeat=stays.groupby("subject_id").size()
    save_table(out,"mimic_patient_stay_counts",repeat.value_counts().sort_index().rename_axis("stays_per_patient").reset_index(name="patients"))
    hours=stays.intime.dt.hour.value_counts().reindex(range(24),fill_value=0).rename_axis("hour").reset_index(name="stays")
    save_table(out,"mimic_arrival_hour_sample",hours)
    save_table(out,"mimic_integrity",pd.DataFrame(quality))
    linkage=pd.crosstab(stays.disposition,stays.hadm_id.notna()).rename(columns={False:"no_hadm_id",True:"has_hadm_id"}).reset_index()
    save_table(out,"mimic_disposition_hadm",linkage)
    fig,axes=plt.subplots(1,2,figsize=(11,4),constrained_layout=True)
    axes[0].hist(cohort.los_hours,bins=30,color="#247b91")
    axes[0].set(xlabel="ED LOS (hours)",ylabel="Stays",title=f"All {len(cohort)} demo stays; tail retained")
    ac=groups["acuity"]
    axes[1].bar(["Missing" if pd.isna(v) else str(int(v)) for v in ac.acuity],ac.median_los_hours,color="#247b91")
    axes[1].set(xlabel="Recorded acuity (see sample sizes in report)",ylabel="Median ED LOS (hours)",title="Descriptive association, not a causal effect")
    fig.savefig(out/"patient_flow.png",dpi=160)
    plt.close(fig)
    summary=dict(stays=len(stays),patients=stays.subject_id.nunique(),repeat_patients=int(repeat.gt(1).sum()),
                 max_stays_per_patient=int(repeat.max()),shifted_first_arrival=str(stays.intime.min()),
                 shifted_last_departure=str(stays.outtime.max()),los_over_24h=int(stays.los_hours.gt(24).sum()),
                 los_over_48h=int(stays.los_hours.gt(48).sum()),hadm_missing=int(stays.hadm_id.isna().sum()))
    return cohort,los_dist,groups,events,summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root",type=Path,default=Path(__file__).resolve().parents[1])
    args=parser.parse_args()
    root=args.project_root.resolve()
    out=root/"EDA"/"outputs"
    out.mkdir(parents=True,exist_ok=True)
    data=root/"Dataset"
    xlsx=list(data.rglob("*.xlsx"))
    if len(xlsx)!=1: raise ValueError("Expected exactly one Dryad workbook")
    tables={}
    paths={}
    for name in ["edstays","triage","diagnosis","medrecon","pyxis","vitalsign"]:
        matches=[p for p in data.rglob(f"{name}.csv") if p.is_file()]
        if len(matches)!=1: raise ValueError(f"Expected one {name}.csv, found {len(matches)}")
        paths[name]=matches[0]
        # Keep code strings (including leading zeros) intact. Blank strings alone are missing.
        df=pd.read_csv(matches[0],keep_default_na=False,na_values=[""],
                       dtype={c:"string" for c in ["subject_id","stay_id","hadm_id","icd_code","gsn","ndc","etccode"]})
        tables[name]=df.replace(r"^\s*$",np.nan,regex=True)
    manifest=[]
    for p in sorted(data.rglob("*")):
        if p.is_file():
            manifest.append(dict(path=str(p.relative_to(root)),bytes=p.stat().st_size,
                                 sha256=hashlib.file_digest(p.open("rb"),"sha256").hexdigest()))
    save_table(out,"source_manifest",pd.DataFrame(manifest))
    inventory,columns=profile(tables,out)
    arrivals,arrival_dist,arrival_groups,dryad_summary=parse_dryad(xlsx[0],out)
    cohort,los_dist,mimic_groups,events,mimic_summary=analyze_mimic(tables,out)
    # The database is reproducible and local. Outputs include only aggregate summaries
    # except the non-patient Dryad hourly table. Patient-level joins stay in SQLite.
    with sqlite3.connect(out/"careflow.sqlite") as db:
        for name,df in tables.items(): df.to_sql(name,db,if_exists="replace",index=False)
        arrivals.to_sql("arrivals",db,if_exists="replace",index=False)
        query_text=(root/"EDA"/"analysis.sql").read_text(encoding="utf-8")
        for block in re.split(r"-- name: ",query_text)[1:]:
            name,query=block.split("\n",1)
            result=pd.read_sql_query(query,db)
            save_table(out,name.strip(),result)
        sql_los=pd.read_sql_query("SELECT COUNT(*) AS n, AVG((julianday(outtime)-julianday(intime))*24) AS mean FROM edstays",db).iloc[0]
        assert sql_los["n"]==len(cohort)
        assert np.isclose(sql_los["mean"],cohort.los_hours.mean(),atol=1e-7)
        sql_total=db.execute("SELECT SUM(arrivals_observed) FROM arrivals").fetchone()[0]
        assert sql_total==dryad_summary["total_arrivals"]
        sql_hour=pd.read_sql_query("SELECT hour, AVG(arrivals_zero_assumption) AS mean FROM arrivals WHERE day_has_total=1 GROUP BY hour ORDER BY hour",db)
        assert np.allclose(sql_hour["mean"],arrival_groups["hour"].mean_if_blank_is_zero)
    summary=dict(dryad=dryad_summary,mimic=mimic_summary,
                 verification="Python and SQL agree on encounter count, mean LOS, total arrivals and all 24 hourly means.",
                 runtime=dict(python=platform.python_version(),pandas=pd.__version__,numpy=np.__version__,matplotlib=matplotlib.__version__))
    (out/"summary.json").write_text(json.dumps(summary,indent=2,default=lambda x:x.item() if hasattr(x,"item") else str(x)),encoding="utf-8")
    report=["# CareFlow computed EDA tables", "Generated by `python EDA/run_eda.py`. See the project README for interpretation, assumptions and limitations.",
            "## Run summary", "```json\n"+json.dumps(summary,indent=2,default=str)+"\n```",
            "## Table inventory",markdown(inventory),"## Complete schema and missingness",markdown(columns),
            "## Dryad distributions",markdown(arrival_dist)]
    for key,df in arrival_groups.items(): report += [f"## Dryad by {key}",markdown(df)]
    report += ["## ED LOS distribution (hours)",markdown(los_dist)]
    for key,df in mimic_groups.items(): report += [f"## MIMIC demo by {key}",markdown(df)]
    report += ["## Event coverage and timing",markdown(events)]
    for name in ["dryad_missing_dates","dryad_calendar_months","dryad_lag_correlations","dryad_future_window_totals",
                 "mimic_numeric_profiles","mimic_integrity","mimic_disposition_hadm","mimic_acuity_disposition",
                 "mimic_patient_stay_counts","mimic_pain_rhythm_values","mimic_missing_code_sentinels","mimic_candidate_keys",
                 "dryad_one_arrival_days","dryad_low_day_sensitivity","mimic_medrecon_key_collision_types"]:
        report += [f"## {name.replace('_',' ')}",markdown(pd.read_csv(out/f"{name}.csv"))]
    (out/"computed_report.md").write_text("\n\n".join(report)+"\n",encoding="utf-8")
    print(json.dumps(summary,indent=2,default=str))


if __name__=="__main__":
    main()
