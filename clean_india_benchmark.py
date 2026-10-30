"""
Clean & structure India tech roles benchmark CSV.

Reads:  ai_salary/india_tech_roles_benchmark.csv
Writes: ai_salary/india_tech_roles_benchmark.csv          (clean filing grain)
        ai_salary/india_tech_roles_benchmark_summary.csv  (Role x Experience grain)
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
INPUT_CSV = SCRIPT_DIR / "india_tech_roles_benchmark.csv"
OUTPUT_FILING = SCRIPT_DIR / "india_tech_roles_benchmark.csv"
OUTPUT_SUMMARY = SCRIPT_DIR / "india_tech_roles_benchmark_summary.csv"

R_B = 40.0

# Multi-metro expansion multipliers (Bengaluru baseline = 1.0)
METRO_MULTIPLIERS: dict[str, float] = {
    "Mumbai": 1.05,
    "Delhi_NCR": 0.95,
    "Hyderabad": 0.90,
    "Chennai": 0.85,
    "Pune": 0.88,
}

METRO_FILING_COLUMNS: dict[str, str] = {
    "Benchmark_INR_Mumbai": "Mumbai",
    "Benchmark_INR_Delhi_NCR": "Delhi_NCR",
    "Benchmark_INR_Hyderabad": "Hyderabad",
    "Benchmark_INR_Chennai": "Chennai",
    "Benchmark_INR_Pune": "Pune",
}

SUMMARY_BANDS = ("P25", "Median", "P75", "Mean")

# Pay above this is treated as a data-quality outlier (not realistic annual base).
PAY_OUTLIER_USD = 500_000.0

ROLE_FAMILY_RULES: list[tuple[str, str]] = [
    # Fallback mapper when source Role_Family is missing — align with MAX taxonomy
    (r"FORWARD DEPLOYED|\bFDE\b", "FD"),
    (r"GENERATIVE AI|AGENTIC|PROMPT / LLM", "Generative_AI"),
    (r"DEEP LEARNING|COMPUTER VISION|\bNLP\b|ROBOTICS AI|RECOMMENDATION|"
     r"MACHINE LEARNING", "ML_Engineering"),
    (r"MLOPS|INFERENCE|AI INFRASTRUCTURE|AI PLATFORM", "AI_Platform_MLOps"),
    (r"AI RESEARCH|APPLIED SCIENTIST|RESEARCH ENGINEER|AI SAFETY", "AI_Research"),
    (r"AI SOLUTIONS|AI SALES|GTM|PRE-SALES", "AI_GTM_Sales"),
    (r"AI PRODUCT|AI DESIGNER", "AI_Product"),
    (r"AI ARCHITECT|AI CONSULTANT", "AI_Consulting_Architecture"),
    (r"HEAD / DIRECTOR OF AI", "AI_Leadership"),
    (r"SOFTWARE ENGINEER \(AI", "Software_AI_Tagged"),
    (r"AI ENGINEER|AI SCIENTIST|MEMBER OF TECHNICAL STAFF", "AI_Engineering"),
    (r"DATA SCIENTIST", "Data_Science"),
    (r"DATA ENGINEER|ANALYTICS ENGINEER", "Data_Engineering"),
]

US_CITY_TIER = {
    1.20: "Tier1_BayArea",
    1.15: "Tier1_NYC",
    1.10: "Tier2_SeattleBellevue",
    1.00: "Tier3_MajorCity",
    0.85: "Tier4_OtherUS",
}


def _strip_str(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def _upper(series: pd.Series) -> pd.Series:
    return _strip_str(series).str.upper()


def map_role_family(role: pd.Series) -> pd.Series:
    role_u = _upper(role)
    out = pd.Series(np.full(len(role), "Other AI/Tech", dtype=object), index=role.index)
    # Apply low-priority first, then higher-priority overwrites via mask order reverse
    for pattern, family in reversed(ROLE_FAMILY_RULES):
        mask = role_u.str.contains(pattern, regex=True, na=False)
        out = out.where(~mask, family)
    # Re-apply in forward priority so first rule wins
    out = pd.Series(np.full(len(role), "Other AI/Tech", dtype=object), index=role.index)
    assigned = pd.Series(False, index=role.index)
    for pattern, family in ROLE_FAMILY_RULES:
        mask = role_u.str.contains(pattern, regex=True, na=False) & ~assigned
        out = out.mask(mask, family)
        assigned = assigned | mask
    return out


def map_experience_band(exp: pd.Series, career: pd.Series) -> pd.Series:
    combo = (_upper(exp) + " " + _upper(career)).str.strip()
    conditions = [
        combo.str.contains(r"EXECUTIVE|LEAD_MANAGER|DIRECTOR", regex=True, na=False),
        combo.str.contains(r"LEVEL_IV|STAFF|PRINCIPAL", regex=True, na=False),
        combo.str.contains(r"LEVEL_III|SENIOR|MID_OR_MIXED", regex=True, na=False),
        combo.str.contains(r"LEVEL_II|ASSOCIATE", regex=True, na=False),
        combo.str.contains(r"ENTRY|LEVEL_I(?![IV])|FRESHER", regex=True, na=False),
    ]
    choices = [
        "Executive (15+ Years)",
        "Lead / Staff (10-14 Years)",
        "Senior (6-9 Years)",
        "Mid (3-5 Years)",
        "Entry (0-2 Years)",
    ]
    return pd.Series(np.select(conditions, choices, default="Senior (6-9 Years)"), index=exp.index)


def map_yoe_proxy(exp: pd.Series, career: pd.Series) -> pd.Series:
    combo = (_upper(exp) + " " + _upper(career)).str.strip()
    conditions = [
        combo.str.contains(r"EXECUTIVE|LEAD_MANAGER|DIRECTOR", regex=True, na=False),
        combo.str.contains(r"LEVEL_IV|STAFF|PRINCIPAL", regex=True, na=False),
        combo.str.contains(r"LEVEL_III|SENIOR|MID_OR_MIXED", regex=True, na=False),
        combo.str.contains(r"LEVEL_II|ASSOCIATE", regex=True, na=False),
        combo.str.contains(r"ENTRY|LEVEL_I(?![IV])|FRESHER", regex=True, na=False),
    ]
    return pd.Series(np.select(conditions, [18, 13, 8, 4, 0], default=8), index=exp.index).astype(int)


def map_scarcity_band(omega: pd.Series) -> pd.Series:
    return pd.cut(
        omega.astype(float),
        bins=[-np.inf, 1.00, 1.05, 1.15, 1.20, np.inf],
        labels=["Baseline", "Standard", "Specialized AI", "ML Premium", "GenAI Premium"],
        right=True,
    ).astype(str)


def clean_filing_grain(df: pd.DataFrame) -> pd.DataFrame:
    n0 = len(df)

    # --- string hygiene ---
    str_cols = [
        "Grain", "Role_Name", "Role_Family", "Country", "Location", "City", "State",
        "Experience_Level", "Career_Level", "Pay_Type", "Currency_Original",
        "Employer_Name", "Case_Number", "SOC_Code", "Visa_Class",
        "Decision_Date", "Source_Name", "Source_URL", "Collection_Date", "Notes",
    ]
    for c in str_cols:
        if c in df.columns:
            df[c] = _strip_str(df[c]).replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})

    # Standardize city display (title case); state uppercase
    if "City" in df.columns:
        df["City"] = df["City"].fillna("").astype(str).str.strip().str.title()
    if "State" in df.columns:
        df["State"] = df["State"].fillna("").astype(str).str.strip().str.upper()

    # --- numeric hygiene ---
    money_cols = [
        "Annual_Pay_USD", "Annual_Pay_INR", "Base_Min_USD",
        "Base_Median_USD", "Base_Max_USD",
    ]
    for c in money_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    for c in ["I_US", "I_IND", "Delta_Geo", "Gamma_Exp", "Omega_Role", "Phi_Floor", "Benchmark_INR_Salary"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    for c in METRO_FILING_COLUMNS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    # Drop always-empty US total-comp fields (100% null in this extract)
    drop_empty = [c for c in ("Total_Comp_USD", "Bonus_USD", "Equity_USD") if c in df.columns]
    df = df.drop(columns=drop_empty)

    # --- dedupe ---
    # Exact duplicate rows
    df = df.drop_duplicates()
    # Same LCA worksite + same pay (retain multi-city worksites as distinct rows)
    subset = [c for c in ("Case_Number", "City", "State", "Annual_Pay_USD", "Role_Name") if c in df.columns]
    df = df.drop_duplicates(subset=subset, keep="first")

    # --- derived structured fields (granularity helpers) ---
    df["Grain"] = "Filing"
    df["Target_Country"] = "India"
    df["Target_City_Hub"] = "Bengaluru"  # filing baseline hub for Benchmark_INR_Salary
    df["R_B"] = R_B
    # Prefer source Role_Family (from MAX rebuild); fill gaps via Role_Name rules
    if "Role_Family" in df.columns:
        src_family = _strip_str(df["Role_Family"]).replace(
            {"": pd.NA, "nan": pd.NA, "None": pd.NA, "<NA>": pd.NA}
        )
        inferred = map_role_family(df["Role_Name"])
        df["Role_Family"] = src_family.fillna(inferred)
    else:
        df["Role_Family"] = map_role_family(df["Role_Name"])
    df["Experience_Band"] = map_experience_band(df["Experience_Level"], df["Career_Level"])
    df["YoE_Proxy"] = map_yoe_proxy(df["Experience_Level"], df["Career_Level"])
    df["US_City_Tier"] = df["I_US"].map(US_CITY_TIER).fillna("Tier4_OtherUS")
    df["Role_Scarcity_Band"] = map_scarcity_band(df["Omega_Role"])

    # Hygiene: strip place-name formatting glitches (e.g. trailing backticks)
    for place_col in ("City", "Location"):
        if place_col in df.columns:
            cleaned = _strip_str(df[place_col]).astype(str)
            cleaned = cleaned.str.replace("`", "", regex=False).str.replace("´", "", regex=False)
            df[place_col] = cleaned.str.replace(r"\s{2,}", " ", regex=True).str.strip()

    # Quality flag
    pay = df["Annual_Pay_USD"]
    flags = np.where(pay > PAY_OUTLIER_USD, "OUTLIER_PAY", "OK")
    flags = np.where(pay.isna() | (pay <= 0), "INVALID_PAY", flags)
    df["Data_Quality_Flag"] = flags

    # Rounding / format
    df["Annual_Pay_USD"] = df["Annual_Pay_USD"].round(2)
    df["Annual_Pay_INR"] = df["Annual_Pay_INR"].round(2)
    for c in ("Base_Min_USD", "Base_Median_USD", "Base_Max_USD"):
        if c in df.columns:
            df[c] = df[c].round(2)

    df["I_US"] = df["I_US"].round(2)
    df["I_IND"] = df["I_IND"].round(2)
    df["Delta_Geo"] = df["Delta_Geo"].round(4)
    df["Gamma_Exp"] = df["Gamma_Exp"].round(3)
    df["Omega_Role"] = df["Omega_Role"].round(2)
    df["Phi_Floor"] = df["Phi_Floor"].round(2)
    df["Benchmark_INR_Salary"] = df["Benchmark_INR_Salary"].round(0).astype("Int64")

    # Derive / refresh metro expansion columns from Bengaluru baseline
    base = df["Benchmark_INR_Salary"].astype(float)
    for col, metro_key in METRO_FILING_COLUMNS.items():
        df[col] = (base * METRO_MULTIPLIERS[metro_key]).round(0).astype("Int64")

    # Rename FX INR for clarity
    df = df.rename(columns={"Annual_Pay_INR": "Annual_Pay_INR_FX"})

    # Stable record id
    df = df.reset_index(drop=True)
    df.insert(0, "Record_ID", np.arange(1, len(df) + 1))

    # --- column order (structured sections) ---
    ordered = [
        # Grain / identity
        "Record_ID", "Grain", "Case_Number",
        # Target (India) context
        "Target_Country", "Target_City_Hub",
        # Role structure
        "Role_Name", "Role_Family", "Role_Scarcity_Band",
        # Source location (US)
        "Country", "State", "City", "Location", "US_City_Tier",
        # Experience structure
        "Experience_Level", "Career_Level", "Experience_Band", "YoE_Proxy",
        # US compensation
        "Pay_Type", "Annual_Pay_USD", "Annual_Pay_INR_FX",
        "Base_Min_USD", "Base_Median_USD", "Base_Max_USD", "Currency_Original",
        # Calibration audit trail
        "R_B", "I_US", "I_IND", "Delta_Geo", "Gamma_Exp", "Omega_Role", "Phi_Floor",
        # India benchmark (Bengaluru baseline + metro expansion)
        "Benchmark_INR_Salary",
        *METRO_FILING_COLUMNS.keys(),
        "Data_Quality_Flag",
        # Provenance
        "Employer_Name", "SOC_Code", "Visa_Class", "Fiscal_Year", "Decision_Date",
        "Source_Name", "Source_URL", "Collection_Date", "Sample_Size", "Notes",
    ]
    ordered = [c for c in ordered if c in df.columns]
    leftover = [c for c in df.columns if c not in ordered]
    df = df[ordered + leftover]

    # Sort for readability: Role → Experience band → City → Benchmark desc
    df = df.sort_values(
        by=["Role_Family", "Role_Name", "Experience_Band", "City", "Benchmark_INR_Salary"],
        ascending=[True, True, True, True, False],
        kind="mergesort",
    ).reset_index(drop=True)
    df["Record_ID"] = np.arange(1, len(df) + 1)

    print(f"[INFO] Filing grain: {n0:,} -> {len(df):,} rows "
          f"(removed {n0 - len(df):,} duplicates/exact dups)")
    print(f"[INFO] Quality flags:\n{df['Data_Quality_Flag'].value_counts().to_string()}")
    return df


def build_summary_grain(df: pd.DataFrame) -> pd.DataFrame:
    """
    Proper analysis grain: Role x Experience_Band (OK rows only).
    Medians / percentiles of calibrated India INR salary.
    """
    ok = df[df["Data_Quality_Flag"] == "OK"].copy()

    def p25(s: pd.Series) -> float:
        return float(s.quantile(0.25))

    def p75(s: pd.Series) -> float:
        return float(s.quantile(0.75))

    g = (
        ok.groupby(["Role_Family", "Role_Name", "Experience_Band", "Role_Scarcity_Band"], dropna=False)
        .agg(
            Sample_Size=("Benchmark_INR_Salary", "size"),
            Benchmark_INR_P25=("Benchmark_INR_Salary", p25),
            Benchmark_INR_Median=("Benchmark_INR_Salary", "median"),
            Benchmark_INR_P75=("Benchmark_INR_Salary", p75),
            Benchmark_INR_Mean=("Benchmark_INR_Salary", "mean"),
            US_Pay_USD_Median=("Annual_Pay_USD", "median"),
            Gamma_Exp_Mode=("Gamma_Exp", lambda s: float(s.mode().iloc[0]) if len(s.mode()) else np.nan),
            Omega_Role=("Omega_Role", "median"),
        )
        .reset_index()
    )

    for c in [
        "Benchmark_INR_P25", "Benchmark_INR_Median", "Benchmark_INR_P75",
        "Benchmark_INR_Mean",
    ]:
        g[c] = g[c].round(-3).astype(int)

    # Metro expansion: scale Bengaluru summary bands by city multipliers
    for metro_key, mult in METRO_MULTIPLIERS.items():
        for band in SUMMARY_BANDS:
            src = f"Benchmark_INR_{band}"
            dst = f"Benchmark_{metro_key}_{band}"
            g[dst] = (g[src].astype(float) * mult).round(0).astype(int)

    g["US_Pay_USD_Median"] = g["US_Pay_USD_Median"].round(2)
    g["Omega_Role"] = g["Omega_Role"].round(2)
    g["Gamma_Exp_Mode"] = g["Gamma_Exp_Mode"].round(3)
    g["Grain"] = "Role_x_Experience"
    g["Target_Country"] = "India"
    # Summary rows carry multi-metro Benchmark_* columns on the same grain
    g["Target_City_Hub"] = "Multi-Metro Calibrated"
    g["Currency"] = "INR"

    g = g.sort_values(
        ["Role_Family", "Role_Name", "Experience_Band"],
        kind="mergesort",
    ).reset_index(drop=True)

    metro_summary_cols = [
        f"Benchmark_{metro}_{band}"
        for metro in METRO_MULTIPLIERS
        for band in SUMMARY_BANDS
    ]
    cols = [
        "Grain", "Target_Country", "Target_City_Hub",
        "Role_Family", "Role_Name", "Experience_Band", "Role_Scarcity_Band",
        "Sample_Size",
        "Benchmark_INR_P25", "Benchmark_INR_Median", "Benchmark_INR_P75", "Benchmark_INR_Mean",
        *metro_summary_cols,
        "US_Pay_USD_Median", "Gamma_Exp_Mode", "Omega_Role", "Currency",
    ]
    print(f"[INFO] Summary grain: {len(g):,} Role x Experience bands")
    return g[cols]


def main() -> int:
    print(f"[INFO] Reading {INPUT_CSV}")
    try:
        df = pd.read_csv(INPUT_CSV, low_memory=False)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Failed to read input: {exc}", file=sys.stderr)
        return 1

    if df.empty:
        print("[ERROR] Input is empty", file=sys.stderr)
        return 1

    filing = clean_filing_grain(df)
    summary = build_summary_grain(filing)

    try:
        filing.to_csv(OUTPUT_FILING, index=False)
        summary.to_csv(OUTPUT_SUMMARY, index=False)
    except Exception as exc:  # noqa: BLE001
        print(f"[ERROR] Failed to write outputs: {exc}", file=sys.stderr)
        return 1

    print(f"[INFO] Wrote filing grain  -> {OUTPUT_FILING}")
    print(f"[INFO] Wrote summary grain -> {OUTPUT_SUMMARY}")
    print(
        f"[INFO] Clean Benchmark_INR (OK only) "
        f"min={filing.loc[filing.Data_Quality_Flag.eq('OK'), 'Benchmark_INR_Salary'].min():,}  "
        f"median={int(filing.loc[filing.Data_Quality_Flag.eq('OK'), 'Benchmark_INR_Salary'].median()):,}  "
        f"max={filing.loc[filing.Data_Quality_Flag.eq('OK'), 'Benchmark_INR_Salary'].max():,}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
