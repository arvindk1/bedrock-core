/**
 * Desk Command Dashboard v2 — PHASE 2 COMPONENTS
 *
 * Decision Inspector: Timestamped execution log
 * Live Positions: Active trade management interface
 *
 * Add these to dashboard-v2.jsx for Phase 2 deployment
 */

import React, { useState } from 'react';

// ============================================================================
// DECISION INSPECTOR COMPONENT
// ============================================================================

/**
 * Timestamped pipeline log showing decision progression
 *
 * Usage:
 * <DecisionInspector log={decisionLog} />
 *
 * Log format:
 * {
 *   steps: [
 *     { time: '10:00:01', status: 'pass', label: '...', reason: '...' },
 *     { time: '10:00:02', status: 'fail', label: '...', reason: '...' }
 *   ]
 * }
 */

const DecisionInspector = ({ log = {} }) => {
  const [expanded, setExpanded] = useState(false);

  // Generate synthetic log from decision log object
  const generateSteps = () => {
    const steps = [];
    const timestamp = new Date(log.timestamp || Date.now());

    // Time helper
    const getTime = (offsetSeconds) => {
      const t = new Date(timestamp.getTime() + offsetSeconds * 1000);
      return t.toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    };

    steps.push({
      time: getTime(0),
      status: 'pass',
      label: 'Regime Detection',
      reason: `Volatility ${log.regime || 'HIGH'} detected. Bias: ${
        log.regime === 'HIGH' ? 'Credit spreads' : 'Directional'
      }`,
    });

    steps.push({
      time: getTime(1),
      status: 'pass',
      label: 'Market Data Loaded',
      reason: `Loaded option chains. Ready to scan ${log.generated || 0} candidates.`,
    });

    steps.push({
      time: getTime(2),
      status: 'pass',
      label: 'Strategy Selection',
      reason: `Strategy: ${log.strategyHint || 'CREDIT_SPREAD'}`,
    });

    steps.push({
      time: getTime(3),
      status: 'pass',
      label: 'Pipeline Started',
      reason: `Generated ${log.generated || 0} candidates based on parameters.`,
    });

    const riskRejected = (log.generated || 0) - (log.riskPassed || 0);
    if (riskRejected > 0) {
      steps.push({
        time: getTime(4),
        status: 'partial',
        label: 'Risk Gate',
        reason: `Rejected ${riskRejected}. Passed: ${log.riskPassed || 0}. Reason: Gamma, concentration, max loss.`,
      });
    } else {
      steps.push({
        time: getTime(4),
        status: 'pass',
        label: 'Risk Gate',
        reason: `All ${log.riskPassed || 0} candidates passed risk filtering.`,
      });
    }

    const gatekeeperRejected = (log.riskPassed || 0) - (log.gatekeeperPassed || 0);
    if (gatekeeperRejected > 0) {
      steps.push({
        time: getTime(5),
        status: 'partial',
        label: 'Gatekeeper',
        reason: `Rejected ${gatekeeperRejected}. Passed: ${log.gatekeeperPassed || 0}. Reason: Spreads, OI, IV rank.`,
      });
    } else {
      steps.push({
        time: getTime(5),
        status: 'pass',
        label: 'Gatekeeper',
        reason: `All ${log.gatekeeperPassed || 0} candidates passed liquidity checks.`,
      });
    }

    const correlationRejected = (log.gatekeeperPassed || 0) - (log.correlationPassed || 0);
    if (correlationRejected > 0) {
      steps.push({
        time: getTime(6),
        status: 'partial',
        label: 'Correlation Matrix',
        reason: `Rejected ${correlationRejected}. Passed: ${log.correlationPassed || 0}. Reason: Portfolio overlap.`,
      });
    } else {
      steps.push({
        time: getTime(6),
        status: 'pass',
        label: 'Correlation Matrix',
        reason: `All ${log.correlationPassed || 0} candidates passed diversity check.`,
      });
    }

    steps.push({
      time: getTime(7),
      status: 'success',
      label: 'Final Selection',
      reason: `${log.finalPicks || 0} high-probability trades ranked and ready for execution.`,
    });

    return steps;
  };

  const steps = generateSteps();

  const getStatusIcon = (status) => {
    switch (status) {
      case 'pass':
        return '✓';
      case 'partial':
        return '⊙';
      case 'fail':
        return '✗';
      case 'success':
        return '★';
      default:
        return '•';
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'pass':
        return '#10b981'; // green
      case 'partial':
        return '#f59e0b'; // amber
      case 'fail':
        return '#ef4444'; // red
      case 'success':
        return '#3b82f6'; // blue
      default:
        return '#64748b'; // gray
    }
  };

  return (
    <div className="decision-inspector">
      <div className="inspector-header" onClick={() => setExpanded(!expanded)}>
        <h3>📋 DECISION LOGIC INSPECTOR</h3>
        <button className="inspector-toggle">{expanded ? '▼' : '▶'}</button>
      </div>

      {expanded && (
        <div className="inspector-timeline">
          {steps.map((step, idx) => (
            <div key={idx} className="timeline-step">
              <div
                className="timeline-icon"
                style={{ color: getStatusColor(step.status) }}
              >
                {getStatusIcon(step.status)}
              </div>
              <div className="timeline-time">{step.time}</div>
              <div className="timeline-content">
                <div className="timeline-label">{step.label}</div>
                <div className="timeline-reason">{step.reason}</div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// ============================================================================
// LIVE POSITIONS COMPONENT
// ============================================================================

/**
 * Active positions management with P&L, Greeks, and risk alerts
 *
 * Usage:
 * <LivePositions positions={positions} />
 *
 * Position format:
 * {
 *   symbol: 'SPY',
 *   strategy: 'Iron Condor',
 *   quantity: 10,
 *   entryPrice: 1.10,
 *   currentPrice: 0.45,
 *   deltaTotal: 45.5,
 *   thetaPerDay: 12.50,
 *   vegaTotal: -8.75,
 *   daysToExpiry: 35,
 *   alerts: ['50% profit target reached']
 * }
 */

const LivePositions = ({ positions = [] }) => {
  const [expandedPos, setExpandedPos] = useState(null);

  if (positions.length === 0) {
    return (
      <div className="live-positions">
        <h3>💼 LIVE POSITIONS</h3>
        <div className="empty-state">
          No active positions. Execute a trade to see it here.
        </div>
      </div>
    );
  }

  const calculatePnL = (entry, current, qty) => {
    const pnl = (current - entry) * qty * 100; // Options are contracts (100 shares)
    const pnlPct = ((current - entry) / entry * 100).toFixed(2);
    return { pnl: pnl.toFixed(0), pnlPct };
  };

  const getRiskAlert = (alert) => {
    if (alert.includes('profit')) return { icon: '✓', color: '#10b981' };
    if (alert.includes('loss')) return { icon: '⚠️', color: '#ef4444' };
    if (alert.includes('Delta')) return { icon: '⚡', color: '#f59e0b' };
    if (alert.includes('Gamma')) return { icon: '📈', color: '#f59e0b' };
    return { icon: 'ℹ️', color: '#3b82f6' };
  };

  return (
    <div className="live-positions">
      <h3>💼 LIVE POSITIONS ({positions.length})</h3>

      <div className="positions-table-container">
        <table className="positions-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Strategy</th>
              <th>Qty</th>
              <th>Entry</th>
              <th>Current</th>
              <th>P&L</th>
              <th>Delta</th>
              <th>Theta/Day</th>
              <th>DTE</th>
              <th>Alerts</th>
            </tr>
          </thead>
          <tbody>
            {positions.map((pos, idx) => {
              const { pnl, pnlPct } = calculatePnL(
                pos.entryPrice,
                pos.currentPrice,
                pos.quantity
              );
              const isProfit = parseFloat(pnl) > 0;

              return (
                <React.Fragment key={idx}>
                  <tr
                    className="position-row"
                    onClick={() =>
                      setExpandedPos(expandedPos === idx ? null : idx)
                    }
                  >
                    <td className="symbol">{pos.symbol}</td>
                    <td className="strategy">{pos.strategy}</td>
                    <td className="qty">{pos.quantity}</td>
                    <td className="price">${pos.entryPrice.toFixed(2)}</td>
                    <td className="price">${pos.currentPrice.toFixed(2)}</td>
                    <td className={`pnl ${isProfit ? 'positive' : 'negative'}`}>
                      ${pnl} ({pnlPct}%)
                    </td>
                    <td className="greek">{pos.deltaTotal.toFixed(1)}</td>
                    <td className="greek positive">${pos.thetaPerDay.toFixed(2)}</td>
                    <td className="dte">{pos.daysToExpiry}d</td>
                    <td className="alerts">
                      {pos.alerts && pos.alerts.length > 0 ? (
                        <span className="alert-count">{pos.alerts.length}</span>
                      ) : (
                        <span className="no-alerts">—</span>
                      )}
                    </td>
                  </tr>

                  {/* Expanded Details Row */}
                  {expandedPos === idx && (
                    <tr className="position-details">
                      <td colSpan="10">
                        <div className="details-panel">
                          <div className="detail-section">
                            <h4>Greeks</h4>
                            <div className="greek-row">
                              <span>Δ (Delta)</span>
                              <span>{pos.deltaTotal.toFixed(2)}</span>
                            </div>
                            <div className="greek-row">
                              <span>Θ (Theta/Day)</span>
                              <span className="positive">
                                +${pos.thetaPerDay.toFixed(2)}
                              </span>
                            </div>
                            <div className="greek-row">
                              <span>ν (Vega)</span>
                              <span>{pos.vegaTotal.toFixed(2)}</span>
                            </div>
                          </div>

                          {pos.alerts && pos.alerts.length > 0 && (
                            <div className="detail-section">
                              <h4>⚠️ Risk Alerts</h4>
                              <div className="alerts-list">
                                {pos.alerts.map((alert, aidx) => {
                                  const { icon, color } = getRiskAlert(alert);
                                  return (
                                    <div
                                      key={aidx}
                                      className="alert-item"
                                      style={{ borderLeftColor: color }}
                                    >
                                      <span className="alert-icon">{icon}</span>
                                      <span className="alert-text">{alert}</span>
                                    </div>
                                  );
                                })}
                              </div>
                            </div>
                          )}

                          <div className="detail-section actions">
                            <button className="action-btn close">
                              ✕ Close Position
                            </button>
                            <button className="action-btn roll">
                              ↻ Roll Legs
                            </button>
                            <button className="action-btn scale">
                              ≡ Scale Out
                            </button>
                          </div>
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
};

// ============================================================================
// EXECUTION SNAPSHOT COMPONENT
// ============================================================================

/**
 * Current policy and constraint settings display
 *
 * Usage:
 * <ExecutionSnapshot settings={settings} />
 */

const ExecutionSnapshot = ({ settings = {} }) => {
  return (
    <div className="execution-snapshot">
      <h3>📊 EXECUTION SNAPSHOT</h3>
      <div className="snapshot-grid">
        <div className="snapshot-item">
          <span className="snap-label">Policy</span>
          <span className="snap-value">{settings.policy || 'Tight'}</span>
        </div>
        <div className="snapshot-item">
          <span className="snap-label">Max Risk/Trade</span>
          <span className="snap-value">${settings.maxRiskPerTrade || '1,000'}</span>
        </div>
        <div className="snapshot-item">
          <span className="snap-label">Min Profit Target</span>
          <span className="snap-value">${settings.minProfit || '0'}</span>
        </div>
        <div className="snapshot-item">
          <span className="snap-label">Max Gamma/100</span>
          <span className="snap-value">{settings.maxGamma || '0.5'}</span>
        </div>
        <div className="snapshot-item">
          <span className="snap-label">Min IV Rank</span>
          <span className="snap-value">{settings.minIVRank || '25'}%</span>
        </div>
        <div className="snapshot-item">
          <span className="snap-label">Sector Limit</span>
          <span className="snap-value">{settings.sectorLimit || '40'}%</span>
        </div>
        <div className="snapshot-item">
          <span className="snap-label">Max Correlation</span>
          <span className="snap-value">{settings.maxCorrelation || '0.70'}</span>
        </div>
        <div className="snapshot-item">
          <span className="snap-label">Min DTE</span>
          <span className="snap-value">{settings.minDTE || '30'}d</span>
        </div>
      </div>
    </div>
  );
};

// ============================================================================
// EXPORTS
// ============================================================================

export { DecisionInspector, LivePositions, ExecutionSnapshot };
