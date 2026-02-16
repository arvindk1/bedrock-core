/**
 * Desk Command Dashboard v2 — Refined Brutalism with Institutional Layout
 *
 * Design Direction: REFINED BRUTALISM
 * - Precise grid-based layout (sidebar + content)
 * - Data-dense but scannable
 * - Institutional (no visual fluff)
 * - High contrast (dark navy + amber accents)
 * - Monospace metrics, serif headers
 *
 * New Architecture:
 * ┌──────────┬──────────────────────────┐
 * │ SIDEBAR  │ MAIN CONTENT             │
 * │ (fixed)  │ ┌─ KPI CARDS (4x)       │
 * │          │ ├─ SCAN FORM            │
 * │ Nav      │ ├─ GATE FUNNEL          │
 * │ Regime   │ ├─ PICKS TABLE          │
 * │ Stats    │ ├─ REJECTIONS           │
 * │          │ └─ DECISION LOG         │
 * └──────────┴──────────────────────────┘
 */

import React, { useState, useMemo, useEffect } from 'react';
import './dashboard-v2.css';

// ============================================================================
// SIDEBAR COMPONENT
// ============================================================================

const Sidebar = ({ regime = 'HIGH', collapsed = false, onToggle = () => {} }) => {
  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'scan', label: 'Scan & Discovery', icon: '🔍' },
    { id: 'portfolio', label: 'Portfolio & Risk', icon: '💼' },
    { id: 'audit', label: 'Decision Audit', icon: '📋' },
  ];

  const regimeColors = {
    HIGH: '#EF4444',    // crimson
    MEDIUM: '#F59E0B',  // amber
    LOW: '#10B981',     // emerald
  };

  return (
    <div className={`sidebar ${collapsed ? 'collapsed' : ''}`}>
      {/* Header with toggle */}
      <div className="sidebar-header">
        <div className="logo">
          <span className="logo-icon">🛡️</span>
          {!collapsed && <span className="logo-text">DESK COMMAND</span>}
        </div>
        <button className="sidebar-toggle" onClick={onToggle}>
          {collapsed ? '→' : '←'}
        </button>
      </div>

      {/* Navigation */}
      <nav className="sidebar-nav">
        {navItems.map((item) => (
          <a
            key={item.id}
            href={`#${item.id}`}
            className="nav-item"
            title={collapsed ? item.label : ''}
          >
            <span className="nav-icon">{item.icon}</span>
            {!collapsed && <span className="nav-label">{item.label}</span>}
          </a>
        ))}
      </nav>

      {/* Regime Indicator */}
      {!collapsed && (
        <div className="sidebar-regime">
          <div className="regime-label">VOL REGIME</div>
          <div
            className="regime-badge"
            style={{ backgroundColor: regimeColors[regime] || '#F59E0B' }}
          >
            {regime}
          </div>
          <div className="regime-hint">
            {regime === 'HIGH' && 'Credit spreads favored'}
            {regime === 'MEDIUM' && 'Balanced strategy'}
            {regime === 'LOW' && 'Directional plays'}
          </div>
        </div>
      )}

      {/* Quick Stats */}
      {!collapsed && (
        <div className="sidebar-stats">
          <div className="stat-row">
            <span className="stat-label">Capital Used</span>
            <span className="stat-value">45%</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Daily P&L</span>
            <span className="stat-value positive">+$1,250</span>
          </div>
          <div className="stat-row">
            <span className="stat-label">Positions</span>
            <span className="stat-value">3</span>
          </div>
        </div>
      )}

      {/* Footer */}
      {!collapsed && (
        <div className="sidebar-footer">
          <a href="#settings" className="settings-link">⚙️ Settings</a>
        </div>
      )}
    </div>
  );
};

// ============================================================================
// KPI CARD COMPONENT
// ============================================================================

const KPICard = ({ title, value, subtext, indicator, trend = 'neutral' }) => {
  return (
    <div className={`kpi-card kpi-card--${trend}`}>
      <div className="kpi-header">
        <h3 className="kpi-title">{title}</h3>
        {indicator && <span className="kpi-indicator">{indicator}</span>}
      </div>
      <div className="kpi-value">{value}</div>
      {subtext && <div className="kpi-subtext">{subtext}</div>}
    </div>
  );
};

// ============================================================================
// KPI GRID COMPONENT
// ============================================================================

const KPIGrid = ({ marketContext = {} }) => {
  const policyAmount = {
    tight: '$1,000',
    moderate: '$2,000',
    aggressive: '$5,000',
  };

  return (
    <div className="kpi-grid">
      <KPICard
        title="Market Regime"
        value={marketContext.regime || 'HIGH'}
        subtext={marketContext.spyTrend || 'Uptrend'}
        indicator="📈"
        trend="neutral"
      />
      <KPICard
        title="SPY Trend"
        value={marketContext.spyTrend || 'Uptrend'}
        subtext={marketContext.macroRisk || 'No macro risk'}
        indicator="📊"
        trend="neutral"
      />
      <KPICard
        title="Policy Mode"
        value={marketContext.policyMode || 'Tight ($1,000)'}
        subtext="Max loss per trade"
        indicator="🎯"
        trend="neutral"
      />
      <KPICard
        title="Macro Risk"
        value={marketContext.macroRisk || 'None'}
        subtext={marketContext.blockingEvents?.length > 0 ? '⚠️ Events' : '✓ Clear'}
        indicator="⚠️"
        trend={marketContext.blockingEvents?.length > 0 ? 'negative' : 'positive'}
      />
    </div>
  );
};

// ============================================================================
// GATE FUNNEL VISUALIZATION
// ============================================================================

const GateFunnel = ({ funnel = {} }) => {
  const stages = [
    { key: 'generated', label: 'Generated', color: '#64748B' },
    { key: 'afterRisk', label: 'Risk Gate', color: '#EF4444' },
    { key: 'afterGatekeeper', label: 'Gatekeeper', color: '#F59E0B' },
    { key: 'afterCorrelation', label: 'Correlation', color: '#3B82F6' },
    { key: 'final', label: 'Final Picks', color: '#10B981' },
  ];

  return (
    <div className="gate-funnel">
      <h3 className="funnel-title">FILTERING PIPELINE</h3>
      <div className="funnel-stages">
        {stages.map((stage, idx) => {
          const value = funnel[stage.key] || 0;
          const maxWidth = idx === 0 ? 100 : 80 - idx * 12;

          return (
            <div key={stage.key} className="funnel-stage">
              <div className="stage-label">{stage.label}</div>
              <div className="stage-bar-container">
                <div
                  className="stage-bar"
                  style={{
                    width: `${maxWidth}%`,
                    backgroundColor: stage.color,
                  }}
                >
                  <span className="stage-count">{value}</span>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ============================================================================
// SCAN FORM COMPONENT (Existing)
// ============================================================================

const ScanForm = ({ onSubmit = () => {}, isLoading = false }) => {
  const [symbol, setSymbol] = useState('NVDA');
  const [startDate, setStartDate] = useState('2026-03-01');
  const [endDate, setEndDate] = useState('2026-06-01');
  const [policyMode, setPolicyMode] = useState('tight');
  const [portfolioJson, setPortfolioJson] = useState('[]');

  const handleSubmit = (e) => {
    e.preventDefault();
    onSubmit({
      symbol: symbol.toUpperCase(),
      start_date: startDate,
      end_date: endDate,
      portfolio_json: portfolioJson,
      policy_mode: policyMode,
      top_n: 5,
    });
  };

  return (
    <form onSubmit={handleSubmit} className="scan-form">
      <div className="form-row">
        <div className="form-group">
          <label>Symbol</label>
          <input
            type="text"
            value={symbol}
            onChange={(e) => setSymbol(e.target.value)}
            placeholder="NVDA"
            disabled={isLoading}
          />
        </div>
        <div className="form-group">
          <label>Start Date</label>
          <input
            type="date"
            value={startDate}
            onChange={(e) => setStartDate(e.target.value)}
            disabled={isLoading}
          />
        </div>
        <div className="form-group">
          <label>End Date</label>
          <input
            type="date"
            value={endDate}
            onChange={(e) => setEndDate(e.target.value)}
            disabled={isLoading}
          />
        </div>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label>Policy Mode</label>
          <select
            value={policyMode}
            onChange={(e) => setPolicyMode(e.target.value)}
            disabled={isLoading}
          >
            <option value="tight">Tight ($1,000)</option>
            <option value="moderate">Moderate ($2,000)</option>
            <option value="aggressive">Aggressive ($5,000)</option>
          </select>
        </div>
        <div className="form-group full-width">
          <label>Portfolio JSON (optional)</label>
          <textarea
            value={portfolioJson}
            onChange={(e) => setPortfolioJson(e.target.value)}
            placeholder='[{"symbol": "QQQ", "max_loss": 500}]'
            disabled={isLoading}
            rows="3"
          />
        </div>
      </div>

      <button
        type="submit"
        disabled={isLoading}
        className="scan-button"
      >
        {isLoading ? '⏳ Scanning...' : '🔍 Run Scan'}
      </button>
    </form>
  );
};

// ============================================================================
// PICKS TABLE COMPONENT
// ============================================================================

const PicksTable = ({ picks = [] }) => {
  if (picks.length === 0) {
    return (
      <div className="picks-section">
        <h3>FINAL PICKS</h3>
        <div className="empty-state">No picks available. Run a scan to get started.</div>
      </div>
    );
  }

  return (
    <div className="picks-section">
      <h3>FINAL PICKS ({picks.length})</h3>
      <table className="picks-table">
        <thead>
          <tr>
            <th>Rank</th>
            <th>Strategy</th>
            <th>Expiration</th>
            <th>Cost</th>
            <th>Max Loss</th>
            <th>Max Profit</th>
            <th>Score</th>
          </tr>
        </thead>
        <tbody>
          {picks.map((pick, idx) => (
            <tr key={idx}>
              <td className="rank">{pick.rank}</td>
              <td className="strategy">{pick.strategy}</td>
              <td className="expiration">{pick.expiration}</td>
              <td className="cost">${pick.cost}</td>
              <td className="max-loss negative">${pick.maxLoss}</td>
              <td className="max-profit positive">${pick.maxProfit}</td>
              <td className="score"><span className="score-badge">{pick.score}</span></td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
};

// ============================================================================
// REJECTIONS COMPONENT
// ============================================================================

const Rejections = ({ rejections = {} }) => {
  const categories = [
    { key: 'risk', title: '❌ Risk Rejections', color: '#EF4444' },
    { key: 'gatekeeper', title: '⚠️ Gatekeeper Rejections', color: '#F59E0B' },
    { key: 'correlation', title: '🔗 Correlation Rejections', color: '#3B82F6' },
  ];

  return (
    <div className="rejections-section">
      <h3>REJECTION ANALYSIS</h3>
      <div className="rejection-tabs">
        {categories.map((cat) => {
          const items = rejections[cat.key] || [];
          if (items.length === 0) return null;

          return (
            <div key={cat.key} className="rejection-category">
              <h4 style={{ color: cat.color }}>{cat.title}</h4>
              <ul>
                {items.slice(0, 3).map((item, idx) => (
                  <li key={idx}>{item}</li>
                ))}
                {items.length > 3 && <li>+ {items.length - 3} more</li>}
              </ul>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ============================================================================
// DECISION LOG COMPONENT
// ============================================================================

const DecisionLog = ({ log = {} }) => {
  return (
    <div className="decision-log-section">
      <h3>DECISION LOG</h3>
      <div className="decision-log">
        <div className="log-row">
          <span className="log-label">Regime:</span>
          <span className="log-value">{log.regime || 'HIGH'}</span>
        </div>
        <div className="log-row">
          <span className="log-label">Strategy Hint:</span>
          <span className="log-value">{log.strategyHint || 'CREDIT_SPREAD'}</span>
        </div>
        <div className="log-row">
          <span className="log-label">Generated:</span>
          <span className="log-value">{log.generated || 0}</span>
        </div>
        <div className="log-row">
          <span className="log-label">Risk Passed:</span>
          <span className="log-value">{log.riskPassed || 0}</span>
        </div>
        <div className="log-row">
          <span className="log-label">Gatekeeper Passed:</span>
          <span className="log-value">{log.gatekeeperPassed || 0}</span>
        </div>
        <div className="log-row">
          <span className="log-label">Correlation Passed:</span>
          <span className="log-value">{log.correlationPassed || 0}</span>
        </div>
        <div className="log-row">
          <span className="log-label">Final Picks:</span>
          <span className="log-value">{log.finalPicks || 0}</span>
        </div>
        <div className="log-row">
          <span className="log-label">Timestamp:</span>
          <span className="log-value">{log.timestamp || new Date().toISOString()}</span>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// MAIN DASHBOARD COMPONENT
// ============================================================================

export default function DashboardV2() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);
  const [apiData, setApiData] = useState(null);

  const mockData = {
    regime: 'HIGH',
    spyTrend: 'Uptrend',
    macroRisk: 'FOMC in 3 days',
    policyMode: 'Tight ($1,000)',
    blockingEvents: [],
    gateFunnel: {
      generated: 12,
      afterRisk: 9,
      afterGatekeeper: 6,
      afterCorrelation: 4,
      final: 3,
    },
    picks: [
      { rank: 1, strategy: 'Bull Call Debit', expiration: 'Mar 20', cost: 1.2, maxLoss: 120, maxProfit: 380, score: 84 },
      { rank: 2, strategy: 'Bull Call Debit', expiration: 'Mar 20', cost: 1.0, maxLoss: 100, maxProfit: 250, score: 79 },
      { rank: 3, strategy: 'Bull Call Debit', expiration: 'Mar 20', cost: 0.85, maxLoss: 85, maxProfit: 180, score: 73 },
    ],
    rejections: {
      risk: ['Max loss $1,500 exceeds limit $1,000', 'Sector concentration: Tech 45%'],
      gatekeeper: ['Leg 1 bid/ask spread 2.1%', 'Open interest below 1,000'],
      correlation: ['Correlation 0.78 with QQQ', 'Correlation 0.72 with SMH'],
    },
    decisionLog: {
      regime: 'HIGH',
      strategyHint: 'CREDIT_SPREAD',
      generated: 12,
      riskPassed: 9,
      gatekeeperPassed: 6,
      correlationPassed: 4,
      finalPicks: 3,
      timestamp: new Date().toISOString(),
    },
  };

  const handleScan = async (params) => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await fetch('/api/scan', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      });
      const data = await response.json();
      setApiData(data);
    } catch (err) {
      setError(err.message);
      console.error('Scan error:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const displayData = apiData || mockData;

  return (
    <div className="dashboard-v2">
      <Sidebar
        regime={displayData.regime}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />

      <div className="dashboard-content">
        {/* Error Display */}
        {error && (
          <div className="error-banner">
            <p>❌ Error: {error}</p>
          </div>
        )}

        {/* KPI Grid */}
        <KPIGrid marketContext={displayData} />

        {/* Scan Form */}
        <ScanForm onSubmit={handleScan} isLoading={isLoading} />

        {/* Gate Funnel */}
        <GateFunnel funnel={displayData.gateFunnel} />

        {/* Picks Table */}
        <PicksTable picks={displayData.picks} />

        {/* Rejections */}
        <Rejections rejections={displayData.rejections} />

        {/* Decision Log */}
        <DecisionLog log={displayData.decisionLog} />
      </div>
    </div>
  );
}
