import csv
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW_PATH = ROOT / "data" / "raw" / "fights_raw.csv"
OUTPUT_PATH = ROOT / "data" / "processed" / "fights_clean.csv"

DATE_FORMAT = "%B %d, %Y"
MIN_YEAR = 2005
MAX_YEAR = 2025

RESULT_MAP = {
    "win": 1,
    "draw": 0.5,
    "nc": None,
}


def load_raw_rows(path: Path) -> list[dict]:
    """Read raw fights oldest→newest, keeping only MIN_YEAR..MAX_YEAR.

    The raw CSV is sorted newest→oldest, so the scan stops at the first row
    older than MIN_YEAR and each kept row is prepended to reverse the order.
    """
    rows: list[dict] = []

    with path.open("r", encoding="utf-8") as f:
        lines = f.readlines()[1:]

    for line in lines:
        parsed = next(csv.reader([line.strip()]))
        date_raw = parsed[0].lower().strip()
        fighter_a = parsed[1].lower().strip()
        fighter_b = parsed[2].lower().strip()
        result = parsed[3].lower().strip()

        try:
            year = int(date_raw.split(",")[1])
        except (IndexError, ValueError):
            continue

        if year < MIN_YEAR:
            break
        if year > MAX_YEAR:
            continue

        rows.insert(
            0,
            {
                "date_raw": date_raw,
                "fighter_a": fighter_a,
                "fighter_b": fighter_b,
                "result": result,
            },
        )

    return rows


def main():
    rows = load_raw_rows(RAW_PATH)
    df = pd.DataFrame(rows)

    df["date"] = pd.to_datetime(df["date_raw"], format=DATE_FORMAT, errors="coerce")
    df["result_numeric"] = df["result"].str.lower().map(RESULT_MAP)

    df_clean = df.dropna(
        subset=["date", "fighter_a", "fighter_b", "result_numeric"]
    )
    df_final = df_clean[["date", "fighter_a", "fighter_b", "result_numeric"]]

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_final.to_csv(OUTPUT_PATH, index=False)

    print(f"Cleaned {len(df_final)} fights from {len(df)} total rows")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
