/**
 * OPTION SCANNER — Frontend Application Logic
 * Handles navigation, API integration, live updates, and UI interactions
 */

// ============================================================================
// CONFIGURATION
// ============================================================================

const API_BASE = '';
let TICKER_SYMBOL = 'SPY'; // Defaults to SPY, updates dynamically on scan
const TICKER_UPDATE_INTERVAL = 5000; // 5 seconds

// ============================================================================
// STATE
// ============================================================================

const appState = {
    currentView: 'dashboard',
    lastScanResult: null,
    currentPortfolio: [],
    tickers: {},
};

// ============================================================================
// UTILITIES
// ============================================================================

function safeSetText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function safeSetClass(id, className) {
    const el = document.getElementById(id);
    if (el) el.className = className;
}

function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
}

function formatPercent(value) {
    return (value * 100).toFixed(2) + '%';
}

function formatRejectionReason(raw) {
    if (!raw || raw === '—') return raw;
    // Parse pipe-delimited reason strings: "RISK_REJECT|rule=SECTOR_CAP|sector=Technology|used_pct=100|limit_pct=25"
    if (!raw.includes('|')) return raw;
    const parts = {};
    raw.split('|').forEach(p => {
        const [k, v] = p.split('=');
        if (v !== undefined) parts[k] = v;
    });
    const rule = (parts.rule || '').replace(/_/g, ' ');
    if (parts.sector && parts.used_pct) {
        return `${rule}: ${parts.sector} at ${parts.used_pct}% (limit ${parts.limit_pct}%)`;
    }
    if (rule) return rule;
    return raw.split('|').slice(1).join(' · ') || raw;
}

// ============================================================================
// INITIALIZATION
// ============================================================================

document.addEventListener('DOMContentLoaded', function () {
    console.log('🚀 Option Scanner initializing...');

    setupNavigation();
    setupLiveTicker();
    loadInitialData();
    startPeriodicUpdates();

    addLiveFeedEntry('Dashboard initialized and ready', 'info');
});

// ============================================================================
// NAVIGATION
// ============================================================================

function setupNavigation() {
    // Unified selector: catches sidebar buttons and any legacy nav buttons
    const navButtons = document.querySelectorAll('[data-view]');
    navButtons.forEach(button => {
        button.addEventListener('click', function (e) {
            e.preventDefault();
            switchView(this.dataset.view);
        });
    });
}

function switchView(viewName) {
    // Hide all views
    document.querySelectorAll('.hd-view').forEach(view => {
        view.classList.remove('active');
        view.classList.add('hidden');
    });

    // Show selected view
    const selectedView = document.getElementById(`view-${viewName}`);
    if (selectedView) {
        selectedView.classList.add('active');
        selectedView.classList.remove('hidden');
    }

    // Update all nav/sidebar button active states
    document.querySelectorAll('[data-view]').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelectorAll(`[data-view="${viewName}"]`).forEach(btn => {
        btn.classList.add('active');
    });

    appState.currentView = viewName;

    // Load view-specific data on switch
    if (viewName === 'portfolio') loadPortfolioRisk();

    console.log(`📍 Switched to view: ${viewName}`);
}

// ============================================================================
// LIVE TICKER
// ============================================================================

function setupLiveTicker() {
    safeSetText('ticker-symbol', TICKER_SYMBOL);
    updateTicker();
}

async function updateTicker() {
    try {
        const response = await fetch(`${API_BASE}/api/market/snapshot/${TICKER_SYMBOL}`);
        const data = await response.json();

        if (data.error) {
            console.error('Ticker error:', data.error);
            return;
        }

        // Price
        safeSetText('ticker-price', `$${data.current_price.toFixed(2)}`);

        // Change
        const changeEl = document.getElementById('ticker-change');
        if (changeEl) {
            const changePct = data.change_pct || 0;
            changeEl.textContent = `${changePct >= 0 ? '+' : ''}${changePct.toFixed(2)}%`;
            changeEl.className = `ticker-change ${changePct >= 0 ? 'positive' : 'negative'}`;
        }

        // Wire IV rank from snapshot if available
        if (data.volatility && data.volatility.iv_rank != null) {
            let ivRank = data.volatility.iv_rank;
            if (ivRank > 0 && ivRank <= 1) ivRank = ivRank * 100;
            safeSetText('iv-rank', `${ivRank.toFixed(0)}%`);
        }

        // Wire regime from snapshot if available
        if (data.volatility && data.volatility.regime) {
            const regime = data.volatility.regime;
            safeSetText('regime-badge', regime);
            const regimeEl = document.getElementById('regime-badge');
            if (regimeEl) {
                const regimeColors = { HIGH: 'var(--accent-danger)', MED: 'var(--accent-warning)', LOW: 'var(--accent-success-lt)' };
                regimeEl.style.color = regimeColors[regime] || 'var(--accent-warning)';
            }
        }

        appState.tickers[TICKER_SYMBOL] = data;
    } catch (err) {
        console.error('Ticker update failed:', err);
    }
}

// ============================================================================
// LIVE FEED
// ============================================================================

function addLiveFeedEntry(message, type = 'info') {
    const liveFeed = document.getElementById('live-feed');
    if (!liveFeed) return;

    const entry = document.createElement('div');
    entry.className = `log-entry log-${type}`;

    const timestamp = new Date().toLocaleTimeString('en-US', {
        hour12: false,
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
    });

    entry.textContent = `[${timestamp}] ${message}`;
    liveFeed.appendChild(entry);
    liveFeed.scrollTop = liveFeed.scrollHeight;

    // Keep only last 50 entries
    while (liveFeed.children.length > 50) {
        liveFeed.removeChild(liveFeed.firstChild);
    }
}

// ============================================================================
// SCAN & DISCOVERY
// ============================================================================



async function initiateDiscoveryScan() {
    const symbol = document.getElementById('scan-symbol')?.value?.toUpperCase() || 'AAPL';
    const startDate = document.getElementById('scan-start-date')?.value || '2026-03-01';
    const endDate = document.getElementById('scan-end-date')?.value || '2026-06-01';
    const policyMode = document.getElementById('scan-policy')?.value || 'tight';
    const topN = parseInt(document.getElementById('scan-top-n')?.value || '5');

    if (!startDate || !endDate) {
        addLiveFeedEntry('Please select valid start and end dates', 'error');
        return;
    }
    if (new Date(startDate) >= new Date(endDate)) {
        addLiveFeedEntry('Start date must be before end date', 'error');
        return;
    }

    const scanBtn = document.getElementById('scan-btn');
    if (scanBtn) { scanBtn.disabled = true; scanBtn.textContent = 'Scanning...'; }

    addLiveFeedEntry(`Initiating scan for ${symbol} (${startDate} → ${endDate}, ${policyMode})...`, 'info');

    // Dynamically update the top-right live ticker to the symbol being scanned
    TICKER_SYMBOL = symbol;
    safeSetText('ticker-symbol', TICKER_SYMBOL);
    updateTicker(); // Fetch immediate live price for the top bar

    try {
        const response = await fetch(`${API_BASE}/api/scan`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol,
                start_date: startDate,
                end_date: endDate,
                policy_mode: policyMode,
                top_n: topN,
            }),
        });

        const scanResult = await response.json();

        if (scanResult.error) {
            addLiveFeedEntry(`Scan failed: ${scanResult.error}`, 'error');
            return;
        }

        appState.lastScanResult = scanResult;

        // --- Wire header fields ---
        const regime = scanResult.regime || '';
        safeSetText('regime-badge', regime || '—');
        safeSetText('dash-regime-badge', regime || '—');
        const regimeBadgeEl = document.getElementById('regime-badge');
        if (regimeBadgeEl && regime) {
            const regimeColors = { HIGH: 'var(--accent-danger)', MED: 'var(--accent-warning)', LOW: 'var(--accent-success-lt)' };
            regimeBadgeEl.style.color = regimeColors[regime] || 'var(--accent-warning)';
        }

        const spyTrend = scanResult.spyTrend || '—';
        const spyTrendEl = document.getElementById('spy-trend');
        if (spyTrendEl) {
            spyTrendEl.textContent = spyTrend;
            spyTrendEl.style.color = spyTrend.toLowerCase().includes('up')
                ? 'var(--accent-success-lt)' : 'var(--accent-danger)';
        }

        safeSetText('policy-mode-display', scanResult.policyMode || '—');

        let ivRank = (scanResult.volatilityContext || {}).iv_rank;
        if (ivRank != null) {
            if (ivRank > 0 && ivRank <= 1) ivRank = ivRank * 100;
            safeSetText('iv-rank', `${ivRank.toFixed(0)}%`);
            safeSetText('dash-iv-rank', `${ivRank.toFixed(0)}%`);
        }

        const strategyHint = (scanResult.decisionLog || {}).strategyHint || '';
        safeSetText('regime-bias', strategyHint.replace(/_/g, ' ') || '—');

        // --- Wire volatility context ---
        updateVolatilityContext(scanResult);

        // --- Wire pipeline ---
        updatePipelineVisualization(scanResult);

        // --- Render trade cards ---
        renderTradeCards(scanResult.picks || []);

        // --- Populate rejection tabs ---
        updateRejectionTabCounts(scanResult);
        switchRejectionTab('risk');

        // --- Populate audit view ---
        populateDecisionAudit(scanResult);

        addLiveFeedEntry(
            `Scan complete: ${(scanResult.decisionLog || {}).finalPicks || 0} picks from ${(scanResult.decisionLog || {}).generated || 0} candidates`,
            'success'
        );

        // Switch to scan view to show results
        switchView('scan');

    } catch (err) {
        console.error('Scan error:', err);
        addLiveFeedEntry(`Scan error: ${err.message}`, 'error');
    } finally {
        if (scanBtn) { scanBtn.disabled = false; scanBtn.textContent = 'Scan'; }
    }
}

// ============================================================================
// PIPELINE VISUALIZATION
// ============================================================================

function updatePipelineVisualization(scanResult) {
    const funnel = scanResult.gateFunnel || {};

    const generated = funnel.generated || 0;
    const afterEvent = funnel.afterEvent !== undefined ? funnel.afterEvent : generated;
    const afterRisk = funnel.afterRisk || 0;
    const afterGk = funnel.afterGatekeeper || 0;
    const afterCorr = funnel.afterCorrelation || 0;
    const final = funnel.final || 0;

    safeSetText('count-generated', generated);
    safeSetText('count-event', afterEvent);
    safeSetText('count-risk', afterRisk);
    safeSetText('count-gatekeeper', afterGk);
    safeSetText('count-correlation', afterCorr);
    safeSetText('count-final', final);

    // Rejection deltas
    const rejectedByEvent = generated - afterEvent;
    const rejectedByRisk = afterEvent - afterRisk;
    const rejectedByGk = afterRisk - afterGk;
    const rejectedByCorr = afterGk - afterCorr;

    safeSetText('rejected-event', rejectedByEvent > 0 ? `-${rejectedByEvent}` : '');
    safeSetText('rejected-risk', rejectedByRisk > 0 ? `-${rejectedByRisk}` : '');
    safeSetText('rejected-gatekeeper', rejectedByGk > 0 ? `-${rejectedByGk}` : '');
    safeSetText('rejected-correlation', rejectedByCorr > 0 ? `-${rejectedByCorr}` : '');

    // Color status on stage cards
    setPipelineStageWarning('event', rejectedByEvent);
    setPipelineStageWarning('risk', rejectedByRisk);
    setPipelineStageWarning('gatekeeper', rejectedByGk);
    setPipelineStageWarning('correlation', rejectedByCorr);
}

function setPipelineStageWarning(stage, rejectedCount) {
    const card = document.querySelector(`[data-stage="${stage}"]`);
    if (!card) return;
    card.classList.remove('status-warning');
    if (rejectedCount > 0) card.classList.add('status-warning');
}

function updateRejectionTabCounts(scanResult) {
    const rejections = scanResult.rejections || {};
    safeSetText('rej-count-risk', (rejections.risk || []).length);
    safeSetText('rej-count-gatekeeper', (rejections.gatekeeper || []).length);
    safeSetText('rej-count-event', (rejections.event || []).length);
    safeSetText('rej-count-correlation', (rejections.correlation || []).length);
}

function selectPipelineStage(stage) {
    // Update active class on pipeline cards
    document.querySelectorAll('.hd-pipeline-stage-card').forEach(card => {
        card.classList.remove('active');
    });
    const selected = document.querySelector(`[data-stage="${stage}"]`);
    if (selected) selected.classList.add('active');

    if (stage === 'generated' || stage === 'final') {
        // Show trade cards for generated/final
        renderTradeCards((appState.lastScanResult || {}).picks || []);
    } else {
        // Show relevant rejection tab
        const tabMap = { event: 'event', risk: 'risk', gatekeeper: 'gatekeeper', correlation: 'correlation' };
        if (tabMap[stage]) switchRejectionTab(tabMap[stage]);
    }
}

function switchRejectionTab(tab) {
    // Update tab active states
    document.querySelectorAll('.hd-rejection-tab').forEach(t => t.classList.remove('active'));
    const activeTab = document.querySelector(`[data-rejection-tab="${tab}"]`);
    if (activeTab) activeTab.classList.add('active');

    const content = document.getElementById('rejection-tab-content');
    if (!content) return;

    if (!appState.lastScanResult) {
        content.innerHTML = '<p style="color:var(--color-text-muted); padding:24px; text-align:center; font-family:var(--font-mono); font-size:0.82rem;">No scan results yet</p>';
        return;
    }

    const rejections = appState.lastScanResult.rejections || {};
    const list = rejections[tab] || [];

    if (list.length === 0) {
        content.innerHTML = '<p style="color:var(--color-text-muted); padding:24px; text-align:center; font-family:var(--font-mono); font-size:0.82rem;">No rejections in this category</p>';
        return;
    }

    content.innerHTML = `
    <table class="hd-table">
        <thead>
            <tr>
                <th>Symbol</th>
                <th>Strategy</th>
                <th>Reason</th>
                <th>Score</th>
            </tr>
        </thead>
        <tbody>
            ${list.map(rej => {
        const candidate = rej.candidate || rej;
        const sym = candidate.symbol || rej.symbol || '—';
        const strat = (candidate.strategy || rej.strategy || '—').replace(/_/g, ' ');
        const rawReason = rej.reason || rej.message || rej.rejection_reason || '—';
        const reason = formatRejectionReason(rawReason);
        const score = rej.score !== undefined ? parseFloat(rej.score).toFixed(1) : '—';
        return `
                <tr>
                    <td style="font-weight:700;">${sym}</td>
                    <td class="text-muted">${strat}</td>
                    <td style="color:var(--accent-danger); font-size:0.78rem;">${reason}</td>
                    <td class="text-mono">${score}</td>
                </tr>`;
    }).join('')}
        </tbody>
    </table>`;
}

// ============================================================================
// TRADE CARDS
// ============================================================================

function renderTradeCards(picks) {
    const container = document.getElementById('picks-cards-container');
    if (!container) return;

    if (!picks || picks.length === 0) {
        container.innerHTML = '<p style="color:var(--color-text-muted); padding:40px; text-align:center; font-family:var(--font-mono); font-size:0.85rem;">No picks found for this scan</p>';
        return;
    }

    container.innerHTML = picks.map((pick, index) => {
        const symbol = pick.symbol || '?';
        const strategy = (pick.strategy || '?').replace(/_/g, ' ');
        const expiration = pick.expiration || '?';
        const maxLoss = pick.max_loss || pick.maxLoss || 0;
        const maxProfit = pick.max_profit || pick.maxProfit || 0;
        const score = pick.gatekeeper_score || pick.gatekeeperScore || 0;
        const cost = pick.cost || pick.netPremium || 0;
        const legs = pick.legs || [];
        const pipeline = pick.pipeline || null;
        const strategyReasoning = pick.strategy_reasoning || null;

        const isCredit = cost > 0;
        const premiumColor = isCredit ? 'var(--accent-success-lt)' : 'var(--color-text-main)';

        let scoreClass = 'low';
        if (score >= 90) scoreClass = 'high';
        else if (score >= 75) scoreClass = 'mid';

        const legsHtml = legs.length > 0
            ? legs.map(leg => `
                <div class="hd-leg-row">
                    <div style="display:flex; align-items:center; gap:8px;">
                        <span class="hd-leg-side-badge ${(leg.side || leg.action || '').toLowerCase()}">
                            ${leg.side || leg.action || '?'}
                        </span>
                        <span style="color:var(--color-text-main); font-weight:700;">
                            ${leg.strike || '—'} ${leg.type || leg.option_type || '?'}
                        </span>
                    </div>
                    <span style="color:var(--color-text-muted);">
                        ${leg.delta !== undefined ? 'Δ ' + parseFloat(leg.delta).toFixed(2) : ''}
                    </span>
                </div>`).join('')
            : '<p style="color:var(--color-text-muted); font-size:0.78rem; font-family:var(--font-mono);">Leg detail not available</p>';

        return `
        <div class="hd-trade-card" id="trade-card-${index}">
            <div class="hd-trade-card-header" onclick="toggleTradeCard(${index})">
                <div style="min-width:70px; flex-shrink:0;">
                    <span class="hd-trade-card-symbol">${symbol}</span>
                    <span class="hd-trade-card-expiry">${expiration}</span>
                </div>
                <div class="hd-trade-card-field">
                    <span class="hd-trade-card-field-label">Strategy</span>
                    <span class="hd-trade-card-field-value" style="font-family:var(--font-sans); font-size:0.82rem;">${strategy}</span>
                </div>
                <div class="hd-trade-card-field">
                    <span class="hd-trade-card-field-label">Premium</span>
                    <span class="hd-trade-card-field-value" style="color:${premiumColor};">${isCredit ? '+' : ''}${cost.toFixed(2)}</span>
                </div>
                <div class="hd-trade-card-field">
                    <span class="hd-trade-card-field-label">Max Risk</span>
                    <span class="hd-trade-card-field-value" style="color:var(--accent-danger);">-$${maxLoss.toFixed(0)}</span>
                </div>
                <div class="hd-trade-card-field">
                    <span class="hd-trade-card-field-label">Max Profit</span>
                    <span class="hd-trade-card-field-value" style="color:var(--accent-success-lt);">+$${maxProfit.toFixed(0)}</span>
                </div>
                <div class="hd-trade-card-field">
                    <span class="hd-trade-card-field-label">Score</span>
                    <span class="hd-score-badge ${scoreClass}">${score.toFixed(0)}</span>
                </div>
                <svg id="chevron-${index}" style="width:16px; height:16px; stroke:var(--color-text-muted); fill:none; stroke-width:2; flex-shrink:0; transition:transform 0.15s; margin-left:auto;" viewBox="0 0 24 24">
                    <polyline points="6 9 12 15 18 9"/>
                </svg>
            </div>
            <div class="hd-trade-card-body" style="grid-template-columns: 1fr 1fr 1fr;">
                <div>
                    <p style="font-size:0.6rem; text-transform:uppercase; letter-spacing:0.15em; color:var(--color-text-muted); font-weight:700; margin-bottom:10px; font-family:var(--font-mono);">Leg Structure</p>
                    ${legsHtml}
                </div>
                <div>
                    <p style="font-size:0.6rem; text-transform:uppercase; letter-spacing:0.15em; color:var(--color-text-muted); font-weight:700; margin-bottom:10px; font-family:var(--font-mono);">Trade Summary</p>
                    <div style="display:grid; grid-template-columns:1fr 1fr; gap:12px; font-family:var(--font-mono); font-size:0.82rem;">
                        <div>
                            <span style="color:var(--color-text-muted); font-size:0.62rem; display:block; text-transform:uppercase; letter-spacing:0.1em; font-weight:700;">Max Profit</span>
                            <span style="color:var(--accent-success-lt); font-weight:700; font-size:1rem;">+$${maxProfit.toFixed(0)}</span>
                        </div>
                        <div>
                            <span style="color:var(--color-text-muted); font-size:0.62rem; display:block; text-transform:uppercase; letter-spacing:0.1em; font-weight:700;">Max Loss</span>
                            <span style="color:var(--accent-danger); font-weight:700; font-size:1rem;">-$${maxLoss.toFixed(0)}</span>
                        </div>
                        <div>
                            <span style="color:var(--color-text-muted); font-size:0.62rem; display:block; text-transform:uppercase; letter-spacing:0.1em; font-weight:700;">Gate Score</span>
                            <span class="hd-score-badge ${scoreClass}">${score.toFixed(0)}</span>
                        </div>
                        <div>
                            <span style="color:var(--color-text-muted); font-size:0.62rem; display:block; text-transform:uppercase; letter-spacing:0.1em; font-weight:700;">Premium</span>
                            <span style="color:${premiumColor}; font-weight:700; font-size:1rem;">${isCredit ? '+' : ''}${cost.toFixed(2)}</span>
                        </div>
                    </div>
                </div>
                <div>
                    <p style="font-size:0.6rem; text-transform:uppercase; letter-spacing:0.15em; color:var(--color-text-muted); font-weight:700; margin-bottom:10px; font-family:var(--font-mono);">Pipeline Journey</p>
                    ${renderPipelineJourney(pipeline, strategyReasoning)}
                </div>
            </div>
        </div>`;
    }).join('');
}

function toggleTradeCard(index) {
    const card = document.getElementById(`trade-card-${index}`);
    const chevron = document.getElementById(`chevron-${index}`);
    if (!card) return;
    const isExpanded = card.classList.toggle('expanded');
    if (chevron) chevron.style.transform = isExpanded ? 'rotate(180deg)' : 'rotate(0)';
}
// ============================================================================
// PIPELINE JOURNEY RENDERER
// ============================================================================

function renderPipelineJourney(pipeline, strategyReasoning) {
    if (!pipeline) {
        return '<p style="color:var(--color-text-muted); font-size:0.78rem; font-family:var(--font-mono);">Pipeline data not available</p>';
    }

    const stageOrder = ['volatility', 'event', 'risk', 'gatekeeper', 'correlation'];
    const stageLabels = {
        volatility: 'Volatility',
        event: 'Event Check',
        risk: 'Risk Gate',
        gatekeeper: 'Gatekeeper',
        correlation: 'Correlation',
    };

    const stageIcons = {
        pass: `<svg style="width:14px;height:14px;stroke:var(--accent-green-lt);fill:none;stroke-width:2.5;flex-shrink:0;" viewBox="0 0 24 24"><polyline points="20 6 9 17 4 12"/></svg>`,
        fail: `<svg style="width:14px;height:14px;stroke:var(--accent-red);fill:none;stroke-width:2.5;flex-shrink:0;" viewBox="0 0 24 24"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>`,
        skip: `<svg style="width:14px;height:14px;stroke:var(--color-text-muted);fill:none;stroke-width:2;flex-shrink:0;" viewBox="0 0 24 24"><line x1="5" y1="12" x2="19" y2="12"/></svg>`,
    };

    const stagesHtml = stageOrder.map(key => {
        const stage = pipeline[key];
        if (!stage) return '';
        const status = stage.status || 'skip';
        const icon = stageIcons[status] || stageIcons.skip;
        const label = stageLabels[key] || key;
        const display = stage.display || '—';
        const labelColor = status === 'pass' ? 'var(--color-text-primary)' : status === 'fail' ? 'var(--accent-red)' : 'var(--color-text-muted)';

        return `
        <div style="display:flex; align-items:flex-start; gap:10px; padding:6px 0; border-bottom:1px solid var(--color-border-subtle);">
            <div style="margin-top:2px;">${icon}</div>
            <div style="flex:1; min-width:0;">
                <span style="font-family:var(--font-mono); font-size:0.65rem; font-weight:700; text-transform:uppercase; letter-spacing:0.1em; color:${labelColor};">${label}</span>
                <p style="margin:2px 0 0; font-family:var(--font-mono); font-size:0.72rem; color:var(--color-text-muted); line-height:1.4;">${display}</p>
            </div>
        </div>`;
    }).join('');

    const reasoningHtml = strategyReasoning
        ? `<div style="margin-top:12px; padding:8px; background:var(--accent-indigo-dim); border-radius:4px; border-left:2px solid var(--accent-indigo);">
            <span style="font-family:var(--font-mono); font-size:0.6rem; font-weight:700; text-transform:uppercase; letter-spacing:0.12em; color:var(--accent-indigo-hover); display:block; margin-bottom:3px;">Strategy Reasoning</span>
            <span style="font-family:var(--font-mono); font-size:0.72rem; color:var(--color-text-secondary);">${strategyReasoning.display || '—'}</span>
          </div>`
        : '';

    return `${stagesHtml}${reasoningHtml}`;
}

// ============================================================================
// VOLATILITY CONTEXT
// ============================================================================

function updateVolatilityContext(scanResult) {
    const volContext = scanResult.volatilityContext || {};
    const blockingEvents = scanResult.blockingEvents || [];

    // Current price from ticker
    const currentPrice = parseFloat(
        (document.getElementById('ticker-price')?.textContent || '').replace('$', '') || '0'
    ) || 500;

    const annualVol = volContext.annual_vol || 0.307;
    const dailyVol = volContext.daily_vol || 0.019;

    let ivRank = volContext.iv_rank;
    if (ivRank != null && ivRank > 0 && ivRank <= 1) ivRank = ivRank * 100;

    // Expected move (30 days)
    const days = 30;
    const move1sigma = currentPrice * annualVol * Math.sqrt(days / 365);
    const move2sigma = move1sigma * 2;
    const move1sigmaPercent = (move1sigma / currentPrice) * 100;
    const move2sigmaPercent = (move2sigma / currentPrice) * 100;

    safeSetText('vol-current-price', currentPrice.toFixed(2));
    safeSetText('vol-annual', (annualVol * 100).toFixed(1) + '%');
    safeSetText('vol-daily', (dailyVol * 100).toFixed(2) + '%');
    safeSetText('vol-iv-rank', ivRank != null ? ivRank.toFixed(0) + '%' : '—');
    safeSetText('vol-1sigma-range', `±$${move1sigma.toFixed(2)} (±${move1sigmaPercent.toFixed(1)}%)`);
    safeSetText('vol-1sigma-down', `$${(currentPrice - move1sigma).toFixed(2)} ↓`);
    safeSetText('vol-1sigma-up', `↑ $${(currentPrice + move1sigma).toFixed(2)}`);
    safeSetText('vol-2sigma-range', `±$${move2sigma.toFixed(2)} (±${move2sigmaPercent.toFixed(1)}%)`);
    safeSetText('vol-2sigma-down', `$${(currentPrice - move2sigma).toFixed(2)} ↓`);
    safeSetText('vol-2sigma-up', `↑ $${(currentPrice + move2sigma).toFixed(2)}`);

    // Event policy — derive from blockingEvents (no dedicated field from API)
    const hasTightEvent = blockingEvents.some(e => (e.days_until || 99) <= 1);
    const hasWarnEvent = blockingEvents.some(e => (e.days_until || 99) <= 14);
    const eventPolicy = hasTightEvent ? 'TIGHT' : hasWarnEvent ? 'WARN' : 'PLAY';

    const policyEl = document.getElementById('vol-event-policy');
    if (policyEl) {
        policyEl.textContent = eventPolicy;
        policyEl.style.color =
            eventPolicy === 'TIGHT' ? 'var(--accent-danger)' :
                eventPolicy === 'WARN' ? 'var(--accent-warning)' :
                    'var(--accent-success-lt)';
    }
}

// ============================================================================
// DECISION AUDIT
// ============================================================================

function populateDecisionAudit(scanResult) {
    const decisionLog = scanResult.decisionLog || {};

    // Symbol: use scan input as fallback (decisionLog.symbol not in API response)
    const symbol = document.getElementById('scan-symbol')?.value?.toUpperCase() || '—';
    safeSetText('audit-symbol', symbol);
    safeSetText('audit-regime', decisionLog.regime || '—');
    safeSetText('audit-strategy', (decisionLog.strategyHint || '—').replace(/_/g, ' '));

    const spyTrend = scanResult.spyTrend || '—';
    safeSetText('audit-spy-trend', spyTrend);
    const auditSpyEl = document.getElementById('audit-spy-trend');
    if (auditSpyEl) {
        auditSpyEl.style.color = spyTrend.toLowerCase().includes('up')
            ? 'var(--accent-success-lt)' : 'var(--accent-danger)';
    }

    // Full decision log text
    const logText = generateDecisionLogText(decisionLog, scanResult);
    const logContainer = document.getElementById('decision-log-container');
    if (logContainer) logContainer.textContent = logText;

    populateRejectionDetails(scanResult);
}

function generateDecisionLogText(decisionLog, scanResult) {
    const lines = [];
    const border = '═'.repeat(70);

    lines.push(border);
    lines.push('DECISION LOG: ' + (document.getElementById('scan-symbol')?.value?.toUpperCase() || 'UNKNOWN'));
    lines.push(border);
    lines.push('');
    lines.push('CONTEXT:');
    lines.push('  Regime:          ' + (decisionLog.regime || 'Unknown'));
    lines.push('  Strategy Hint:   ' + (decisionLog.strategyHint || 'None'));
    lines.push('  Blocking Events: ' + (decisionLog.blockingEvents || 'None'));
    lines.push('  SPY Trend:       ' + (scanResult.spyTrend || 'Unknown'));
    lines.push('  Policy Mode:     ' + (scanResult.policyMode || 'Unknown'));
    lines.push('');
    lines.push('CANDIDATES FLOW:');
    lines.push('  Generated:           ' + (decisionLog.generated || 0));
    lines.push('  After Risk Gate:     ' + (decisionLog.riskPassed || 0));
    lines.push('  After Gatekeeper:    ' + (decisionLog.gatekeeperPassed || 0));
    lines.push('  After Correlation:   ' + (decisionLog.correlationPassed || 0));
    lines.push('  Final Picks:         ' + (decisionLog.finalPicks || 0));
    lines.push('');

    const picks = scanResult.picks || [];
    if (picks.length > 0) {
        lines.push('TOP PICKS:');
        picks.forEach((pick, i) => {
            lines.push(`  ${i + 1}. ${(pick.strategy || '?').replace(/_/g, ' ')} on ${pick.symbol || '?'} (Exp: ${pick.expiration || '?'})`);
            lines.push(`     Premium: $${(pick.cost || 0).toFixed(2)} | Max Profit: $${(pick.max_profit || 0).toFixed(0)} | Max Loss: $${(pick.max_loss || 0).toFixed(0)} | Score: ${(pick.gatekeeper_score || 0).toFixed(0)}`);
        });
    } else {
        lines.push('No final picks generated');
    }

    lines.push('');
    lines.push(border);
    lines.push('Timestamp: ' + (decisionLog.timestamp || new Date().toISOString()));
    lines.push(border);

    return lines.join('\n');
}

function populateRejectionDetails(scanResult) {
    const rejections = scanResult.rejections || {};

    const riskRejList = document.getElementById('risk-rejections-list');
    const riskRejections = rejections.risk || [];
    if (riskRejList) {
        if (riskRejections.length === 0) {
            riskRejList.innerHTML = '<p style="color:var(--color-text-muted);">No rejections</p>';
        } else {
            riskRejList.innerHTML = riskRejections.map(rej => `
                <div style="margin-bottom:8px; padding:8px; background:rgba(248,113,113,0.08); border-left:2px solid var(--accent-danger); border-radius:2px; font-size:0.8rem;">
                    <strong>${rej.candidate?.symbol || '?'}</strong> — ${formatRejectionReason(rej.reason || 'Unknown')}
                </div>`).join('');
        }
    }

    const gkRejList = document.getElementById('gatekeeper-rejections-list');
    const gkRejections = rejections.gatekeeper || [];
    if (gkRejList) {
        if (gkRejections.length === 0) {
            gkRejList.innerHTML = '<p style="color:var(--color-text-muted);">No rejections</p>';
        } else {
            gkRejList.innerHTML = gkRejections.map(rej => `
                <div style="margin-bottom:8px; padding:8px; background:rgba(245,158,11,0.08); border-left:2px solid var(--accent-warning); border-radius:2px; font-size:0.8rem;">
                    <strong>${rej.candidate?.symbol || '?'}</strong> (Score: ${(rej.score || 0).toFixed(1)})<br>
                    <small>${formatRejectionReason(rej.reason || 'Unknown')}</small>
                </div>`).join('');
        }
    }
}

// ============================================================================
// PORTFOLIO & RISK
// ============================================================================

async function loadPortfolioRisk() {
    try {
        const response = await fetch(`${API_BASE}/api/portfolio/risk`);
        const data = await response.json();

        if (data.error) {
            console.error('Portfolio risk error:', data.error);
            return;
        }

        // Capital utilization
        const capital = data.total_capital_at_risk || 0;
        const maxRisk = data.max_risk_per_trade || 1000;
        const capitalPct = Math.min(Math.round((capital / (maxRisk * 10)) * 100), 100);

        safeSetText('capital-util', `$${capital.toLocaleString()}`);
        safeSetText('port-delta', `${(data.net_delta || 0) >= 0 ? '+' : ''}${data.net_delta || 0}`);

        // P&L — handle negative float properly
        const dd = data.daily_drawdown || 0;
        const ddSign = dd >= 0 ? '+' : '-';
        const ddEl = document.getElementById('port-pnl');
        if (ddEl) {
            ddEl.textContent = `${ddSign}$${Math.abs(dd).toFixed(0)}`;
            ddEl.className = `hd-metric-value ${dd < 0 ? 'negative' : ''}`;
        }

        // Portfolio Greeks
        safeSetText('port-greeks', `${data.net_vega || '—'} / +${data.net_theta || '—'}`);

        // Capital fill bar
        const fillEl = document.getElementById('capital-fill');
        if (fillEl) fillEl.style.width = `${capitalPct}%`;

        // Wire to dashboard metric strip
        const netDeltaEl = document.getElementById('net-delta');
        if (netDeltaEl) netDeltaEl.textContent = `${(data.net_delta || 0) >= 0 ? '+' : ''}${data.net_delta || 0}`;

        const dailyDdEl = document.getElementById('daily-dd');
        if (dailyDdEl) {
            dailyDdEl.textContent = `${ddSign}$${Math.abs(dd).toFixed(0)}`;
            dailyDdEl.className = `hd-metric-value ${dd < 0 ? 'negative' : ''}`;
        }

        safeSetText('capital-used', `${capitalPct}%`);

        const pnlTodayEl = document.getElementById('pnl-today');
        if (pnlTodayEl) {
            pnlTodayEl.textContent = `${ddSign}$${Math.abs(dd).toFixed(0)}`;
            pnlTodayEl.className = `hd-metric-value ${dd < 0 ? 'negative' : ''}`;
        }

        // Sector chart
        updateSectorChart(data.sector_exposure || []);

        // Risk alerts
        displayRiskAlerts(data.alerts || []);

        // Active positions
        updateActivePositions();

        // Log alerts
        (data.alerts || []).forEach(alert => {
            addLiveFeedEntry(`[${(alert.type || '').toUpperCase()}] ${alert.message}`,
                alert.severity === 'critical' ? 'error' : 'warning');
        });

    } catch (err) {
        console.error('Portfolio risk load failed:', err);
    }
}

function updateSectorChart(sectors) {
    const chart = document.getElementById('sector-chart');
    if (!chart) return;

    const colorMap = {
        Technology: 'var(--accent-danger)',
        Finance: 'var(--accent-success-lt)',
        Healthcare: 'var(--accent-indigo)',
        Energy: 'var(--accent-warning)',
    };

    chart.innerHTML = sectors.map(sector => {
        const pct = (sector.value || 0) * 100;
        const color = colorMap[sector.name] || 'var(--accent-indigo)';
        return `
        <div class="sector-bar" style="--pct: ${pct.toFixed(1)}%; --color: ${color};">
            <span class="sector-name">${sector.name}</span>
            <span class="sector-value">${pct.toFixed(0)}%</span>
        </div>`;
    }).join('');
}

function displayRiskAlerts(alerts) {
    const container = document.getElementById('risk-alerts-container');
    if (!container) return;

    if (alerts.length === 0) {
        container.innerHTML = '<p style="color:var(--color-text-muted); padding:16px; font-size:0.85rem;">No critical alerts</p>';
        return;
    }

    container.innerHTML = alerts.map(alert => `
        <div style="padding:10px 14px; margin-bottom:6px; border-left:3px solid ${alert.severity === 'critical' ? 'var(--accent-danger)' : 'var(--accent-warning)'}; background:rgba(0,0,0,0.2); border-radius:3px;">
            <div style="font-weight:700; font-size:0.8rem; margin-bottom:3px; color:${alert.severity === 'critical' ? 'var(--accent-danger)' : 'var(--accent-warning)'};">
                ${alert.severity === 'critical' ? 'CRITICAL' : 'WARNING'} — ${(alert.type || '').toUpperCase()}
            </div>
            <div style="color:var(--color-text-main); font-size:0.85rem; margin-bottom:3px;">${alert.message || ''}</div>
            <div style="color:var(--color-text-muted); font-size:0.78rem;">${alert.recommendation || ''}</div>
        </div>`).join('');
}

function updateActivePositions() {
    const tbody = document.getElementById('positions-table-body');
    if (!tbody) return;

    // Positions table uses mock data — no dedicated positions endpoint
    const positions = [
        { symbol: 'AAPL', strategy: 'Bull Call Spread', quantity: 2, costBasis: 250, mark: 285, pnl: 70, daysHeld: 12, greeks: { delta: 0.65, gamma: 0.12, theta: -0.08, vega: -0.15 } },
        { symbol: 'NVDA', strategy: 'Short Call Spread', quantity: 3, costBasis: 180, mark: 162, pnl: 54, daysHeld: 8, greeks: { delta: -0.45, gamma: -0.08, theta: 0.18, vega: -0.25 } },
        { symbol: 'JPM', strategy: 'Iron Condor', quantity: 1, costBasis: 150, mark: 155, pnl: 5, daysHeld: 5, greeks: { delta: 0.05, gamma: -0.02, theta: 0.25, vega: -0.30 } },
        { symbol: 'UNH', strategy: 'Put Credit Spread', quantity: 2, costBasis: 120, mark: 110, pnl: 20, daysHeld: 4, greeks: { delta: 0.15, gamma: -0.05, theta: 0.12, vega: -0.10 } },
        { symbol: 'XOM', strategy: 'Covered Call', quantity: 1, costBasis: 120, mark: 105, pnl: -15, daysHeld: 15, greeks: { delta: 0.40, gamma: 0.05, theta: -0.02, vega: 0.10 } },
    ];

    tbody.innerHTML = positions.map(pos => {
        const pnlClass = pos.pnl >= 0 ? 'text-success' : 'text-danger';
        const pnlSign = pos.pnl >= 0 ? '+' : '';
        return `
        <tr>
            <td class="text-mono-small"><strong>${pos.symbol}</strong></td>
            <td class="text-muted">${pos.strategy}</td>
            <td class="text-mono-small">${pos.quantity}</td>
            <td class="text-mono-small">$${pos.costBasis.toFixed(2)}</td>
            <td class="text-mono-small">$${pos.mark.toFixed(2)}</td>
            <td class="text-mono-small ${pnlClass}"><strong>${pnlSign}$${Math.abs(pos.pnl).toFixed(0)}</strong></td>
            <td class="text-mono-small">${pos.daysHeld}d</td>
            <td class="text-mono-small" style="font-size:0.72rem;">
                ${pos.greeks.delta.toFixed(2)}/${pos.greeks.gamma.toFixed(2)}/${pos.greeks.theta.toFixed(2)}/${pos.greeks.vega.toFixed(2)}
            </td>
        </tr>`;
    }).join('');
}

// ============================================================================
// CORRELATION MATRIX
// ============================================================================

function generateCorrelationMatrix() {
    const symbols = ['AAPL', 'NVDA', 'JPM', 'UNH', 'XOM'];
    const matrix = document.getElementById('correlation-matrix');
    if (!matrix) return;

    const correlationData = [
        [1.0, 0.72, 0.65, 0.78, 0.45],
        [0.72, 1.0, 0.68, 0.81, 0.42],
        [0.65, 0.68, 1.0, 0.75, 0.38],
        [0.78, 0.81, 0.75, 1.0, 0.50],
        [0.45, 0.42, 0.38, 0.50, 1.0],
    ];

    let html = '<div style="grid-column:1/-1; display:grid; grid-template-columns:repeat(5,1fr); gap:3px;">';
    symbols.forEach(sym => {
        html += `<div style="text-align:center; font-size:0.62rem; font-weight:700; color:var(--color-text-muted); padding:3px; font-family:var(--font-mono);">${sym}</div>`;
    });
    html += '</div>';

    correlationData.forEach((row, i) => {
        row.forEach((corr, j) => {
            let bg, color;
            if (corr > 0.7) { bg = 'rgba(248,113,113,0.25)'; color = 'var(--accent-danger)'; }
            else if (corr > 0.5) { bg = 'rgba(245,158,11,0.18)'; color = 'var(--accent-warning)'; }
            else if (corr < -0.4) { bg = 'rgba(52,211,153,0.2)'; color = 'var(--accent-success-lt)'; }
            else if (corr === 1.0) { bg = 'var(--bg-surface-light)'; color = 'var(--color-text-muted)'; }
            else { bg = 'var(--bg-surface)'; color = 'var(--color-text-muted)'; }

            html += `
            <div style="background:${bg}; border:1px solid var(--color-border); border-radius:2px; padding:4px; text-align:center; font-family:var(--font-mono); font-size:0.65rem; color:${color}; cursor:pointer; transition:opacity 0.1s;" title="${symbols[i]} vs ${symbols[j]}: ${corr.toFixed(2)}">
                ${corr.toFixed(2)}
            </div>`;
        });
    });

    matrix.innerHTML = html;
}

// ============================================================================
// INITIAL DATA LOADING
// ============================================================================

function loadInitialData() {
    console.log('📊 Loading initial data...');
    loadPortfolioRisk();
    generateCorrelationMatrix();
    updateTicker();
}

// ============================================================================
// PERIODIC UPDATES
// ============================================================================

function startPeriodicUpdates() {
    setInterval(updateTicker, TICKER_UPDATE_INTERVAL);

    setInterval(() => {
        if (appState.currentView === 'portfolio') loadPortfolioRisk();
    }, 10000);
}

console.log('✅ App.js loaded and ready');
