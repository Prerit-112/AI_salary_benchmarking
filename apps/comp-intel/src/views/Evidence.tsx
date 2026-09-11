import { useMemo, useRef, useState } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";

import { useGapAnalysis, useApp } from "../state";
import { Card, EmptyState, SectionTitle, Stat, ThreatBadge, inputClass } from "../components/ui";
import { downloadCsv, observationsToCsv } from "../lib/export";
import { hubOption } from "../lib/metros";
import { formatCompactINR, formatINR } from "../lib/money";
import { metricValue } from "../lib/stats";
import {
  geographicPremiumInsight,
  MARKET_POSITION_LABEL,
  PAY_GAP_LABEL,
  roleCompensationPremiumInsight,
  roleDemandInsight,
} from "../lib/marketBenchmark";

export function EvidenceView() {
  const analysis = useGapAnalysis();
  const { state, dispatch } = useApp();
  const [q, setQ] = useState("");
  const [aboveOnly, setAboveOnly] = useState(false);
  const parentRef = useRef<HTMLDivElement>(null);
  const hub = hubOption(state.hub);

  const metric = "market" as const;

  const rows = useMemo(() => {
    if (!analysis) return [];
    let list = aboveOnly ? analysis.aboveYou : analysis.matched;
    const needle = q.trim().toLowerCase();
    if (needle) {
      list = list.filter(
        (o) =>
          o.sourceName.toLowerCase().includes(needle) ||
          o.roleName.toLowerCase().includes(needle) ||
          o.city.toLowerCase().includes(needle) ||
          o.metro.toLowerCase().includes(needle) ||
          o.employerGroup.toLowerCase().includes(needle) ||
          o.employerName.toLowerCase().includes(needle),
      );
    }
    return [...list].sort((a, b) => {
      const av = metricValue(a, metric, state.hub) ?? a.salaryInr;
      const bv = metricValue(b, metric, state.hub) ?? b.salaryInr;
      return bv - av;
    });
  }, [analysis, q, aboveOnly, state.hub]);

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 56,
    overscan: 12,
  });

  if (!analysis) {
    return (
      <EmptyState title="No evidence slice" body="Match a market on Desk to inspect India multi-metro filing samples." />
    );
  }

  const selected = rows.find((r) => r.id === state.selectedId) ?? null;
  const selectedPay = selected ? metricValue(selected, metric, state.hub) : null;
  const selectedDelta =
    selectedPay != null ? selectedPay - analysis.yourPay : null;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <SectionTitle
          title="Evidence"
          subtitle={`${hub.shortLabel} filing samples behind the Desk slice · target ${analysis.benchmarkLabel}.`}
        />
        <button
          type="button"
          className="btn-secondary"
          onClick={() =>
            downloadCsv(
              `payrisk-evidence-${Date.now()}.csv`,
              observationsToCsv(aboveOnly ? analysis.aboveYou : analysis.matched),
            )
          }
        >
          Export slice CSV
        </button>
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Card className="p-4">
          <Stat
            label={`${hub.shortLabel} P50`}
            value={formatCompactINR(analysis.marketBenchmarkValue ?? analysis.marketMedian)}
          />
        </Card>
        <Card className="p-4">
          <Stat
            label={analysis.benchmarkLabel}
            value={formatCompactINR(analysis.marketValue)}
            hint="Active strategic target"
          />
        </Card>
        <Card className="p-4">
          <Stat
            label="Pay gap"
            value={
              analysis.payGapPct != null
                ? `${analysis.payGapPct >= 0 ? "+" : ""}${analysis.payGapPct.toFixed(1)}%`
                : "—"
            }
            hint={PAY_GAP_LABEL[analysis.payGapClass]}
            tone={
              analysis.payGapPct != null && analysis.payGapPct < -10 ? "danger" : "default"
            }
          />
        </Card>
        <Card className="p-4">
          <Stat
            label="Offer band"
            value={`${formatCompactINR(analysis.expectedOfferLow)} – ${formatCompactINR(analysis.expectedOfferHigh)}`}
            hint="P75–P90"
          />
        </Card>
      </div>

      <div className="flex flex-wrap gap-x-6 gap-y-2 rounded-xl border border-ink/8 bg-paper/60 px-4 py-3 text-sm">
        <span>
          <span className="text-[10px] uppercase tracking-wider text-mute">P25 </span>
          <span className="tabular">{formatCompactINR(analysis.band.p25)}</span>
        </span>
        <span>
          <span className="text-[10px] uppercase tracking-wider text-mute">P75 </span>
          <span className="tabular">{formatCompactINR(analysis.band.p75)}</span>
        </span>
        <span>
          <span className="text-[10px] uppercase tracking-wider text-mute">P90 </span>
          <span className="tabular">{formatCompactINR(analysis.band.p90)}</span>
        </span>
        <span>
          <span className="text-[10px] uppercase tracking-wider text-mute">Paying </span>
          <span className="tabular">{formatCompactINR(analysis.yourPay)}</span>
        </span>
      </div>

      <Card className="p-4 text-sm leading-relaxed text-ink/85">
        <p>
          <strong>Position:</strong> {MARKET_POSITION_LABEL[analysis.marketPosition]}
          {" · "}
          <strong>Demand:</strong> {analysis.roleDemandIndex?.toFixed(2) ?? "—"}
          {" · "}
          <strong>Scarcity:</strong> {analysis.talentScarcityIndicator ?? "—"}
        </p>
        <p className="mt-2 text-xs text-mute">
          {roleDemandInsight(analysis.roleDemandIndex) ?? ""}
        </p>
        <p className="mt-1 text-xs text-mute">
          {geographicPremiumInsight(
            analysis.geographicPremiumIndex,
            analysis.hubMultiplier !== 1
              ? hub.shortLabel
              : analysis.matchedBandRecord?.geographyName || analysis.bandGeographyLevel,
            analysis.hubMultiplier !== 1 ? "the Bengaluru baseline" : "the India national",
          ) ?? "Geographic premium: —"}{" "}
          (insight only)
        </p>
        <p className="mt-1 text-xs text-mute">
          {roleCompensationPremiumInsight(
            analysis.compensationCompetitivenessIndex,
            state.profile.roleFamily,
          ) ?? "Role compensation premium: —"}{" "}
          (insight only)
        </p>
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <ThreatBadge
            tier={analysis.competitiveThreatTier}
            score={analysis.competitiveThreatScore}
          />
          <span className="text-xs text-mute">
            Top employers:{" "}
            {analysis.topCompetitors.map((c) => c.employerLabel).slice(0, 5).join(", ") || "—"}
          </span>
        </div>
      </Card>

      <Card className="flex flex-wrap items-center gap-3 p-3">
        <input
          className={`${inputClass} max-w-sm`}
          placeholder="Search employer, role, city, metro…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <label className="flex items-center gap-2 text-xs text-mute">
          <input
            type="checkbox"
            checked={aboveOnly}
            onChange={(e) => setAboveOnly(e.target.checked)}
            className="accent-copper"
          />
          Only filings above my pay
        </label>
        <span className="text-xs text-mute tabular">{rows.length.toLocaleString()} rows</span>
        <span className="ml-auto rounded-md bg-ink/5 px-2 py-1 text-[10px] font-semibold uppercase tracking-wider text-mute">
          Your pay (INR): {formatCompactINR(analysis.yourPay)}
        </span>
      </Card>

      <div className="grid gap-6 lg:grid-cols-[1.4fr_0.8fr]">
        <Card className="overflow-hidden">
          <div ref={parentRef} className="h-[560px] overflow-auto">
            <div style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
              {virtualizer.getVirtualItems().map((vi) => {
                const o = rows[vi.index]!;
                const pay = metricValue(o, metric) ?? o.salaryInr;
                const above = pay > analysis.yourPay;
                return (
                  <button
                    key={o.id}
                    type="button"
                    onClick={() => dispatch({ type: "select", id: o.id })}
                    className={`absolute left-0 flex w-full items-center gap-3 border-b border-ink/5 px-4 text-left text-sm hover:bg-ink-50 ${
                      state.selectedId === o.id ? "bg-copper/10" : ""
                    }`}
                    style={{ height: vi.size, transform: `translateY(${vi.start}px)` }}
                  >
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-medium">{o.roleName}</div>
                      <div className="truncate text-[11px] text-mute">
                        {o.employerGroup || o.employerName} · {o.city || o.metro || o.stateRegion}
                      </div>
                    </div>
                    <div className={`shrink-0 tabular ${above ? "text-crimson" : "text-ink"}`}>
                      {formatCompactINR(pay)}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </Card>

        <Card className="p-5">
          {selected ? (
            <div className="space-y-3 text-sm">
              <h3 className="font-display text-2xl leading-tight">{selected.roleName}</h3>
              <p className="text-xs text-mute">{selected.originalRoleTitle}</p>

              <div className="rounded-xl border border-copper/30 bg-copper/5 p-3">
                <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-copper">
                  Filing salary · {hub.shortLabel} hub INR
                </div>
                <div className="mt-1 font-display text-2xl tabular text-ink">
                  {formatINR(selectedPay)}
                </div>
                {selectedDelta != null ? (
                  <p className="mt-1 text-[11px] text-mute">
                    {selectedDelta >= 0 ? "+" : "−"}
                    {formatCompactINR(Math.abs(selectedDelta))} vs your pay
                  </p>
                ) : null}
              </div>

              <dl className="space-y-2">
                <Row k="Employer group" v={selected.employerGroup} />
                <Row k="Employer name" v={selected.employerName} />
                <Row k="Metro" v={selected.metro} />
                <Row
                  k="City / state"
                  v={`${selected.city}${selected.stateRegion ? `, ${selected.stateRegion}` : ""}`}
                />
                <Row k="Experience" v={selected.experienceLevel} />
                <Row k="Pay type" v={selected.payType} />
                <Row k="Quality flag" v={selected.qualityFlag} />
                <Row
                  k={`Hub pay · ${hub.shortLabel}`}
                  v={formatCompactINR(selected.hubPay?.[state.hub] ?? selected.salaryInr)}
                  active
                />
                <Row
                  k="Bengaluru baseline INR"
                  v={formatCompactINR(selected.salaryInr)}
                  active={false}
                />
                <Row k="Source" v={selected.sourceName} />
              </dl>

              {selected.sourceUrl ? (
                <a
                  href={selected.sourceUrl}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-block text-xs text-copper hover:underline"
                >
                  Open source
                </a>
              ) : null}
            </div>
          ) : (
            <p className="text-sm text-mute">Select a row to inspect the India filing sample.</p>
          )}
        </Card>
      </div>
    </div>
  );
}

function Row({ k, v, active }: { k: string; v: string; active?: boolean }) {
  return (
    <div
      className={`flex justify-between gap-3 border-b border-ink/5 py-1.5 ${
        active ? "rounded-md bg-copper/10 px-2 -mx-2" : ""
      }`}
    >
      <dt className={active ? "font-medium text-ink" : "text-mute"}>
        {k}
        {active ? " · active" : ""}
      </dt>
      <dd className={`text-right tabular ${active ? "font-semibold text-ink" : "text-ink"}`}>
        {v || "—"}
      </dd>
    </div>
  );
}
