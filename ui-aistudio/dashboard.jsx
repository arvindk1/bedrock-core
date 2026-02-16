/**
 * Professional Hedge Fund Options Desk Dashboard
 *
 * A sophisticated, institutional-grade interface for scan workflow,
 * risk management, and trade decision tracking.
 */

import React, { useState, useMemo } from 'react';
import './dashboard.css';

// ============================================================================
// 1️⃣ MARKET CONTEXT COMPONENT
// ============================================================================

const MarketContext = ({ regime = 'HIGH', spyTrend = 'Uptrend', macroRisk = 'FOMC in 3 days', policyMode = 'Tight' }) => {
  const regimeColor = {
    LOW: '#10B981',
    MEDIUM: '#F59E0B',
    HIGH: '#EF4444',
  }[regime] || '#6B7280';

  return (
    <div className="market-context">
      <div className="context-item">
        <span className="context-label">Vol Regime</span>
        <span className="context-value" style={{ color: regimeColor }}>
          {regime}
        </span>
      </div>
      <div className="context-divider"></div>
      <div className="context-item">
        <span className="context-label">SPY Trend</span>
        <span className="context-value">{spyTrend}</span>
      </div>
      <div className="context-divider"></div>
      <div className="context-item">
        <span className="context-label">Macro Risk</span>
        <span className="context-value warning">{macroRisk}</span>
      </div>
      <div className="context-divider"></div>
      <div className="context-item">
        <span className="context-label">Policy</span>
        <span className="context-value">${policyMode}</span>
      </div>
    </div>
  );
};

// ============================================================================
// 2️⃣ FUNNEL VISUALIZATION (Gate Flow)
// ============================================================================

const GateFunnel = ({ generated = 0, afterRisk = 0, afterGatekeeper = 0, afterCorrelation = 0, final = 0, isLoading = false }) => {
  const stages = [
    { label: 'Generated', value: generated, color: '#3B82F6' },
    { label: 'Risk Gate', value: afterRisk, color: '#8B5CF6' },
    { label: 'Gatekeeper', value: afterGatekeeper, color: '#EC4899' },
    { label: 'Correlation', value: afterCorrelation, color: '#F59E0B' },
    { label: 'Final Picks', value: final, color: '#10B981' },
  ];

  const maxValue = Math.max(...stages.map(s => s.value), 1);

  return (
    <div className="gate-funnel">
      <h3 className="funnel-title">Scan Gate Flow</h3>
      <div className="funnel-container">
        {stages.map((stage, idx) => {
          const width = (stage.value / maxValue) * 100;
          const isActive = stage.value > 0;

          return (
            <div key={idx} className="funnel-stage">
              <div className="stage-label">
                <span className="stage-name">{stage.label}</span>
                <span className={`stage-count ${isActive ? 'active' : 'empty'}`}>
                  {stage.value}
                </span>
              </div>
              <div className="stage-bar-container">
                <div
                  className={`stage-bar ${isLoading ? 'loading' : ''}`}
                  style={{
                    width: `${Math.max(width, 15)}%`,
                    backgroundColor: stage.color,
                    opacity: isActive ? 1 : 0.2,
                  }}
                ></div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// ============================================================================
// 3️⃣ BLOCKING EVENTS BANNER
// ============================================================================

const BlockingEventsBanner = ({ events = [] }) => {
  if (events.length === 0) return null;

  return (
    <div className="blocking-banner">
      <div className="blocking-content">
        <span className="blocking-icon">⚠️</span>
        <div>
          <p className="blocking-title">Blocking Events Detected</p>
          <ul className="blocking-list">
            {events.map((event, idx) => (
              <li key={idx}>{event}</li>
            ))}
          </ul>
          <p className="blocking-note">System blocked new positions inside trade window.</p>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// 4️⃣ FINAL PICKS TABLE
// ============================================================================

const FinalPicksTable = ({ picks = [], onRowClick = () => {} }) => {
  return (
    <div className="final-picks-section">
      <h3 className="section-title">Final Picks</h3>
      <div className="table-wrapper">
        <table className="picks-table">
          <thead>
            <tr>
              <th>Rank</th>
              <th>Strategy</th>
              <th>Exp</th>
              <th>Cost</th>
              <th>Max Loss</th>
              <th>Max Profit</th>
              <th>Score</th>
            </tr>
          </thead>
          <tbody>
            {picks.length === 0 ? (
              <tr>
                <td colSpan="7" className="empty-state">No picks available</td>
              </tr>
            ) : (
              picks.map((pick, idx) => (
                <tr key={idx} className="pick-row" onClick={() => onRowClick(pick)}>
                  <td className="rank-cell">{pick.rank}</td>
                  <td className="strategy-cell">{pick.strategy}</td>
                  <td className="exp-cell">{pick.expiration}</td>
                  <td className="cost-cell">${pick.cost.toFixed(2)}</td>
                  <td className="loss-cell"><span className="risk-value">${pick.maxLoss}</span></td>
                  <td className="profit-cell"><span className="reward-value">${pick.maxProfit}</span></td>
                  <td className="score-cell">
                    <div className="score-badge" style={{ backgroundColor: `rgba(16, 185, 129, ${pick.score / 100})` }}>
                      {pick.score}
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ============================================================================
// 5️⃣ TRADE DETAIL MODAL
// ============================================================================

const TradeDetailModal = ({ pick, isOpen, onClose }) => {
  if (!isOpen || !pick) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>{pick.strategy}</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="modal-body">
          <div className="detail-grid">
            <div className="detail-section">
              <h4>Trade Overview</h4>
              <div className="detail-row">
                <span className="label">Expiration:</span>
                <span className="value">{pick.expiration}</span>
              </div>
              <div className="detail-row">
                <span className="label">Cost (Debit):</span>
                <span className="value">${pick.cost.toFixed(2)}</span>
              </div>
              <div className="detail-row">
                <span className="label">Max Loss:</span>
                <span className="value loss">${pick.maxLoss}</span>
              </div>
              <div className="detail-row">
                <span className="label">Max Profit:</span>
                <span className="value profit">${pick.maxProfit}</span>
              </div>
              <div className="detail-row">
                <span className="label">Breakeven:</span>
                <span className="value">{pick.breakeven}</span>
              </div>
            </div>

            <div className="detail-section">
              <h4>Leg Details</h4>
              {pick.legs && pick.legs.map((leg, idx) => (
                <div key={idx} className="leg-detail">
                  <div className="leg-header">{leg.side} {leg.strike}</div>
                  <div className="detail-row">
                    <span className="label">Delta:</span>
                    <span className="value">{leg.delta}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">IV:</span>
                    <span className="value">{leg.iv}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">Bid/Ask:</span>
                    <span className="value">{leg.bid} / {leg.ask}</span>
                  </div>
                  <div className="detail-row">
                    <span className="label">OI:</span>
                    <span className="value">{leg.oi}</span>
                  </div>
                </div>
              ))}
            </div>

            <div className="detail-section">
              <h4>Gatekeeper Assessment</h4>
              <div className="assessment-badge pass">✓ Passed</div>
              {pick.warnings && pick.warnings.length > 0 && (
                <div className="warnings-list">
                  <p className="warnings-title">Warnings:</p>
                  <ul>
                    {pick.warnings.map((w, idx) => (
                      <li key={idx}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// 6️⃣ REJECTIONS TAB
// ============================================================================

const RejectionsPanel = ({ rejections = {} }) => {
  const categories = [
    { key: 'risk', label: '❌ Risk Rejections', color: '#EF4444' },
    { key: 'gatekeeper', label: '❌ Gatekeeper Rejections', color: '#F59E0B' },
    { key: 'correlation', label: '❌ Correlation Rejections', color: '#8B5CF6' },
  ];

  return (
    <div className="rejections-panel">
      <h3 className="section-title">Rejections & Filtering</h3>
      <div className="rejections-grid">
        {categories.map(cat => (
          <div key={cat.key} className="rejection-category">
            <h4 style={{ color: cat.color }}>{cat.label}</h4>
            <ul className="rejection-list">
              {rejections[cat.key] && rejections[cat.key].length > 0 ? (
                rejections[cat.key].map((reason, idx) => (
                  <li key={idx}>{reason}</li>
                ))
              ) : (
                <li className="no-rejections">None</li>
              )}
            </ul>
          </div>
        ))}
      </div>
    </div>
  );
};

// ============================================================================
// 7️⃣ DECISION LOG
// ============================================================================

const DecisionLog = ({ log = {}, isOpen, onClose }) => {
  if (!isOpen || !log) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content wide" onClick={e => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Decision Log & Audit Trail</h2>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>

        <div className="decision-log-body">
          <div className="log-section">
            <h4>Regime & Strategy</h4>
            <div className="log-item">
              <span className="log-label">Detected Regime:</span>
              <span className="log-value" style={{ color: '#F59E0B' }}>{log.regime || 'HIGH'}</span>
            </div>
            <div className="log-item">
              <span className="log-label">Strategy Hint:</span>
              <span className="log-value">{log.strategyHint || 'CREDIT_SPREAD'}</span>
            </div>
            <div className="log-item">
              <span className="log-label">Blocking Events:</span>
              <span className="log-value">{log.blockingEvents || 'None'}</span>
            </div>
          </div>

          <div className="log-section">
            <h4>Gate Progression</h4>
            <div className="progression-bar">
              <div className="progression-step">
                <div className="step-number">1</div>
                <div className="step-label">Generated</div>
                <div className="step-value">{log.generated || 0}</div>
              </div>
              <div className="progression-arrow">→</div>
              <div className="progression-step">
                <div className="step-number">2</div>
                <div className="step-label">Risk Passed</div>
                <div className="step-value">{log.riskPassed || 0}</div>
              </div>
              <div className="progression-arrow">→</div>
              <div className="progression-step">
                <div className="step-number">3</div>
                <div className="step-label">Gatekeeper</div>
                <div className="step-value">{log.gatekeeperPassed || 0}</div>
              </div>
              <div className="progression-arrow">→</div>
              <div className="progression-step">
                <div className="step-number">4</div>
                <div className="step-label">Correlation</div>
                <div className="step-value">{log.correlationPassed || 0}</div>
              </div>
              <div className="progression-arrow">→</div>
              <div className="progression-step final">
                <div className="step-number">★</div>
                <div className="step-label">Final Picks</div>
                <div className="step-value">{log.finalPicks || 0}</div>
              </div>
            </div>
          </div>

          <div className="log-section">
            <h4>Timestamp & Metadata</h4>
            <div className="log-item">
              <span className="log-label">Scanned:</span>
              <span className="log-value">{log.timestamp || new Date().toISOString()}</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// 8️⃣ TRADE MANAGEMENT (Live Positions)
// ============================================================================

const TradeManagementView = ({ positions = [] }) => {
  return (
    <div className="trade-management-section">
      <h3 className="section-title">Live Positions</h3>
      <div className="table-wrapper">
        <table className="positions-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Strategy</th>
              <th>Entry</th>
              <th>Current P/L</th>
              <th>Expected Move</th>
              <th>DTE</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {positions.length === 0 ? (
              <tr>
                <td colSpan="7" className="empty-state">No open positions</td>
              </tr>
            ) : (
              positions.map((pos, idx) => (
                <tr key={idx} className="position-row">
                  <td>{pos.symbol}</td>
                  <td>{pos.strategy}</td>
                  <td>${pos.entry.toFixed(2)}</td>
                  <td className={pos.pnl >= 0 ? 'positive' : 'negative'}>
                    {pos.pnl >= 0 ? '+' : ''}{pos.pnl.toFixed(2)}%
                  </td>
                  <td>${pos.expectedMove.toFixed(2)}</td>
                  <td>{pos.dte}</td>
                  <td>
                    <span className={`status-badge ${pos.status}`}>
                      {pos.status === 'target' ? '🎯 Target' :
                       pos.status === 'warning' ? '⚠️ DTE < 30' : '✓ Active'}
                    </span>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ============================================================================
// MAIN DASHBOARD COMPONENT
// ============================================================================

export default function TradingDashboard() {
  const [selectedPick, setSelectedPick] = useState(null);
  const [showTradeDetail, setShowTradeDetail] = useState(false);
  const [showDecisionLog, setShowDecisionLog] = useState(false);
  const [activeTab, setActiveTab] = useState('picks'); // 'picks', 'rejections', 'positions'

  // Mock Data
  const mockPicks = [
    {
      rank: 1,
      strategy: 'Bull Call Debit',
      expiration: 'Mar 20',
      cost: 1.2,
      maxLoss: 120,
      maxProfit: 380,
      score: 84,
      breakeven: '$425',
      legs: [
        { side: 'Long Call', strike: '420', delta: '0.65', iv: '22%', bid: '2.50', ask: '2.65', oi: '12,400' },
        { side: 'Short Call', strike: '425', delta: '0.45', iv: '21%', bid: '1.30', ask: '1.45', oi: '8,900' },
      ],
      warnings: [],
    },
    {
      rank: 2,
      strategy: 'Bull Call Debit',
      expiration: 'Mar 20',
      cost: 1.0,
      maxLoss: 100,
      maxProfit: 250,
      score: 79,
      breakeven: '$424',
      legs: [
        { side: 'Long Call', strike: '420', delta: '0.60', iv: '22%', bid: '2.30', ask: '2.50', oi: '11,200' },
        { side: 'Short Call', strike: '424', delta: '0.42', iv: '20%', bid: '1.30', ask: '1.50', oi: '7,800' },
      ],
      warnings: ['Slightly tighter risk/reward'],
    },
    {
      rank: 3,
      strategy: 'Bull Call Debit',
      expiration: 'Mar 20',
      cost: 0.85,
      maxLoss: 85,
      maxProfit: 180,
      score: 73,
      breakeven: '$422.85',
      legs: [
        { side: 'Long Call', strike: '420', delta: '0.58', iv: '22%', bid: '2.10', ask: '2.30', oi: '10,500' },
        { side: 'Short Call', strike: '422', delta: '0.40', iv: '19%', bid: '1.25', ask: '1.45', oi: '6,900' },
      ],
      warnings: ['Lower profit potential'],
    },
  ];

  const mockRejections = {
    risk: [
      'Max loss $1,500 exceeds limit $1,000',
      'Sector Technology cap exceeded',
      'Concentration: Already 3x NVDA exposure',
    ],
    gatekeeper: [
      'Leg 1 bid/ask spread too wide (1.8% > 1.5%)',
      'Market impact 3.2% exceeds 2% threshold',
      'Open interest below threshold for short strike',
    ],
    correlation: [
      'Correlation 0.78 with AAPL exceeds 0.70 threshold',
      'Correlation 0.72 with QQQ exceeds 0.70 threshold',
    ],
  };

  const mockDecisionLog = {
    regime: 'HIGH',
    strategyHint: 'CREDIT_SPREAD',
    blockingEvents: 'None',
    generated: 12,
    riskPassed: 9,
    gatekeeperPassed: 6,
    correlationPassed: 4,
    finalPicks: 3,
    timestamp: new Date().toISOString(),
  };

  const mockBlockingEvents = [];

  return (
    <div className="dashboard">
      {/* Header */}
      <header className="dashboard-header">
        <div className="header-logo">
          <h1>🛡️ Desk Command</h1>
          <p className="header-subtitle">Structured Risk Management</p>
        </div>
      </header>

      {/* Market Context Bar */}
      <MarketContext regime="HIGH" spyTrend="Uptrend" macroRisk="FOMC in 3 days ⚠️" policyMode="Tight ($1,000)" />

      {/* Main Content */}
      <main className="dashboard-main">
        {/* Blocking Events */}
        {mockBlockingEvents.length > 0 && <BlockingEventsBanner events={mockBlockingEvents} />}

        {/* Funnel Visualization */}
        <GateFunnel
          generated={12}
          afterRisk={9}
          afterGatekeeper={6}
          afterCorrelation={4}
          final={3}
        />

        {/* Tabs */}
        <div className="tabs-container">
          <div className="tabs-header">
            <button
              className={`tab-button ${activeTab === 'picks' ? 'active' : ''}`}
              onClick={() => setActiveTab('picks')}
            >
              📊 Final Picks
            </button>
            <button
              className={`tab-button ${activeTab === 'rejections' ? 'active' : ''}`}
              onClick={() => setActiveTab('rejections')}
            >
              ❌ Rejections
            </button>
            <button
              className={`tab-button ${activeTab === 'positions' ? 'active' : ''}`}
              onClick={() => setActiveTab('positions')}
            >
              💼 Live Positions
            </button>
            <button
              className="tab-button secondary"
              onClick={() => setShowDecisionLog(true)}
            >
              📋 Decision Log
            </button>
          </div>

          <div className="tabs-content">
            {activeTab === 'picks' && (
              <FinalPicksTable
                picks={mockPicks}
                onRowClick={(pick) => {
                  setSelectedPick(pick);
                  setShowTradeDetail(true);
                }}
              />
            )}
            {activeTab === 'rejections' && <RejectionsPanel rejections={mockRejections} />}
            {activeTab === 'positions' && <TradeManagementView positions={[]} />}
          </div>
        </div>
      </main>

      {/* Modals */}
      <TradeDetailModal
        pick={selectedPick}
        isOpen={showTradeDetail}
        onClose={() => setShowTradeDetail(false)}
      />
      <DecisionLog
        log={mockDecisionLog}
        isOpen={showDecisionLog}
        onClose={() => setShowDecisionLog(false)}
      />
    </div>
  );
}
