import { useApp, useGapAnalysis, useMarketMatch } from "../state";
import { ProfileForm } from "../components/ProfileForm";
import { GapLadder } from "../components/GapLadder";
import { RiskMeter } from "../components/RiskMeter";
import { CopilotPanel } from "../components/CopilotPanel";
import {
  Card,
  CompetitorEvidenceCard,
  EmptyState,
  MarketPositionBadge,
  PayGapBadge,
  RiskBadge,
  SectionTitle,
  Stat,
} from "../components/ui";
import { formatCompactINR, formatINR } from "../lib/money";
import { briefingText } from "../lib/export";
import { OBSERVATION_DISCLAIMER, STRATEGIC_TARGET_OPTIONS } from "../lib/constants";
import { hubOption } from "../lib/metros";
import {
  alignmentSummary,
  FLIGHT_RISK_LABEL,
  formatGapPhrase,
  scoreFlightRisk,
} from "../lib/indiaExecutive";
import {
  geographicPremiumInsight,
  roleCompensationPremiumInsight,
  roleDemandInsight,
} from "../lib/marketBenchmark";
import {
  CONFIDENCE_LABEL,
  confidenceFromSampleSize,
  evidenceBasedOnLabel,
} from "../lib/evidenceConfidence";

export function DeskHome() {
  const { state, dispatch } = useApp();
  const analysis = useGapAnalysis();
  const { relaxNotes, bandRelaxNotes } = useMarketMatch();
  const hub = hubOption(state.hub);
  const targetOpt =
    STRATEGIC_TARGET_OPTIONS.find((o) => o.id === state.targetPercentile) ??
    STRATEGIC_TARGET_OPTIONS[1]!;

  const align = analysis
    ? alignmentSummary({
        yourPay: analysis.yourPay,
        marketTarget: analysis.marketValue,
        hubId: state.hub,
        targetLabel: targetOpt.title,
      })
    : null;

  const flight = analysis
    ? scoreFlightRisk({
        payGapPct: analysis.payGapPct,
        record: analysis.matchedBandRecord,
        roleFamily: state.profile.roleFamily,
      })
    : null;

  const geoInsight = analysis
    ? geographicPremiumInsight(
        analysis.geographicPremiumIndex,
        hub.shortLabel,
        "the Bengaluru baseline",
      )
    : null;
  const cciInsight = analysis
    ? roleCompensationPremiumInsight(
        analysis.compensationCompetitivenessIndex,
        state.profile.roleFamily,
      )
    : null;
  const demandInsight = analysis ? roleDemandInsight(analysis.roleDemandIndex) : null;
  const matchNotes = [...bandRelaxNotes, ...relaxNotes];

  const alignToneClass =
    align?.tone === "underpaid_critical"
      ? "border-crimson/40 bg-crimson/8"
      : align?.tone === "underpaid_warn"
        ? "border-crimson/25 bg-crimson/5"
        : align?.tone === "overpaid"
          ? "border-forest/30 bg-forest/8"
          : "border-ink/10 bg-ink-50/60";

  return (
    <div className="grid gap-8 lg:grid-cols-[340px_1fr]">
      <aside className="space-y-3 lg:sticky lg:top-24 lg:self-start">
        <Card className="p-5">
          <SectionTitle
            title="Incumbent"
            subtitle="Annual INR · role · experience. Hub and target live in the header."
          />
          <ProfileForm compact />
        </Card>
        <p className="px-1 text-[11px] leading-relaxed text-mute">{OBSERVATION_DISCLAIMER}</p>
      </aside>

      <div className="space-y-5">
        <header>
          <p className="eyebrow">
            {hub.shortLabel} · {targetOpt.title}
          </p>
          <h1 className="font-display mt-2 max-w-2xl text-3xl leading-tight text-ink md:text-4xl">
            Alignment vs local market target
          </h1>
          <p className="mt-2 max-w-xl text-sm text-mute">
            <span className="font-medium text-ink">{state.profile.label || "Incumbent"}</span>
            {" · "}
            paying vs {hub.shortLabel} {targetOpt.shortLabel}
          </p>
        </header>

        {!analysis || !align ? (
          <EmptyState
            title="No market slice yet"
            body="Choose role family and experience. Thin slices auto-relax filters."
          />
        ) : (
          <>
            <Card className={`border p-6 ${alignToneClass}`}>
              <p className="text-[10px] font-semibold uppercase tracking-[0.16em] text-mute">
                Verdict
              </p>
              <p className="mt-2 font-display text-2xl leading-snug text-ink md:text-3xl">
                {align.status === "Aligned" ? (
                  <>Aligned to the {hub.shortLabel} {targetOpt.shortLabel} target.</>
                ) : (
                  <>
                    {align.status} by {formatINR(Math.abs(align.gapInr ?? 0))} (
                    {Math.abs(align.gapPct ?? 0).toFixed(0)}%) vs {hub.shortLabel}{" "}
                    {targetOpt.shortLabel}.
                  </>
                )}
              </p>
              <div className="mt-4 flex flex-wrap gap-2 text-xs">
                <MarketPositionBadge position={analysis.marketPosition} />
                <PayGapBadge gapClass={analysis.payGapClass} />
                <RiskBadge tier={analysis.riskTier} score={analysis.riskScore} />
                {flight ? (
                  <span className="badge badge-watch">{FLIGHT_RISK_LABEL[flight.level]}</span>
                ) : null}
              </div>
              {align.tone === "underpaid_critical" ? (
                <p className="mt-3 text-sm font-medium text-crimson">
                  Gap exceeds 15% — model a correction on Scenario before competitor pull rises.
                </p>
              ) : null}
            </Card>

            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <Card className="p-4">
                <Stat
                  label="Paying"
                  value={formatCompactINR(analysis.yourPay)}
                  hint="Incumbent annual INR"
                />
              </Card>
              <Card className="p-4">
                <Stat
                  label={`${hub.shortLabel} ${targetOpt.shortLabel}`}
                  value={formatCompactINR(analysis.marketValue)}
                  hint={`${evidenceBasedOnLabel(analysis.band.n)} · ${CONFIDENCE_LABEL[confidenceFromSampleSize(analysis.band.n)]}`}
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
                  hint={formatGapPhrase(align.gapInr)}
                  tone={
                    analysis.payGapPct != null && analysis.payGapPct < -15
                      ? "danger"
                      : analysis.payGapPct != null && analysis.payGapPct < -10
                        ? "warn"
                        : analysis.payGapPct != null && analysis.payGapPct > 10
                          ? "ok"
                          : "default"
                  }
                />
              </Card>
              <Card className="p-4">
                <Stat
                  label="Cash to close"
                  value={
                    analysis.recommendedAdjustment > 0
                      ? formatCompactINR(analysis.recommendedAdjustment)
                      : "₹0"
                  }
                  tone={analysis.recommendedAdjustment > 0 ? "warn" : "ok"}
                  hint={`To ${targetOpt.shortLabel}`}
                />
              </Card>
            </div>

            <div className="flex flex-wrap gap-x-6 gap-y-2 rounded-xl border border-ink/8 bg-paper/60 px-4 py-3 text-sm">
              <BandChip
                label="P25"
                value={formatCompactINR(analysis.band.p25)}
                active={state.targetPercentile === "p25"}
              />
              <BandChip
                label="P50"
                value={formatCompactINR(analysis.band.p50)}
                active={state.targetPercentile === "p50"}
              />
              <BandChip
                label="P75"
                value={formatCompactINR(analysis.band.p75)}
                active={state.targetPercentile === "p75"}
              />
              <BandChip
                label="Offer band"
                value={`${formatCompactINR(analysis.expectedOfferLow)} – ${formatCompactINR(analysis.expectedOfferHigh)}`}
              />
            </div>

            <div className="grid gap-5 lg:grid-cols-2">
              <Card className="p-5">
                <h3 className="font-display text-xl">Position ladder</h3>
                <p className="mt-1 text-xs text-mute">
                  Current pay on the {hub.shortLabel} P25 / P50 / P75 scale.
                </p>
                <div className="mt-5">
                  <GapLadder analysis={analysis} />
                </div>
              </Card>
              <Card className="p-5">
                <RiskMeter analysis={analysis} />
              </Card>
            </div>

            {(geoInsight || cciInsight || demandInsight || analysis.talentScarcityIndicator) && (
              <Card className="p-4 text-sm leading-relaxed text-ink/85">
                <p className="eyebrow mb-2">Market signals</p>
                <ul className="space-y-1.5">
                  {demandInsight ? (
                    <li>
                      <span className="text-mute">Demand · </span>
                      {demandInsight}
                    </li>
                  ) : null}
                  {analysis.talentScarcityIndicator ? (
                    <li>
                      <span className="text-mute">Scarcity · </span>
                      {analysis.talentScarcityIndicator}
                    </li>
                  ) : null}
                  {geoInsight ? (
                    <li>
                      <span className="text-mute">Hub · </span>
                      {geoInsight}
                    </li>
                  ) : null}
                  {cciInsight ? (
                    <li>
                      <span className="text-mute">Role premium · </span>
                      {cciInsight}
                    </li>
                  ) : null}
                </ul>
              </Card>
            )}

            {matchNotes.length ? (
              <p className="rounded-lg border border-amber/25 bg-amber/5 px-3 py-2 text-xs text-ink/80">
                Match notes: {matchNotes.join(" ")}
              </p>
            ) : null}

            <Card className="p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="font-display text-xl">Competitors above pay</h3>
                <span className="text-xs text-mute">
                  {analysis.competitiveAbovePct.toFixed(0)}% of sample filings above incumbent
                </span>
              </div>
              <ul className="mt-4 space-y-2">
                {analysis.topCompetitors.length ? (
                  analysis.topCompetitors.slice(0, 4).map((c) => (
                    <CompetitorEvidenceCard
                      key={c.employerKey}
                      employerLabel={c.employerLabel}
                      estimatedOffer={c.medianPay}
                      n={c.n}
                      evidence={{
                        roleFamily: state.profile.roleFamily || undefined,
                        experience: state.profile.experienceLevel || undefined,
                        geography: hub.shortLabel,
                        sampleRoles: c.sampleRoles,
                      }}
                    />
                  ))
                ) : (
                  <li className="text-sm text-mute">No employer groups above pay in this slice.</li>
                )}
              </ul>
            </Card>

            <CopilotPanel analysis={analysis} label={state.profile.label} />

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-ink/8 pt-4">
              <p className="text-xs text-mute">
                Full · {formatINR(analysis.yourPay)}
                {" · "}
                {hub.shortLabel} median {formatINR(analysis.marketMedian)}
              </p>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => dispatch({ type: "view", view: "scenarios" })}
                >
                  Open Scenario
                </button>
                <button
                  type="button"
                  className="btn-secondary"
                  onClick={() => dispatch({ type: "view", view: "evidence" })}
                >
                  View Evidence
                </button>
                <button
                  type="button"
                  className="btn-primary"
                  onClick={() => {
                    const text = briefingText(analysis, state.profile.label);
                    void navigator.clipboard?.writeText(text);
                  }}
                >
                  Copy brief
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function BandChip({
  label,
  value,
  active,
}: {
  label: string;
  value: string;
  active?: boolean;
}) {
  return (
    <div className="flex items-baseline gap-2">
      <span className={`text-[10px] uppercase tracking-wider ${active ? "text-copper font-semibold" : "text-mute"}`}>
        {label}
      </span>
      <span className="tabular text-ink">{value}</span>
    </div>
  );
}
