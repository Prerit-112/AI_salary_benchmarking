import { useMemo } from "react";

import { useApp, useGapAnalysis } from "../state";
import { RiskMeter } from "../components/RiskMeter";
import {
  Card,
  EmptyState,
  EvidenceCell,
  RiskBadge,
  SectionTitle,
  Stat,
  ThreatBadge,
} from "../components/ui";
import { hubOption } from "../lib/metros";
import {
  FLIGHT_RISK_LABEL,
  formatGapPhrase,
  scoreFlightRisk,
} from "../lib/indiaExecutive";
import { formatCompactINR } from "../lib/money";

export function FlightRisk() {
  const { state, dispatch } = useApp();
  const analysis = useGapAnalysis();
  const hub = hubOption(state.hub);

  const flight = useMemo(() => {
    if (!analysis) return null;
    return scoreFlightRisk({
      payGapPct: analysis.payGapPct,
      record: analysis.matchedBandRecord,
      roleFamily: state.profile.roleFamily,
    });
  }, [analysis, state.profile.roleFamily]);

  if (!analysis || !flight) {
    return (
      <EmptyState
        title="No retention score yet"
        body="Configure the incumbent on Desk to compute flight risk vs the selected hub median."
      />
    );
  }

  const underAbs =
    analysis.payGapPct != null && analysis.payGapPct < 0
      ? Math.abs(analysis.payGapPct)
      : 0;

  const narrative =
    flight.level === "critical" || flight.level === "high"
      ? `Elevated flight risk in ${hub.shortLabel}: underpayment and talent pressure suggest competitors can win this person.`
      : flight.level === "medium"
        ? `Medium flight risk in ${hub.shortLabel}. Monitor P75 competitor offers and scarce-skill demand.`
        : analysis.payGapPct != null && analysis.payGapPct > 10
          ? `Package sits above the ${hub.shortLabel} median. Pay-driven flight risk is low.`
          : `Pay is broadly competitive vs the ${hub.shortLabel} market median.`;

  return (
    <div className="space-y-8">
      <SectionTitle
        title="Retention · flight risk"
        subtitle={`Underpaid 0–10% → Low · 11–25% → Medium · >25% → High vs strategic target. High scarcity / Specialized AI escalates one tier. Hub: ${hub.label}.`}
      />

      <div className="grid gap-6 lg:grid-cols-[1.1fr_0.9fr]">
        <Card className="p-6">
          <div className="flex flex-wrap items-center gap-2">
            <RiskBadge tier={flight.tier} score={flight.score} />
            <span className="rounded-md bg-ink/8 px-2 py-1 text-xs font-medium text-ink">
              {FLIGHT_RISK_LABEL[flight.level]}
            </span>
            <ThreatBadge
              tier={analysis.competitiveThreatTier}
              score={analysis.competitiveThreatScore}
            />
            <span className="text-xs text-mute">{state.profile.label}</span>
          </div>
          <p className="mt-4 max-w-xl text-sm leading-relaxed text-ink/85">{narrative}</p>
          <div className="mt-6">
            <RiskMeter analysis={analysis} />
          </div>
        </Card>

        <div className="space-y-4">
          <Card className="p-4">
            <Stat
              label={`Pay gap vs ${hub.shortLabel} target`}
              value={
                analysis.payGapPct != null
                  ? `${analysis.payGapPct >= 0 ? "+" : ""}${analysis.payGapPct.toFixed(1)}%`
                  : "—"
              }
              hint={formatGapPhrase(analysis.gapVsBenchmark)}
              tone={
                analysis.payGapPct != null && analysis.payGapPct < -15
                  ? "danger"
                  : analysis.payGapPct != null && analysis.payGapPct < -10
                    ? "warn"
                    : "default"
              }
            />
          </Card>
          <Card className="p-4">
            <Stat
              label="Underpayment band"
              value={
                analysis.payGapPct == null || analysis.payGapPct >= 0
                  ? "Not underpaid"
                  : underAbs <= 10
                    ? "0–10% (Low)"
                    : underAbs <= 25
                      ? "11–25% (Medium)"
                      : ">25% (High)"
              }
            />
          </Card>
          <Card className="p-4">
            <Stat
              label="Cash to reach target"
              value={
                analysis.recommendedAdjustment > 0
                  ? formatCompactINR(analysis.recommendedAdjustment)
                  : "₹0"
              }
              hint={`Annual remediation to ${analysis.benchmarkLabel}`}
              tone={analysis.recommendedAdjustment > 0 ? "warn" : "ok"}
            />
          </Card>
          <Card className="p-4">
            <Stat
              label="Expected competitor offer"
              value={`${formatCompactINR(analysis.expectedOfferLow)} – ${formatCompactINR(analysis.expectedOfferHigh)}`}
              hint={`${hub.shortLabel} P75–P90`}
            />
          </Card>
          <Card className="flex gap-2 p-4">
            <button
              type="button"
              className="btn-primary flex-1"
              onClick={() => dispatch({ type: "view", view: "scenarios" })}
            >
              Model a raise
            </button>
            <button
              type="button"
              className="btn-secondary flex-1"
              onClick={() => dispatch({ type: "view", view: "evidence" })}
            >
              See competitors
            </button>
          </Card>
        </div>
      </div>

      <Card className="p-5">
        <h3 className="font-display text-2xl">Flight-risk drivers</h3>
        <ul className="mt-3 space-y-2">
          {flight.reasons.map((r, i) => (
            <li key={i} className="flex gap-2 text-sm text-ink/80">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-crimson" />
              {r}
            </li>
          ))}
          {analysis.competitiveThreatReasons.map((r, i) => (
            <li key={`t-${i}`} className="flex gap-2 text-sm text-ink/80">
              <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-copper" />
              {r}
            </li>
          ))}
        </ul>
        {flight.scarcityEscalated ? (
          <p className="mt-4 text-xs text-mute">
            Scarcity escalation applied (High Scarcity / Specialized AI).
          </p>
        ) : null}
      </Card>

      <Card className="p-5">
        <h3 className="font-display text-2xl">Top competitor companies</h3>
        <p className="mt-1 text-xs text-mute">
          Same role family / experience from India filings, ranked by {hub.shortLabel} hub pay.
        </p>
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-[640px] text-left text-sm">
            <thead className="text-[11px] uppercase tracking-wider text-mute">
              <tr className="border-b border-ink/10">
                <th className="py-2 pr-3 font-medium">Employer</th>
                <th className="py-2 pr-3 font-medium">Roles</th>
                <th className="py-2 pr-3 font-medium">Market evidence</th>
                <th className="py-2 font-medium tabular">Estimated offer</th>
              </tr>
            </thead>
            <tbody>
              {analysis.topCompetitors.map((p) => (
                <tr key={p.employerKey} className="border-b border-ink/5">
                  <td className="py-2.5 pr-3 font-medium text-ink">{p.employerLabel}</td>
                  <td className="py-2.5 pr-3 text-mute">{p.sampleRoles.join(" · ")}</td>
                  <td className="py-2.5 pr-3">
                    <EvidenceCell n={p.n} />
                  </td>
                  <td className="py-2.5 tabular">{formatCompactINR(p.medianPay)}</td>
                </tr>
              ))}
              {!analysis.topCompetitors.length ? (
                <tr>
                  <td colSpan={4} className="py-6 text-center text-mute">
                    No competitor employers in the current slice.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
