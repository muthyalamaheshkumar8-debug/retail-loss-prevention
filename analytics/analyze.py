"""Analyze a downloaded incident CSV and create portable CSV/SQL/PNG outputs."""

import argparse
import sqlite3
from pathlib import Path
import pandas as pd
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv", type=Path)
    parser.add_argument("--output", type=Path, default=Path("analytics-output"))
    args = parser.parse_args()
    df = pd.read_csv(args.csv)
    args.output.mkdir(parents=True, exist_ok=True)
    df["created_at"] = pd.to_datetime(df["created_at"], utc=True, errors="coerce")
    df["reviewed_at"] = pd.to_datetime(df["reviewed_at"], utc=True, errors="coerce")
    df["minutes_to_latest_review"] = (
        df.reviewed_at - df.created_at
    ).dt.total_seconds() / 60
    summary = (
        df.groupby(["store_id", "status"], dropna=False)
        .size()
        .rename("incidents")
        .reset_index()
    )
    summary.to_csv(args.output / "store-outcomes.csv", index=False)
    with sqlite3.connect(args.output / "incidents.sqlite") as connection:
        df.to_sql("incidents", connection, index=False, if_exists="replace")
    if len(df):
        df.groupby(df.created_at.dt.date).size().plot(
            kind="bar", color="#347d62", title="Human-created incidents by day"
        )
        plt.ylabel("Incidents")
        plt.tight_layout()
        plt.savefig(args.output / "daily-incidents.png", dpi=160)
    print(f"Analyzed {len(df)} incidents. Outputs: {args.output}")


if __name__ == "__main__":
    main()
