"""
STEP 2: Inspect every raw table before assuming anything from the deck.

WHAT THIS DOES
For every CSV in data/raw/, prints its columns, data types, a few sample
rows, and which columns have missing values. This is the source of truth
you'll use to fill in schema.md and to fix any wrong assumptions in the
other scripts (they're written with best-guess column names — you WILL
need to tweak some).

BEFORE RUNNING
Put each raw table as a CSV in data/raw/, named after the table, e.g.:
  data/raw/screens.csv
  data/raw/bookings.csv
  ...etc for all 14 tables.

(If your organizers gave you a different format — Excel, JSON, a DB dump —
tell me and I'll rewrite this to match.)

HOW TO RUN
    python inspect_tables.py > inspect_report.txt
Then open inspect_report.txt and read it top to bottom. Keep it open next
to schema.md while you fill that in.
"""
import pandas as pd
from pathlib import Path

RAW_DIR = Path("data/raw")

# The 14 tables named in the problem statement deck.
EXPECTED_TABLES = [
    "cities", "zone_demographics", "locations",
    "route_stops", "vehicles", "route_schedules", "ridership_actuals",
    "screens",
    "points_of_interest", "events",
    "client_facts", "dim_slot", "bookings", "lost_leads",
]


def inspect_table(path: Path):
    df = pd.read_csv(path)
    print("=" * 70)
    print(f"TABLE: {path.stem}   ({len(df)} rows, {len(df.columns)} columns)")
    print("-" * 70)
    print("Columns and dtypes:")
    print(df.dtypes.to_string())
    print("-" * 70)
    print("Sample rows:")
    print(df.head(3).to_string())
    print("-" * 70)
    nulls = df.isnull().sum()
    has_nulls = nulls[nulls > 0]
    print("Columns with missing values:")
    print(has_nulls.to_string() if len(has_nulls) else "  (none)")
    print()


def main():
    if not RAW_DIR.exists():
        print(f"⚠️  {RAW_DIR} does not exist yet. Create it and drop your CSVs there.")
        return

    found = {p.stem for p in RAW_DIR.glob("*.csv")}
    missing = set(EXPECTED_TABLES) - found
    extra = found - set(EXPECTED_TABLES)

    if missing:
        print(f"⚠️  Missing expected tables: {sorted(missing)}")
    if extra:
        print(f"ℹ️  Found tables not mentioned in the deck: {sorted(extra)}")
    print()

    for table in EXPECTED_TABLES:
        path = RAW_DIR / f"{table}.csv"
        if path.exists():
            inspect_table(path)


if __name__ == "__main__":
    main()