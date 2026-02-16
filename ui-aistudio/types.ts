export interface TradeLeg {
  type: 'Call' | 'Put';
  side: 'Long' | 'Short';
  strike: number;
  delta: number;
}

export interface TradeCandidate {
  id: string;
  symbol: string;
  strategy: string; // e.g., Iron Condor, Vertical Spread
  dte: number;
  expiration: string;
  netPremium: number; // Positive = Credit, Negative = Debit
  maxProfit: number;
  maxLoss: number;
  breakeven: [number, number] | [number];
  gatekeeperScore: number;
  liquidityImpact: number;
  legs: TradeLeg[];
  status: 'pending' | 'active' | 'rejected';
  rejectionReason?: string;
  rejectionCategory?: 'Risk' | 'Gatekeeper' | 'Correlation';
}

export interface PipelineStage {
  id: string;
  label: string;
  count: number;
  status: 'normal' | 'warning' | 'critical' | 'success';
}

export interface RejectionLog {
  id: string;
  symbol: string;
  strategy: string;
  reasonCode: string;
  message: string;
  timestamp: string;
  category: 'Risk' | 'Gatekeeper' | 'Correlation';
}

export interface PortfolioRisk {
  totalCapitalAtRisk: number;
  maxRiskPerTrade: number;
  dailyDrawdown: number;
  netDelta: number;
  sectorExposure: { name: string; value: number }[];
}

export enum VolatilityRegime {
  LOW = 'LOW',
  MED = 'MED',
  HIGH = 'HIGH',
}

export enum PolicyMode {
  TIGHT = 'Tight',
  MODERATE = 'Moderate',
  AGGRESSIVE = 'Aggressive',
}
