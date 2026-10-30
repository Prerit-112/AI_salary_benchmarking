"""
Extract H-1B wage intelligence from DOL OFLC LCA disclosure files.

Source:
  data/raw/dol_lca/LCA_Disclosure_Data_FY2026_Q1.xlsx
  data/raw/dol_lca/LCA_Worksites_FY2026_Q1.xlsx

Outputs:
  data/processed/h1b_lca_cases_fy2026_q1.csv
  data/processed/h1b_lca_worksites_fy2026_q1.csv
  data/processed/h1b_wage_summary_fy2026_q1.csv
  data/processed/h1b_cap_season_proxy_fy2026_q1.csv

Loads DuckDB tables:
  h1b_lca_cases
  h1b_lca_worksites
  h1b_wage_summary
  h1b_cap_season_proxy
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import urllib.request
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional
from xml.etree.ElementTree import iterparse
from zipfile import ZipFile

import duckdb


BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / "data" / "raw" / "dol_lca"
PROCESSED_DIR = BASE_DIR / "data" / "processed"
DB_PATH = BASE_DIR / "database" / "immigration.duckdb"

DOL_BASE_URL = "https://www.dol.gov/sites/dolgov/files/ETA/oflc/pdfs"
DEFAULT_FY = 2026
AVAILABLE_QUARTERS = {
    2024: ["Q4"],
    2025: ["Q1", "Q2", "Q3", "Q4"],
    2026: ["Q1"],
}

CASE_COLUMNS = [
    "CASE_NUMBER",
    "CASE_STATUS",
    "RECEIVED_DATE",
    "DECISION_DATE",
    "VISA_CLASS",
    "JOB_TITLE",
    "SOC_CODE",
    "SOC_TITLE",
    "FULL_TIME_POSITION",
    "BEGIN_DATE",
    "END_DATE",
    "TOTAL_WORKER_POSITIONS",
    "NEW_EMPLOYMENT",
    "CONTINUED_EMPLOYMENT",
    "CHANGE_PREVIOUS_EMPLOYMENT",
    "NEW_CONCURRENT_EMPLOYMENT",
    "CHANGE_EMPLOYER",
    "AMENDED_PETITION",
    "EMPLOYER_NAME",
    "TRADE_NAME_DBA",
    "EMPLOYER_CITY",
    "EMPLOYER_STATE",
    "EMPLOYER_POSTAL_CODE",
    "EMPLOYER_COUNTRY",
    "NAICS_CODE",
    "WORKSITE_WORKERS",
    "SECONDARY_ENTITY",
    "SECONDARY_ENTITY_BUSINESS_NAME",
    "WORKSITE_CITY",
    "WORKSITE_COUNTY",
    "WORKSITE_STATE",
    "WORKSITE_POSTAL_CODE",
    "WAGE_RATE_OF_PAY_FROM",
    "WAGE_RATE_OF_PAY_TO",
    "WAGE_UNIT_OF_PAY",
    "PREVAILING_WAGE",
    "PW_UNIT_OF_PAY",
    "PW_WAGE_LEVEL",
    "TOTAL_WORKSITE_LOCATIONS",
    "H_1B_DEPENDENT",
    "WILLFUL_VIOLATOR",
    "SUPPORT_H1B",
    "STATUTORY_BASIS",
]

WORKSITE_COLUMNS = [
    "CASE_NUMBER",
    "WORKSITE_WORKERS",
    "SECONDARY_ENTITY",
    "SECONDARY_ENTITY_BUSINESS_NAME",
    "WORKSITE_CITY",
    "WORKSITE_COUNTY",
    "WORKSITE_STATE",
    "WORKSITE_POSTAL_CODE",
    "WAGE_RATE_OF_PAY_FROM",
    "WAGE_RATE_OF_PAY_TO",
    "WAGE_UNIT_OF_PAY",
    "PREVAILING_WAGE",
    "PW_UNIT_OF_PAY",
    "PW_WAGE_LEVEL",
]

CASE_OUTPUT_COLUMNS = [
    "case_number",
    "case_status",
    "received_date",
    "decision_date",
    "visa_class",
    "job_title",
    "soc_code",
    "soc_title",
    "full_time_position",
    "begin_date",
    "end_date",
    "total_worker_positions",
    "new_employment",
    "continued_employment",
    "change_previous_employment",
    "new_concurrent_employment",
    "change_employer",
    "amended_petition",
    "employer_name",
    "trade_name_dba",
    "employer_city",
    "employer_state",
    "employer_postal_code",
    "employer_country",
    "naics_code",
    "worksite_workers",
    "secondary_entity",
    "secondary_entity_business_name",
    "worksite_city",
    "worksite_county",
    "worksite_state",
    "worksite_postal_code",
    "wage_rate_of_pay_from",
    "wage_rate_of_pay_to",
    "wage_unit_of_pay",
    "prevailing_wage",
    "pw_unit_of_pay",
    "pw_wage_level_raw",
    "wage_level",
    "weighted_entries_per_worker",
    "annual_wage_from",
    "annual_wage_to",
    "annual_prevailing_wage",
    "wage_plausibility_flag",
    "total_worksite_locations",
    "h1b_dependent",
    "willful_violator",
    "support_h1b",
    "statutory_basis",
    "fiscal_year",
    "quarter",
    "source_file",
]

WORKSITE_OUTPUT_COLUMNS = [
    "case_number",
    "worksite_workers",
    "secondary_entity",
    "secondary_entity_business_name",
    "worksite_city",
    "worksite_county",
    "worksite_state",
    "worksite_postal_code",
    "wage_rate_of_pay_from",
    "wage_rate_of_pay_to",
    "wage_unit_of_pay",
    "prevailing_wage",
    "pw_unit_of_pay",
    "pw_wage_level_raw",
    "wage_level",
    "weighted_entries_per_worker",
    "annual_wage_from",
    "annual_wage_to",
    "annual_prevailing_wage",
    "wage_plausibility_flag",
    "fiscal_year",
    "quarter",
    "source_file",
]

WAGE_MULTIPLIERS = {
    "YEAR": 1,
    "MONTH": 12,
    "BI-WEEKLY": 26,
    "BIWEEKLY": 26,
    "WEEK": 52,
    "HOUR": 2080,
}

WAGE_LEVELS = {
    "I": ("Level I", 1),
    "1": ("Level I", 1),
    "II": ("Level II", 2),
    "2": ("Level II", 2),
    "III": ("Level III", 3),
    "3": ("Level III", 3),
    "IV": ("Level IV", 4),
    "4": ("Level IV", 4),
}


def excel_col_to_index(ref: str) -> int:
    """Return 1-based column index from an Excel cell reference."""
    letters = re.match(r"([A-Z]+)", ref or "")
    if not letters:
        return 0
    idx = 0
    for char in letters.group(1):
        idx = idx * 26 + (ord(char) - ord("A") + 1)
    return idx


def load_shared_strings(zf: ZipFile) -> List[str]:
    """Read shared strings from an .xlsx file."""
    if "xl/sharedStrings.xml" not in zf.namelist():
        return []

    strings: List[str] = []
    with zf.open("xl/sharedStrings.xml") as handle:
        for _, elem in iterparse(handle, events=("end",)):
            if elem.tag.endswith("}si"):
                strings.append("".join(t.text or "" for t in elem.iter() if t.tag.endswith("}t")))
                elem.clear()
    return strings


def cell_value(cell, shared_strings: List[str]) -> str:
    """Extract a cell value from worksheet XML."""
    value = ""
    cell_type = cell.attrib.get("t")

    if cell_type == "inlineStr":
        return "".join(t.text or "" for t in cell.iter() if t.tag.endswith("}t")).strip()

    for child in cell:
        if child.tag.endswith("}v"):
            value = child.text or ""
            break

    if cell_type == "s" and value:
        try:
            return shared_strings[int(value)].strip()
        except (ValueError, IndexError):
            return ""
    return str(value).strip()


def iter_xlsx_rows(path: Path, wanted_columns: Optional[Iterable[str]] = None) -> Iterator[Dict[str, str]]:
    """Stream rows from the first worksheet as dictionaries."""
    with ZipFile(path) as zf:
        shared_strings = load_shared_strings(zf)
        header_by_index: Dict[int, str] = {}
        wanted = set(wanted_columns or [])

        with zf.open("xl/worksheets/sheet1.xml") as handle:
            for _, elem in iterparse(handle, events=("end",)):
                if not elem.tag.endswith("}row"):
                    continue

                row_values: Dict[int, str] = {}
                for cell in list(elem):
                    if not cell.tag.endswith("}c"):
                        continue
                    idx = excel_col_to_index(cell.attrib.get("r", ""))
                    if idx:
                        row_values[idx] = cell_value(cell, shared_strings)

                if not header_by_index:
                    header_by_index = {idx: val for idx, val in row_values.items() if val}
                    elem.clear()
                    continue

                row = {}
                for idx, name in header_by_index.items():
                    if wanted and name not in wanted:
                        continue
                    row[name] = row_values.get(idx, "")
                elem.clear()
                yield row


def parse_number(value: object) -> Optional[float]:
    """Parse a numeric field that may include commas or blanks."""
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_int(value: object) -> int:
    num = parse_number(value)
    if num is None:
        return 0
    return int(num)


def parse_excel_date(value: object) -> str:
    """Convert Excel serial dates or date-like strings to YYYY-MM-DD."""
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""

    num = parse_number(text)
    if num is not None and num > 20000:
        dt = datetime(1899, 12, 30) + timedelta(days=num)
        return dt.date().isoformat()

    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            pass
    return text


def annualize(amount: object, unit: object) -> Optional[float]:
    num = parse_number(amount)
    if num is None:
        return None
    normalized_unit = str(unit or "").strip().upper().replace(" ", "-")
    multiplier = WAGE_MULTIPLIERS.get(normalized_unit)
    if not multiplier:
        return None
    return round(num * multiplier, 2)


def wage_plausibility_flag(annual_wage: Optional[float]) -> str:
    if annual_wage is None:
        return "MISSING_OR_UNNORMALIZED"
    if annual_wage < 15080:
        return "LOW_OUTLIER"
    if annual_wage > 1000000:
        return "HIGH_OUTLIER"
    return "PLAUSIBLE"


def normalize_wage_level(value: object) -> tuple[str, int]:
    text = str(value or "").strip().upper().replace("LEVEL", "").replace(" ", "")
    if text in WAGE_LEVELS:
        return WAGE_LEVELS[text]
    return "Unknown", 0


def clean_text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def clean_case_row(row: Dict[str, str], fiscal_year: int, quarter: str, source_file: str) -> Dict[str, object]:
    wage_level, weight = normalize_wage_level(row.get("PW_WAGE_LEVEL"))
    total_positions = parse_int(row.get("TOTAL_WORKER_POSITIONS"))
    annual_from = annualize(row.get("WAGE_RATE_OF_PAY_FROM"), row.get("WAGE_UNIT_OF_PAY"))
    annual_to = annualize(row.get("WAGE_RATE_OF_PAY_TO"), row.get("WAGE_UNIT_OF_PAY"))
    annual_pw = annualize(row.get("PREVAILING_WAGE"), row.get("PW_UNIT_OF_PAY"))

    return {
        "case_number": clean_text(row.get("CASE_NUMBER")),
        "case_status": clean_text(row.get("CASE_STATUS")),
        "received_date": parse_excel_date(row.get("RECEIVED_DATE")),
        "decision_date": parse_excel_date(row.get("DECISION_DATE")),
        "visa_class": clean_text(row.get("VISA_CLASS")),
        "job_title": clean_text(row.get("JOB_TITLE")).title(),
        "soc_code": clean_text(row.get("SOC_CODE")),
        "soc_title": clean_text(row.get("SOC_TITLE")).title(),
        "full_time_position": clean_text(row.get("FULL_TIME_POSITION")),
        "begin_date": parse_excel_date(row.get("BEGIN_DATE")),
        "end_date": parse_excel_date(row.get("END_DATE")),
        "total_worker_positions": total_positions,
        "new_employment": parse_int(row.get("NEW_EMPLOYMENT")),
        "continued_employment": parse_int(row.get("CONTINUED_EMPLOYMENT")),
        "change_previous_employment": parse_int(row.get("CHANGE_PREVIOUS_EMPLOYMENT")),
        "new_concurrent_employment": parse_int(row.get("NEW_CONCURRENT_EMPLOYMENT")),
        "change_employer": parse_int(row.get("CHANGE_EMPLOYER")),
        "amended_petition": parse_int(row.get("AMENDED_PETITION")),
        "employer_name": clean_text(row.get("EMPLOYER_NAME")).upper(),
        "trade_name_dba": clean_text(row.get("TRADE_NAME_DBA")),
        "employer_city": clean_text(row.get("EMPLOYER_CITY")).title(),
        "employer_state": clean_text(row.get("EMPLOYER_STATE")).upper(),
        "employer_postal_code": clean_text(row.get("EMPLOYER_POSTAL_CODE")),
        "employer_country": clean_text(row.get("EMPLOYER_COUNTRY")),
        "naics_code": clean_text(row.get("NAICS_CODE")),
        "worksite_workers": parse_int(row.get("WORKSITE_WORKERS")),
        "secondary_entity": clean_text(row.get("SECONDARY_ENTITY")),
        "secondary_entity_business_name": clean_text(row.get("SECONDARY_ENTITY_BUSINESS_NAME")),
        "worksite_city": clean_text(row.get("WORKSITE_CITY")).title(),
        "worksite_county": clean_text(row.get("WORKSITE_COUNTY")).title(),
        "worksite_state": clean_text(row.get("WORKSITE_STATE")).upper(),
        "worksite_postal_code": clean_text(row.get("WORKSITE_POSTAL_CODE")),
        "wage_rate_of_pay_from": parse_number(row.get("WAGE_RATE_OF_PAY_FROM")),
        "wage_rate_of_pay_to": parse_number(row.get("WAGE_RATE_OF_PAY_TO")),
        "wage_unit_of_pay": clean_text(row.get("WAGE_UNIT_OF_PAY")).title(),
        "prevailing_wage": parse_number(row.get("PREVAILING_WAGE")),
        "pw_unit_of_pay": clean_text(row.get("PW_UNIT_OF_PAY")).title(),
        "pw_wage_level_raw": clean_text(row.get("PW_WAGE_LEVEL")),
        "wage_level": wage_level,
        "weighted_entries_per_worker": weight,
        "annual_wage_from": annual_from,
        "annual_wage_to": annual_to,
        "annual_prevailing_wage": annual_pw,
        "wage_plausibility_flag": wage_plausibility_flag(annual_from),
        "total_worksite_locations": parse_int(row.get("TOTAL_WORKSITE_LOCATIONS")),
        "h1b_dependent": clean_text(row.get("H_1B_DEPENDENT")),
        "willful_violator": clean_text(row.get("WILLFUL_VIOLATOR")),
        "support_h1b": clean_text(row.get("SUPPORT_H1B")),
        "statutory_basis": clean_text(row.get("STATUTORY_BASIS")),
        "fiscal_year": fiscal_year,
        "quarter": quarter,
        "source_file": source_file,
    }


def clean_worksite_row(row: Dict[str, str], fiscal_year: int, quarter: str, source_file: str) -> Dict[str, object]:
    wage_level, weight = normalize_wage_level(row.get("PW_WAGE_LEVEL"))
    annual_from = annualize(row.get("WAGE_RATE_OF_PAY_FROM"), row.get("WAGE_UNIT_OF_PAY"))
    annual_to = annualize(row.get("WAGE_RATE_OF_PAY_TO"), row.get("WAGE_UNIT_OF_PAY"))
    annual_pw = annualize(row.get("PREVAILING_WAGE"), row.get("PW_UNIT_OF_PAY"))
    return {
        "case_number": clean_text(row.get("CASE_NUMBER")),
        "worksite_workers": parse_int(row.get("WORKSITE_WORKERS")),
        "secondary_entity": clean_text(row.get("SECONDARY_ENTITY")),
        "secondary_entity_business_name": clean_text(row.get("SECONDARY_ENTITY_BUSINESS_NAME")),
        "worksite_city": clean_text(row.get("WORKSITE_CITY")).title(),
        "worksite_county": clean_text(row.get("WORKSITE_COUNTY")).title(),
        "worksite_state": clean_text(row.get("WORKSITE_STATE")).upper(),
        "worksite_postal_code": clean_text(row.get("WORKSITE_POSTAL_CODE")),
        "wage_rate_of_pay_from": parse_number(row.get("WAGE_RATE_OF_PAY_FROM")),
        "wage_rate_of_pay_to": parse_number(row.get("WAGE_RATE_OF_PAY_TO")),
        "wage_unit_of_pay": clean_text(row.get("WAGE_UNIT_OF_PAY")).title(),
        "prevailing_wage": parse_number(row.get("PREVAILING_WAGE")),
        "pw_unit_of_pay": clean_text(row.get("PW_UNIT_OF_PAY")).title(),
        "pw_wage_level_raw": clean_text(row.get("PW_WAGE_LEVEL")),
        "wage_level": wage_level,
        "weighted_entries_per_worker": weight,
        "annual_wage_from": annual_from,
        "annual_wage_to": annual_to,
        "annual_prevailing_wage": annual_pw,
        "wage_plausibility_flag": wage_plausibility_flag(annual_from),
        "fiscal_year": fiscal_year,
        "quarter": quarter,
        "source_file": source_file,
    }


def download_if_missing(path: Path, url: str) -> None:
    if path.exists() and path.stat().st_size > 0:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url}")
    urllib.request.urlretrieve(url, path)


def quarter_value(quarter: str, fiscal_year: int) -> int:
    q = int(quarter.upper().replace("Q", ""))
    return (fiscal_year * 10) + q


def remote_file_exists(url: str) -> bool:
    request = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return 200 <= response.status < 400
    except Exception:
        return False


def latest_local_quarter(fiscal_year: int) -> Optional[str]:
    local = sorted(
        RAW_DIR.glob(f"LCA_Disclosure_Data_FY{fiscal_year}_Q*.xlsx"),
        key=lambda p: p.name,
    )
    if not local:
        return None
    return local[-1].stem.split("_")[-1].upper()


def resolve_quarter(fiscal_year: int, quarter: str, prefer_local: bool = False) -> str:
    if quarter.lower() != "latest":
        return quarter.upper()
    if prefer_local:
        local_quarter = latest_local_quarter(fiscal_year)
        if local_quarter:
            return local_quarter
    for candidate in ("Q4", "Q3", "Q2", "Q1"):
        name = f"LCA_Disclosure_Data_FY{fiscal_year}_{candidate}.xlsx"
        if remote_file_exists(f"{DOL_BASE_URL}/{name}"):
            return candidate
    local_quarter = latest_local_quarter(fiscal_year)
    if local_quarter:
        return local_quarter
    if fiscal_year in AVAILABLE_QUARTERS:
        return AVAILABLE_QUARTERS[fiscal_year][-1]
    return "Q1"


def extract_cases(raw_path: Path, out_path: Path, fiscal_year: int, quarter: str) -> set[str]:
    """Stream the disclosure file and write cleaned H-1B rows."""
    print(f"Extracting H-1B cases from {raw_path.name}")
    h1b_cases: set[str] = set()
    total_rows = 0
    h1b_rows = 0
    certified_rows = 0

    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=CASE_OUTPUT_COLUMNS)
        writer.writeheader()

        for row in iter_xlsx_rows(raw_path, CASE_COLUMNS):
            total_rows += 1
            if clean_text(row.get("VISA_CLASS")) != "H-1B":
                continue
            cleaned = clean_case_row(row, fiscal_year, quarter, raw_path.name)
            if not cleaned["case_number"]:
                continue
            writer.writerow(cleaned)
            h1b_cases.add(str(cleaned["case_number"]))
            h1b_rows += 1
            if cleaned["case_status"] == "Certified":
                certified_rows += 1
            if h1b_rows and h1b_rows % 100000 == 0:
                print(f"  {h1b_rows:,} H-1B rows written")

    print(f"  scanned {total_rows:,} LCA rows")
    print(f"  wrote {h1b_rows:,} H-1B rows ({certified_rows:,} certified)")
    return h1b_cases


def extract_worksites(
    raw_path: Path,
    out_path: Path,
    h1b_cases: set[str],
    fiscal_year: int,
    quarter: str,
) -> int:
    """Stream the worksite file and keep rows for H-1B cases."""
    print(f"Extracting worksites from {raw_path.name}")
    count = 0
    with out_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=WORKSITE_OUTPUT_COLUMNS)
        writer.writeheader()

        for row in iter_xlsx_rows(raw_path, WORKSITE_COLUMNS):
            case_number = clean_text(row.get("CASE_NUMBER"))
            if case_number not in h1b_cases:
                continue
            writer.writerow(clean_worksite_row(row, fiscal_year, quarter, raw_path.name))
            count += 1
    print(f"  wrote {count:,} H-1B worksite rows")
    return count


def load_and_derive(
    cases_csv: Path,
    worksites_csv: Path,
    summary_csv: Path,
    proxy_csv: Path,
    fiscal_year: int,
    quarter: str,
) -> None:
    print("Loading DuckDB tables and deriving summaries")
    con = duckdb.connect(str(DB_PATH))

    con.execute("DROP TABLE IF EXISTS h1b_lca_cases")
    con.execute(
        """
        CREATE TABLE h1b_lca_cases AS
        SELECT * FROM read_csv_auto(?, header=true, ignore_errors=true)
        """,
        [str(cases_csv)],
    )

    con.execute("DROP TABLE IF EXISTS h1b_lca_worksites")
    con.execute(
        """
        CREATE TABLE h1b_lca_worksites AS
        SELECT * FROM read_csv_auto(?, header=true, ignore_errors=true)
        """,
        [str(worksites_csv)],
    )

    con.execute("DROP TABLE IF EXISTS h1b_wage_summary")
    con.execute(
        """
        CREATE TABLE h1b_wage_summary AS
        SELECT
            fiscal_year,
            quarter,
            employer_name,
            soc_code,
            soc_title,
            worksite_state,
            worksite_city,
            wage_level,
            COUNT(*) AS case_count,
            SUM(total_worker_positions) AS worker_positions,
            MEDIAN(annual_wage_from) AS median_annual_wage,
            AVG(annual_wage_from) AS avg_annual_wage,
            MIN(annual_wage_from) AS min_annual_wage,
            MAX(annual_wage_from) AS max_annual_wage,
            SUM(total_worker_positions * weighted_entries_per_worker) AS weighted_entries
        FROM h1b_lca_cases
        WHERE case_status = 'Certified'
          AND wage_plausibility_flag = 'PLAUSIBLE'
        GROUP BY
            fiscal_year, quarter, employer_name, soc_code, soc_title,
            worksite_state, worksite_city, wage_level
        """
    )

    # Early FY2027 proxy: public FY2026 Q1 LCAs can only show filings certified
    # by Dec. 31, 2025, so the window starts at the earliest plausible cap start
    # support date and remains intentionally caveated in the dashboard.
    con.execute("DROP TABLE IF EXISTS h1b_cap_season_proxy")
    con.execute(
        """
        CREATE TABLE h1b_cap_season_proxy AS
        SELECT
            *,
            CASE
                WHEN new_employment > 0 THEN new_employment
                ELSE total_worker_positions
            END AS proxy_worker_positions,
            CASE
                WHEN new_employment > 0 THEN new_employment * weighted_entries_per_worker
                ELSE total_worker_positions * weighted_entries_per_worker
            END AS proxy_weighted_entries
        FROM h1b_lca_cases
        WHERE case_status = 'Certified'
          AND new_employment > 0
          AND begin_date >= DATE '2026-04-01'
          AND begin_date <= DATE '2026-12-31'
          AND wage_plausibility_flag = 'PLAUSIBLE'
        """
    )

    con.execute(f"COPY h1b_wage_summary TO '{summary_csv}' (HEADER, DELIMITER ',')")
    con.execute(f"COPY h1b_cap_season_proxy TO '{proxy_csv}' (HEADER, DELIMITER ',')")

    tables = {
        "h1b_lca_cases": con.execute("SELECT COUNT(*) FROM h1b_lca_cases").fetchone()[0],
        "h1b_lca_worksites": con.execute("SELECT COUNT(*) FROM h1b_lca_worksites").fetchone()[0],
        "h1b_wage_summary": con.execute("SELECT COUNT(*) FROM h1b_wage_summary").fetchone()[0],
        "h1b_cap_season_proxy": con.execute("SELECT COUNT(*) FROM h1b_cap_season_proxy").fetchone()[0],
    }

    print("\n=== DuckDB Verification ===")
    for table, rows in tables.items():
        print(f"{table}: {rows:,} rows")

    levels = con.execute(
        """
        SELECT wage_level, COUNT(*) AS cases, SUM(total_worker_positions) AS positions
        FROM h1b_lca_cases
        WHERE case_status = 'Certified'
        GROUP BY wage_level
        ORDER BY wage_level
        """
    ).fetchall()
    print("\nCertified wage-level distribution:")
    for level, cases, positions in levels:
        print(f"  {level:8s} {cases:>8,} cases {positions:>8,} positions")

    median_wage = con.execute(
        """
        SELECT MEDIAN(annual_wage_from)
        FROM h1b_lca_cases
        WHERE case_status = 'Certified'
          AND wage_plausibility_flag = 'PLAUSIBLE'
        """
    ).fetchone()[0]
    print(f"\nMedian certified offered annual wage: ${median_wage:,.0f}")

    flags = con.execute(
        """
        SELECT wage_plausibility_flag, COUNT(*) AS cases
        FROM h1b_lca_cases
        WHERE case_status = 'Certified'
        GROUP BY wage_plausibility_flag
        ORDER BY wage_plausibility_flag
        """
    ).fetchall()
    print("\nCertified wage plausibility flags:")
    for flag, cases in flags:
        print(f"  {flag:24s} {cases:>8,} cases")

    con.close()


def parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract H-1B LCA wage intelligence from DOL OFLC data.")
    parser.add_argument("--fy", type=int, default=DEFAULT_FY, help="Federal fiscal year, e.g. 2026")
    parser.add_argument("--quarter", default="latest", help="Quarter, e.g. Q1, Q2, Q3, Q4, or latest")
    parser.add_argument("--skip-download", action="store_true", help="Use existing files in data/raw/dol_lca")
    return parser.parse_args(argv)


def main(argv: List[str]) -> int:
    args = parse_args(argv)
    fiscal_year = args.fy
    quarter = resolve_quarter(fiscal_year, args.quarter, prefer_local=args.skip_download)
    suffix = f"FY{fiscal_year}_{quarter}"
    output_suffix = f"fy{fiscal_year}_{quarter.lower()}"

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    cases_raw = RAW_DIR / f"LCA_Disclosure_Data_{suffix}.xlsx"
    worksites_raw = RAW_DIR / f"LCA_Worksites_{suffix}.xlsx"
    layout_raw = RAW_DIR / f"LCA_Record_Layout_{suffix}.pdf"

    if not args.skip_download:
        download_if_missing(cases_raw, f"{DOL_BASE_URL}/{cases_raw.name}")
        download_if_missing(worksites_raw, f"{DOL_BASE_URL}/{worksites_raw.name}")
        download_if_missing(layout_raw, f"{DOL_BASE_URL}/{layout_raw.name}")

    if not cases_raw.exists():
        raise FileNotFoundError(f"Missing raw case file: {cases_raw}")
    if not worksites_raw.exists():
        print(f"WARNING: Worksites file not found ({worksites_raw.name}) — location columns will be NULL for this quarter.")

    cases_csv = PROCESSED_DIR / f"h1b_lca_cases_{output_suffix}.csv"
    worksites_csv = PROCESSED_DIR / f"h1b_lca_worksites_{output_suffix}.csv"
    summary_csv = PROCESSED_DIR / f"h1b_wage_summary_{output_suffix}.csv"
    proxy_csv = PROCESSED_DIR / f"h1b_cap_season_proxy_{output_suffix}.csv"

    print("=" * 72)
    print("  H-1B LCA Wage Intelligence ETL")
    print("=" * 72)
    print(f"Fiscal year: {fiscal_year}  Quarter: {quarter}")

    h1b_cases = extract_cases(cases_raw, cases_csv, fiscal_year, quarter)
    if worksites_raw.exists():
        extract_worksites(worksites_raw, worksites_csv, h1b_cases, fiscal_year, quarter)
    else:
        # Write header-only CSV so load_and_derive can still LEFT JOIN with zero matches
        with worksites_csv.open("w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=WORKSITE_OUTPUT_COLUMNS).writeheader()
        print(f"  wrote empty worksites CSV (no source file for {quarter})")
    load_and_derive(cases_csv, worksites_csv, summary_csv, proxy_csv, fiscal_year, quarter)

    print("\nOutputs:")
    for path in [cases_csv, worksites_csv, summary_csv, proxy_csv]:
        print(f"  {path}")
    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))