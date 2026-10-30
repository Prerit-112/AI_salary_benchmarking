# India Tech Salary Benchmark Engine

## What this folder does (in plain English)

We take a large **US AI/Tech salary file** and convert each US pay figure into a **calibrated India-market salary (INR)**.

This is **not** a simple dollar-to-rupee currency conversion.

- Simple FX (about ×95) only answers: *“What is this US salary worth in rupees if I exchange money?”*
- Our formula answers: *“What would a similar India tech salary look like after adjusting for city, experience, role scarcity, and pay band?”*

| Item | Path |
|------|------|
| **Input (raw US data)** | `AI_Talent_Salary_Benchmark_MAX_FreeSources.csv` (~56,731 FY2026 Q3 filings; includes `Role_Family`) |
| **Engine script** | `india_tech_benchmark_engine.py` |
| **Clean / structure script** | `clean_india_benchmark.py` |
| **Filing grain (clean row-level)** | `india_tech_roles_benchmark.csv` (~53,754 rows) |
| **Summary grain (Role × Experience)** | `india_tech_roles_benchmark_summary.csv` (106 bands) |
| **DOL → MAX rebuild** | `build_max_from_dol_fy2026_q3.py` |
| **PayRisk Desk (UI)** | `apps/comp-intel/` |
| **Related India country deliverable (separate published/GCC file)** | `output/country/India_AI_Salary_Benchmark.csv` |

> **Note:** `output/country/India_AI_Salary_Benchmark.csv` is the project’s India country benchmark deliverable (different schema; published/GCC-style rows).  
> The **US → India calibration formula** (plus multi-metro expansion) is in `india_tech_benchmark_engine.py`.  
> `clean_india_benchmark.py` then formats, dedupes, structures that output into two clear grains, and refreshes metro columns on both.

---

## The master formula

```text
Benchmark_INR_Salary =
    Annual_Pay_USD
  × R_B
  × Delta_Geo
  × Gamma_Exp
  × Omega_Role
  × Phi_Floor
```

Then we **round to the nearest ₹1,000** for clean compensation tables.

`Benchmark_INR_Salary` is always the **Bengaluru baseline** (`Target_City_Hub = Bengaluru`).

### Multi-metro expansion (after the master formula)

Other Indian tech hubs are scaled from that Bengaluru result:

```text
Benchmark_INR_<Metro> = Benchmark_INR_Salary × Metro_Multiplier
```

| Metro | Multiplier | Plain meaning |
|-------|------------|---------------|
| Mumbai | **1.05** | ~5% premium vs Bengaluru |
| Delhi_NCR | **0.95** | ~5% discount |
| Hyderabad | **0.90** | ~10% discount |
| Pune | **0.88** | ~12% discount |
| Chennai | **0.85** | ~15% discount |

Filing columns: `Benchmark_INR_Mumbai`, `Benchmark_INR_Delhi_NCR`, `Benchmark_INR_Hyderabad`, `Benchmark_INR_Chennai`, `Benchmark_INR_Pune`.  
Summary grain carries the same metros as `Benchmark_<Metro>_P25 / Median / P75 / Mean`.

> **Note:** Metro multipliers are a **post-hoc hub expansion** on the Bengaluru baseline.  
> They are separate from `I_IND` / `Delta_Geo` (those only apply when a `Target_India_City` column exists in the source — it does not today).

### Tiny walkthrough (real row from the data)

**Input row**

| Field | Value |
|-------|-------|
| Role | AI Research Scientist |
| City | Bellevue |
| Experience / Career | Other / Mid_Or_Mixed |
| Annual_Pay_USD | 184,287 |

**Factors chosen**

| Factor | Value | Why |
|--------|-------|-----|
| R_B | 40.0 | Fixed India parity anchor |
| I_US | 1.10 | Bellevue is a high-cost US tech hub |
| I_IND | 1.00 | No India target city in source → Bengaluru baseline |
| Delta_Geo | 1.00 / 1.10 = **0.909** | India vs US city ratio |
| Gamma_Exp | **1.280** | Mid_Or_Mixed → ~8 YoE proxy |
| Omega_Role | **1.15** | AI Research Scientist scarcity band |
| Phi_Floor | **1.00** | Pay > $140k → no junior compression |

**Calculation**

```text
184,287 × 40 × 0.909 × 1.280 × 1.15 × 1.00
  ≈ 9,864,380
  → rounded → Benchmark_INR_Salary = ₹9,864,000 (Bengaluru)
  → Mumbai × 1.05 → Benchmark_INR_Mumbai = ₹10,357,200
```

Compare that with the source column `Annual_Pay_INR` ≈ ₹17,586,508 (naive FX only). Same US pay, very different India meaning.

---

## Factor-by-factor guide

### 1) `Annual_Pay_USD` — starting US annual pay

**What it is:** The US salary from the source file (base / offered annual pay in USD).

**How we handle it:**
- Convert to number
- If missing/blank, fill with the **dataset average** so the pipeline does not break

**Example:** `184,287` means the US offer was about $184k/year.

---

### 2) `R_B` — Base Parity Anchor (fixed constant)

**What it is:** A hardcoded multiplier that converts US dollars into an India rupee **market-parity scale** (not live FX).

```text
R_B = 40.0   (immutable in the script)
```

**Why 40 (not ~95 FX)?**  
FX (~95) keeps US purchasing power in rupee *units*.  
`R_B = 40` is a deliberate **India market calibration anchor** so results sit closer to realistic India tech bands after the other factors apply.

**Example:**  
`$100,000 × 40 = ₹4,000,000` before geo / experience / role / floor adjustments.

---

### 3) `Delta_Geo` — Geographic Pair Index Ratio

**Idea:** A San Francisco salary should not map 1:1 to an India hub the same way a smaller US city salary does. We adjust using:

```text
Delta_Geo = I_IND / I_US
```

#### Step A — clean the city text
City names are normalized: strip spaces + uppercase  
(`" Bellevue "` → `"BELLEVUE"`)

#### Step B — `I_US` (US city cost/tech premium)

| US city (examples) | I_US | Why this value |
|--------------------|------|----------------|
| San Francisco, SF, Sunnyvale, Palo Alto, Menlo Park, Silicon Valley | **1.20** | Highest US tech premium |
| New York, NYC | **1.15** | Very high cost / finance-tech hub |
| Bellevue, Seattle | **1.10** | Strong Pacific NW tech hubs |
| Austin, Boston, Cambridge, Los Angeles, Irvine | **1.00** | Mid / standard major-city baseline |
| Any other / missing city | **0.85** | Lower US regional fallback |

**What we take:** `City` column → map → `I_US`

**Example:** Bellevue → `I_US = 1.10`  
Prosper, TX (not in map) → `I_US = 0.85`

#### Step C — `I_IND` (India city index)

| India city | I_IND | Meaning |
|------------|-------|---------|
| Bengaluru / Bangalore | **1.00** | Hub baseline (reference = 1) |
| Mumbai | **1.10** | Higher than Bengaluru |
| Delhi / NCR / Gurgaon / Noida | **0.92** | Slightly below Bengaluru |
| Hyderabad | **0.88** | Below NCR |
| Pune / Chennai | **0.82** | Lower relative index |

**What we take:**
- If column `Target_India_City` exists → map it to `I_IND`
- If it does **not** exist (true for current source file) → set every row `I_IND = 1.00` (Bengaluru default)

#### Step D — compute `Delta_Geo`

| Case | I_IND | I_US | Delta_Geo | Plain meaning |
|------|-------|------|-----------|---------------|
| Bellevue → Bengaluru | 1.00 | 1.10 | **0.91** | High US city → pull India result down a bit |
| Prosper → Bengaluru | 1.00 | 0.85 | **1.18** | Lower US city → India result rises relatively |
| If Mumbai target existed | 1.10 | 1.20 (SF) | **0.92** | SF → Mumbai still a discount vs SF premium |

---

### 4) `Gamma_Exp` — Experience Elasticity Scalar

**Idea:** More experience → higher India premium factor.

We read **both** `Experience_Level` and `Career_Level`, uppercase them, and match keywords (highest tier wins).

```text
Gamma_Exp = 1 + 0.035 × YoE
```

| If text contains… | Assumed YoE | Gamma_Exp formula | Gamma_Exp value |
|-------------------|-------------|-------------------|-----------------|
| EXECUTIVE, LEAD_MANAGER, DIRECTOR | 18 | `1 + 0.035×18` | **1.630** |
| LEVEL_IV, STAFF, PRINCIPAL | 13 | `1 + 0.035×13` | **1.455** |
| LEVEL_III, SENIOR, MID_OR_MIXED | 8 | `1 + 0.035×8` | **1.280** |
| LEVEL_II, ASSOCIATE | 4 | `1 + 0.035×4` | **1.140** |
| ENTRY, LEVEL_I, FRESHER | 0 | `1 + 0.035×0` | **1.000** |
| Empty / unmapped (e.g. Other alone) | — | default | **1.280** (senior proxy) |

**Why this selection order?**  
We check senior labels first so `LEVEL_IV + Mid_Or_Mixed` keeps **Level IV (13 YoE)**, not Mid_Or_Mixed (8).  
Also `LEVEL_II` is checked before `LEVEL_I` so “Level_II” is not misread as “Level_I”.

**Examples**

| Experience_Level | Career_Level | Match used | YoE | Gamma_Exp |
|------------------|--------------|------------|-----|-----------|
| Level_IV | Mid_Or_Mixed | LEVEL_IV | 13 | **1.455** |
| Level_II | Senior | SENIOR (higher tier than Level_II) | 8 | **1.280** |
| Other | Mid_Or_Mixed | MID_OR_MIXED | 8 | **1.280** |
| Entry | — | ENTRY | 0 | **1.000** |

---

### 5) `Omega_Role` — Role Scarcity Index

**Idea:** Scarce AI specialties pay a premium over general data roles.

When `Role_Family` is present (current MAX), we map scarcity by family first:

| Role_Family | Omega_Role |
|-------------|------------|
| Generative_AI | **1.25** |
| ML_Engineering · FD · AI_Platform_MLOps | **1.20** |
| AI_Research · AI_Leadership | **1.15** |
| AI_Engineering · AI_Product · AI_Consulting_Architecture | **1.12** |
| AI_GTM_Sales · Software_AI_Tagged | **1.08** |
| Data_Science | **1.05** |
| Data_Engineering | **1.00** |
| Anything else | **1.05** (default) |

If `Role_Family` is missing, we fall back to ordered `Role_Name` substring matching (same scarcity ladder).

**Examples**

| Role_Name | Role_Family | Omega_Role |
|-----------|-------------|------------|
| Forward Deployed AI Engineer | FD | **1.20** |
| Generative AI Engineer | Generative_AI | **1.25** |
| AI Research Scientist | AI_Research | **1.15** |
| Data Engineer | Data_Engineering | **1.00** |
| Data Scientist | Data_Science | **1.05** |

---

### 6) `Phi_Floor` — Pay-band Floor Compression

**Idea:** Very high US junior offers can overstate India pay if converted linearly. We compress lower US bands more, and leave high expert bands alone.

| Annual_Pay_USD | Phi_Floor | Plain meaning |
|----------------|-----------|---------------|
| **< $90,000** | **0.45** | Strong compression (junior / lower band) |
| **$90,000 – $140,000** | **0.75** | Medium compression |
| **> $140,000** | **1.00** | No compression (premium band kept) |

**Examples**

| Annual_Pay_USD | Phi_Floor |
|----------------|-----------|
| 80,000 | 0.45 |
| 130,000 | 0.75 |
| 184,287 | 1.00 |

---

## End-to-end worked examples

### Example A — High US hub, research role (Bellevue)

```text
Annual_Pay_USD = 184,287
R_B            = 40
Delta_Geo      = 1.00 / 1.10 = 0.909
Gamma_Exp      = 1.280
Omega_Role     = 1.15
Phi_Floor      = 1.00

Benchmark_INR_Salary ≈ ₹9,864,000   (Bengaluru baseline)
Benchmark_INR_Mumbai ≈ ₹10,357,200  (× 1.05)
Benchmark_INR_Pune   ≈ ₹8,680,320   (× 0.88)
```

### Example B — Non-mapped US city, Data Engineer, Level IV (Prosper, TX)

```text
Annual_Pay_USD = 155,939.24
I_US           = 0.85   (fallback)
I_IND          = 1.00
Delta_Geo      = 1.176
Gamma_Exp      = 1.455  (Level_IV → 13 YoE)
Omega_Role     = 1.00   (Data Engineer)
Phi_Floor      = 1.00   (pay > 140k)

Benchmark_INR_Salary ≈ ₹10,677,000
```

### Example C — Mid band + Senior label (Jersey City Data Scientist)

```text
Annual_Pay_USD = 130,000
I_US           = 0.85
Delta_Geo      = 1.176
Gamma_Exp      = 1.280  (Senior matched)
Omega_Role     = 1.05
Phi_Floor      = 0.75   (90k–140k band)

Benchmark_INR_Salary ≈ ₹6,167,000
```

---

## Clean structured output (two grains)

### Grain 1 — Filing (row-level)

File: `india_tech_roles_benchmark.csv`  
One row = one US LCA filing worksite, mapped to India.

**Cleaning applied**
- Removed **1,960** duplicate rows (exact / same case + city + pay + role)
- Dropped empty columns (`Total_Comp_USD`, `Bonus_USD`, `Equity_USD` — all blank)
- Rounded money to 2 decimals; factors to 2–4 decimals; INR benchmark to whole rupees
- Renamed `Annual_Pay_INR` → `Annual_Pay_INR_FX` (clearer: FX only, not market benchmark)
- Flagged unrealistic US base pay **> $500,000** as `OUTLIER_PAY` (54 rows kept but flagged)
- Sorted by Role Family → Role → Experience Band → City

**Column layout (left → right)**

| Section | Columns |
|---------|---------|
| Identity | `Record_ID`, `Grain`, `Case_Number` |
| India target | `Target_Country`, `Target_City_Hub` |
| Role | `Role_Name`, `Role_Family`, `Role_Scarcity_Band` |
| US location | `Country`, `State`, `City`, `Location`, `US_City_Tier` |
| Experience | `Experience_Level`, `Career_Level`, `Experience_Band`, `YoE_Proxy` |
| US pay | `Pay_Type`, `Annual_Pay_USD`, `Annual_Pay_INR_FX`, base min/median/max |
| Calibration | `R_B`, `I_US`, `I_IND`, `Delta_Geo`, `Gamma_Exp`, `Omega_Role`, `Phi_Floor` |
| India result (Bengaluru) | `Benchmark_INR_Salary` |
| India metros | `Benchmark_INR_Mumbai`, `Benchmark_INR_Delhi_NCR`, `Benchmark_INR_Hyderabad`, `Benchmark_INR_Chennai`, `Benchmark_INR_Pune` |
| Quality | `Data_Quality_Flag` |
| Provenance | Employer, SOC, visa, dates, source, notes |

### Grain 2 — Role × Experience (summary)

File: `india_tech_roles_benchmark_summary.csv`  
One row = one **Role_Name × Experience_Band** market band (OK rows only).  
`Target_City_Hub = Multi-Metro Calibrated`.

Includes sample size and India INR **P25 / Median / P75 / Mean** for Bengaluru, plus the same bands for each metro — the grain you usually use for compensation tables.

**Example (Bengaluru medians)**

| Role | Experience_Band | Sample | Median INR (BLR) |
|------|-----------------|--------|------------------|
| AI Engineer | Entry (0-2 Years) | 5 | ₹3,335,000 |
| AI Engineer | Lead / Staff (10-14 Years) | 72 | ₹13,660,000 |

Entry AI Engineer metro medians from the same row: Mumbai ≈ ₹3,501,750 · Delhi_NCR ≈ ₹3,168,250 · Hyderabad ≈ ₹3,001,500 · Pune ≈ ₹2,934,800 · Chennai ≈ ₹2,834,750.

### Do not confuse these INR fields

| Column | Meaning |
|--------|---------|
| `Annual_Pay_INR_FX` | Original FX-style conversion of US pay (≈ USD × ~95). **Not** India market pay. |
| `Benchmark_INR_Salary` | Calibrated India tech market salary (Bengaluru baseline). **Primary India figure.** |
| `Benchmark_INR_<Metro>` / `Benchmark_<Metro>_*` | Same benchmark scaled to Mumbai / Delhi_NCR / Hyderabad / Chennai / Pune. |

---

## How processing works (engineering notes)

1. Read `AI_Talent_Salary_Benchmark_MAX_FreeSources.csv`
2. Fill missing `Annual_Pay_USD` with the column mean
3. Compute all factors with **vectorized pandas/numpy** (no row loops)
4. Multiply factors → round `Benchmark_INR_Salary` to nearest ₹1,000 (Bengaluru)
5. Expand metros: `Benchmark_INR_<Metro> = Benchmark_INR_Salary × metro multiplier`
6. Write calibrated filing file
7. Run cleaner: dedupe, format, structure columns, refresh metro columns, build multi-metro summary grain

### Run it (India calibration only)

From this folder (`ai_salary/`):

```bash
python india_tech_benchmark_engine.py
python clean_india_benchmark.py
```

Requires: `pandas`, `numpy`

---

## Run the UI (PayRisk Desk)

```bash
cd apps/comp-intel
npm install
npm run dev
```

`npm run dev` re-ingests the India CSVs into `public/data/*.json`, then starts Vite. Open the URL it prints (usually `http://localhost:5173`).

If CSVs changed while the server was already running, stop it (Ctrl+C) and run `npm run dev` again so ingest picks up the new bands.

---

## Updating the data later (refresh runbook)

When DOL publishes a newer quarter (or you want to remap roles):

1. **Download** from https://www.dol.gov/agencies/eta/foreign-labor/performance  
   - `LCA_Disclosure_Data_FY{YYYY}_Q{n}.xlsx`  
   - `LCA_Worksites_FY{YYYY}_Q{n}.xlsx` (filename may use `FY_` with an extra underscore)

2. **Place** both files in this folder (`ai_salary/`). Update default paths in `build_max_from_dol_fy2026_q3.py` if the quarter/year changed, or pass CLI flags.

3. **Rebuild MAX** (canonical roles + `Role_Family`, including `FD`):

```bash
python build_max_from_dol_fy2026_q3.py
# or, for a newer quarter:
python build_max_from_dol_fy2026_q3.py --disclosure LCA_Disclosure_Data_FY2027_Q1.xlsx --worksites LCA_Worksites_FY2027_Q1.xlsx
```

   Writes `AI_Talent_Salary_Benchmark_MAX_FreeSources.csv`.

4. **Recalibrate India filings + summary:**

```bash
python india_tech_benchmark_engine.py
python clean_india_benchmark.py
```

5. **Refresh the UI data layer:**

```bash
cd apps/comp-intel
npm run ingest
# or just:
npm run dev
```

Role taxonomy lives in `build_max_from_dol_fy2026_q3.py` (`INCLUDE_RE`, `DENYLIST_RE`, `ROLE_RULES`). Scarcity (`Omega_Role`) lives in `india_tech_benchmark_engine.py` and should stay aligned with `Role_Family` names.

---

## Quick mental model

Think of the formula as five dials on top of US pay, then one hub switch:

1. **R_B** — “Convert into India salary scale”
2. **Delta_Geo** — “Adjust for city pair (US city vs India hub)”
3. **Gamma_Exp** — “Adjust for experience”
4. **Omega_Role** — “Adjust for how scarce the skill is”
5. **Phi_Floor** — “Compress junior US bands; keep senior bands”
6. **Metro multiplier** — “Scale Bengaluru baseline → Mumbai / NCR / Hyderabad / Pune / Chennai”

Together they turn a US offer into India-market **benchmark INR salaries** (Bengaluru + metros), with every dial stored in the CSV so anyone can audit the math.
