"""Independent checks of saved outputs, source cells, and input preservation.

Run after run_eda.py: python EDA/verify_eda.py
This uses only the standard library and openpyxl. It does not regenerate outputs.
"""
import csv
import hashlib
import json
import math
import sqlite3
import statistics
from datetime import datetime, timedelta
from pathlib import Path

from openpyxl import load_workbook


def read_csv(path):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream))


def main():
    root=Path(__file__).resolve().parents[1]
    out=root/"EDA"/"outputs"
    summary=json.loads((out/"summary.json").read_text(encoding="utf-8"))
    manifest=read_csv(out/"source_manifest.csv")
    for item in manifest:
        with (root/item["path"]).open("rb") as source:
            assert hashlib.file_digest(source,"sha256").hexdigest()==item["sha256"]

    # Verify EVERY parsed hourly count against a separate Excel reader, not
    # only a subtotal produced by the same pandas transformation.
    book=load_workbook(next((root/"Dataset").rglob("*.xlsx")),read_only=True,data_only=True)
    cells=list(book["Sheet1"].values)
    hours=read_csv(out/"dryad_hourly.csv")
    timestamps=set()
    total=0
    for row in hours:
        timestamp=datetime.fromisoformat(row["timestamp"])
        assert timestamp not in timestamps
        timestamps.add(timestamp)
        source=cells[int(row["excel_row"])-1][int(row["excel_column"])-1]
        if source is None:
            assert row["arrivals_observed"]==""
            assert row["arrivals_zero_assumption"]==("0.0" if row["day_has_total"]=="1" else "")
        else:
            assert float(row["arrivals_observed"])==float(source)
            total+=float(source)
        label=cells[int(row["excel_row"])-1][0]
        assert datetime.strptime(label,"%I %p").hour==timestamp.hour
        assert cells[2][int(row["excel_column"])-1]==f"{timestamp.day}-{timestamp.strftime('%b')}"
    assert total==summary["dryad"]["total_arrivals"]
    active_days={datetime.fromisoformat(row["date"]).date() for row in hours if row["day_has_total"]=="1"}
    missing={datetime.fromisoformat(row["date"]).date() for row in read_csv(out/"dryad_missing_dates.csv")}
    first,last=min(active_days),max(active_days)
    calendar={first+timedelta(days=k) for k in range((last-first).days+1)}
    assert missing==calendar-active_days

    source_stays=next(p for p in (root/"Dataset").rglob("edstays.csv") if p.is_file())
    stays=read_csv(source_stays)
    los=[(datetime.fromisoformat(r["outtime"])-datetime.fromisoformat(r["intime"])).total_seconds()/3600 for r in stays]
    result=read_csv(out/"mimic_los_distribution.csv")[0]
    assert len(stays)==int(result["n"])
    assert math.isclose(statistics.mean(los),float(result["mean"]),abs_tol=1e-10)
    assert math.isclose(statistics.median(los),float(result["median"]),abs_tol=1e-10)
    with sqlite3.connect(f"file:{(out/'careflow.sqlite').as_posix()}?mode=ro",uri=True) as db:
        assert db.execute("SELECT COUNT(*) FROM edstays").fetchone()[0]==len(stays)
        assert db.execute("SELECT SUM(arrivals_observed) FROM arrivals").fetchone()[0]==total
    print(f"PASS: {len(manifest)} input hashes, {len(hours):,} hourly source cells, missing-date calendar, "
          f"{len(los)} independently calculated LOS values, and SQLite totals.")


if __name__=="__main__":
    main()
