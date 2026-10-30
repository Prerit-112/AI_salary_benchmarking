# India Tech Salary Benchmark Engine  
## Engineering System Design & Documentation Handbook

| Attribute | Value |
|-----------|-------|
| **Document class** | Publication-grade system design / data architecture handbook |
| **System** | India Tech Salary Benchmark Engine (`ai_salary/`) |
| **Primary calibration script** | `india_tech_benchmark_engine.py` |
| **Primary quality / grain script** | `clean_india_benchmark.py` |
| **Source grain** | `AI_Talent_Salary_Benchmark_MAX_FreeSources.csv` — **56,731** FY2026 Q3 filings × **30** columns (incl. `Role_Family`) |
| **Filing grain (output)** | `india_tech_roles_benchmark.csv` — **53,754** rows |
| **Summary grain (output)** | `india_tech_roles_benchmark_summary.csv` — **106** Role × Experience bands |
| **Runtime model** | Fully vectorized NumPy / pandas (no Python row loops in calibration math) |
| **Currency of truth for India market pay** | `Benchmark_INR_Salary` (Bengaluru baseline) and metro-expanded `Benchmark_INR_*` / `Benchmark_<Metro>_*` |

---

## Table of Contents

1. [System Architecture & Data Lineage](#1-system-architecture--data-lineage)  
2. [Algorithmic Mathematical Derivation](#2-algorithmic-mathematical-derivation)  
3. [Weight Matrix Metadata & Justifications](#3-weight-matrix-metadata--justifications)  
4. [Cleaning & Quality Engineering Reconciliation](#4-cleaning--quality-engineering-reconciliation)  
5. [Multi-Grain Schema Specification](#5-multi-grain-schema-specification)  
6. [Operational Runbook](#6-operational-runbook)  
7. [Audit Appendix — Empirical Population Snapshots](#7-audit-appendix--empirical-population-snapshots)

---

## 1. System Architecture & Data Lineage

### 1.1 Architectural Intent

The engine does **not** perform foreign-exchange (FX) conversion of United States offered base wages into Indian rupees. FX answers the cash-transfer question:

> “If I exchanged this USD wage at the spot rate, how many INR would I hold?”

The engine answers the **labor-market parity** question:

> “What India-market annual cash compensation (INR) is the economically coherent analogue for this US AI/Tech filing after city-pair, experience elasticity, role scarcity, and pay-band floor compression?”

That distinction is material. Source column `Annual_Pay_INR` (later renamed `Annual_Pay_INR_FX`) is typically USD × ≈95 and must never be treated as India market pay. Calibrated India pay lives exclusively in `Benchmark_INR_Salary` and its metro expansions.

### 1.2 End-to-End Pipeline Topology

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ STAGE 0 — SOURCE OF RECORD                                                   │
│ AI_Talent_Salary_Benchmark_MAX_FreeSources.csv                               │
│ Grain: LCA_Filing | n = 56,731 | schema width = 30 (Role_Family)             │
│ Provenance: US DOL OFLC LCA Disclosure FY2026 Q3 (H-1B wage facts)           │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STAGE 1 — CALIBRATION ENGINE                                                 │
│ india_tech_benchmark_engine.py                                               │
│                                                                              │
│  1.1 load_source()              CSV → DataFrame                              │
│  1.2 prepare_numeric_inputs()   Annual_Pay_USD → float; NaN → column mean    │
│  1.3 compute_delta_geo()        I_US, I_IND, Delta_Geo = I_IND / I_US        │
│  1.4 compute_gamma_exp()        YoE proxy → Gamma_Exp = 1 + 0.035·YoE        │
│  1.5 compute_omega_role()       Role_Name regex ladder → Omega_Role          │
│  1.6 compute_phi_floor()        Pay-band thresholds → Phi_Floor              │
│  1.7 compute_benchmark_inr()    Master product; round to nearest ₹1,000      │
│  1.8 compute_metro_benchmarks() Bengaluru × metro multipliers                │
│                                                                              │
│ Intermediate write: india_tech_roles_benchmark.csv (calibrated, pre-clean)   │
└───────────────────────────────────┬──────────────────────────────────────────┘
                                    │
                                    ▼
┌──────────────────────────────────────────────────────────────────────────────┐
│ STAGE 2 — QUALITY / STRUCTURE ENGINE                                         │
│ clean_india_benchmark.py                                                     │
│                                                                              │
│  2.1 String hygiene + Title/UPPER place normalization                        │
│  2.2 Numeric coercion of money + calibration audit columns                   │
│  2.3 Drop always-null Total_Comp_USD / Bonus_USD / Equity_USD                │
│  2.4 Deduplicate: exact rows + (Case_Number, City, State, Pay, Role)         │
│  2.5 Derive Role_Family, Experience_Band, YoE_Proxy, US_City_Tier,           │
│      Role_Scarcity_Band, Target_*, R_B, Data_Quality_Flag                    │
│  2.6 Round / rename Annual_Pay_INR → Annual_Pay_INR_FX                       │
│  2.7 Refresh metro INR columns from Bengaluru baseline                       │
│  2.8 Column sectional reorder + stable Record_ID + mergesort                 │
│                                                                              │
│  GRAIN 1 WRITE → india_tech_roles_benchmark.csv          (64,839 filings)    │
│  GRAIN 2 BUILD → Role × Experience OK-only percentiles + metro scale         │
│  GRAIN 2 WRITE → india_tech_roles_benchmark_summary.csv  (236 bands)         │
└──────────────────────────────────────────────────────────────────────────────┘
```

### 1.3 Data Lineage Graph (Column Families)

```text
SOURCE COLUMNS (consumed by Stage 1)
────────────────────────────────────
Annual_Pay_USD ─────────────────────┐
City ──────────► I_US ──┐            │
(Target_India_City*)     │            │
               I_IND ────┤► Delta_Geo ┤
Experience_Level ┐       │            │
Career_Level ────┴► YoE ► Gamma_Exp ──┤► Benchmark_INR_Salary
Role_Name ──────────────► Omega_Role ─┤   (= Bengaluru baseline)
Annual_Pay_USD ─────────► Phi_Floor ──┤
R_B = 40 (constant) ──────────────────┘
                                      │
                                      ├──► Benchmark_INR_Mumbai      (× 1.05)
                                      ├──► Benchmark_INR_Delhi_NCR   (× 0.95)
                                      ├──► Benchmark_INR_Hyderabad   (× 0.90)
                                      ├──► Benchmark_INR_Pune        (× 0.88)
                                      └──► Benchmark_INR_Chennai     (× 0.85)

* Target_India_City is supported by the engine but is ABSENT from the current
  source extract; I_IND is therefore forced to 1.00 (Bengaluru) for every row.

STAGE 2 DERIVED COLUMNS (not in source)
───────────────────────────────────────
Record_ID, Grain, Target_Country, Target_City_Hub, R_B,
Role_Family, Role_Scarcity_Band, Experience_Band, YoE_Proxy,
US_City_Tier, Data_Quality_Flag, Annual_Pay_INR_FX (rename)
```

### 1.4 Row-Count Reconciliation (Observed Production Counts)

| Stage | Artifact | Rows | Delta vs prior |
|-------|----------|------|----------------|
| Source | `AI_Talent_Salary_Benchmark_MAX_FreeSources.csv` | **66,799** | — |
| Post-calibration write | Engine output (same path as filing grain) | 66,799 | 0 (row-preserving transform) |
| Post-clean filing grain | `india_tech_roles_benchmark.csv` | **64,839** | **−1,960** (dedupe) |
| Quality OK subset | `Data_Quality_Flag == "OK"` | **64,785** | −54 outliers retained but excluded from summary |
| Summary grain | `india_tech_roles_benchmark_summary.csv` | **236** | Aggregation of OK filings; `Sample_Size` Σ = **64,785** |

### 1.5 Trust Boundary Between Stages

| Concern | Owner | Guarantees |
|---------|-------|------------|
| Factor mathematics | `india_tech_benchmark_engine.py` | Deterministic vectorized product; audit columns always written |
| Economic interpretability columns | `clean_india_benchmark.py` | Role family, experience bands, scarcity labels, quality flags |
| Deduplication | `clean_india_benchmark.py` | Exact + LCA worksite uniqueness |
| Metro consistency | Both scripts share identical `METRO_MULTIPLIERS` | Cleaner **recomputes** metros from Bengaluru so summary and filing cannot drift |
| Outlier exclusion from bands | `build_summary_grain()` | Only `OK` rows enter P25 / Median / P75 / Mean |

---

## 2. Algorithmic Mathematical Derivation

### 2.1 Master Formula

Let each filing \(i\) carry an offered United States annual base wage \(P_i^{\text{USD}}\). The India-market Bengaluru baseline benchmark is:

\[
B_i^{\text{INR}}
=
P_i^{\text{USD}}
\cdot
R_B
\cdot
\Delta_i^{\text{Geo}}
\cdot
\Gamma_i^{\text{Exp}}
\cdot
\Omega_i^{\text{Role}}
\cdot
\Phi_i^{\text{Floor}}
\]

with discrete presentation rounding:

\[
\texttt{Benchmark\_INR\_Salary}_i
=
\operatorname{round}_{1000}\!\left(B_i^{\text{INR}}\right)
=
\left\lfloor
\frac{B_i^{\text{INR}}}{1000}
+
\frac{1}{2}
\right\rfloor
\cdot 1000
\]

In pandas this is implemented as `.round(-3)` (negative decimal places = nearest thousand), then cast to integer.

### 2.2 Factor Definitions (Closed Form)

#### Base parity anchor

\[
R_B = 40
\]

Immutable scalar. Not a live FX quote. It is a **purchasing-power / market-parity calibration constant** that places the subsequent multiplicative field into realistic India tech cash bands.

#### Geographic pair index ratio

\[
\Delta_i^{\text{Geo}}
=
\frac{I_i^{\text{IND}}}{I_i^{\text{US}}}
\]

where \(I_i^{\text{US}}\) is mapped from normalized `City`, and \(I_i^{\text{IND}}\) is mapped from `Target_India_City` when present, else \(I_i^{\text{IND}} = 1.00\).

Division-by-zero guard in code:

\[
I_i^{\text{US}} \leftarrow
\begin{cases}
I_i^{\text{US}} & I_i^{\text{US}} \neq 0 \\
\text{NaN} & I_i^{\text{US}} = 0
\end{cases}
\quad\Rightarrow\quad
\Delta_i^{\text{Geo}}
\leftarrow
\frac{I^{\text{IND}}_{\text{default}}}{I^{\text{US}}_{\text{fallback}}}
=
\frac{1.00}{0.85}
\approx 1.1765
\text{ when undefined}
\]

#### Experience elasticity

\[
\Gamma_i^{\text{Exp}}
=
\begin{cases}
1 + 0.035 \cdot Y_i & Y_i \ge 0 \\
1.280 & \text{unmapped / null / OTHER-only}
\end{cases}
\]

where \(Y_i\) (years-of-experience proxy) is selected by ordered keyword containment over the concatenated field:

\[
C_i = \operatorname{upper}\!\big(\operatorname{strip}(\texttt{Experience\_Level}_i)\big)
\;\|\;
\operatorname{upper}\!\big(\operatorname{strip}(\texttt{Career\_Level}_i)\big)
\]

\[
Y_i =
\begin{cases}
18 & C_i \supset \{\texttt{EXECUTIVE}, \texttt{LEAD\_MANAGER}, \texttt{DIRECTOR}\} \\
13 & C_i \supset \{\texttt{LEVEL\_IV}, \texttt{STAFF}, \texttt{PRINCIPAL}\} \\
8  & C_i \supset \{\texttt{LEVEL\_III}, \texttt{SENIOR}, \texttt{MID\_OR\_MIXED}\} \\
4  & C_i \supset \{\texttt{LEVEL\_II}, \texttt{ASSOCIATE}\} \\
0  & C_i \supset \{\texttt{ENTRY}, \texttt{LEVEL\_I}(\text{not followed by I/V}), \texttt{FRESHER}\} \\
-1 & \text{otherwise (triggers default }\Gamma=1.280\text{)}
\end{cases}
\]

Explicit tier values therefore expand to:

\[
\begin{align*}
Y=0 &\Rightarrow \Gamma=1.000 \\
Y=4 &\Rightarrow \Gamma=1.140 \\
Y=8 &\Rightarrow \Gamma=1.280 \\
Y=13 &\Rightarrow \Gamma=1.455 \\
Y=18 &\Rightarrow \Gamma=1.630
\end{align*}
\]

#### Role scarcity index

\[
\Omega_i^{\text{Role}}
=
\begin{cases}
1.25 & \texttt{Role\_Name} \supset \{\texttt{GENERATIVE AI}, \texttt{LLM ARCHITECT}, \texttt{DEEP LEARNING}\} \\
1.20 & \supset \{\texttt{MACHINE LEARNING}, \texttt{MLOPS}\} \\
1.15 & \supset \{\texttt{AI RESEARCH SCIENTIST}, \texttt{APPLIED SCIENTIST}, \texttt{RESEARCH ENGINEER}, \texttt{COMPUTER VISION}, \texttt{NLP}\} \\
1.05 & \supset \{\texttt{DATA SCIENTIST}\} \\
1.00 & \supset \{\texttt{DATA ENGINEER}, \texttt{ANALYTICS ENGINEER}\} \\
1.05 & \text{default (unmatched AI/tech titles)}
\end{cases}
\]

First match wins (highest scarcity evaluated first).

#### Pay-band floor compression

\[
\Phi_i^{\text{Floor}}
=
\begin{cases}
0.45 & P_i^{\text{USD}} < 90{,}000 \\
0.75 & 90{,}000 \le P_i^{\text{USD}} \le 140{,}000 \\
1.00 & P_i^{\text{USD}} > 140{,}000
\end{cases}
\]

### 2.3 Multi-Metro Expansion (Post-Master Formula)

Let \(B_i^{\star}\) denote the rounded Bengaluru baseline (`Benchmark_INR_Salary`). For each metro \(m\):

\[
B_{i,m}^{\text{INR}}
=
B_i^{\star}
\cdot
\mu_m
\]

\[
\mu
=
\{
\texttt{Mumbai}: 1.05,\;
\texttt{Delhi\_NCR}: 0.95,\;
\texttt{Hyderabad}: 0.90,\;
\texttt{Pune}: 0.88,\;
\texttt{Chennai}: 0.85
\}
\]

**Architectural note:** \(\mu_m\) is a **post-hoc hub expansion** on the Bengaluru baseline. It is *not* the same mechanism as \(I^{\text{IND}}\) inside \(\Delta^{\text{Geo}}\). Today’s source lacks `Target_India_City`, so \(\Delta^{\text{Geo}}\) always uses \(I^{\text{IND}}=1.00\); metro diversity is delivered exclusively via \(\mu_m\).

Summary-grain percentiles are computed on Bengaluru \(B_i^{\star}\), then scaled:

\[
\operatorname{P}_q(B_{\cdot,m})
=
\mu_m \cdot \operatorname{P}_q(B^{\star})
\quad\text{for } q \in \{0.25, 0.50, 0.75\},\;\text{and Mean likewise.}
\]

### 2.4 Vector Mechanics — How pandas / NumPy Avoid Row Loops

The calibration stage never iterates `for row in df`. Every factor is a **column vector** of length \(N = 66{,}799\). Element-wise multiplication is a single SIMD-friendly ufunc chain.

#### String normalization (vectorized)

```python
series.fillna("").astype(str).str.strip().str.upper()
```

Produces a length-\(N\) object array of normalized tokens without Python-level per-cell branching.

#### Dictionary map with fillna (I_US)

```python
city_norm.map(US_CITIES_MAP).fillna(I_US_FALLBACK).astype(float)
```

This is an \(O(N)\) hash join against a tiny constant dictionary, not a Python `if/elif` tree.

#### Ordered categorical selection via `np.select`

`np.select(conditions, choices, default=...)` evaluates a list of Boolean masks of shape \((N,)\) and emits a single numeric array. Internally this is equivalent to:

\[
v_i = c_{k^*(i)}
\quad\text{where}\quad
k^*(i) = \min\{k : M_{k,i} = \texttt{True}\}
\]

Used for \(Y_i\), \(\Omega_i\), and \(\Phi_i\).

#### Master product as broadcasted Series arithmetic

```python
raw = (
    df["Annual_Pay_USD"].astype(float)
    * R_B
    * df["Delta_Geo"]
    * df["Gamma_Exp"]
    * df["Omega_Role"]
    * df["Phi_Floor"]
)
df["Benchmark_INR_Salary"] = raw.round(-3).astype(int)
```

In linear-algebra terms, if \(\mathbf{p}, \boldsymbol{\delta}, \boldsymbol{\gamma}, \boldsymbol{\omega}, \boldsymbol{\phi} \in \mathbb{R}^{N}\), then:

\[
\mathbf{b}
=
R_B
\cdot
\big(
\mathbf{p}
\odot
\boldsymbol{\delta}
\odot
\boldsymbol{\gamma}
\odot
\boldsymbol{\omega}
\odot
\boldsymbol{\phi}
\big)
\]

where \(\odot\) denotes Hadamard (element-wise) product. Complexity is \(O(N)\) with constant factors dominated by contiguous float arrays — orders of magnitude cheaper than an interpreted Python loop over 66k rows with six branches each.

#### Metro expansion as scalar broadcast

```python
base = df["Benchmark_INR_Salary"].astype(float)
df[col] = (base * mult).round(0).astype(int)
```

Each metro is \(O(N)\) multiply-broadcast; five metros remain cheap relative to I/O.

### 2.5 Worked Numeric Proof (Filing from Source)

| Input | Value |
|-------|-------|
| Role | AI Research Scientist |
| City | Bellevue |
| Experience / Career | Other / Mid_Or_Mixed |
| \(P^{\text{USD}}\) | 184,287 |

| Factor | Derivation | Value |
|--------|------------|-------|
| \(R_B\) | constant | 40 |
| \(I^{\text{US}}\) | Bellevue map | 1.10 |
| \(I^{\text{IND}}\) | no target city → default | 1.00 |
| \(\Delta^{\text{Geo}}\) | \(1.00 / 1.10\) | 0.909090… |
| \(\Gamma^{\text{Exp}}\) | MID_OR_MIXED → \(Y=8\) → \(1+0.035\cdot8\) | 1.280 |
| \(\Omega^{\text{Role}}\) | AI RESEARCH SCIENTIST | 1.15 |
| \(\Phi^{\text{Floor}}\) | \(184{,}287 > 140{,}000\) | 1.00 |

\[
\begin{align*}
B
&= 184287 \times 40 \times \frac{1}{1.10} \times 1.280 \times 1.15 \times 1.00 \\
&\approx 9{,}864{,}380 \\
\texttt{Benchmark\_INR\_Salary}
&= 9{,}864{,}000 \quad\text{(Bengaluru)} \\
\texttt{Benchmark\_INR\_Mumbai}
&= 9{,}864{,}000 \times 1.05 = 10{,}357{,}200
\end{align*}
\]

Contrast: source FX field ≈ ₹17,586,508 — same USD wage, economically different India meaning.

---

## 3. Weight Matrix Metadata & Justifications

### 3.1 \(R_B = 40\) — Base Parity Anchor

| Property | Value |
|----------|-------|
| Symbol | \(R_B\) |
| Code constant | `R_B: float = 40.0` |
| Mutability | Immutable in production scripts |
| Applied as | Global scalar multiplier on every filing |

**Economic rationale.** Spot USD/INR (≈90–95 in recent windows) preserves *currency translation*, not *labor purchasing power*. World Bank / OECD PPP series historically imply that one dollar of US wage-equivalent consumption requires materially fewer rupees than the market FX rate suggests — often on the order of roughly half FX, depending on basket and year. Setting \(R_B = 40\) (≈ FX × 0.42) intentionally anchors the pre-adjustment product near India tech market cash scales **before** geo, experience, scarcity, and floor dials refine the estimate. Using raw FX would systematically overstate India offers by nearly 2× and break compensation-committee usability.

**Talent-mobility reading.** Global capability centers and India product firms do not pay “US salary × FX.” They pay local scarcity-adjusted cash. \(R_B\) encodes that institutional reality as a single auditable constant rather than a hidden FX crawl.

---

### 3.2 \(I^{\text{US}}\) — United States City Cost / Tech-Premium Index

| Normalized city tokens | \(I^{\text{US}}\) | Code key(s) | Market rationale |
|------------------------|-------------------|-------------|------------------|
| SAN FRANCISCO, SF, SUNNYVALE, MENLO PARK, PALO ALTO, SILICON VALLEY | **1.20** | Bay Area cluster | Highest US AI/tech wage gravity; COLA + equity culture inflate LCA bases |
| NEW YORK, NYC, NEWYORKX | **1.15** | NYC cluster | Finance-tech competition + extreme housing COLA |
| BELLEVUE, SEATTLE | **1.10** | PNW cluster | Hyperscaler / cloud density with high but sub-Bay cash |
| AUSTIN, BOSTON, CAMBRIDGE, LOS ANGELES, IRVINE | **1.00** | Major-city baseline | Large tech markets without Bay/NYC extreme premium |
| Any other / missing | **0.85** | `I_US_FALLBACK` | Secondary / tertiary US locations; lower COLA and weaker AI wage competition |

**Cleaner label map (`US_CITY_TIER`):**

| \(I^{\text{US}}\) | `US_City_Tier` |
|-------------------|----------------|
| 1.20 | Tier1_BayArea |
| 1.15 | Tier1_NYC |
| 1.10 | Tier2_SeattleBellevue |
| 1.00 | Tier3_MajorCity |
| 0.85 | Tier4_OtherUS |

**Why \(\Delta^{\text{Geo}} = I^{\text{IND}} / I^{\text{US}}\) compresses high-US cities.** A Bellevue \(I^{\text{US}}=1.10\) against Bengaluru \(I^{\text{IND}}=1.00\) yields \(\Delta \approx 0.91\). That is deliberate: US hub wages already embed local COLA; mapping them 1:1 into India would import American coastal scarcity into Indian GCC pay structures. Lower US cities (\(I^{\text{US}}=0.85\)) produce \(\Delta \approx 1.176\), relatively lifting the India analogue because the US base was less hub-inflated.

---

### 3.3 \(I^{\text{IND}}\) — India Hub Index (Engine-Ready; Currently Defaulted)

| Normalized India tokens | \(I^{\text{IND}}\) | Interpretation vs Bengaluru = 1.00 |
|-------------------------|--------------------|------------------------------------|
| BENGALURU, BANGALORE | **1.00** | Reference India AI/tech hub |
| MUMBAI | **1.10** | Highest metro premium (finance + real estate COLA) |
| DELHI, NCR, GURGAON, NOIDA | **0.92** | Strong consumer-tech / captive market; slight discount to Bengaluru product premium |
| HYDERABAD, HYDRABAD | **0.88** | Large GCC / product ecosystem with structural discount |
| PUNE, CHENNAI | **0.82** | Engineering depth with lower cash clearing vs Bengaluru |

| Runtime behavior today | Value |
|------------------------|-------|
| `Target_India_City` present in source? | **No** |
| Applied \(I^{\text{IND}}\) for all rows | **1.00** (`I_IND_DEFAULT`) |
| Practical effect | All master-formula results are Bengaluru-baseline; metro diversity via \(\mu_m\) only |

**PPP / COLA nuance.** India intra-metro PPP gaps are smaller than US coastal gaps, but *cash compensation* still clears differently across hubs because of product-company density (Bengaluru), BFSI competition (Mumbai), and GCC arbitrage (Hyderabad / Chennai / Pune). The dual system (\(I^{\text{IND}}\) for true city-pair targeting + \(\mu_m\) for hub expansion) anticipates future source enrichment without rewriting the master formula.

---

### 3.4 Metro Multipliers \(\mu_m\) (Post-Hoc Hub Expansion)

| Metro | \(\mu_m\) | Filing column | Summary columns | Economic justification |
|-------|-----------|---------------|-----------------|------------------------|
| Bengaluru (baseline) | **1.00** | `Benchmark_INR_Salary` | `Benchmark_INR_{P25,Median,P75,Mean}` | India AI product / startup / MNC R&D clearing price |
| Mumbai | **1.05** | `Benchmark_INR_Mumbai` | `Benchmark_Mumbai_*` | Housing + BFSI talent competition → ~5% cash premium |
| Delhi_NCR | **0.95** | `Benchmark_INR_Delhi_NCR` | `Benchmark_Delhi_NCR_*` | Large consumer-internet market; ~5% discount to Bengaluru product premium |
| Hyderabad | **0.90** | `Benchmark_INR_Hyderabad` | `Benchmark_Hyderabad_*` | Deep GCC bench; employers sustain ~10% structural discount |
| Pune | **0.88** | `Benchmark_INR_Pune` | `Benchmark_Pune_*` | Strong product engineering; sits just under Hyderabad |
| Chennai | **0.85** | `Benchmark_INR_Chennai` | `Benchmark_Chennai_*` | Enterprise / automotive systems mix; ~15% discount |

These multipliers encode **observed India hub wage geography**, not PPP consumption baskets. A practitioner reading Mumbai = 1.05 should interpret: “same calibrated skill/experience package clears ~5% higher cash in Mumbai than in Bengaluru under this model.”

---

### 3.5 Experience → YoE → \(\Gamma^{\text{Exp}}\) Mapping

| Match tokens (highest tier first) | YoE proxy \(Y\) | \(\Gamma = 1 + 0.035Y\) | Cleaner `Experience_Band` |
|-----------------------------------|-----------------|-------------------------|---------------------------|
| EXECUTIVE, LEAD_MANAGER, DIRECTOR | 18 | **1.630** | Executive (15+ Years) |
| LEVEL_IV, STAFF, PRINCIPAL | 13 | **1.455** | Lead / Staff (10-14 Years) |
| LEVEL_III, SENIOR, MID_OR_MIXED | 8 | **1.280** | Senior (6-9 Years) |
| LEVEL_II, ASSOCIATE | 4 | **1.140** | Mid (3-5 Years) |
| ENTRY, LEVEL_I (negative lookahead vs II/III/IV), FRESHER | 0 | **1.000** | Entry (0-2 Years) |
| Empty / OTHER-only / unmapped | default | **1.280** | Senior (6-9 Years) |

**Ordering rationale (collision control).**

1. Senior labels are checked first so `LEVEL_IV + Mid_Or_Mixed` resolves to \(Y=13\), not 8.  
2. `LEVEL_II` precedes `LEVEL_I` so substring `LEVEL_I` cannot falsely match inside `LEVEL_II`.  
3. Regex `LEVEL_I(?![IV])` blocks Roman-suffix bleed.  
4. Default \(\Gamma=1.280\) biases unknown LCA experience text toward the senior mode of the dataset rather than underpaying via entry defaults — conservative for India offer modeling when US filings omit clean ladders.

**Elasticity coefficient 0.035.** Each proxy year adds 3.5% multiplicative lift. Over 0→18 YoE this yields a 63% span \((1.630/1.000)-1\), consistent with India tech ladders where senior IC / staff premiums are large but not US Bay Area extreme, and where experience is a primary sorting variable under constrained equity culture.

---

### 3.6 \(\Omega^{\text{Role}}\) — Role Scarcity Increments

| Priority | Role_Name containment | \(\Omega\) | Cleaner scarcity band | Market justification |
|----------|----------------------|------------|-----------------------|----------------------|
| 1 | GENERATIVE AI, LLM ARCHITECT, DEEP LEARNING | **1.25** | GenAI Premium | Newest skill scarcity; frontier model / LLM platform demand |
| 2 | MACHINE LEARNING, MLOPS | **1.20** | ML Premium | Production ML platform & reliability talent shortage |
| 3 | AI RESEARCH SCIENTIST, APPLIED SCIENTIST, RESEARCH ENGINEER, COMPUTER VISION, NLP | **1.15** | Specialized AI | Research / specialized inference talent; thinner India supply |
| 4 | DATA SCIENTIST | **1.05** | Standard | Broad demand; moderate premium over pure engineering data roles |
| 5 | DATA ENGINEER, ANALYTICS ENGINEER | **1.00** | Baseline | Largest liquid India talent pool; reference scarcity = 1 |
| default | All other titles | **1.05** | Standard | Mild premium so unmatched AI/tech titles do not fall below DS |

**Scarcity band bin edges in cleaner (`pd.cut`, `right=True`):**

| \(\Omega\) interval | `Role_Scarcity_Band` |
|---------------------|----------------------|
| \((-\\infty, 1.00]\) | Baseline |
| \((1.00, 1.05]\) | Standard |
| \((1.05, 1.15]\) | Specialized AI |
| \((1.15, 1.20]\) | ML Premium |
| \((1.20, \\infty)\) | GenAI Premium |

**Mobility principle.** Cross-border AI talent is not homogeneous. GenAI / LLM architects clear global premiums because the skill half-life is short and India supply pipelines lag US / EU research labs. Data engineering, by contrast, is a deep domestic market — hence \(\Omega=1.00\) as the scarcity floor.

---

### 3.7 \(\Phi^{\text{Floor}}\) — Pay-Band Floor Thresholds

| US annual base \(P^{\text{USD}}\) | \(\Phi\) | Interpretation |
|-----------------------------------|----------|----------------|
| \(< 90{,}000\) | **0.45** | Strong junior / lower-band compression |
| \(90{,}000\) – \(140{,}000\) | **0.75** | Mid-band partial compression |
| \(> 140{,}000\) | **1.00** | Expert / premium band preserved |

**Why compression exists.** US LCA bases for early-career AI titles in secondary cities can still look high in absolute USD. Linear mapping (even after \(R_B\) and \(\Delta\)) would manufacture India “junior” packages that exceed local market clearing for 0–2 YoE talent. \(\Phi\) is a **non-linear dampener** that acknowledges:

- India junior cash bands are compressed relative to US entry offers (equity / brand substitute for cash in the US).  
- Above ≈$140k USD offered base, the filing is already in a senior scarcity regime; further compression would understate India staff / lead cash.  
- The 90k / 140k thresholds align with common US tech leveling breaks (roughly early-career vs mid vs senior IC cash).

---

### 3.8 Missing-Pay Imputation (Pre-Formula)

| Rule | Implementation |
|------|----------------|
| Coerce | `pd.to_numeric(Annual_Pay_USD, errors="coerce")` |
| Impute | Column mean (`skipna=True`) |
| Catastrophic fallback | If mean itself is NaN → **120,000.0** USD (industry mid-band) |

Imputation is a **pipeline continuity** control, not a statistical claim that missing wages equal the mean. In the current MAX FreeSources extract, pay coverage is dense; the rule primarily protects against schema drift and partial extracts.

---

## 4. Cleaning & Quality Engineering Reconciliation

All steps below are executed by `clean_india_benchmark.py` on the calibrated filing CSV.

### 4.1 Ordered Manipulation Ledger

| Step | Operation | Engineering detail | Effect |
|------|-----------|--------------------|--------|
| C1 | **String hygiene** | Strip whitespace on identity / provenance string columns; empty / `"nan"` / `"None"` → pandas `NA` | Removes parse artifacts without inventing values |
| C2 | **City display normalization** | `City` → Title Case; `State` → UPPER | Stable human-readable geography |
| C3 | **Numeric coercion** | Money columns + calibration columns → `to_numeric(..., errors="coerce")` | Guarantees arithmetic types before flags / rounding |
| C4 | **Feature pruning (null columns)** | Drop `Total_Comp_USD`, `Bonus_USD`, `Equity_USD` when present | These fields are **100% null** in this extract; retaining them invites false “missing equity” analysis |
| C5 | **Exact deduplication** | `drop_duplicates()` with no subset | Purges byte-identical rows |
| C6 | **Worksite-key deduplication** | `drop_duplicates(subset=[Case_Number, City, State, Annual_Pay_USD, Role_Name], keep="first")` | Collapses repeated LCA worksite facts; **retains multi-city worksites as distinct rows** |
| C7 | **Grain / target stamps** | `Grain="Filing"`, `Target_Country="India"`, `Target_City_Hub="Bengaluru"`, `R_B=40.0` | Explicit semantic headers for downstream consumers |
| C8 | **Role family mapping** | Ordered regex ladder → 10 families + `Other AI/Tech` | Analytical rollup without losing `Role_Name` |
| C9 | **Experience band + YoE proxy** | Same token ladder as engine; human-readable bands + integer YoE | Aligns summary grain keys with \(\Gamma\) logic |
| C10 | **US city tier labeling** | Map `I_US` → Tier1–Tier4 labels | Compensation reporting without exposing raw indices alone |
| C11 | **Scarcity band labeling** | `pd.cut` on `Omega_Role` | Discrete scarcity taxonomy for dashboards |
| C12 | **Place-name glitch purge** | Strip backticks / acute accents; collapse multi-spaces on `City` / `Location` | Fixes LCA text noise (e.g., trailing `` ` ``) |
| C13 | **Quality flag assignment** | See §4.3 | Separates analytic-ready rows from extreme pay anomalies |
| C14 | **Rounding protocol** | Money 2 dp; `I_US`/`I_IND` 2 dp; `Delta_Geo` 4 dp; `Gamma_Exp` 3 dp; `Omega`/`Phi` 2 dp; INR ints | Publication-stable numerics |
| C15 | **Metro refresh** | Recompute all `Benchmark_INR_<Metro>` from Bengaluru × \(\mu_m\) | Eliminates drift if engine/cleaner multipliers ever diverge temporarily |
| C16 | **FX rename** | `Annual_Pay_INR` → `Annual_Pay_INR_FX` | Hard semantic firewall vs calibrated benchmark |
| C17 | **Record_ID** | Contiguous integers after final sort | Stable citation keys within a build |
| C18 | **Sectional column order** | Identity → Target → Role → US geo → Experience → US pay → Audit factors → India INR → Quality → Provenance | Engineer-readable schema |
| C19 | **Deterministic sort** | `Role_Family`, `Role_Name`, `Experience_Band`, `City`, `Benchmark_INR_Salary` desc; `mergesort` | Stable, auditable row order |
| C20 | **Summary aggregation** | OK-only groupby Role × Experience (+ family/scarcity); P25/Median/P75/Mean; metro scale | Grain 2 build |

### 4.2 Duplicate Resolution Strategy (1,960 Rows Purged)

**Observed:** \(66{,}799 \rightarrow 64{,}839\) ⇒ **1,960** rows removed.

**Two-pass strategy:**

1. **Exact row equality** — removes perfect clones from upstream union / export duplication.  
2. **Business key uniqueness** — `(Case_Number, City, State, Annual_Pay_USD, Role_Name)` with `keep="first"`.

**What is intentionally kept:** Distinct cities on the same LCA case (multi-worksite filings) remain separate rows because India metro mapping and US city tier depend on worksite city. Collapsing those would destroy geographic signal inside \(\Delta^{\text{Geo}}\).

**What is intentionally removed:** Repeated identical wage facts for the same case/city/role that would otherwise overweight employers in Role × Experience percentiles.

### 4.3 Missing Value & Invalid Pay Routines

| Condition | Action | Flag |
|-----------|--------|------|
| Blank strings after strip | → `NA` | (none until pay check) |
| Non-numeric money / factor text | → `NaN` via coerce | May become `INVALID_PAY` if pay NaN |
| `Annual_Pay_USD` NaN or \(\le 0\) after clean | Flagged | **`INVALID_PAY`** |
| `Annual_Pay_USD` \(> 500{,}000\) | Kept in filing grain; excluded from summary | **`OUTLIER_PAY`** |
| Else | Analytic-ready | **`OK`** |

**Observed quality distribution (production filing grain):**

| `Data_Quality_Flag` | Count |
|---------------------|------:|
| OK | 64,785 |
| OUTLIER_PAY | 54 |
| INVALID_PAY | 0 |

**OUTLIER_PAY boundary criteria (explicit):**

\[
\texttt{Data\_Quality\_Flag}
=
\begin{cases}
\texttt{OUTLIER\_PAY} & \texttt{Annual\_Pay\_USD} > 500{,}000 \\
\texttt{INVALID\_PAY} & \texttt{Annual\_Pay\_USD} \in \{\text{NaN}\} \lor \texttt{Annual\_Pay\_USD} \le 0 \\
\texttt{OK} & \text{otherwise}
\end{cases}
\]

Constant: `PAY_OUTLIER_USD = 500_000.0`.

**Observed outlier envelope:** USD **504,000** … **8,800,356** (54 filings). These rows remain in Grain 1 for forensic audit but **do not** enter Grain 2 percentile math.

### 4.4 Text Normalization Protocols

| Field class | Protocol |
|-------------|----------|
| Engine matching keys (`City`, experience, role) | `strip` + `UPPER` before regex / map |
| Filing display `City` | Title Case after clean |
| Filing display `State` | UPPER |
| Role / employer / notes | Strip; blanks → `NA` |
| Location glitches | Remove `` ` `` and U+00B4; squeeze whitespace |

### 4.5 Feature Pruning

| Dropped column | Reason |
|----------------|--------|
| `Total_Comp_USD` | Entirely null in MAX FreeSources AI extract |
| `Bonus_USD` | Entirely null |
| `Equity_USD` | Entirely null |

LCA base-wage disclosure is **not** total compensation. Notes fields already warn: “Not total compensation.” Pruning empty TC columns prevents dashboards from plotting zero-filled equity as a feature.

### 4.6 Role Family Taxonomy (Cleaner)

Applied in priority order (first match wins):

| Pattern | `Role_Family` |
|---------|---------------|
| GENERATIVE AI \| LLM ARCHITECT | Generative AI |
| DEEP LEARNING | Deep Learning |
| MACHINE LEARNING \| MLOPS | Machine Learning |
| COMPUTER VISION | Computer Vision |
| `\bNLP\b` | NLP |
| AI RESEARCH SCIENTIST \| APPLIED SCIENTIST \| RESEARCH ENGINEER | AI Research |
| AI ENGINEER \| AI PLATFORM \| AI PRODUCT | AI Engineering |
| DATA SCIENTIST | Data Science |
| DATA ENGINEER \| ANALYTICS ENGINEER | Data Engineering |
| (else) | Other AI/Tech |

---

## 5. Multi-Grain Schema Specification

### 5.1 Grain 1 — Filing Level (`india_tech_roles_benchmark.csv`)

| Property | Specification |
|----------|---------------|
| **Grain name** | `Filing` |
| **Atomic unit** | One US LCA worksite wage fact, calibrated to India |
| **Primary key** | `Record_ID` (build-local surrogates 1…N after sort) |
| **Natural key** | (`Case_Number`, `City`, `State`, `Role_Name`, `Annual_Pay_USD`) |
| **Target hub for master INR** | `Target_City_Hub = Bengaluru` |
| **Row count** | 64,839 |
| **Column count** | 48 |

#### 5.1.1 Sectional Schema

**A. Identity**

| Column | Type | Definition |
|--------|------|------------|
| `Record_ID` | Int | Contiguous surrogate after final sort |
| `Grain` | String | Always `Filing` |
| `Case_Number` | String | US DOL LCA case identifier |

**B. India target context**

| Column | Type | Definition |
|--------|------|------------|
| `Target_Country` | String | Always `India` |
| `Target_City_Hub` | String | Always `Bengaluru` for the master benchmark column |

**C. Role structure**

| Column | Type | Definition |
|--------|------|------------|
| `Role_Name` | String | Source role title |
| `Role_Family` | String | Taxonomy in §4.6 |
| `Role_Scarcity_Band` | String | Baseline / Standard / Specialized AI / ML Premium / GenAI Premium |

**D. US location**

| Column | Type | Definition |
|--------|------|------------|
| `Country` | String | Source country (United States) |
| `State` | String | US state (UPPER) |
| `City` | String | US worksite city (Title Case) |
| `Location` | String | Combined location text |
| `US_City_Tier` | String | Tier label from `I_US` |

**E. Experience structure**

| Column | Type | Definition |
|--------|------|------------|
| `Experience_Level` | String | Source experience text |
| `Career_Level` | String | Source career text |
| `Experience_Band` | String | Entry / Mid / Senior / Lead-Staff / Executive bands |
| `YoE_Proxy` | Int | 0 / 4 / 8 / 13 / 18 |

**F. US compensation**

| Column | Type | Definition |
|--------|------|------------|
| `Pay_Type` | String | Typically `Base` |
| `Annual_Pay_USD` | Float | Offered annual base USD |
| `Annual_Pay_INR_FX` | Float | FX-style INR (**not** market benchmark) |
| `Base_Min_USD` / `Base_Median_USD` / `Base_Max_USD` | Float | Source wage range facts |
| `Currency_Original` | String | `USD` |

**G. Calibration audit trail**

| Column | Type | Definition |
|--------|------|------------|
| `R_B` | Float | 40.0 |
| `I_US` | Float | US city index |
| `I_IND` | Float | India city index (1.0 today) |
| `Delta_Geo` | Float | \(I_IND / I_US\) |
| `Gamma_Exp` | Float | Experience elasticity |
| `Omega_Role` | Float | Role scarcity |
| `Phi_Floor` | Float | Pay-band floor |

**H. India results**

| Column | Type | Definition |
|--------|------|------------|
| `Benchmark_INR_Salary` | Int | Bengaluru calibrated INR (nearest ₹1,000 from engine; integer in clean) |
| `Benchmark_INR_Mumbai` | Int | × 1.05 |
| `Benchmark_INR_Delhi_NCR` | Int | × 0.95 |
| `Benchmark_INR_Hyderabad` | Int | × 0.90 |
| `Benchmark_INR_Chennai` | Int | × 0.85 |
| `Benchmark_INR_Pune` | Int | × 0.88 |

**I. Quality**

| Column | Type | Definition |
|--------|------|------------|
| `Data_Quality_Flag` | String | `OK` / `OUTLIER_PAY` / `INVALID_PAY` |

**J. Provenance**

| Column | Type | Definition |
|--------|------|------------|
| `Employer_Name` | String | LCA employer |
| `SOC_Code` | String | Occupational code |
| `Visa_Class` | String | e.g. H-1B |
| `Fiscal_Year` | Int/String | Filing FY |
| `Decision_Date` | Date/String | Decision date |
| `Source_Name` | String | US DOL OFLC LCA Disclosure |
| `Source_URL` | String | DOL performance URL |
| `Collection_Date` | Date/String | Extract date |
| `Sample_Size` | Int | Usually 1 for single filing facts |
| `Notes` | String | Caveats (base wage ≠ TC) |

#### 5.1.2 INR Field Semantics (Do Not Confuse)

| Column | Meaning | Use in India offer modeling? |
|--------|---------|------------------------------|
| `Annual_Pay_INR_FX` | USD × FX-style factor | **No** — cash translation only |
| `Benchmark_INR_Salary` | Calibrated Bengaluru market analogue | **Yes — primary** |
| `Benchmark_INR_<Metro>` | Same package scaled to hub | **Yes — hub-specific** |

---

### 5.2 Grain 2 — Aggregated Role × Experience (`india_tech_roles_benchmark_summary.csv`)

| Property | Specification |
|----------|---------------|
| **Grain name** | `Role_x_Experience` |
| **Atomic unit** | One `Role_Name` × `Experience_Band` market band (with family & scarcity attributes) |
| **Filter** | `Data_Quality_Flag == "OK"` only |
| **Target hub label** | `Target_City_Hub = Multi-Metro Calibrated` |
| **Currency** | `INR` |
| **Row count** | 236 |
| **Distinct roles** | 189 |
| **Role families** | 10 |
| **Experience bands present** | Entry (0-2), Mid (3-5), Senior (6-9), Lead/Staff (10-14), Executive (15+) |
| **Σ Sample_Size** | 64,785 (matches OK filing count) |

#### 5.2.1 Aggregation Key

```text
GROUP BY
  Role_Family,
  Role_Name,
  Experience_Band,
  Role_Scarcity_Band
```

#### 5.2.2 Distribution Measures (Bengaluru Baseline)

| Column | Definition |
|--------|------------|
| `Sample_Size` | Count of OK filings in the band |
| `Benchmark_INR_P25` | 25th percentile of `Benchmark_INR_Salary`; rounded to nearest ₹1,000 |
| `Benchmark_INR_Median` | 50th percentile; rounded to nearest ₹1,000 |
| `Benchmark_INR_P75` | 75th percentile; rounded to nearest ₹1,000 |
| `Benchmark_INR_Mean` | Arithmetic mean; rounded to nearest ₹1,000 |

#### 5.2.3 Multi-Metro Extension

For each metro \(m \in \{\texttt{Mumbai}, \texttt{Delhi\_NCR}, \texttt{Hyderabad}, \texttt{Chennai}, \texttt{Pune}\}\) and each band \(q \in \{\texttt{P25}, \texttt{Median}, \texttt{P75}, \texttt{Mean}\}\):

| Pattern | Example |
|---------|---------|
| `Benchmark_<Metro>_<Band>` | `Benchmark_Mumbai_Median`, `Benchmark_Hyderabad_P75`, `Benchmark_Pune_Mean` |

\[
\texttt{Benchmark\_}<m>\_{q}
=
\operatorname{round}\big(
\mu_m \cdot \texttt{Benchmark\_INR\_}<q>
\big)
\]

This yields **20 metro distribution columns** (5 metros × 4 statistics) plus 4 Bengaluru columns.

#### 5.2.4 Auxiliary Audit Columns on Summary

| Column | Definition |
|--------|------------|
| `US_Pay_USD_Median` | Median source USD pay in the band |
| `Gamma_Exp_Mode` | Modal \(\Gamma\) within the band |
| `Omega_Role` | Median scarcity index within the band |
| `Currency` | `INR` |

#### 5.2.5 Example Band (Production)

| Field | Value |
|-------|-------|
| Role | AI Engineer |
| Experience_Band | Entry (0-2 Years) |
| Sample_Size | 5 |
| Benchmark_INR_Median (Bengaluru) | ₹3,335,000 |
| Benchmark_Mumbai_Median | ₹3,501,750 |
| Benchmark_Delhi_NCR_Median | ₹3,168,250 |
| Benchmark_Hyderabad_Median | ₹3,001,500 |
| Benchmark_Pune_Median | ₹2,934,800 |
| Benchmark_Chennai_Median | ₹2,834,750 |

---

### 5.3 Source Schema Reference (Stage 0)

`AI_Talent_Salary_Benchmark_MAX_FreeSources.csv` — 29 columns:

`Grain`, `Role_Name`, `Country`, `Location`, `City`, `State`, `Experience_Level`, `Career_Level`, `Pay_Type`, `Annual_Pay_USD`, `Annual_Pay_INR`, `Base_Min_USD`, `Base_Median_USD`, `Base_Max_USD`, `Total_Comp_USD`, `Bonus_USD`, `Equity_USD`, `Currency_Original`, `Employer_Name`, `Case_Number`, `SOC_Code`, `Visa_Class`, `Fiscal_Year`, `Decision_Date`, `Source_Name`, `Source_URL`, `Collection_Date`, `Sample_Size`, `Notes`

---

## 6. Operational Runbook

### 6.1 Execution Order

```bash
python ai_salary/india_tech_benchmark_engine.py
python ai_salary/clean_india_benchmark.py
```

Dependencies: `pandas`, `numpy`.

### 6.2 Path Contract

| Role | Path |
|------|------|
| Input | `ai_salary/AI_Talent_Salary_Benchmark_MAX_FreeSources.csv` |
| Engine output / cleaner input / filing grain | `ai_salary/india_tech_roles_benchmark.csv` |
| Summary grain | `ai_salary/india_tech_roles_benchmark_summary.csv` |

The cleaner **overwrites** the filing grain in place after structuring. Always re-run the engine before the cleaner if source inputs change.

### 6.3 Invariants Peer Engineers Must Assert

1. `R_B` in output equals **40.0** for every filing row.  
2. `Benchmark_INR_<Metro>` equals `round(Benchmark_INR_Salary * μ_m)` within integer tolerance.  
3. Summary `Sample_Size` sum equals count of filing rows with `Data_Quality_Flag == "OK"`.  
4. No summary row may be built from `OUTLIER_PAY` filings.  
5. `Annual_Pay_INR_FX` must never be labeled or joined as India market pay.  
6. `Target_City_Hub` is `Bengaluru` on filings and `Multi-Metro Calibrated` on summary rows.

---

## 7. Audit Appendix — Empirical Population Snapshots

*Snapshot of the cleaned production artifacts reviewed for this handbook.*

### 7.1 Filing Grain Distributions

**Role family**

| Role_Family | Rows |
|-------------|------:|
| Data Science | 37,932 |
| Data Engineering | 12,881 |
| AI Research | 8,431 |
| Machine Learning | 4,451 |
| AI Engineering | 402 |
| Other AI/Tech | 316 |
| Generative AI | 194 |
| Computer Vision | 157 |
| Deep Learning | 38 |
| NLP | 37 |

**Experience band**

| Experience_Band | Rows |
|-----------------|------:|
| Senior (6-9 Years) | 45,671 |
| Lead / Staff (10-14 Years) | 10,638 |
| Executive (15+ Years) | 7,245 |
| Entry (0-2 Years) | 714 |
| Mid (3-5 Years) | 571 |

**US city tier**

| US_City_Tier | Rows |
|--------------|------:|
| Tier4_OtherUS | 47,686 |
| Tier1_BayArea | 4,958 |
| Tier2_SeattleBellevue | 4,425 |
| Tier1_NYC | 4,243 |
| Tier3_MajorCity | 3,527 |

**Scarcity band**

| Role_Scarcity_Band | Rows |
|--------------------|------:|
| Standard | 38,650 |
| Baseline | 12,881 |
| Specialized AI | 8,625 |
| ML Premium | 4,451 |
| GenAI Premium | 232 |

### 7.2 OK Population Pay Envelope

| Metric | Annual_Pay_USD | Benchmark_INR_Salary (Bengaluru) |
|--------|----------------|----------------------------------|
| Minimum | 42,000 | ₹900,000 |
| Median | 139,405 | ₹7,127,000 |
| Maximum | 500,000 | ₹45,821,000 |

### 7.3 Distinct Factor Support Observed in Filing Grain

| Factor | Observed discrete values |
|--------|--------------------------|
| `I_US` | 0.85, 1.0, 1.1, 1.15, 1.2 |
| `Gamma_Exp` | 1.0, 1.14, 1.28, 1.455, 1.63 |
| `Omega_Role` | 1.0, 1.05, 1.15, 1.2, 1.25 |
| `Phi_Floor` | 0.45, 0.75, 1.0 |

---

## Document Control

| Item | Detail |
|------|--------|
| Canonical formula | \(B^{\text{INR}} = P^{\text{USD}} \cdot R_B \cdot \Delta^{\text{Geo}} \cdot \Gamma^{\text{Exp}} \cdot \Omega^{\text{Role}} \cdot \Phi^{\text{Floor}}\) |
| Code authority | `india_tech_benchmark_engine.py`, `clean_india_benchmark.py` |
| Companion narrative README | `ai_salary/README.md` |
| Related but distinct deliverable | `output/country/India_AI_Salary_Benchmark.csv` (different schema; not this formula’s multi-metro filing grain) |

This handbook is the peer-engineer specification for lineage, mathematics, coefficient justification, quality reconciliation, and dual-grain schemas of the India Tech Salary Benchmark Engine.
