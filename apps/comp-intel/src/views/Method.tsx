import { Card, SectionTitle } from "../components/ui";
import {
  DIRECTIONAL_N,
  GEO_THRESHOLDS,
  OBSERVATION_DISCLAIMER,
  PRODUCT_NAME,
  STRATEGIC_TARGET_OPTIONS,
} from "../lib/constants";
import { HUB_OPTIONS } from "../lib/metros";

export function MethodView() {
  return (
    <article className="mx-auto max-w-3xl space-y-8">
      <header>
        <SectionTitle
          title="Method"
          subtitle={`${PRODUCT_NAME} compares incumbent INR pay to India multi-metro Role × Experience market bands. Strategic targets (P25 / P50 / P75) set the benchmark; hub context scales geography. Demand, scarcity, and premium indices are insight-only — never salary multipliers.`}
        />
      </header>

      <Card className="p-5 text-sm leading-relaxed text-ink/85">
        <p>{OBSERVATION_DISCLAIMER}</p>
      </Card>

      <section className="space-y-3">
        <h2 className="font-display text-2xl">What we measure</h2>
        <p className="text-sm leading-7 text-ink/90">
          For each incumbent we match a <strong>Role Family × Experience</strong> band (optional role
          title), then read the selected hub’s percentile columns. Current salary is always annual INR
          and is never re-indexed when you change hub.
        </p>
        <ol className="list-decimal space-y-2 pl-5 text-sm leading-7 text-ink/90">
          <li>Match Role Family × Experience (and title when present) to summary market bands.</li>
          <li>
            Read hub-native percentiles: <code>metros.&lt;hub&gt;.p25 / p50 / p75</code> (Bengaluru =
            baseline; other hubs are pre-scaled INR bands).
          </li>
          <li>
            Set <strong>Strategic Compensation Target</strong> to P25, P50 (median), or P75 — that
            percentile becomes the active market target.
          </li>
          <li>
            <strong>Pay gap %</strong> = (Incumbent − Target) / Target × 100. Cash to close = max(0,
            Target − Incumbent).
          </li>
        </ol>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl">Strategic compensation target</h2>
        <p className="text-sm leading-7 text-ink/90">
          Replaces older Talent / FX / PPP mode switches. One market methodology; three policy
          stances:
        </p>
        <ul className="space-y-2 text-sm leading-7 text-ink/90">
          {STRATEGIC_TARGET_OPTIONS.map((o) => (
            <li key={o.id} className="rounded-lg border border-ink/8 bg-paper/50 px-4 py-3">
              <strong>
                {o.shortLabel} — {o.title}
              </strong>
              <span className="text-mute"> · {o.explanation}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl">Market hubs</h2>
        <p className="text-sm leading-7 text-ink/90">
          Bengaluru is the India tech baseline (index 1.00). Other hubs use the same Role × Experience
          grain with metro cost indices applied in the ingest pipeline — Desk only selects which
          column to read.
        </p>
        <ul className="list-disc space-y-1.5 pl-5 text-sm leading-7 text-ink/90">
          {HUB_OPTIONS.map((h) => (
            <li key={h.id}>
              <strong>{h.shortLabel}</strong> · index {h.multiplier.toFixed(2)} — {h.legend}
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl">Market position</h2>
        <p className="text-sm leading-7 text-ink/90">
          Position is classified against the hub band, independent of which strategic target you
          picked for gap math:
        </p>
        <ul className="list-disc space-y-1.5 pl-5 text-sm leading-7 text-ink/90">
          <li>Below P25 — Significantly underpaid</li>
          <li>P25–P50 — Underpaid</li>
          <li>P50–P75 — Market competitive</li>
          <li>P75–P90 — Highly competitive</li>
          <li>Above P90 — Market leading</li>
        </ul>
        <p className="text-sm leading-7 text-ink/90">
          Expected external offer band uses matched <strong>P75–P90</strong> (directional), not the
          strategic target.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl">Retention & competitor signals</h2>
        <p className="text-sm leading-7 text-ink/90">
          Flight / retention risk blends pay gap vs the strategic target with scarcity, role demand,
          and competitor premium from matched filings. Competitive threat ranks employers in the
          Evidence sample whose hub-adjusted pay sits above the incumbent. These are decision aids,
          not confirmed offers or attrition predictions.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl">Insight-only indices</h2>
        <p className="text-sm leading-7 text-ink/90">
          The following never multiply salary. Band percentiles already embed role, experience, and
          hub geography.
        </p>
        <ul className="list-disc space-y-1.5 pl-5 text-sm leading-7 text-ink/90">
          <li>
            <strong>Geographic / hub premium</strong> — narrative vs Bengaluru baseline.
          </li>
          <li>
            <strong>Role compensation premium</strong> — how the role sits vs a national family
            reference.
          </li>
          <li>
            <strong>Role demand</strong> — hiring pressure signal across families.
          </li>
          <li>
            <strong>Talent scarcity</strong> — Low / Medium / High difficulty to replace.
          </li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl">Matching & confidence</h2>
        <p className="text-sm leading-7 text-ink/90">
          Geography fallback for band selection: City (n≥{GEO_THRESHOLDS.city}) → Metro (n≥
          {GEO_THRESHOLDS.metro}) → State (n≥{GEO_THRESHOLDS.state}) → National (n≥
          {GEO_THRESHOLDS.national}). Samples with n &lt; {DIRECTIONAL_N} are flagged directional.
          Thin role slices may auto-relax title or experience filters; Desk shows match notes when
          that happens.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl">Data sources</h2>
        <p className="text-sm leading-7 text-ink/90">
          Desk does not scrape live payroll. It reads India multi-metro benchmarks built from US
          certified wage filings, then calibrated to Indian hubs.
        </p>
        <ul className="list-disc space-y-2 pl-5 text-sm leading-7 text-ink/90">
          <li>
            <strong>Primary wage facts</strong> — US Department of Labor OFLC LCA disclosures
            (H-1B certified offered base wages), FY2026 Q3 extract in{" "}
            <code>AI_Talent_Salary_Benchmark_MAX_FreeSources.csv</code> with canonical{" "}
            <code>Role_Name</code> / <code>Role_Family</code> (incl. FD). Base wage only — not total
            compensation, equity, or benefits.
          </li>
          <li>
            <strong>India filing grain</strong> —{" "}
            <code>india_tech_roles_benchmark.csv</code> (output of{" "}
            <code>india_tech_benchmark_engine.py</code>): each US filing mapped to Bengaluru-baseline
            INR plus five metro columns.
          </li>
          <li>
            <strong>Market bands</strong> —{" "}
            <code>india_tech_roles_benchmark_summary.csv</code>: Role × Experience percentiles (P25 /
            median / P75 / mean) per hub. Desk gap math reads these columns.
          </li>
          <li>
            <strong>Evidence ledger</strong> — progressive top-paying sample of filings per Role ×
            Experience (ingest caps the slice). Not headcount and not confirmed India offers.
          </li>
        </ul>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl">US salary → India INR (by city)</h2>
        <p className="text-sm leading-7 text-ink/90">
          Conversion is <strong>not</strong> a simple market FX multiply (e.g. USD × 95.43). Each US
          filing’s <code>Annual_Pay_USD</code> is transformed into a Bengaluru-anchored India tech
          benchmark, then scaled to other Indian metros.
        </p>

        <Card className="border border-ink/10 bg-paper/60 p-4 text-sm leading-relaxed text-ink/90">
          <p className="font-mono text-xs md:text-sm">
            Benchmark_INR_Salary = Annual_Pay_USD × R_B × Δ_Geo × Γ_Exp × Ω_Role × Φ_Floor
          </p>
          <p className="mt-2 text-xs text-mute">
            Rounded to the nearest ₹1,000. This is the Bengaluru baseline column used by Desk when
            hub = Bengaluru.
          </p>
        </Card>

        <ul className="list-disc space-y-2 pl-5 text-sm leading-7 text-ink/90">
          <li>
            <strong>R_B = 40</strong> — immutable USD→INR purchasing-power parity anchor (not spot
            FX; not World Bank PPP factor 23). Sets the cash scale for India tech roles.
          </li>
          <li>
            <strong>Δ_Geo = I_IND / I_US</strong> — city cost pair index. US city index (
            <code>I_US</code>) and India target-city index (<code>I_IND</code>) adjust for where the
            US wage was filed vs the India hub being modeled.
          </li>
          <li>
            <strong>Γ_Exp</strong> — experience elasticity from career / LCA level (≈ 1 + 0.035 ×
            YoE proxy; default senior proxy 1.28 when unmapped).
          </li>
          <li>
            <strong>Ω_Role</strong> — role scarcity band (e.g. GenAI / LLM ≈ 1.25 · ML / MLOps ≈ 1.20
            · Applied / CV / NLP ≈ 1.15 · Data Scientist ≈ 1.05 · Data Engineer ≈ 1.00).
          </li>
          <li>
            <strong>Φ_Floor</strong> — base-floor compression on USD pay: &lt;$90k → 0.45 · $90–140k
            → 0.75 · &gt;$140k → 1.00 (avoids importing US junior floors 1:1 into India bands).
          </li>
        </ul>

        <h3 className="font-display text-xl pt-2">US city indices (I_US)</h3>
        <p className="text-sm leading-7 text-ink/90">
          Higher <code>I_US</code> means the US filing city is more expensive, which <em>lowers</em>{" "}
          Δ_Geo and therefore the India INR benchmark for the same USD wage (Bay Area wages are not
          treated as national-average USD).
        </p>
        <ul className="list-disc space-y-1.5 pl-5 text-sm leading-7 text-ink/90">
          <li>
            <strong>1.20</strong> — San Francisco / Bay Area (Sunnyvale, Menlo Park, Palo Alto, …)
          </li>
          <li>
            <strong>1.15</strong> — New York / NYC
          </li>
          <li>
            <strong>1.10</strong> — Seattle / Bellevue
          </li>
          <li>
            <strong>1.00</strong> — Austin, Boston / Cambridge, Los Angeles / Irvine
          </li>
          <li>
            <strong>0.85</strong> — all other US cities (fallback)
          </li>
        </ul>

        <h3 className="font-display text-xl pt-2">India target-city indices (I_IND)</h3>
        <p className="text-sm leading-7 text-ink/90">
          Used inside Δ_Geo when a target India city is present on the filing. Default is Bengaluru
          = 1.00.
        </p>
        <ul className="list-disc space-y-1.5 pl-5 text-sm leading-7 text-ink/90">
          <li>
            <strong>1.10</strong> — Mumbai
          </li>
          <li>
            <strong>1.00</strong> — Bengaluru / Bangalore
          </li>
          <li>
            <strong>0.92</strong> — Delhi / NCR / Gurgaon / Noida
          </li>
          <li>
            <strong>0.88</strong> — Hyderabad
          </li>
          <li>
            <strong>0.82</strong> — Pune, Chennai
          </li>
        </ul>

        <h3 className="font-display text-xl pt-2">Multi-metro expansion (Desk hubs)</h3>
        <p className="text-sm leading-7 text-ink/90">
          After the Bengaluru baseline is computed, every filing is expanded to the five other hubs
          Desk can select. This is a second, structural metro scale — separate from Δ_Geo:
        </p>
        <Card className="border border-ink/10 bg-paper/60 p-4 text-sm leading-relaxed text-ink/90">
          <p className="font-mono text-xs md:text-sm">
            Benchmark_INR_&lt;Metro&gt; = Benchmark_INR_Salary × Metro_Multiplier
          </p>
        </Card>
        <ul className="list-disc space-y-1.5 pl-5 text-sm leading-7 text-ink/90">
          {HUB_OPTIONS.map((h) => (
            <li key={h.id}>
              <strong>{h.shortLabel}</strong> · ×{h.multiplier.toFixed(2)} — {h.legend}
            </li>
          ))}
        </ul>
        <p className="text-sm leading-7 text-ink/90">
          Summary bands (P25 / P50 / P75) are percentiles of these hub INR columns by Role ×
          Experience. Changing hub on Desk only switches which pre-scaled column is read —
          incumbent pay is never FX- or metro-reindexed.
        </p>
        <p className="text-sm leading-7 text-mute">
          Note: filings also store <code>Annual_Pay_INR_FX</code> (USD × spot FX) for audit. Desk
          alignment uses the calibrated <code>Benchmark_INR_*</code> columns above, not raw FX.
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="font-display text-2xl">How to use the tabs</h2>
        <ul className="list-disc space-y-1.5 pl-5 text-sm leading-7 text-ink/90">
          <li>
            <strong>Desk</strong> — set incumbent, read alignment vs hub × target, ladder, risk, and
            competitor preview.
          </li>
          <li>
            <strong>Method</strong> — this page.
          </li>
          <li>
            <strong>Scenario</strong> — cost to reach P25 / P50 / P75 or a custom raise.
          </li>
          <li>
            <strong>Evidence</strong> — inspect matched filing rows behind the slice.
          </li>
        </ul>
      </section>
    </article>
  );
}
