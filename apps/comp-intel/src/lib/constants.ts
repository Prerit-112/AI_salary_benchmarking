export const COUNTRY_FX_TO_INR: Record<string, number> = {
  IN: 1,
  US: 95.43,
  AE: 25.9856,
  GB: 128.9259,
  DE: 110.1453,
  AU: 67.364,
  NZ: 55.9792,
};

export const WORLD_BANK_PPP: Record<string, number> = {
  /** India: World Bank GDP PPP conversion factor (~₹23 per international dollar). */
  IN: 23,
  US: 1,
  AE: 2.32695589646038,
  GB: 0.677133,
  DE: 0.709983,
  AU: 1.398943,
  NZ: 1.472957,
};

export const FX_USD_INR = 95.43;
export const FX_DATE = "2026-08-12";

/** Alias for USD → PPP-adjusted INR (India purchasing-power equivalent). */
export { INDIA_PPP_FACTOR, convertUsdToPppInr, PPP_COMPARISON_DESCRIPTION } from "./ppp";

export const COUNTRY_ORDER = ["IN", "US", "GB", "AE", "DE", "AU", "NZ"];

export const COUNTRY_LABEL: Record<string, string> = {
  IN: "India",
  US: "United States",
  GB: "United Kingdom",
  AE: "United Arab Emirates",
  DE: "Germany",
  AU: "Australia",
  NZ: "New Zealand",
};

export const EXPERIENCE_ORDER = [
  "Entry (0-2 Years)",
  "Mid (3-5 Years)",
  "Senior (6-9 Years)",
  "Lead / Staff (10-14 Years)",
  "Executive (15+ Years)",
  // Legacy US LCA labels (kept for older cached profiles)
  "Entry Level (0-2 years)",
  "Mid Level (3-5 years)",
  "Senior Level (6-9 years)",
  "Lead Level (10-14 years)",
  "All Levels (unspecified)",
];

export const PAY_TYPE_LABEL: Record<string, string> = {
  Base: "Base salary (annual INR)",
  Base_Salary: "Base salary",
  Total_Compensation: "Total compensation",
  Mixed: "Mixed (base + TC)",
};

/** Geography fallback minimum n for pre-aggregated market bands. */
export const GEO_THRESHOLDS = {
  city: 5,
  metro: 10,
  state: 15,
  national: 30,
} as const;

export const DIRECTIONAL_N = 30;

export const RISK_LABEL: Record<string, string> = {
  critical: "Critical retention risk",
  high: "High retention risk",
  watch: "Moderate retention risk",
  stable: "Low retention risk",
  premium: "Premium / insulated",
};

export const VERDICT_LABEL: Record<string, string> = {
  underpaid: "Underpaid vs market",
  at_market: "Market aligned",
  overpaid: "Above market",
};

export const PRODUCT_NAME = "PayRisk Desk";
export const PRODUCT_TAGLINE =
  "India multi-metro alignment — hub × strategic target.";

export const OBSERVATION_DISCLAIMER =
  "India multi-metro tech benchmarks (Bengaluru baseline + Mumbai / Delhi-NCR / Hyderabad / Chennai / Pune). Market median is the selected hub’s P50 from Role × Experience summary bands. Filing samples are progressive Evidence excerpts — not headcount or confirmed offers. Flight-risk and competitor views are directional decision aids.";

export const COMPETITOR_DISCLAIMER =
  "Competitor data maps tier-one organizations leveraging certified baseline offered-wage records calibrated to this market hub.";

export const STORAGE_PORTFOLIO = "payrisk-portfolio-v2-in";
export const STORAGE_PROFILE = "payrisk-profile-v2-in";
export const STORAGE_TARGET = "payrisk-strategic-target-v1";

/** Strategic Compensation Target — replaces legacy Talent / Market / FX / PPP toggles. */
export type StrategicTargetId = "p25" | "p50" | "p75";

export const STRATEGIC_TARGET_OPTIONS: {
  id: StrategicTargetId;
  label: string;
  shortLabel: string;
  title: string;
  explanation: string;
}[] = [
  {
    id: "p25",
    label: "Conservative",
    shortLabel: "P25",
    title: "Conservative (P25)",
    explanation: "Align metrics to the local 25th percentile market band",
  },
  {
    id: "p50",
    label: "Market Rate",
    shortLabel: "Median",
    title: "Market Rate (Median / P50)",
    explanation: "Standard market baseline — 50th percentile median",
  },
  {
    id: "p75",
    label: "Aggressive",
    shortLabel: "P75",
    title: "Aggressive (Top Tier / P75)",
    explanation: "Elite retention — align to the 75th percentile band",
  },
];

/** @deprecated Kept for older scripts; UI uses STRATEGIC_TARGET_OPTIONS. */
export const BENCHMARK_MODE_OPTIONS = [
  { id: "market" as const, label: "Market", title: "Market", explanation: "Market median" },
];
