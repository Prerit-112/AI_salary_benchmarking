import { useMemo } from "react";
import { useApp, useGapAnalysis } from "../state";
import { Card, EmptyState, RiskBadge, SectionTitle, Field } from "../components/ui";
import { analyzeGap, buildScenarios } from "../lib/analysis";
import { hubOption } from "../lib/metros";
import { formatCompactINR, formatINR } from "../lib/money";

export function ScenariosView() {
  const { state, dispatch } = useApp();
  const analysis = useGapAnalysis();
  const hub = hubOption(state.hub);

  const scenarios = useMemo(() => (analysis ? buildScenarios(analysis) : []), [analysis]);

  const custom = useMemo(() => {
    if (!analysis) return null;
    const target = analysis.yourPay * (1 + state.customRaisePct / 100);
    if (target <= analysis.yourPay) return null;
    const next = analyzeGap(analysis.matched, target, analysis.metric, analysis.sliceLabel, {
      matchedBandRecord: analysis.matchedBandRecord,
      hubId: state.hub,
      targetPercentile: state.targetPercentile,
    });
    return {
      target,
      delta: target - analysis.yourPay,
      next,
    };
  }, [analysis, state.customRaisePct, state.hub, state.targetPercentile]);

  if (!analysis) {
    return (
      <EmptyState title="No scenarios" body="Set incumbent pay on Desk to model remediation." />
    );
  }

  return (
    <div className="space-y-8">
      <SectionTitle
        title="Scenario"
        subtitle={`Cost to close gaps to P25 / P50 / P75 in ${hub.shortLabel} (index ${hub.multiplier.toFixed(2)}) — and how retention risk moves after each raise.`}
      />

      <Card className="p-5">
        <div className="grid gap-6 md:grid-cols-[1fr_auto] md:items-end">
          <Field label={`Custom raise · ${state.customRaisePct}%`}>
            <input
              type="range"
              min={0}
              max={40}
              step={1}
              value={state.customRaisePct}
              onChange={(e) =>
                dispatch({ type: "customRaise", pct: Number(e.target.value) })
              }
              className="w-full accent-copper"
            />
          </Field>
          {custom ? (
            <div className="rounded-xl bg-ink-50 px-4 py-3 text-sm">
              <div className="eyebrow">New package</div>
              <div className="font-display text-2xl tabular">{formatCompactINR(custom.target)}</div>
              <div className="mt-1 text-mute">
                +{formatCompactINR(custom.delta)} / yr · score {custom.next.riskScore}
              </div>
              <div className="mt-2">
                <RiskBadge tier={custom.next.riskTier} />
              </div>
            </div>
          ) : (
            <p className="text-sm text-mute">Move the slider to preview a raise.</p>
          )}
        </div>
      </Card>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {scenarios.map((s) => (
          <Card key={s.id} className="flex flex-col p-5">
            <div className="eyebrow">{s.id.toUpperCase()}</div>
            <h3 className="mt-1 font-display text-xl">{s.label}</h3>
            <div className="mt-4 space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-mute">Target</span>
                <span className="tabular font-medium">{formatINR(s.targetPay)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-mute">Incremental cost</span>
                <span className="tabular text-copper">+{formatCompactINR(s.deltaPay)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-mute">Raise %</span>
                <span className="tabular">+{s.deltaPct.toFixed(1)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-mute">New percentile</span>
                <span className="tabular">{s.newPercentile ?? "—"}</span>
              </div>
            </div>
            <div className="mt-4 flex flex-wrap items-center gap-2">
              <RiskBadge tier={s.newRiskTier} score={s.newRiskScore} />
              {s.closesGapToP50 ? (
                <span className="badge badge-stable">Closes P50 gap</span>
              ) : null}
            </div>
          </Card>
        ))}
        {!scenarios.length ? (
          <Card className="p-5 text-sm text-mute md:col-span-2">
            You are already at or above P75 / modeled raise targets for this slice. Premium position —
            scenarios focus on closing underpay gaps.
          </Card>
        ) : null}
      </div>

      <Card className="p-5 text-sm text-mute leading-relaxed">
        Costs are annual INR increments for the active hub. Equity, bonus structure, and benefits are
        out of scope unless already in Total Compensation observations.
      </Card>
    </div>
  );
}
