"""
Build AI_Talent_Salary_Benchmark_MAX_FreeSources.csv
from official DOL OFLC Disclosure + Worksites workbooks.

Grain: LCA_Filing (one certified AI-related worksite wage fact per row).
Phase-1 taxonomy: AI core + AI-adjacent (incl. FD family). Not full-tech.

Default inputs are FY2026 Q3 filenames in this folder; override via CLI if needed.
Writes the primary MAX CSV consumed by india_tech_benchmark_engine.py.
"""
from __future__ import annotations

import argparse
import csv
import re
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, Iterable, Iterator, List, Optional, Set, Tuple
from xml.etree.ElementTree import iterparse
from zipfile import ZipFile

SCRIPT_DIR = Path(__file__).resolve().parent

DISCLOSURE_DEFAULT = SCRIPT_DIR / "LCA_Disclosure_Data_FY2026_Q3.xlsx"
WORKSITES_CANDIDATES = [
    SCRIPT_DIR / "LCA_Worksites_FY2026_Q3.xlsx",
    SCRIPT_DIR / "LCA_Worksites_FY_2026_Q3.xlsx",
]

OUT_CSV = SCRIPT_DIR / "AI_Talent_Salary_Benchmark_MAX_FreeSources.csv"

FX = 95.43  # USD->INR FX-style column (matches prior MAX convention)
TODAY = date.today().isoformat()
FISCAL_YEAR = "2026"
SOURCE_NAME = "US DOL OFLC LCA Disclosure"
SOURCE_URL = "https://www.dol.gov/agencies/eta/foreign-labor/performance"
NOTES = "Single certified LCA offered base wage fact. Not total compensation."

HEADERS = [
    "Grain",
    "Role_Name",
    "Role_Family",
    "Country",
    "Location",
    "City",
    "State",
    "Experience_Level",
    "Career_Level",
    "Pay_Type",
    "Annual_Pay_USD",
    "Annual_Pay_INR",
    "Base_Min_USD",
    "Base_Median_USD",
    "Base_Max_USD",
    "Total_Comp_USD",
    "Bonus_USD",
    "Equity_USD",
    "Currency_Original",
    "Employer_Name",
    "Case_Number",
    "SOC_Code",
    "Visa_Class",
    "Fiscal_Year",
    "Decision_Date",
    "Source_Name",
    "Source_URL",
    "Collection_Date",
    "Sample_Size",
    "Notes",
]

CASE_COLUMNS = [
    "CASE_NUMBER",
    "CASE_STATUS",
    "DECISION_DATE",
    "VISA_CLASS",
    "JOB_TITLE",
    "SOC_CODE",
    "SOC_TITLE",
    "EMPLOYER_NAME",
    "WORKSITE_CITY",
    "WORKSITE_STATE",
    "WAGE_RATE_OF_PAY_FROM",
    "WAGE_RATE_OF_PAY_TO",
    "WAGE_UNIT_OF_PAY",
    "PW_WAGE_LEVEL",
]

WORKSITE_COLUMNS = [
    "CASE_NUMBER",
    "WORKSITE_CITY",
    "WORKSITE_STATE",
    "WAGE_RATE_OF_PAY_FROM",
    "WAGE_RATE_OF_PAY_TO",
    "WAGE_UNIT_OF_PAY",
    "PW_WAGE_LEVEL",
]

# False-positive / non-AI occupation noise
DENYLIST_RE = re.compile(
    r"air pollution|air quality|air fire|air vehicle|pharmacist|attorney|"
    r"sailpoint|rail safety|supply chain planner|immigrant defense|"
    r"powertrain|infotainment(?!.*\b(ai|ml|llm)\b)|drivetrain",
    re.I,
)

# Strong AI / data inclusion cues (word-boundary safe for \bai\b)
INCLUDE_RE = re.compile(
    r"generative\s*ai|genai|\bllm\b|prompt\s*engineer|agentic|"
    r"machine\s*learning|\bmlops\b|ml\s*ops|model\s*ops|deep\s*learning|"
    r"computer\s*vision|\bnlp\b|natural\s*language|"
    r"artificial\s*intelligence|"
    r"\bai\b[\s\-_/]*(engineer|scientist|architect|platform|product|consultant|"
    r"specialist|researcher|research|safety|inference|infra|infrastructure|"
    r"deployment|implementation|solutions?|sales|gtm|pre[\s\-]?sales|"
    r"manager|director|head|vp|chief|designer|ux)|"
    r"\b(engineer|scientist|architect|manager|specialist|consultant|director|"
    r"head|vp)\b[\s\-_/]*\bai\b|"
    r"forward\s*deploy|fwd\s*deploy|\bfde\b|"
    r"applied\s*scientist|research\s*scientist|research\s*engineer|"
    r"data\s*scientist|data\s*science|data\s*engineer|analytics\s*engineer|"
    r"ml\s*engineer|ml\s*scientist|ml\s*specialist|"
    r"feature\s*store|model\s*serving|inference\s*engineer|"
    r"foundation\s*model|post[\s\-]?training|pre[\s\-]?training|"
    r"ai\s*safety|alignment|interpretability|"
    r"recommendation\s*engineer|ranking\s*engineer|recsys|"
    r"robotics.*\bai\b|\bai\b.*robotics|"
    r"(software\s*engineer|software\s*engineering|full[\s\-]?stack|"
    r"\bsde\b|\bswe\b).{0,40}\b(ai|ml|llm|genai|machine\s*learning)\b|"
    r"\b(ai|ml|llm|genai|machine\s*learning)\b.{0,40}"
    r"(software\s*engineer|software\s*engineering|full[\s\-]?stack|\bsde\b|\bswe\b)|"
    r"(product\s*manager|product\s*design).{0,40}\b(ai|ml|llm|genai)\b|"
    r"\b(ai|ml|llm|genai)\b.{0,40}(product\s*manager|product\s*design)|"
    r"(solutions?\s*engineer|account\s*executive|pre[\s\-]?sales|gtm)"
    r".{0,40}\b(ai|ml|llm|genai)\b|"
    r"\b(ai|ml|llm|genai)\b.{0,40}"
    r"(solutions?\s*engineer|account\s*executive|pre[\s\-]?sales|gtm)|"
    r"member\s*of\s*technical\s*staff.{0,60}\b(ai|ml|llm|genai|machine\s*learning|"
    r"inference|pre[\s\-]?train|post[\s\-]?train)\b|"
    r"\bmts\b.{0,40}\b(ai|ml|llm)\b",
    re.I,
)

# (pattern, Role_Name, Role_Family) — first match wins; order matters
ROLE_RULES: List[Tuple[str, str, str]] = [
    # FD family — all forward deployed variants
    (
        r"forward\s*deploy|fwd\s*deploy|forward\-deployed|\bfde\b",
        "Forward Deployed AI Engineer",
        "FD",
    ),
    # AI_GTM_Sales before Generative (so "Agentic AI GTM" lands in GTM)
    (
        r"(account\s*executive|\bae\b).{0,40}\b(ai|ml|llm|genai)\b|"
        r"\b(ai|ml|llm|genai)\b.{0,40}(account\s*executive|ai\s*sales)|"
        r"ai\s*sales",
        "AI Sales / Account Executive",
        "AI_GTM_Sales",
    ),
    (
        r"(pre[\s\-]?sales|gtm).{0,40}\b(ai|ml|llm|genai|agentic)\b|"
        r"\b(ai|ml|llm|genai|agentic)\b.{0,40}(pre[\s\-]?sales|gtm)|\bgtm\b",
        "AI Pre-Sales / GTM Specialist",
        "AI_GTM_Sales",
    ),
    (
        r"solutions?\s*engineer.{0,40}\b(ai|ml|llm|genai)\b|"
        r"\b(ai|ml|llm|genai)\b.{0,40}solutions?\s*engineer|"
        r"ai\s*solutions?\s*engineer",
        "AI Solutions Engineer",
        "AI_GTM_Sales",
    ),
    # Generative_AI
    (
        r"agentic|ai\s*agent|multi[\s\-]?agent",
        "AI Agent / Agentic Engineer",
        "Generative_AI",
    ),
    (
        r"prompt\s*engineer|llm\s*app|rag\s*engineer",
        "Prompt / LLM Application Engineer",
        "Generative_AI",
    ),
    (
        r"generative\s*ai|genai|\bllm\b|gen\s*ai",
        "Generative AI Engineer",
        "Generative_AI",
    ),
    # AI_Leadership
    (
        r"head\s*of\s*ai|director\s*of\s*ai|vp[,\s].*\bai\b|vice\s*president.*\bai\b|"
        r"chief\s*ai|chief\s*digital\s*and\s*ai|\bcaio\b",
        "Head / Director of AI",
        "AI_Leadership",
    ),
    # AI_Product
    (
        r"ai\s*(product\s*)?designer|product\s*designer.{0,40}\bai\b|ai\s*ux|\bux\b.{0,20}\bai\b",
        "AI Designer / UX",
        "AI_Product",
    ),
    (
        r"ai\s*product|ml\s*product|product\s*manager.{0,40}\b(ai|ml|llm|genai|agent)\b|"
        r"\b(ai|ml|llm|genai)\b.{0,40}product\s*manager",
        "AI Product Manager",
        "AI_Product",
    ),
    # AI_Platform_MLOps
    (
        r"inference|model\s*serving|model\s*ops",
        "Inference / Serving Engineer",
        "AI_Platform_MLOps",
    ),
    (
        r"ai\s*infra|ai\s*infrastructure|training\s*infra|ml\s*infra|"
        r"gpu\s*cluster|(hpc).{0,20}\b(ml|ai)\b",
        "AI Infrastructure Engineer",
        "AI_Platform_MLOps",
    ),
    (r"mlops|ml\s*ops|machine\s*learning\s*ops", "MLOps Engineer", "AI_Platform_MLOps"),
    (r"ai\s*platform|ml\s*platform|feature\s*store", "AI Platform Engineer", "AI_Platform_MLOps"),
    # AI_Consulting_Architecture
    (r"ai\s*architect|ai\s*solution\s*architect", "AI Architect", "AI_Consulting_Architecture"),
    (
        r"ai\s*consultant|data[,\s/&]*ai\s*consultant|(consultant).{0,40}\b(ai|genai)\b",
        "AI Consultant",
        "AI_Consulting_Architecture",
    ),
    # AI_Research
    (
        r"ai\s*safety|alignment|interpretability",
        "AI Safety / Alignment",
        "AI_Research",
    ),
    (r"applied\s*scientist|applied\s*ai\s*scientist", "Applied Scientist", "AI_Research"),
    (
        r"research\s*scientist|ai\s*researcher|ai\s*research\s*scientist",
        "AI Research Scientist",
        "AI_Research",
    ),
    (r"research\s*engineer", "Research Engineer", "AI_Research"),
    # ML_Engineering
    (
        r"robotics.{0,40}\bai\b|\bai\b.{0,40}robotics|ai\s*manipulation",
        "Robotics AI Engineer",
        "ML_Engineering",
    ),
    (
        r"recommendation|ranking\s*engineer|recsys",
        "Recommendation / Ranking Engineer",
        "ML_Engineering",
    ),
    (r"deep\s*learning", "Deep Learning Engineer", "ML_Engineering"),
    (r"computer\s*vision|\bcv\s*engineer", "Computer Vision Engineer", "ML_Engineering"),
    (r"\bnlp\b|natural\s*language", "NLP Engineer", "ML_Engineering"),
    (
        r"machine\s*learning|\bml\s*engineer|\bml\s*scientist",
        "Machine Learning Engineer",
        "ML_Engineering",
    ),
    # Software_AI_Tagged (before generic AI Engineer)
    (
        r"(software\s*engineer|software\s*engineering|full[\s\-]?stack|\bsde\b|\bswe\b)"
        r".{0,50}\b(ai|ml|llm|genai|machine\s*learning)\b|"
        r"\b(ai|ml|llm|genai|machine\s*learning)\b.{0,50}"
        r"(software\s*engineer|software\s*engineering|full[\s\-]?stack|\bsde\b|\bswe\b)",
        "Software Engineer (AI/ML)",
        "Software_AI_Tagged",
    ),
    # AI_Engineering
    (
        r"member\s*of\s*technical\s*staff|\bmts\b",
        "Member of Technical Staff (AI)",
        "AI_Engineering",
    ),
    (r"\bai\s*scientist\b|artificial\s*intelligence\s*scientist", "AI Scientist", "AI_Engineering"),
    (
        r"\bai\s*engineer\b|artificial\s*intelligence\s*engineer|"
        r"ai\s*engineering|applied\s*ai\s*engineering",
        "AI Engineer",
        "AI_Engineering",
    ),
    (r"\bai\s*specialist\b|ml\s*specialist", "AI Engineer", "AI_Engineering"),
    # Data
    (r"analytics\s*engineer", "Analytics Engineer", "Data_Engineering"),
    (r"data\s*engineer", "Data Engineer", "Data_Engineering"),
    (r"data\s*scientist|data\s*science", "Data Scientist", "Data_Science"),
    # Late catch-alls
    (r"artificial\s*intelligence|\bai\b", "AI Engineer", "AI_Engineering"),
]


def excel_col_to_index(ref: str) -> int:
    letters = re.match(r"([A-Z]+)", ref or "")
    if not letters:
        return 0
    idx = 0
    for char in letters.group(1):
        idx = idx * 26 + (ord(char) - ord("A") + 1)
    return idx


def load_shared_strings(zf: ZipFile) -> List[str]:
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


def iter_xlsx_rows(
    path: Path, wanted_columns: Optional[Iterable[str]] = None
) -> Iterator[Dict[str, str]]:
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


def clean_text(value: object) -> str:
    return " ".join(str(value or "").strip().split())


def parse_number(value: object) -> Optional[float]:
    if value is None:
        return None
    text = str(value).strip().replace(",", "")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def parse_excel_date(value: object) -> str:
    if value is None:
        return ""
    text = str(value).strip()
    if not text:
        return ""
    try:
        serial = float(text)
        if serial > 20000:
            return (datetime(1899, 12, 30) + timedelta(days=serial)).date().isoformat()
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%m-%d-%Y"):
        try:
            return datetime.strptime(text[:10], fmt).date().isoformat()
        except ValueError:
            continue
    if len(text) >= 10 and text[4] == "-" and text[7] == "-":
        return text[:10]
    return text


def annualize(amount: object, unit: object) -> Optional[float]:
    num = parse_number(amount)
    if num is None:
        return None
    key = clean_text(unit).upper().replace(" ", "")
    if key.startswith("YEAR"):
        mult = 1
    elif key.startswith("MONTH"):
        mult = 12
    elif key in {"BI-WEEKLY", "BIWEEKLY"} or key.startswith("BI"):
        mult = 26
    elif key.startswith("WEEK"):
        mult = 52
    elif key.startswith("HOUR"):
        mult = 2080
    else:
        mult = 1
    return num * mult


def map_role(title: str, soc_code: str = "", soc_title: str = "") -> Optional[Tuple[str, str]]:
    """Return (Role_Name, Role_Family) or None if out of Phase-1 scope."""
    t = (title or "").lower()
    if DENYLIST_RE.search(t):
        return None

    matched = bool(INCLUDE_RE.search(t))
    if not matched:
        soc = (soc_code or "").strip()
        st = (soc_title or "").lower()
        if soc.startswith("15-2051") or "data scientist" in st:
            return ("Data Scientist", "Data_Science")
        if soc.startswith("15-1221") or "computer and information research" in st:
            return ("AI Research Scientist", "AI_Research")
        return None

    for pat, role_name, family in ROLE_RULES:
        if re.search(pat, t, flags=re.I):
            return (role_name, family)

    # Included by gate but no rule — keep in AI_Engineering rather than raw title
    return ("AI Engineer", "AI_Engineering")


def experience_level(pw_wage_level: object) -> str:
    text = clean_text(pw_wage_level).upper().replace("LEVEL", "").strip(" :-_")
    if text in {"IV", "4"}:
        return "Level_IV"
    if text in {"III", "3"}:
        return "Level_III"
    if text in {"II", "2"}:
        return "Level_II"
    if text in {"I", "1"}:
        return "Level_I"
    if "IV" in text:
        return "Level_IV"
    if "III" in text:
        return "Level_III"
    if "II" in text:
        return "Level_II"
    if re.search(r"\bI\b", text) or text == "1":
        return "Level_I"
    return "Other"


def career_level(title: str) -> str:
    t = (title or "").lower()
    if any(x in t for x in ("chief", "vp ", "vice president", "executive")):
        return "Executive"
    if any(x in t for x in ("principal", "staff", "distinguished")):
        return "Staff_Principal"
    if any(x in t for x in ("lead", "manager", "director", "head of")):
        return "Lead_Manager"
    if any(x in t for x in ("senior", "sr.", "sr ")):
        return "Senior"
    if any(x in t for x in ("junior", "associate", "intern", "entry")):
        return "Entry"
    return "Mid_Or_Mixed"


def is_certified(status: object) -> bool:
    return clean_text(status).upper().startswith("CERTIF")


def wage_ok(annual_from: Optional[float]) -> bool:
    return annual_from is not None and 30_000 <= annual_from <= 1_000_000


def resolve_worksites_path() -> Path:
    for path in WORKSITES_CANDIDATES:
        if path.exists():
            return path
    raise FileNotFoundError(
        "Worksites workbook not found. Expected one of:\n  "
        + "\n  ".join(str(p) for p in WORKSITES_CANDIDATES)
    )


def make_row(
    *,
    role: str,
    family: str,
    city: str,
    state: str,
    exp: str,
    career: str,
    annual_from: float,
    annual_to: Optional[float],
    employer: str,
    case_number: str,
    soc_code: str,
    visa_class: str,
    decision_date: str,
) -> Dict[str, object]:
    city_t = clean_text(city).title()
    state_u = clean_text(state).upper()
    loc = f"{city_t}, {state_u}".strip(", ")
    med = annual_from
    if annual_to is not None and annual_to > 0:
        med = (annual_from + annual_to) / 2.0
    base_max = annual_to if annual_to is not None and annual_to > 0 else annual_from
    pay = round(float(med), 2)
    return {
        "Grain": "LCA_Filing",
        "Role_Name": role,
        "Role_Family": family,
        "Country": "United States",
        "Location": loc or "United States",
        "City": city_t,
        "State": state_u,
        "Experience_Level": exp,
        "Career_Level": career,
        "Pay_Type": "Base",
        "Annual_Pay_USD": pay,
        "Annual_Pay_INR": round(pay * FX, 2),
        "Base_Min_USD": round(float(annual_from), 2),
        "Base_Median_USD": pay,
        "Base_Max_USD": round(float(base_max), 2),
        "Total_Comp_USD": "",
        "Bonus_USD": "",
        "Equity_USD": "",
        "Currency_Original": "USD",
        "Employer_Name": clean_text(employer).upper(),
        "Case_Number": clean_text(case_number),
        "SOC_Code": clean_text(soc_code),
        "Visa_Class": clean_text(visa_class) or "H-1B",
        "Fiscal_Year": FISCAL_YEAR,
        "Decision_Date": decision_date,
        "Source_Name": SOURCE_NAME,
        "Source_URL": SOURCE_URL,
        "Collection_Date": TODAY,
        "Sample_Size": "1",
        "Notes": NOTES,
    }


def load_ai_cases(disclosure: Path) -> Dict[str, Dict[str, object]]:
    print(f"Pass 1 - scanning disclosure: {disclosure.name}", flush=True)
    cases: Dict[str, Dict[str, object]] = {}
    scanned = 0
    kept = 0

    for row in iter_xlsx_rows(disclosure, CASE_COLUMNS):
        scanned += 1
        if scanned % 200_000 == 0:
            print(f"  scanned {scanned:,} ... kept {kept:,}", flush=True)

        if clean_text(row.get("VISA_CLASS")) != "H-1B":
            continue
        if not is_certified(row.get("CASE_STATUS")):
            continue

        title = clean_text(row.get("JOB_TITLE"))
        soc = clean_text(row.get("SOC_CODE"))
        soc_title = clean_text(row.get("SOC_TITLE"))
        mapped = map_role(title, soc, soc_title)
        if not mapped:
            continue
        role_name, role_family = mapped

        annual_from = annualize(row.get("WAGE_RATE_OF_PAY_FROM"), row.get("WAGE_UNIT_OF_PAY"))
        if not wage_ok(annual_from):
            continue

        case_number = clean_text(row.get("CASE_NUMBER"))
        if not case_number:
            continue

        annual_to = annualize(row.get("WAGE_RATE_OF_PAY_TO"), row.get("WAGE_UNIT_OF_PAY"))
        cases[case_number] = {
            "role": role_name,
            "family": role_family,
            "title": title,
            "employer": clean_text(row.get("EMPLOYER_NAME")),
            "soc_code": soc,
            "visa_class": clean_text(row.get("VISA_CLASS")),
            "decision_date": parse_excel_date(row.get("DECISION_DATE")),
            "city": clean_text(row.get("WORKSITE_CITY")),
            "state": clean_text(row.get("WORKSITE_STATE")),
            "annual_from": annual_from,
            "annual_to": annual_to,
            "exp": experience_level(row.get("PW_WAGE_LEVEL")),
            "career": career_level(title),
        }
        kept += 1

    print(f"  scanned {scanned:,} LCA rows -> {kept:,} AI H-1B certified cases", flush=True)
    return cases


def emit_from_worksites(
    worksites: Path,
    cases: Dict[str, Dict[str, object]],
    writer: csv.DictWriter,
) -> Set[str]:
    print(f"Pass 2 - streaming worksites: {worksites.name}", flush=True)
    seen: Set[str] = set()
    written = 0
    scanned = 0

    for row in iter_xlsx_rows(worksites, WORKSITE_COLUMNS):
        scanned += 1
        if scanned % 200_000 == 0:
            print(f"  scanned {scanned:,} worksites ... written {written:,}", flush=True)

        case_number = clean_text(row.get("CASE_NUMBER"))
        meta = cases.get(case_number)
        if not meta:
            continue

        annual_from = annualize(row.get("WAGE_RATE_OF_PAY_FROM"), row.get("WAGE_UNIT_OF_PAY"))
        if not wage_ok(annual_from):
            continue

        annual_to = annualize(row.get("WAGE_RATE_OF_PAY_TO"), row.get("WAGE_UNIT_OF_PAY"))
        city = clean_text(row.get("WORKSITE_CITY")) or str(meta["city"])
        state = clean_text(row.get("WORKSITE_STATE")) or str(meta["state"])
        exp = experience_level(row.get("PW_WAGE_LEVEL"))
        if exp == "Other":
            exp = str(meta["exp"])

        writer.writerow(
            make_row(
                role=str(meta["role"]),
                family=str(meta["family"]),
                city=city,
                state=state,
                exp=exp,
                career=str(meta["career"]),
                annual_from=float(annual_from),
                annual_to=annual_to,
                employer=str(meta["employer"]),
                case_number=case_number,
                soc_code=str(meta["soc_code"]),
                visa_class=str(meta["visa_class"]),
                decision_date=str(meta["decision_date"]),
            )
        )
        seen.add(case_number)
        written += 1

    print(
        f"  scanned {scanned:,} worksite rows -> wrote {written:,} filing rows "
        f"({len(seen):,} distinct cases)",
        flush=True,
    )
    return seen


def emit_disclosure_fallback(
    cases: Dict[str, Dict[str, object]],
    already: Set[str],
    writer: csv.DictWriter,
) -> int:
    print("Pass 3 - disclosure primary worksite fallback", flush=True)
    n = 0
    for case_number, meta in cases.items():
        if case_number in already:
            continue
        writer.writerow(
            make_row(
                role=str(meta["role"]),
                family=str(meta["family"]),
                city=str(meta["city"]),
                state=str(meta["state"]),
                exp=str(meta["exp"]),
                career=str(meta["career"]),
                annual_from=float(meta["annual_from"]),
                annual_to=meta["annual_to"] if meta["annual_to"] else None,
                employer=str(meta["employer"]),
                case_number=case_number,
                soc_code=str(meta["soc_code"]),
                visa_class=str(meta["visa_class"]),
                decision_date=str(meta["decision_date"]),
            )
        )
        n += 1
    print(f"  wrote {n:,} fallback rows", flush=True)
    return n


def print_role_summary(path: Path) -> None:
    from collections import Counter

    roles: Counter = Counter()
    families: Counter = Counter()
    with path.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            roles[row["Role_Name"]] += 1
            families[row["Role_Family"]] += 1
    print("Role_Family counts:")
    for fam, n in families.most_common():
        print(f"  {n:6d}  {fam}")
    print("Role_Name counts:")
    for role, n in roles.most_common():
        print(f"  {n:6d}  {role}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild MAX FreeSources CSV from DOL LCA Disclosure + Worksites."
    )
    parser.add_argument(
        "--disclosure",
        type=Path,
        default=DISCLOSURE_DEFAULT,
        help="Path to LCA_Disclosure_Data_*.xlsx",
    )
    parser.add_argument(
        "--worksites",
        type=Path,
        default=None,
        help="Path to LCA_Worksites_*.xlsx (optional; auto-detects defaults)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=OUT_CSV,
        help="Output MAX CSV path",
    )
    args = parser.parse_args()

    disclosure = args.disclosure
    if not disclosure.exists():
        raise FileNotFoundError(f"Missing disclosure workbook: {disclosure}")
    worksites = args.worksites if args.worksites else resolve_worksites_path()
    if not worksites.exists():
        raise FileNotFoundError(f"Missing worksites workbook: {worksites}")
    out_csv = args.out

    print("=" * 72)
    print("  Build MAX CSV (Role_Name / Role_Family taxonomy)")
    print("=" * 72)
    print(f"Disclosure : {disclosure.name}")
    print(f"Worksites  : {worksites.name}")
    print(f"Output     : {out_csv.name}")

    cases = load_ai_cases(disclosure)

    with out_csv.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=HEADERS)
        writer.writeheader()
        seen = emit_from_worksites(worksites, cases, writer)
        fallback_n = emit_disclosure_fallback(cases, seen, writer)

    with out_csv.open(encoding="utf-8") as handle:
        row_count = sum(1 for _ in handle) - 1

    print("-" * 72)
    print(
        f"DONE  rows={row_count:,}  cases_with_worksites={len(seen):,}  "
        f"fallback={fallback_n:,}"
    )
    print_role_summary(out_csv)
    print(f"Wrote {out_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
