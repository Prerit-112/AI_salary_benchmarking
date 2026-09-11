import { useMemo, useState } from "react";
import type { GapAnalysis } from "../types";
import {
  MARKET_POSITION_LABEL,
  PAY_GAP_LABEL,
  THREAT_LABEL,
} from "../lib/marketBenchmark";
import { formatCompactINR, formatINR } from "../lib/money";
import { Card } from "./ui";

const PROMPTS = [
  { id: "underpaid", label: "Is this employee underpaid?" },
  { id: "market_value", label: "What is their market target?" },
  { id: "hire", label: "Who would likely hire them?" },
  { id: "offer", label: "How much would competitors offer?" },
  { id: "adjust", label: "What adjustment is required?" },
] as const;

type PromptId = (typeof PROMPTS)[number]["id"];

function answerFor(id: PromptId, analysis: GapAnalysis, label: string): string {
  const gap = analysis.payGapPct;
  const mv = analysis.marketValue;

  switch (id) {
    case "underpaid":
      return [
        `${label} is classified as ${PAY_GAP_LABEL[analysis.payGapClass]}`,
        gap != null
          ? `(${gap >= 0 ? "+" : ""}${gap.toFixed(1)}% vs ${analysis.benchmarkLabel}).`
          : ".",
        `Market position: ${MARKET_POSITION_LABEL[analysis.marketPosition]}.`,
        `Gap uses the selected hub’s strategic target (P25 / P50 / P75).`,
      ]
        .filter(Boolean)
        .join(" ");

    case "market_value":
      return [
        `${analysis.benchmarkLabel} for ${label}: ${mv != null ? formatINR(mv) : "unavailable"}.`,
        `Hub median (P50): ${formatCompactINR(analysis.marketMedian)}.`,
        `Current pay: ${formatINR(analysis.yourPay)}.`,
        `Demand, scarcity, and premium indices are insight-only — not salary multipliers.`,
      ].join(" ");

    case "hire": {
      const names = analysis.topCompetitors.map((c) => c.employerLabel).slice(0, 5);
      return names.length
        ? `Employers above pay in this hub slice (by median): ${names.join(", ")}.`
        : "No competitor employers matched above pay in the current filing slice.";
    }

    case "offer":
      return [
        `Hub P50: ${formatCompactINR(analysis.marketBenchmarkValue ?? analysis.marketMedian)}.`,
        `Expected external offer range (P75–P90): ${formatCompactINR(analysis.expectedOfferLow)} – ${formatCompactINR(analysis.expectedOfferHigh)}.`,
        `Competitive threat: ${THREAT_LABEL[analysis.competitiveThreatTier]} (${analysis.competitiveThreatScore}/100).`,
      ].join(" ");

    case "adjust":
      return analysis.recommendedAdjustment > 0
        ? `Cash to reach ${analysis.benchmarkLabel}: +${formatINR(analysis.recommendedAdjustment)} annual. Retention risk: ${analysis.riskTier} (${analysis.riskScore}/100).`
        : `No upward cash adjustment needed for ${analysis.benchmarkLabel}. Package is at or above the strategic target.`;

    default:
      return "";
  }
}

export function CopilotPanel({
  analysis,
  label,
}: {
  analysis: GapAnalysis;
  label: string;
}) {
  const [active, setActive] = useState<PromptId>("underpaid");
  const answer = useMemo(() => answerFor(active, analysis, label), [active, analysis, label]);

  return (
    <Card className="p-5">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <h3 className="font-display text-xl">Copilot</h3>
        <span className="text-[10px] uppercase tracking-[0.16em] text-mute">
          {analysis.benchmarkLabel}
        </span>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        {PROMPTS.map((p) => (
          <button
            key={p.id}
            type="button"
            className={`rounded-md px-2.5 py-1.5 text-xs transition ${
              active === p.id
                ? "bg-ink text-paper"
                : "bg-ink-100 text-mute hover:bg-ink-200 hover:text-ink"
            }`}
            onClick={() => setActive(p.id)}
          >
            {p.label}
          </button>
        ))}
      </div>
      <p className="mt-4 text-sm leading-relaxed text-ink/90">{answer}</p>
    </Card>
  );
}
