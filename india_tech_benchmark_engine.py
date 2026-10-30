"""
India Tech Roles Benchmark Engine
=================================
Production-grade, fully vectorized US → India AI/Tech compensation calibrator.

Formula
-------
Benchmark_INR_Salary = Annual_Pay_USD * R_B * Delta_Geo * Gamma_Exp * Omega_Role * Phi_Floor

Multi-metro expansion (Bengaluru baseline = 1.0)
------------------------------------------------
Benchmark_INR_<Metro> = Benchmark_INR_Salary * METRO_MULTIPLIERS[<Metro>]
  Mumbai 1.05 | Delhi_NCR 0.95 | Hyderabad 0.90 | Chennai 0.85 | Pune 0.88

All transforms are NumPy/pandas vectorized — no row-wise Python loops.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Immutable base parity anchor (USD→INR purchasing-power proxy)
# ---------------------------------------------------------------------------
R_B: float = 40.0

# ---------------------------------------------------------------------------
# Geographic pair index maps (keys MUST be uppercase / strip-normalized)
# ---------------------------------------------------------------------------
US_CITIES_MAP: dict[str, float] = {
    "SAN FRANCISCO": 1.20,
    "SF": 1.20,
    "SUNNYVALE": 1.20,
    "MENLO PARK": 1.20,
    "PALO ALTO": 1.20,
    "SILICON VALLEY": 1.20,
    "NEW YORK": 1.15,
    "NYC": 1.15,
    "NEWYORKX": 1.15,
    "BELLEVUE": 1.10,
    "SEATTLE": 1.10,
    "AUSTIN": 1.00,
    "BOSTON": 1.00,
    "CAMBRIDGE": 1.00,
    "LOS ANGELES": 1.00,
    "IRVINE": 1.00,
}

IND_CITIES_MAP: dict[str, float] = {
    "BENGALURU": 1.00,
    "BANGALORE": 1.00,
    "DELHI": 0.92,
    "NCR": 0.92,
    "GURGAON": 0.92,
    "NOIDA": 0.92,
    "HYDERABAD": 0.88,
    "HYDRABAD": 0.88,
    "PUNE": 0.82,
    "CHENNAI": 0.82,
    "MUMBAI": 1.10,
}

# Fallback / default scalars
I_US_FALLBACK: float = 0.85
I_IND_DEFAULT: float = 1.00  # Bengaluru hub parity
GAMMA_EXP_DEFAULT: float = 1.280  # Senior-tier proxy
OMEGA_ROLE_DEFAULT: float = 1.05

# ---------------------------------------------------------------------------
# Multi-metro expansion multipliers (relative to Bengaluru baseline = 1.0)
# Scales Benchmark_INR_Salary (Bengaluru) → other Indian tech hubs.
# ---------------------------------------------------------------------------
METRO_MULTIPLIERS: dict[str, float] = {
    "Mumbai": 1.05,      # High real estate / banking premium
    "Delhi_NCR": 0.95,   # Consumer tech / e-commerce hubs
    "Hyderabad": 0.90,   # Competitive ecosystem ~10% structural discount
    "Chennai": 0.85,     # Enterprise / automotive systems discount
    "Pune": 0.88,        # Product engineering just under baseline
}

# Filing-grain column name → multiplier key
METRO_FILING_COLUMNS: dict[str, str] = {
    "Benchmark_INR_Mumbai": "Mumbai",
    "Benchmark_INR_Delhi_NCR": "Delhi_NCR",
    "Benchmark_INR_Hyderabad": "Hyderabad",
    "Benchmark_INR_Chennai": "Chennai",
    "Benchmark_INR_Pune": "Pune",
}

SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_CSV = SCRIPT_DIR / "AI_Talent_Salary_Benchmark_MAX_FreeSources.csv"
OUTPUT_CSV = SCRIPT_DIR / "india_tech_roles_benchmark.csv"


# ---------------------------------------------------------------------------
# Vectorized parameter builders
# ---------------------------------------------------------------------------
def _normalize_str_series(series: pd.Series) -> pd.Series:
    """Strip whitespace and uppercase; coerce non-strings / NaN → empty."""
    return series.fillna("").astype(str).str.strip().str.upper()


def compute_delta_geo(df: pd.DataFrame) -> pd.DataFrame:
    """Derive I_US, I_IND, and Delta_Geo = I_IND / I_US."""
    city_norm = _normalize_str_series(df["City"] if "City" in df.columns else pd.Series("", index=df.index))
    df["I_US"] = city_norm.map(US_CITIES_MAP).fillna(I_US_FALLBACK).astype(float)

    if "Target_India_City" in df.columns:
        ind_norm = _normalize_str_series(df["Target_India_City"])
        df["I_IND"] = ind_norm.map(IND_CITIES_MAP).fillna(I_IND_DEFAULT).astype(float)
    else:
        df["I_IND"] = np.full(len(df), I_IND_DEFAULT, dtype=float)

    # Guard against any zero I_US (should not occur with current maps)
    df["Delta_Geo"] = (df["I_IND"] / df["I_US"].replace(0, np.nan)).fillna(I_IND_DEFAULT / I_US_FALLBACK)
    return df


def compute_gamma_exp(df: pd.DataFrame) -> pd.DataFrame:
    """
    Experience elasticity scalar.

    YoE parsed from Experience_Level ∪ Career_Level via ordered containment.
    LEVEL_IV → LEVEL_III → LEVEL_II → LEVEL_I ordering avoids prefix collisions.
    Unmapped / null / empty → Gamma_Exp = 1.280 (senior proxy).
    """
    exp = _normalize_str_series(
        df["Experience_Level"] if "Experience_Level" in df.columns else pd.Series("", index=df.index)
    )
    career = _normalize_str_series(
        df["Career_Level"] if "Career_Level" in df.columns else pd.Series("", index=df.index)
    )
    # Combined token field for single-pass containment checks
    combo = (exp + " " + career).str.strip()

    # Highest-tier first so LEVEL_IV beats MID_OR_MIXED, SENIOR beats LEVEL_II, etc.
    conditions = [
        combo.str.contains(r"EXECUTIVE|LEAD_MANAGER|DIRECTOR", regex=True, na=False),
        combo.str.contains(r"LEVEL_IV|STAFF|PRINCIPAL", regex=True, na=False),
        combo.str.contains(r"LEVEL_III|SENIOR|MID_OR_MIXED", regex=True, na=False),
        combo.str.contains(r"LEVEL_II|ASSOCIATE", regex=True, na=False),
        # Negative lookahead: LEVEL_I but not LEVEL_II / LEVEL_III / LEVEL_IV
        combo.str.contains(r"ENTRY|LEVEL_I(?![IV])|FRESHER", regex=True, na=False),
    ]
    yoe_choices = [18, 13, 8, 4, 0]

    yoe = np.select(conditions, yoe_choices, default=-1).astype(float)

    gamma = np.where(yoe >= 0, 1.0 + (0.035 * yoe), GAMMA_EXP_DEFAULT)
    # Explicit empty / "OTHER" safety net (already covered by default=-1, reinforced here)
    empty_mask = (combo == "") | combo.str.contains(r"\bOTHER\b", regex=True, na=False)
    # Only force default when no positive YoE tier matched
    gamma = np.where(empty_mask & (yoe < 0), GAMMA_EXP_DEFAULT, gamma)

    df["Gamma_Exp"] = gamma.astype(float)
    return df


def compute_omega_role(df: pd.DataFrame) -> pd.DataFrame:
    """
    Role scarcity index.

    Prefer Role_Family when present (Phase-1 taxonomy). Fall back to Role_Name
    substring matching for legacy extracts without Role_Family.
    """
    family = _normalize_str_series(
        df["Role_Family"] if "Role_Family" in df.columns else pd.Series("", index=df.index)
    )
    role = _normalize_str_series(
        df["Role_Name"] if "Role_Name" in df.columns else pd.Series("", index=df.index)
    )

    # Family-first ladder (highest scarcity first)
    family_conditions = [
        family.isin(["GENERATIVE_AI"]),
        family.isin(["ML_ENGINEERING", "FD", "AI_PLATFORM_MLOPS"]),
        family.isin(["AI_RESEARCH", "AI_LEADERSHIP"]),
        family.isin(["AI_ENGINEERING", "AI_PRODUCT", "AI_CONSULTING_ARCHITECTURE"]),
        family.isin(["AI_GTM_SALES", "SOFTWARE_AI_TAGGED"]),
        family.isin(["DATA_SCIENCE"]),
        family.isin(["DATA_ENGINEERING"]),
    ]
    family_choices = [1.25, 1.20, 1.15, 1.12, 1.08, 1.05, 1.00]

    omega_family = np.select(family_conditions, family_choices, default=np.nan)

    # Name fallback for rows without usable family
    name_conditions = [
        role.str.contains(
            r"GENERATIVE AI|AGENTIC|PROMPT / LLM|DEEP LEARNING", regex=True, na=False
        ),
        role.str.contains(
            r"MACHINE LEARNING|MLOPS|FORWARD DEPLOYED|INFERENCE|AI INFRASTRUCTURE|"
            r"AI PLATFORM|COMPUTER VISION|\bNLP\b|ROBOTICS AI|RECOMMENDATION",
            regex=True,
            na=False,
        ),
        role.str.contains(
            r"AI RESEARCH|APPLIED SCIENTIST|RESEARCH ENGINEER|AI SAFETY|"
            r"HEAD / DIRECTOR OF AI",
            regex=True,
            na=False,
        ),
        role.str.contains(
            r"AI ENGINEER|AI SCIENTIST|MEMBER OF TECHNICAL STAFF|AI ARCHITECT|"
            r"AI CONSULTANT|AI PRODUCT|AI DESIGNER",
            regex=True,
            na=False,
        ),
        role.str.contains(
            r"AI SOLUTIONS|AI SALES|GTM|SOFTWARE ENGINEER \(AI",
            regex=True,
            na=False,
        ),
        role.str.contains(r"DATA SCIENTIST", regex=True, na=False),
        role.str.contains(r"DATA ENGINEER|ANALYTICS ENGINEER", regex=True, na=False),
    ]
    name_choices = [1.25, 1.20, 1.15, 1.12, 1.08, 1.05, 1.00]
    omega_name = np.select(name_conditions, name_choices, default=OMEGA_ROLE_DEFAULT)

    df["Omega_Role"] = np.where(np.isnan(omega_family), omega_name, omega_family).astype(float)
    return df


def compute_phi_floor(df: pd.DataFrame) -> pd.DataFrame:
    """Vectorized base-floor compression over Annual_Pay_USD via np.select."""
    pay = df["Annual_Pay_USD"].to_numpy(dtype=float, copy=False)

    conditions = [
        pay < 90_000,
        (pay >= 90_000) & (pay <= 140_000),
        pay > 140_000,
    ]
    choices = [0.45, 0.75, 1.00]

    df["Phi_Floor"] = np.select(conditions, choices, default=1.00).astype(float)
    return df


def compute_benchmark_inr(df: pd.DataFrame) -> pd.DataFrame:
    """
    Master transform:
        Benchmark_INR_Salary = Annual_Pay_USD * R_B * Delta_Geo * Gamma_Exp * Omega_Role * Phi_Floor
    Rounded to nearest thousand INR.
    """
    raw = (
        df["Annual_Pay_USD"].astype(float)
        * R_B
        * df["Delta_Geo"]
        * df["Gamma_Exp"]
        * df["Omega_Role"]
        * df["Phi_Floor"]
    )
    df["Benchmark_INR_Salary"] = raw.round(-3).astype(int)
    return df


def compute_metro_benchmarks(df: pd.DataFrame) -> pd.DataFrame:
    """
    Expand Bengaluru-baseline Benchmark_INR_Salary across major Indian tech metros.

        Benchmark_INR_<Metro> = Benchmark_INR_Salary * METRO_MULTIPLIERS[<Metro>]

    Values rounded to nearest integer INR.
    """
    if "Benchmark_INR_Salary" not in df.columns:
        raise KeyError("Benchmark_INR_Salary required before metro expansion.")

    base = df["Benchmark_INR_Salary"].astype(float)
    for col, metro_key in METRO_FILING_COLUMNS.items():
        mult = METRO_MULTIPLIERS[metro_key]
        df[col] = (base * mult).round(0).astype(int)
    return df


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------
def prepare_numeric_inputs(df: pd.DataFrame) -> pd.DataFrame:
    """Coerce Annual_Pay_USD; fill NaN with global mean before transforms."""
    if "Annual_Pay_USD" not in df.columns:
        raise KeyError(
            "Required numeric column 'Annual_Pay_USD' is missing from the source schema."
        )

    df["Annual_Pay_USD"] = pd.to_numeric(df["Annual_Pay_USD"], errors="coerce")
    mean_pay = df["Annual_Pay_USD"].mean(skipna=True)
    if pd.isna(mean_pay):
        mean_pay = 120_000.0  # safe industry mid-band fallback
    df["Annual_Pay_USD"] = df["Annual_Pay_USD"].fillna(mean_pay)
    return df


def run_pipeline(df: pd.DataFrame) -> pd.DataFrame:
    """Execute the full vectorized calibration chain."""
    df = prepare_numeric_inputs(df)
    df = compute_delta_geo(df)
    df = compute_gamma_exp(df)
    df = compute_omega_role(df)
    df = compute_phi_floor(df)
    df = compute_benchmark_inr(df)
    df = compute_metro_benchmarks(df)
    return df


def load_source(path: Path) -> pd.DataFrame:
    try:
        df = pd.read_csv(path, low_memory=False)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Source file not found: {path}") from exc
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"Source file is empty: {path}") from exc
    except Exception as exc:  # noqa: BLE001 — surface any I/O / parse failure cleanly
        raise RuntimeError(f"Failed to read source CSV '{path}': {exc}") from exc

    if df.empty:
        raise ValueError(f"Source file loaded but contains zero rows: {path}")
    return df


def write_output(df: pd.DataFrame, path: Path) -> None:
    audit_cols = [
        "I_US",
        "I_IND",
        "Delta_Geo",
        "Gamma_Exp",
        "Omega_Role",
        "Phi_Floor",
        "Benchmark_INR_Salary",
        *METRO_FILING_COLUMNS.keys(),
    ]
    missing = [c for c in audit_cols if c not in df.columns]
    if missing:
        raise RuntimeError(f"Pipeline incomplete — missing audit columns: {missing}")

    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(path, index=False)
    except PermissionError as exc:
        raise PermissionError(f"Cannot write output (file may be open): {path}") from exc
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Failed to write output CSV '{path}': {exc}") from exc


def main() -> int:
    print(f"[INFO] R_B (base parity anchor) = {R_B}")
    print(f"[INFO] Metro multipliers (vs Bengaluru): {METRO_MULTIPLIERS}")
    print(f"[INFO] Reading: {INPUT_CSV}")

    try:
        df = load_source(INPUT_CSV)
        print(f"[INFO] Ingested {len(df):,} rows x {len(df.columns)} columns")

        df = run_pipeline(df)

        write_output(df, OUTPUT_CSV)
        print(f"[INFO] Wrote calibrated benchmark -> {OUTPUT_CSV}")
        print(
            f"[INFO] Benchmark_INR_Salary  "
            f"min={df['Benchmark_INR_Salary'].min():,}  "
            f"median={int(df['Benchmark_INR_Salary'].median()):,}  "
            f"max={df['Benchmark_INR_Salary'].max():,}"
        )
        sample = df[
            ["Benchmark_INR_Salary", *METRO_FILING_COLUMNS.keys()]
        ].head(3)
        print("[INFO] Metro expansion sample (first 3 rows):")
        print(sample.to_string(index=False))
    except (FileNotFoundError, KeyError, ValueError, PermissionError, RuntimeError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
