import { TradeCandidate, RejectionLog, PipelineStage, PortfolioRisk, VolatilityRegime, PolicyMode } from './types';

export const PIPELINE_STAGES: PipelineStage[] = [
  { id: 'gen', label: 'Generated', count: 142, status: 'normal' },
  { id: 'risk', label: 'Risk Gate', count: 86, status: 'warning' },
  { id: 'gate', label: 'Gatekeeper', count: 42, status: 'normal' },
  { id: 'corr', label: 'Correlation', count: 12, status: 'normal' },
  { id: 'final', label: 'Final Picks', count: 5, status: 'success' },
];

export const MOCK_TRADES: TradeCandidate[] = [
  {
    id: 't1',
    symbol: 'SPX',
    strategy: 'Iron Condor',
    dte: 4,
    expiration: '2023-11-14',
    netPremium: 1.25,
    maxProfit: 125,
    maxLoss: 375,
    breakeven: [4350, 4410],
    gatekeeperScore: 92,
    liquidityImpact: 0.01,
    status: 'active',
    legs: [
      { type: 'Put', side: 'Long', strike: 4340, delta: -0.10 },
      { type: 'Put', side: 'Short', strike: 4350, delta: -0.18 },
      { type: 'Call', side: 'Short', strike: 4410, delta: 0.16 },
      { type: 'Call', side: 'Long', strike: 4420, delta: 0.09 },
    ]
  },
  {
    id: 't2',
    symbol: 'NVDA',
    strategy: 'Short Put Vertical',
    dte: 18,
    expiration: '2023-11-28',
    netPremium: 0.85,
    maxProfit: 85,
    maxLoss: 415,
    breakeven: [445.15],
    gatekeeperScore: 88,
    liquidityImpact: 0.04,
    status: 'active',
    legs: [
      { type: 'Put', side: 'Long', strike: 440, delta: -0.22 },
      { type: 'Put', side: 'Short', strike: 445, delta: -0.30 },
    ]
  },
  {
    id: 't3',
    symbol: 'AMD',
    strategy: 'Long Call Butterfly',
    dte: 25,
    expiration: '2023-12-05',
    netPremium: -0.45, // Debit
    maxProfit: 455,
    maxLoss: 45,
    breakeven: [110.45, 119.55],
    gatekeeperScore: 78,
    liquidityImpact: 0.02,
    status: 'active',
    legs: [
      { type: 'Call', side: 'Long', strike: 110, delta: 0.45 },
      { type: 'Call', side: 'Short', strike: 115, delta: 0.52 }, // x2 technically
      { type: 'Call', side: 'Long', strike: 120, delta: 0.20 },
    ]
  }
];

export const MOCK_REJECTIONS: RejectionLog[] = [
  { id: 'r1', symbol: 'TSLA', strategy: 'Short Straddle', category: 'Risk', reasonCode: 'R-MAX-DD', message: 'Projected DD exceeds daily limit', timestamp: '10:02:41' },
  { id: 'r2', symbol: 'META', strategy: 'Iron Condor', category: 'Gatekeeper', reasonCode: 'G-IV-RANK', message: 'IV Rank < 15%', timestamp: '10:03:12' },
  { id: 'r3', symbol: 'GOOGL', strategy: 'Vertical Call', category: 'Correlation', reasonCode: 'C-BETA', message: 'Portfolio Beta > 1.2 threshold', timestamp: '10:04:05' },
  { id: 'r4', symbol: 'AMZN', strategy: 'Calendar', category: 'Gatekeeper', reasonCode: 'G-LIQUID', message: 'Bid/Ask Spread > 0.15%', timestamp: '10:05:00' },
  { id: 'r5', symbol: 'MSFT', strategy: 'Put Credit Spread', category: 'Risk', reasonCode: 'R-EXP-CON', message: 'Too many positions expiring 11-28', timestamp: '10:05:45' },
];

export const PORTFOLIO_RISK: PortfolioRisk = {
  totalCapitalAtRisk: 145250,
  maxRiskPerTrade: 2500,
  dailyDrawdown: -0.45,
  netDelta: 124.5,
  sectorExposure: [
    { name: 'Tech', value: 45 },
    { name: 'Fin', value: 20 },
    { name: 'Cons', value: 15 },
    { name: 'Health', value: 10 },
    { name: 'Energy', value: 5 },
    { name: 'Utils', value: 5 },
  ]
};

export const CORRELATION_MATRIX = [
  [1.0, 0.8, 0.2, -0.1, 0.5],
  [0.8, 1.0, 0.3, -0.2, 0.4],
  [0.2, 0.3, 1.0, 0.6, 0.1],
  [-0.1, -0.2, 0.6, 1.0, -0.3],
  [0.5, 0.4, 0.1, -0.3, 1.0],
];
export const CORRELATION_LABELS = ['SPY', 'QQQ', 'TLT', 'GLD', 'USO'];
