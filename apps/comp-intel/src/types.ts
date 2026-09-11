export type CountryCode = "US" | "IN" | string;
export type PayType = "Base" | "Base_Salary" | "Total_Compensation" | string;

/**
 * Benchmark methodology switcher — each mode has a distinct calculation path.
 * - talent (default): Talent Market Value = matched P50 × Role Demand × Scarcity
 * - market: Market Benchmark Value = matched P50 only (band already includes role × geo × experience)
 * - fx: pure USD × FX_USD_INR (no market / scarcity / demand)
 * - ppp: pure USD × PPP_Conversion_Factor (purchasing power only)
 * Geo Premium and CCI are insight-only — never salary multipliers.
 * Legacy aliases: "nominal" → treated as fx in loaders.
 */
export type MetricMode = "market" | "talent" | "fx" | "ppp" | "nominal";

/** Indian target market hub for multi-metro INR benchmark scaling (Bengaluru = 1.0). */
export type HubId =
  | "bengaluru"
  | "mumbai"
  | "delhi_ncr"
  | "hyderabad"
  | "chennai"
  | "pune";

/** Strategic Compensation Target percentile (drives Pay_Gap / remediation). */
export type TargetPercentile = "p25" | "p50" | "p75";

export type ViewId = "desk" | "method" | "scenarios" | "evidence";

export type RiskTier = "critical" | "high" | "watch" | "stable" | "premium";
export type GapVerdict = "underpaid" | "at_market" | "overpaid";
export type BandSource = "market_band" | "computed";

export type MarketPosition =
  | "significantly_underpaid"
  | "underpaid"
  | "market_competitive"
  | "highly_competitive"
  | "market_leading";

export type PayGapClass =
  | "critical_underpayment"
  | "high_underpayment_risk"
  | "market_aligned"
  | "above_market"
  | "significantly_above_market";

export type CompetitiveThreatTier = "low" | "medium" | "high" | "critical";

/** Sample-size confidence for market / competitor estimates (executive display). */
export type EvidenceConfidence = "low" | "medium" | "high" | "very_high";

export interface CompetitorCompany {
  employerKey: string;
  employerLabel: string;
  n: number;
  medianPay: number;
  sampleRoles: string[];
}

export interface Observation {
  id: string;
  analyticGrain: string;
  payPeriod: string;
  country: string;
  countryCode: CountryCode;
  stateRegion: string;
  city: string;
  metro: string;
  geographyLevel: string;
  geographyName: string;
  roleName: string;
  originalRoleTitle: string;
  roleFamily: string;
  experienceLevel: string;
  careerLevel: string;
  payType: PayType;
  compensationDefinition: string;
  /** Hardcoded INR for India multi-metro ingest. */
  currency?: string;
  salaryInr: number;
  salaryPppInr: number | null;
  salaryPppInrCorrected: number | null;
  salaryUsd: number | null;
  pppSuspect: boolean;
  employerGroup: string;
  employerName: string;
  caseNumber?: string;
  fxUsdInr: number | null;
  fxConversionDate: string;
  sourceName: string;
  sourceType: string;
  sourceUrl: string;
  retrievalDate: string;
  sampleSize: number | null;
  qualityFlag: string;
  dataQualityScore: number | null;
  notes: string;
  isEmployerFiling: boolean;
  /**
   * Per-hub India INR benchmarks (filing grain).
   * bengaluru ≡ Benchmark_INR_Salary; others are metro-scaled integers.
   */
  hubPay?: Partial<Record<HubId, number>>;
  benchmarkInrBengaluru?: number | null;
  benchmarkInrMumbai?: number | null;
  benchmarkInrDelhiNcr?: number | null;
  benchmarkInrHyderabad?: number | null;
  benchmarkInrChennai?: number | null;
  benchmarkInrPune?: number | null;
}

/** Per-hub summary percentile payload (INR integers). */
export interface HubBandStats {
  p25: number | null;
  p50: number | null;
  p75: number | null;
  mean: number | null;
}

export interface MarketBandRecord {
  id: string;
  roleFamily: string;
  roleFamilyKey: string;
  /** Present on India Role×Experience summary bands. */
  roleName?: string;
  countryCode: string;
  countryName: string;
  geographyLevel: string;
  geographyName: string;
  state: string;
  city: string;
  metro: string;
  experienceLevel: string;
  experienceBandKey: string;
  payType: string;
  compensationDefinition: string;
  currency?: string;
  p10Usd: number | null;
  p25Usd: number | null;
  p50Usd: number | null;
  p75Usd: number | null;
  p90Usd: number | null;
  minUsd: number | null;
  maxUsd: number | null;
  meanUsd: number | null;
  p10Inr: number | null;
  p25Inr: number | null;
  p50Inr: number | null;
  p75Inr: number | null;
  p90Inr: number | null;
  minInr: number | null;
  maxInr: number | null;
  meanInr: number | null;
  p10PppInr: number | null;
  p25PppInr: number | null;
  p50PppInr: number | null;
  p75PppInr: number | null;
  p90PppInr: number | null;
  minPppInr: number | null;
  maxPppInr: number | null;
  meanPppInr: number | null;
  sampleSize: number;
  geographicPremiumIndex: number | null;
  leadershipPremiumIndex: number | null;
  roleDemandIndex: number | null;
  talentScarcityIndicator: string;
  compensationCompetitivenessIndex: number | null;
  sourceName: string;
  collectionDate: string;
  fxUsdInr: number;
  fxConversionDate: string;
  notes: string;
  /** Multi-metro INR bands keyed by HubId (Bengaluru baseline + 5 metros). */
  metros?: Partial<Record<HubId, HubBandStats>>;
  /** Pre-computed Bengaluru salary histogram bins (full population) for Recharts. */
  payBins?: { x0: number; x1: number; n: number }[];
}

export interface NamedCount {
  name: string;
  n: number;
}

export interface Catalog {
  generatedFrom: string[];
  standardizedDuplicate?: string;
  rowCount: number;
  /** Full filing population before Evidence sampling. */
  filingPopulation?: number;
  bandCount: number;
  grain: string;
  grainNotes: string;
  countries: { code: string; name: string; n: number }[];
  roleFamilies: NamedCount[];
  roleNames: NamedCount[];
  /** Nested Role_Name facets under each Role_Family (India summary grain). */
  roleNamesByFamily?: Record<string, NamedCount[]>;
  experienceLevels: NamedCount[];
  payTypes: NamedCount[];
  cities: { countryCode: string; name: string; n: number }[];
  metros: { countryCode: string; name: string; n: number }[];
  states: { countryCode: string; name: string; n: number }[];
  employerGroups: NamedCount[];
  hubs?: string[];
  fxUsdInr: number;
  pppFactor: number;
  fxConversionDate: string;
  collectionDate: string;
  compensationDefinition: string;
  disclaimer: string;
  countryFxToInr: Record<string, number>;
  worldBankPpp: Record<string, number>;
}

/** Incumbent the business is assessing. */
export interface IncumbentProfile {
  label: string;
  countryCode: string;
  roleFamily: string;
  roleName: string;
  experienceLevel: string;
  city: string;
  metro: string;
  payType: PayType;
  /** Annual pay in INR (cash / nominal). */
  currentPayInr: number;
  currencyInput: "INR" | "USD" | "local";
  /** Raw amount typed before conversion (for display). */
  rawAmount: number;
  notes: string;
}

export interface PortfolioPerson extends IncumbentProfile {
  id: string;
}

export interface Filters {
  countries: string[];
  roleFamilies: string[];
  roleNames: string[];
  experienceLevels: string[];
  payTypes: string[];
  sources: string[];
  cities: string[];
  metros: string[];
  allowMixPayTypes: boolean;
}

export interface MarketBand {
  p10: number | null;
  p25: number | null;
  p50: number | null;
  p75: number | null;
  p90: number | null;
  min: number | null;
  max: number | null;
  mean: number | null;
  n: number;
  sourceCount: number;
  directional: boolean;
}

export interface EmployerPull {
  employerKey: string;
  employerLabel: string;
  n: number;
  medianPay: number;
  premiumVsYou: number;
  premiumPct: number;
  sampleRoles: string[];
}

export interface SourcePull {
  sourceName: string;
  sourceType: string;
  n: number;
  medianPay: number;
  premiumVsYou: number;
  premiumPct: number;
  isEmployerFiling: boolean;
  sampleRoles: string[];
}

export interface DestinationPull {
  key: string;
  label: string;
  kind: "city" | "country" | "metro" | "employer" | "source";
  n: number;
  medianPay: number;
  premiumVsYou: number;
  premiumPct: number;
}

export interface GapAnalysis {
  yourPay: number;
  metric: MetricMode;
  /** Active Indian target hub (Bengaluru baseline or metro-scaled). */
  hubId: HubId;
  /** Hub multiplier applied to FX INR market bands (1.0 = Bengaluru). */
  hubMultiplier: number;
  /** Strategic Compensation Target (P25 / P50 / P75). */
  targetPercentile: TargetPercentile;
  band: MarketBand;
  bandSource: BandSource;
  matchedBandRecord: MarketBandRecord | null;
  bandGeographyLevel: string | null;
  compensationDefinition: string | null;
  compensationCompetitivenessIndex: number | null;
  geographicPremiumIndex: number | null;
  leadershipPremiumIndex: number | null;
  roleDemandIndex: number | null;
  talentScarcityIndicator: string | null;
  /**
   * Selected benchmark for the active mode (drives pay gap / adjustment / KPIs).
   * Talent → Talent Market Value; Market → Market Benchmark;
   * FX → current salary × FX; PPP → current salary × PPP factor.
   * Distinct from yourPay (current salary), which never changes with mode.
   */
  marketValue: number | null;
  /** Always matched P50 (FX currency of the band), for cross-mode comparison. */
  marketBenchmarkValue: number | null;
  /** Always Talent Market Value = P50 × Demand × Scarcity (FX currency). */
  talentMarketValue: number | null;
  /** Human label for the selected benchmark in the active mode. */
  benchmarkLabel: string;
  marketMedian: number | null;
  marketPosition: MarketPosition;
  payGapPct: number | null;
  payGapClass: PayGapClass;
  expectedOfferLow: number | null;
  expectedOfferHigh: number | null;
  /** Competitor offer range only in Talent Market View. */
  offerRangeSupported: boolean;
  topCompetitors: CompetitorCompany[];
  competitiveThreatTier: CompetitiveThreatTier;
  competitiveThreatScore: number;
  competitiveThreatReasons: string[];
  recommendedAdjustment: number;
  /** 0–100 approximate percentile among observations. */
  percentileRank: number | null;
  gapVsP50: number | null;
  gapVsP50Pct: number | null;
  gapVsP25: number | null;
  gapVsP75: number | null;
  /** Gap vs selected mode benchmark. */
  gapVsBenchmark: number | null;
  gapVsBenchmarkPct: number | null;
  verdict: GapVerdict;
  /** False in FX/PPP — risk is benchmark-based only. */
  riskSupported: boolean;
  riskTier: RiskTier;
  riskScore: number;
  riskReasons: string[];
  competitiveAbove: number;
  competitiveAbovePct: number;
  sliceLabel: string;
  matched: Observation[];
  aboveYou: Observation[];
}

export interface ScenarioResult {
  id: string;
  label: string;
  targetPay: number;
  deltaPay: number;
  deltaPct: number;
  newRiskTier: RiskTier;
  newRiskScore: number;
  newPercentile: number | null;
  closesGapToP50: boolean;
}

export interface SourceGroup {
  sourceName: string;
  sourceType: string;
  n: number;
  values: number[];
  minPublished: number | null;
  medianPublished: number | null;
  maxPublished: number | null;
  rows: Observation[];
  isEmployerFiling: boolean;
  kind: "published_range" | "observation_set" | "employer_filing";
}
