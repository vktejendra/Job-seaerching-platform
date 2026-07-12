"""
JobLens — Data Cleaning Pipeline
Handles: missing values, salary outliers, type conversion,
         deduplication, feature engineering
"""

import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)


# ─────────────────────────────────────────
# COLUMN DEFINITIONS (from dataset spec)
# ─────────────────────────────────────────
EXPECTED_COLS = [
    "job_id", "title", "company", "location_display", "location_area",
    "description", "created", "contract_time", "contract_type",
    "salary_min", "salary_max", "salary_is_predicted",
    "redirect_url", "category_label", "category_tag",
    "latitude", "longitude", "adref"
]

# Salary sanity bounds (£/$/€ — treat as same unit)
SALARY_MIN_FLOOR   =  5_000
SALARY_MIN_CAP     = 500_000
SALARY_MAX_FLOOR   =  5_000
SALARY_MAX_CAP     = 800_000


def load_clean_data(path: str) -> pd.DataFrame:
    """
    Load CSV → clean → return analysis-ready DataFrame.
    """
    log.info(f"Loading dataset from: {path}")
    df = pd.read_csv(path, low_memory=False)
    log.info(f"Raw shape: {df.shape}")

    df = _validate_columns(df)
    df = _deduplicate(df)
    df = _clean_text_fields(df)
    df = _parse_dates(df)
    df = _clean_salary(df)
    df = _clean_geo(df)
    df = _normalise_contract(df)
    df = _feature_engineer(df)

    log.info(f"Clean shape: {df.shape}")
    return df


# ─────────────────────────────────────────
# STEP 1: Validate / align columns
# ─────────────────────────────────────────
def _validate_columns(df: pd.DataFrame) -> pd.DataFrame:
    missing = [c for c in EXPECTED_COLS if c not in df.columns]
    if missing:
        log.warning(f"Missing columns (will fill with NaN): {missing}")
        for c in missing:
            df[c] = np.nan
    # .copy() matters here: without it, this returns a *view* into the
    # original DataFrame. Every later df[col] = ... assignment throughout
    # this whole pipeline (_clean_text_fields, _clean_salary, etc.) would
    # then be an ambiguous chained assignment under pandas' Copy-on-Write
    # semantics — pandas warns about exactly this ("ChainedAssignmentError:
    # behaviour will change in pandas 3.0!"). Copying once here, right at
    # the source, means every downstream assignment is unambiguously safe.
    return df[EXPECTED_COLS].copy()


# ─────────────────────────────────────────
# STEP 2: Deduplicate
# ─────────────────────────────────────────
def _deduplicate(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)
    df = df.drop_duplicates(subset=["job_id"])
    df = df.drop_duplicates(subset=["adref"], keep="first")
    log.info(f"Dedup: {before} → {len(df)} rows")
    return df.reset_index(drop=True)


# ─────────────────────────────────────────
# STEP 3: Clean text fields
# ─────────────────────────────────────────
def _clean_text_fields(df: pd.DataFrame) -> pd.DataFrame:
    text_cols = ["title", "company", "location_display", "location_area",
                 "description", "category_label", "category_tag"]
    for col in text_cols:
        df[col] = (
            df[col]
            .fillna("")
            .astype(str)
            .str.strip()
            .str.replace(r"\s+", " ", regex=True)
        )
    # Title casing for display fields
    df["title"]            = df["title"].str.title()
    df["company"]          = df["company"].str.title()
    df["location_display"] = df["location_display"].str.title()
    df["category_label"]   = df["category_label"].str.title()
    return df


# ─────────────────────────────────────────
# STEP 4: Parse timestamps
# ─────────────────────────────────────────
def _parse_dates(df: pd.DataFrame) -> pd.DataFrame:
    df["created"] = pd.to_datetime(df["created"], errors="coerce", utc=True)
    df["created_date"]  = df["created"].dt.date
    df["created_month"] = (
    pd.to_datetime(
        df["created"],
        utc=True,
        errors="coerce"
    )
    .dt.tz_localize(None)
    .dt.to_period("M")
    .astype(str)
)
    df["created_year"]  = df["created"].dt.year
    null_dates = df["created"].isna().sum()
    if null_dates:
        log.warning(f"{null_dates} rows have unparseable 'created' timestamps")
    return df


# ─────────────────────────────────────────
# STEP 5: Clean salary
# ─────────────────────────────────────────
def _clean_salary(df: pd.DataFrame) -> pd.DataFrame:
    df["salary_min"] = pd.to_numeric(df["salary_min"], errors="coerce")
    df["salary_max"] = pd.to_numeric(df["salary_max"], errors="coerce")
    df["salary_is_predicted"] = pd.to_numeric(df["salary_is_predicted"], errors="coerce").fillna(0).astype(int)

    # Clip outliers
    df.loc[df["salary_min"] < SALARY_MIN_FLOOR, "salary_min"] = np.nan
    df.loc[df["salary_min"] > SALARY_MIN_CAP,   "salary_min"] = np.nan
    df.loc[df["salary_max"] < SALARY_MAX_FLOOR, "salary_max"] = np.nan
    df.loc[df["salary_max"] > SALARY_MAX_CAP,   "salary_max"] = np.nan

    # Swap if min > max
    swap = df["salary_min"] > df["salary_max"]
    df.loc[swap, ["salary_min", "salary_max"]] = df.loc[swap, ["salary_max", "salary_min"]].values

    # Derived
    df["salary_mid"]   = (df["salary_min"] + df["salary_max"]) / 2
    df["salary_range"] = df["salary_max"] - df["salary_min"]

    log.info(f"Salary: {df['salary_mid'].notna().sum()} valid salary rows")
    return df


# ─────────────────────────────────────────
# STEP 6: Clean geo coordinates
# ─────────────────────────────────────────
def _clean_geo(df: pd.DataFrame) -> pd.DataFrame:
    df["latitude"]  = pd.to_numeric(df["latitude"],  errors="coerce")
    df["longitude"] = pd.to_numeric(df["longitude"], errors="coerce")

    valid_lat = (df["latitude"].between(-90,  90))
    valid_lon = (df["longitude"].between(-180, 180))
    df.loc[~valid_lat, "latitude"]  = np.nan
    df.loc[~valid_lon, "longitude"] = np.nan

    log.info(f"Geo: {(df['latitude'].notna() & df['longitude'].notna()).sum()} valid coordinates")
    return df


# ─────────────────────────────────────────
# STEP 7: Normalise contract fields
# ─────────────────────────────────────────
def _normalise_contract(df: pd.DataFrame) -> pd.DataFrame:
    TIME_MAP = {
        "full_time": "full_time", "fulltime": "full_time", "full time": "full_time",
        "part_time": "part_time", "parttime": "part_time", "part time": "part_time",
    }
    TYPE_MAP = {
        "permanent": "permanent", "perm": "permanent",
        "contract": "contract", "contractor": "contract",
        "temporary": "temporary", "temp": "temporary",
    }
    df["contract_time"] = df["contract_time"].str.lower().str.strip().map(TIME_MAP).fillna("unknown")
    df["contract_type"] = df["contract_type"].str.lower().str.strip().map(TYPE_MAP).fillna("unknown")
    return df


# ─────────────────────────────────────────
# STEP 8: Feature engineering
# ─────────────────────────────────────────
def _feature_engineer(df: pd.DataFrame) -> pd.DataFrame:
    # Description length (proxy for job detail richness)
    df["desc_length"] = df["description"].str.len()

    # Country extracted from location_area
    df["country"] = df["location_area"].apply(_extract_country)

    # Salary tier
    conditions = [
        df["salary_mid"] < 30_000,
        df["salary_mid"].between(30_000, 60_000),
        df["salary_mid"].between(60_000, 100_000),
        df["salary_mid"] > 100_000,
    ]
    choices = ["Entry", "Mid", "Senior", "Executive"]
    df["salary_tier"] = np.select(conditions, choices, default="Unknown")

    return df


def _extract_country(area: str) -> str:
    if not area or area == "nan":
        return "Unknown"
    parts = [p.strip() for p in area.split("›")]
    return parts[0] if parts else "Unknown"


# ─────────────────────────────────────────
# STANDALONE: run as script for EDA preview
# ─────────────────────────────────────────
if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "adzuna_jobs.csv"
    df = load_clean_data(path)
    print("\n=== CLEAN DATASET SUMMARY ===")
    print(df.dtypes)
    print("\nNull counts:\n", df.isnull().sum())
    print("\nSalary stats:\n", df[["salary_min", "salary_max", "salary_mid"]].describe())
    print("\nContract time dist:\n", df["contract_time"].value_counts())
    print("\nTop 10 categories:\n", df["category_label"].value_counts().head(10))