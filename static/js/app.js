// SqueezeSeeker Trading Dashboard - Open Claw V4 Integration
// AI Analyst Partnership Interface - 4-View Tab System

let portfolioChart = null;
let stockChart = null;
let confidenceRingChart = null;
let currentSymbol = null;
let currentPrice = 0;
let thesisData = {};
let positionsData = [];
let ordersData = [];
let accountData = {};
let approvalQueueData = [];
let learningData = {};
let currentSort = { column: 'market_value', direction: 'desc' };
let tradeSide = 'buy';
let tradeOrderBy = 'shares';
let activeView = 'command-center';
let scannerOnline = false;

// =============================================
// INITIALIZATION
// =============================================
document.addEventListener('DOMContentLoaded', async () => {
    setupEventListeners();
    await loadDashboard();

    // Refresh data every 30 seconds - only active view
    setInterval(() => {
        loadDashboard();
    }, 30000);
});

// =============================================
// VIEW SYSTEM
// =============================================
function switchView(viewName) {
    if (viewName === activeView) return;

    // Update tabs
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.view === viewName);
    });

    // Update view containers
    document.querySelectorAll('.view').forEach(view => {
        view.classList.remove('active');
    });

    const targetView = document.getElementById('view-' + viewName);
    if (targetView) {
        targetView.classList.add('active');
    }

    activeView = viewName;
    onViewActivated(viewName);
}

function onViewActivated(viewName) {
    switch (viewName) {
        case 'command-center':
            loadCommandCenter();
            break;
        case 'portfolio':
            loadAccount();
            loadPositions();
            loadThesis();
            break;
        case 'research':
            loadScannerStatus();
            loadScannerResults();
            loadApprovalQueue();
            loadRejectedPicks();
            break;
        case 'brain':
            loadLearning();
            break;
    }
}

// =============================================
// EVENT LISTENERS
// =============================================
function setupEventListeners() {
    // Tab clicks
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            switchView(tab.dataset.view);
        });
    });

    // Search
    const searchBtn = document.getElementById('searchBtn');
    const searchInput = document.getElementById('stockSearch');
    searchBtn.addEventListener('click', handleSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });

    // Analysis modal close
    document.getElementById('modalClose').addEventListener('click', () => {
        document.getElementById('analysisModal').classList.remove('active');
    });

    // Trade modal close
    document.getElementById('tradeModalClose').addEventListener('click', () => {
        document.getElementById('tradeModal').classList.remove('active');
    });

    // Modal buy/sell buttons
    document.getElementById('modalBuyBtn').addEventListener('click', () => {
        showTradeModal(currentSymbol, currentPrice, 'buy');
    });
    document.getElementById('modalSellBtn').addEventListener('click', () => {
        showTradeModal(currentSymbol, currentPrice, 'sell');
    });

    // Confirm trade
    document.getElementById('confirmTradeBtn').addEventListener('click', handleTrade);

    // Side toggle (Buy/Sell)
    document.querySelectorAll('#sideToggle .toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#sideToggle .toggle-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            tradeSide = btn.dataset.value;
            updateTradeUI();
        });
    });

    // Order-by toggle (Shares/Dollars)
    document.querySelectorAll('#orderByToggle .toggle-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#orderByToggle .toggle-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            tradeOrderBy = btn.dataset.value;
            document.getElementById('sharesGroup').style.display = tradeOrderBy === 'shares' ? '' : 'none';
            document.getElementById('dollarsGroup').style.display = tradeOrderBy === 'dollars' ? '' : 'none';
            updateTradeEstimate();
        });
    });

    document.getElementById('tradeShares').addEventListener('input', updateTradeEstimate);
    document.getElementById('tradeDollars').addEventListener('input', updateTradeEstimate);

    // Sortable column headers
    document.querySelectorAll('.positions-table th.sortable').forEach(th => {
        th.addEventListener('click', () => {
            const column = th.dataset.sort;
            if (currentSort.column === column) {
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            } else {
                currentSort.column = column;
                currentSort.direction = column === 'symbol' ? 'asc' : 'desc';
            }
            renderPositions();
            updateSortArrows();
        });
    });

    // Thesis panel close
    document.getElementById('thesisPanelClose').addEventListener('click', () => {
        document.getElementById('thesisPanel').style.display = 'none';
    });

    // Modal backdrop click
    document.getElementById('analysisModal').addEventListener('click', (e) => {
        if (e.target.id === 'analysisModal') {
            document.getElementById('analysisModal').classList.remove('active');
        }
    });
    document.getElementById('tradeModal').addEventListener('click', (e) => {
        if (e.target.id === 'tradeModal') {
            document.getElementById('tradeModal').classList.remove('active');
        }
    });

    // Orders slide panel
    document.getElementById('ordersSlideClose').addEventListener('click', closeOrdersPanel);
    document.getElementById('ordersSlideBackdrop').addEventListener('click', closeOrdersPanel);
}

// =============================================
// DASHBOARD LOADER (View-Aware)
// =============================================
async function loadDashboard() {
    try {
        // Always load account + positions + thesis + scanner status (shared data)
        const promises = [
            loadAccount(),
            loadPositions(),
            loadThesis(),
            loadScannerStatus(),
            loadOrders()
        ];

        // Load view-specific data
        switch (activeView) {
            case 'command-center':
                promises.push(loadScannerResults());
                promises.push(loadApprovalQueueBadge());
                promises.push(loadCCConfidence());
                break;
            case 'research':
                promises.push(loadScannerResults());
                promises.push(loadApprovalQueue());
                promises.push(loadRejectedPicks());
                break;
            case 'brain':
                promises.push(loadLearning());
                break;
        }

        await Promise.all(promises);

        // Populate Command Center if active
        if (activeView === 'command-center') {
            loadCommandCenter();
        }
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showToast('Error loading dashboard data', 'error');
    }
}

// =============================================
// COMMAND CENTER (View 1)
// =============================================
function loadCommandCenter() {
    loadCCPortfolioStrip();
    loadCCActions();
    loadCCTopPositions();
    loadCCOrders();
    loadCCScannerHighlights();
}

function loadCCPortfolioStrip() {
    if (!accountData.portfolio_value) return;

    document.getElementById('ccPortfolioValue').textContent = formatCurrency(accountData.portfolio_value);
    document.getElementById('ccBuyingPower').textContent = formatCurrency(accountData.buying_power);
    document.getElementById('ccCash').textContent = formatCurrency(accountData.cash);
    document.getElementById('ccPositionCount').textContent = positionsData.length;

    const lastEquity = accountData.last_equity || accountData.portfolio_value;
    const dailyChange = accountData.portfolio_value - lastEquity;
    const dailyChangePercent = lastEquity > 0 ? (dailyChange / lastEquity) * 100 : 0;

    const changeEl = document.getElementById('ccPortfolioChange');
    changeEl.querySelector('.cc-change-amount').textContent = formatCurrency(dailyChange);
    changeEl.querySelector('.cc-change-percent').textContent = `(${dailyChangePercent >= 0 ? '+' : ''}${dailyChangePercent.toFixed(2)}%)`;

    if (dailyChange < 0) {
        changeEl.classList.add('negative');
    } else {
        changeEl.classList.remove('negative');
    }
}

function loadCCActions() {
    const list = document.getElementById('ccActionsList');
    const actions = [];

    // Pending approvals
    if (approvalQueueData.length > 0) {
        actions.push({
            icon: '\u{1F4CB}',
            text: 'Pending approvals',
            count: approvalQueueData.length,
            countClass: 'warning',
            onClick: () => switchView('research')
        });
    }

    // Broken theses
    const brokenTheses = Object.values(thesisData).filter(t => t.validation_status === 'broken');
    if (brokenTheses.length > 0) {
        actions.push({
            icon: '\u{1F6A8}',
            text: 'Broken theses',
            count: brokenTheses.length,
            countClass: 'danger',
            onClick: () => switchView('portfolio')
        });
    }

    // Watch theses
    const watchTheses = Object.values(thesisData).filter(t => t.validation_status === 'watch');
    if (watchTheses.length > 0) {
        actions.push({
            icon: '\u{26A0}',
            text: 'Theses to watch',
            count: watchTheses.length,
            countClass: 'warning',
            onClick: () => switchView('portfolio')
        });
    }

    // Pending orders
    if (ordersData.length > 0) {
        actions.push({
            icon: '\u{23F3}',
            text: 'Open orders',
            count: ordersData.length,
            countClass: '',
            onClick: openOrdersPanel
        });
    }

    if (actions.length === 0) {
        list.innerHTML = '<div class="cc-action-empty">No pending actions</div>';
        return;
    }

    list.innerHTML = actions.map(a => `
        <div class="cc-action-item" onclick="(${a.onClick.toString()})()">
            <span class="cc-action-icon">${a.icon}</span>
            <span class="cc-action-text">${a.text}</span>
            <span class="cc-action-count ${a.countClass}">${a.count}</span>
        </div>
    `).join('');
}

async function loadCCConfidence() {
    try {
        const response = await fetch('/api/learning/performance');
        const perf = await response.json();

        if (perf.error || perf.offline) {
            document.getElementById('ccConfidenceCenter').textContent = '--%';
            return;
        }

        learningData = perf;
        const winRate = perf.overall_win_rate || 0;
        document.getElementById('ccConfidenceCenter').textContent = `${winRate.toFixed(0)}%`;
        document.getElementById('ccConfTrades').textContent = perf.total_trades || 0;
        document.getElementById('ccConfReturn').textContent = `${(perf.avg_return || 0).toFixed(1)}%`;

        renderConfidenceRing(winRate);
    } catch (error) {
        console.error('Error loading confidence:', error);
    }
}

function renderConfidenceRing(winRate) {
    const ctx = document.getElementById('confidenceRingChart');
    if (!ctx) return;

    if (confidenceRingChart) {
        confidenceRingChart.destroy();
    }

    const rate = Math.max(0, Math.min(100, winRate));
    const remaining = 100 - rate;

    confidenceRingChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            datasets: [{
                data: [rate, remaining],
                backgroundColor: [
                    rate >= 60 ? '#00c805' : rate >= 40 ? '#f59e0b' : '#ff5000',
                    '#e6e9eb'
                ],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '75%',
            plugins: {
                legend: { display: false },
                tooltip: { enabled: false }
            }
        }
    });
}

function loadCCTopPositions() {
    const container = document.getElementById('ccTopPositions');

    if (positionsData.length === 0) {
        container.innerHTML = '<div class="cc-action-empty">No positions yet</div>';
        return;
    }

    // Top 3 by market value
    const top3 = [...positionsData]
        .sort((a, b) => parseFloat(b.market_value || 0) - parseFloat(a.market_value || 0))
        .slice(0, 3);

    container.innerHTML = top3.map(pos => {
        const pl = parseFloat(pos.unrealized_pl || 0);
        const plpc = parseFloat(pos.unrealized_plpc || 0);
        const thesis = thesisData[pos.symbol];
        const validationIcon = getThesisValidationIcon(thesis);

        return `
            <div class="cc-position-row">
                <div class="cc-pos-left">
                    <span class="cc-pos-symbol">${pos.symbol}</span>
                    <span class="cc-pos-thesis-icon">${validationIcon}</span>
                </div>
                <div class="cc-pos-right">
                    <span class="cc-pos-value">${formatCurrency(parseFloat(pos.market_value))}</span>
                    <span class="cc-pos-change ${pl >= 0 ? 'positive' : 'negative'}">${pl >= 0 ? '+' : ''}${plpc.toFixed(2)}%</span>
                </div>
            </div>
        `;
    }).join('');
}

function loadCCScannerHighlights() {
    const container = document.getElementById('ccScannerHighlights');

    if (!scannerOnline) {
        container.innerHTML = '<div class="cc-action-empty">Scanner offline</div>';
        return;
    }

    // Try to use cached scanner data
    const grid = document.getElementById('candidatesGrid');
    const candidateCards = grid ? grid.querySelectorAll('.candidate-card') : [];

    if (candidateCards.length === 0) {
        container.innerHTML = '<div class="cc-action-empty">No scanner picks today</div>';
        return;
    }

    // We need to re-fetch or use stored data - use loadScannerResults result
    loadScannerHighlightsFromAPI();
}

async function loadScannerHighlightsFromAPI() {
    try {
        const response = await fetch('/api/scanner/results');
        const data = await response.json();
        const candidates = data.candidates || [];
        const container = document.getElementById('ccScannerHighlights');

        if (candidates.length === 0) {
            container.innerHTML = '<div class="cc-action-empty">No scanner picks today</div>';
            return;
        }

        // Top S/A tier or top 3 by score
        const highlights = candidates
            .filter(c => c.tier === 'S' || c.tier === 'A')
            .sort((a, b) => (b.total_score || 0) - (a.total_score || 0))
            .slice(0, 3);

        if (highlights.length === 0) {
            // Fall back to top 3 by score
            highlights.push(...candidates.sort((a, b) => (b.total_score || 0) - (a.total_score || 0)).slice(0, 3));
        }

        container.innerHTML = highlights.map(c => `
            <div class="cc-highlight-card" onclick="viewStock('${c.symbol}')">
                <div class="cc-hl-left">
                    <span class="cc-hl-symbol">${c.symbol}</span>
                    <span class="cc-hl-tier tier-${(c.tier || 'c').toLowerCase()}">${c.tier || 'C'}</span>
                </div>
                <span class="cc-hl-score">${(c.total_score || 0).toFixed(1)}/100</span>
            </div>
        `).join('');
    } catch (error) {
        console.error('Error loading scanner highlights:', error);
    }
}

function loadCCOrders() {
    const container = document.getElementById('ccOrders');

    if (ordersData.length === 0) {
        container.innerHTML = '<div class="cc-action-empty">No pending orders</div>';
        return;
    }

    container.innerHTML = ordersData.slice(0, 3).map(order => {
        const side = order.side.toUpperCase();
        return `
            <div class="cc-order-row ${order.side}">
                <span class="cc-order-symbol">${order.symbol}</span>
                <span class="cc-order-details">${side} ${order.qty} @ Market</span>
            </div>
        `;
    }).join('');
}

// =============================================
// APPROVAL QUEUE (View 3 - Key Feature)
// =============================================
async function loadApprovalQueue() {
    try {
        const response = await fetch('/api/approval/queue');
        const data = await response.json();

        if (data.error || data.offline) {
            renderApprovalQueueOffline();
            return;
        }

        approvalQueueData = data.queue || data.candidates || [];
        renderApprovalQueue();
        loadApprovalQueueBadge();
    } catch (error) {
        console.error('Error loading approval queue:', error);
        renderApprovalQueueOffline();
    }
}

function renderApprovalQueueOffline() {
    const container = document.getElementById('approvalQueue');
    container.innerHTML = `
        <div class="approval-offline">
            Approval system offline - scanner results still available below
        </div>
    `;
    approvalQueueData = [];
    loadApprovalQueueBadge();
}

function renderApprovalQueue() {
    const container = document.getElementById('approvalQueue');

    if (approvalQueueData.length === 0) {
        container.innerHTML = `
            <div class="approval-empty" id="approvalEmpty">
                <div class="approval-empty-icon">\u2705</div>
                <h3>Queue clear</h3>
                <p>No picks pending your review. Open Claw will queue new picks when the scanner finds candidates.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = approvalQueueData.map((item, idx) => {
        const tier = item.tier || 'C';
        const score = item.total_score || item.score || 0;
        const reasoning = item.reasoning || item.thesis || 'No reasoning provided';
        const price = item.price || 0;
        const breakdown = item.score_breakdown || {};

        return `
            <div class="approval-card" id="approval-card-${idx}">
                <div class="approval-card-header">
                    <div>
                        <div class="approval-card-symbol">${item.symbol}</div>
                        <div class="approval-card-price">$${price.toFixed(2)}</div>
                    </div>
                    <span class="approval-card-tier tier-${tier.toLowerCase()}">${tier}-Tier</span>
                </div>
                <div class="approval-reasoning">${reasoning}</div>
                ${renderScoreBreakdown(breakdown, score)}
                <textarea class="approval-notes" id="approval-notes-${idx}" placeholder="Optional notes (why you approve/reject)..." rows="2"></textarea>
                <div class="approval-actions">
                    <button class="btn-approve" onclick="approveCandidate(${idx})">Approve</button>
                    <button class="btn-reject" onclick="rejectCandidate(${idx})">Reject</button>
                    <button class="btn-approve-buy" onclick="approveAndBuy(${idx})">Approve + Buy</button>
                </div>
            </div>
        `;
    }).join('');
}

function renderScoreBreakdown(breakdown, totalScore) {
    const components = Object.entries(breakdown);
    if (components.length === 0 && totalScore > 0) {
        // Show just the total as a single bar
        return `
            <div class="approval-score-breakdown">
                <div class="bd-row">
                    <span class="bd-label">Total</span>
                    <div class="bd-bar"><div class="bd-fill ${totalScore >= 70 ? 'high' : totalScore >= 40 ? 'medium' : 'low'}" style="width:${Math.min(totalScore, 100)}%"></div></div>
                    <span class="bd-value">${totalScore.toFixed(0)}</span>
                </div>
            </div>
        `;
    }

    if (components.length === 0) return '';

    return `
        <div class="approval-score-breakdown">
            ${components.map(([key, value]) => {
                const numVal = typeof value === 'number' ? value : parseFloat(value) || 0;
                const maxVal = key === 'vigl_bonus' ? 20 : 30;
                const pct = Math.min((numVal / maxVal) * 100, 100);
                const level = pct >= 66 ? 'high' : pct >= 33 ? 'medium' : 'low';
                const label = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());

                return `
                    <div class="bd-row">
                        <span class="bd-label">${label}</span>
                        <div class="bd-bar"><div class="bd-fill ${level}" style="width:${pct}%"></div></div>
                        <span class="bd-value">${numVal.toFixed(0)}</span>
                    </div>
                `;
            }).join('')}
        </div>
    `;
}

async function approveCandidate(idx) {
    const item = approvalQueueData[idx];
    if (!item) return;

    const notes = document.getElementById(`approval-notes-${idx}`)?.value || '';

    try {
        const response = await fetch('/api/approval/decide', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: item.symbol,
                decision: 'approve',
                notes: notes,
                price_at_decision: item.price
            })
        });

        const result = await response.json();

        if (result.error || result.offline) {
            showToast('Approval system offline - decision not recorded', 'error');
            return;
        }

        showToast(`Approved ${item.symbol}`, 'success');
        removeFromApprovalQueue(idx);
    } catch (error) {
        showToast('Error submitting approval', 'error');
    }
}

async function rejectCandidate(idx) {
    const item = approvalQueueData[idx];
    if (!item) return;

    const notes = document.getElementById(`approval-notes-${idx}`)?.value || '';

    try {
        const response = await fetch('/api/approval/decide', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: item.symbol,
                decision: 'reject',
                notes: notes,
                price_at_decision: item.price
            })
        });

        const result = await response.json();

        if (result.error || result.offline) {
            showToast('Approval system offline - decision not recorded', 'error');
            return;
        }

        showToast(`Rejected ${item.symbol}`, 'info');
        removeFromApprovalQueue(idx);
    } catch (error) {
        showToast('Error submitting rejection', 'error');
    }
}

async function approveAndBuy(idx) {
    const item = approvalQueueData[idx];
    if (!item) return;

    const notes = document.getElementById(`approval-notes-${idx}`)?.value || '';

    // First approve
    try {
        await fetch('/api/approval/decide', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                symbol: item.symbol,
                decision: 'approve',
                notes: notes,
                price_at_decision: item.price
            })
        });
    } catch (e) {
        // Continue even if approval recording fails
    }

    removeFromApprovalQueue(idx);

    // Then show trade modal
    showTradeModal(item.symbol, item.price || 0, 'buy');
}

function removeFromApprovalQueue(idx) {
    approvalQueueData.splice(idx, 1);
    renderApprovalQueue();
    loadApprovalQueueBadge();
    loadCCActions();
}

async function loadApprovalQueueBadge() {
    const badge = document.getElementById('approvalBadge');
    if (!badge) return;

    // If we already have data, use it
    if (approvalQueueData.length > 0) {
        badge.textContent = approvalQueueData.length;
        badge.style.display = '';
        return;
    }

    // Try fetching if we don't have data yet
    try {
        const response = await fetch('/api/approval/queue');
        const data = await response.json();

        if (data.error || data.offline) {
            badge.style.display = 'none';
            return;
        }

        const queue = data.queue || data.candidates || [];
        if (queue.length > 0) {
            approvalQueueData = queue;
            badge.textContent = queue.length;
            badge.style.display = '';
        } else {
            badge.style.display = 'none';
        }
    } catch (error) {
        badge.style.display = 'none';
    }
}

// =============================================
// REJECTED PICKS (View 3)
// =============================================
async function loadRejectedPicks() {
    try {
        const response = await fetch('/api/approval/history?status=rejected');
        const data = await response.json();

        if (data.error || data.offline) {
            renderRejectedPicksEmpty();
            return;
        }

        const rejected = data.decisions || data.history || [];
        renderRejectedPicks(rejected);
    } catch (error) {
        renderRejectedPicksEmpty();
    }
}

function renderRejectedPicksEmpty() {
    document.getElementById('rejectedPicksBody').innerHTML =
        '<tr><td colspan="6" class="rejected-empty">No rejection history available</td></tr>';
    document.getElementById('rejectedSummaryStats').innerHTML = '';
}

function renderRejectedPicks(rejected) {
    const tbody = document.getElementById('rejectedPicksBody');
    const statsContainer = document.getElementById('rejectedSummaryStats');

    if (!rejected || rejected.length === 0) {
        renderRejectedPicksEmpty();
        return;
    }

    // Summary stats
    const totalRejected = rejected.length;
    const wouldHaveWon = rejected.filter(r => (r.would_be_return || 0) > 0).length;
    const avgMissedReturn = rejected.reduce((sum, r) => sum + (r.would_be_return || 0), 0) / totalRejected;

    statsContainer.innerHTML = `
        <div class="rejected-stat">
            <span class="rejected-stat-label">Total Rejected:</span>
            <span class="rejected-stat-value">${totalRejected}</span>
        </div>
        <div class="rejected-stat">
            <span class="rejected-stat-label">Would Have Won:</span>
            <span class="rejected-stat-value">${wouldHaveWon}/${totalRejected}</span>
        </div>
        <div class="rejected-stat">
            <span class="rejected-stat-label">Avg Missed Return:</span>
            <span class="rejected-stat-value ${avgMissedReturn > 0 ? 'rejected-wouldbe-positive' : ''}">${avgMissedReturn >= 0 ? '+' : ''}${avgMissedReturn.toFixed(1)}%</span>
        </div>
    `;

    tbody.innerHTML = rejected.map(r => {
        const wouldBe = r.would_be_return || 0;
        const wouldBeClass = wouldBe > 0 ? 'rejected-wouldbe-positive' : 'rejected-wouldbe-negative';

        return `
            <tr>
                <td><strong>${r.symbol}</strong></td>
                <td>${r.rejected_date ? formatTimeAgo(r.rejected_date) : '--'}</td>
                <td>${r.price_at_decision ? '$' + r.price_at_decision.toFixed(2) : '--'}</td>
                <td>${r.current_price ? '$' + r.current_price.toFixed(2) : '--'}</td>
                <td class="${wouldBeClass}">${wouldBe >= 0 ? '+' : ''}${wouldBe.toFixed(1)}%</td>
                <td>${r.notes || '--'}</td>
            </tr>
        `;
    }).join('');
}

// =============================================
// THESIS VALIDATION
// =============================================
function getThesisValidationIcon(thesis) {
    if (!thesis) return '<span class="thesis-validation-icon unknown" title="No thesis data">\u{2B1C}</span>';

    const status = thesis.validation_status;
    switch (status) {
        case 'working':
            return '<span class="thesis-validation-icon working" title="Thesis working">\u2705</span>';
        case 'watch':
            return '<span class="thesis-validation-icon watch" title="Thesis needs watching">\u26A0\uFE0F</span>';
        case 'broken':
            return '<span class="thesis-validation-icon broken" title="Thesis broken">\u274C</span>';
        default:
            return '<span class="thesis-validation-icon unknown" title="Validation pending">\u{2B1C}</span>';
    }
}

// =============================================
// BRAIN / LEARNING INSIGHTS (View 4)
// =============================================
function renderBrainInsights(perf) {
    // Hero stats
    document.getElementById('brainWinRate').textContent = `${(perf.overall_win_rate || 0).toFixed(0)}%`;
    document.getElementById('brainAvgReturn').textContent = `${(perf.avg_return || 0).toFixed(1)}%`;
    document.getElementById('brainTotalTrades').textContent = perf.total_trades || 0;
    document.getElementById('brainAvgHold').textContent = (perf.avg_hold_days || 0).toFixed(1);

    // What's Working / What's NOT
    const workingContainer = document.getElementById('brainWorking');
    const notWorkingContainer = document.getElementById('brainNotWorking');

    // Generate insights from performance data
    const workingInsights = [];
    const notWorkingInsights = [];

    const scoreRanges = perf.by_score_range || {};
    const viglPatterns = perf.by_vigl_pattern || {};

    // Analyze score ranges
    Object.entries(scoreRanges).forEach(([range, stats]) => {
        if (stats.win_rate >= 65 && stats.total_trades >= 3) {
            workingInsights.push(`Score range ${range}: ${stats.win_rate.toFixed(0)}% win rate across ${stats.total_trades} trades`);
        } else if (stats.win_rate < 40 && stats.total_trades >= 3) {
            notWorkingInsights.push(`Score range ${range}: Only ${stats.win_rate.toFixed(0)}% win rate - ${stats.total_trades} trades`);
        }
    });

    // Analyze VIGL patterns
    Object.entries(viglPatterns).forEach(([pattern, stats]) => {
        if (stats.win_rate >= 60 && stats.total_trades >= 2) {
            const label = pattern.charAt(0).toUpperCase() + pattern.slice(1);
            workingInsights.push(`VIGL ${label}: ${stats.win_rate.toFixed(0)}% win rate, +${(stats.total_return || 0).toFixed(1)}% total return`);
        } else if (stats.win_rate < 40 && stats.total_trades >= 2) {
            const label = pattern.charAt(0).toUpperCase() + pattern.slice(1);
            notWorkingInsights.push(`VIGL ${label}: ${stats.win_rate.toFixed(0)}% win rate - consider filtering`);
        }
    });

    // General insights
    if ((perf.overall_win_rate || 0) >= 55) {
        workingInsights.push(`Overall system: ${(perf.overall_win_rate).toFixed(0)}% win rate is above breakeven`);
    }
    if ((perf.avg_return || 0) > 0) {
        workingInsights.push(`Positive expectancy: ${(perf.avg_return).toFixed(1)}% average return per trade`);
    }
    if ((perf.overall_win_rate || 0) < 45 && perf.total_trades >= 5) {
        notWorkingInsights.push(`Win rate below 45% - may need tighter entry criteria`);
    }
    if ((perf.avg_hold_days || 0) > 10) {
        notWorkingInsights.push(`Average hold of ${(perf.avg_hold_days).toFixed(0)} days - consider tighter exit rules`);
    }

    if (workingInsights.length > 0) {
        workingContainer.innerHTML = workingInsights.map(insight =>
            `<div class="brain-insight"><span class="brain-insight-icon">\u2705</span>${insight}</div>`
        ).join('');
    } else {
        workingContainer.innerHTML = '<p class="no-data-text">Not enough data to identify winning patterns</p>';
    }

    if (notWorkingInsights.length > 0) {
        notWorkingContainer.innerHTML = notWorkingInsights.map(insight =>
            `<div class="brain-insight"><span class="brain-insight-icon">\u26A0\uFE0F</span>${insight}</div>`
        ).join('');
    } else {
        notWorkingContainer.innerHTML = '<p class="no-data-text">No concerning patterns detected yet</p>';
    }
}

async function loadApprovalHistory() {
    try {
        const response = await fetch('/api/approval/history');
        const data = await response.json();
        return data.decisions || data.history || [];
    } catch (error) {
        return [];
    }
}

async function renderDecisionAccuracy() {
    const container = document.getElementById('decisionAccuracy');
    const history = await loadApprovalHistory();

    if (!history || history.length === 0) {
        container.innerHTML = '<p class="no-data-text">No decision history yet</p>';
        return;
    }

    const approved = history.filter(h => h.decision === 'approve');
    const rejected = history.filter(h => h.decision === 'reject');
    const approvedWon = approved.filter(h => (h.actual_return || 0) > 0).length;
    const rejectedWouldHaveWon = rejected.filter(h => (h.would_be_return || 0) > 0).length;

    const goodApprovals = approved.length > 0 ? ((approvedWon / approved.length) * 100).toFixed(0) : '--';
    const goodRejections = rejected.length > 0 ? (((rejected.length - rejectedWouldHaveWon) / rejected.length) * 100).toFixed(0) : '--';

    container.innerHTML = `
        <div class="da-stat-row">
            <span class="da-stat-label">Total Decisions</span>
            <span class="da-stat-value">${history.length}</span>
        </div>
        <div class="da-stat-row">
            <span class="da-stat-label">Approved (won)</span>
            <span class="da-stat-value">${approvedWon}/${approved.length} (${goodApprovals}%)</span>
        </div>
        <div class="da-stat-row">
            <span class="da-stat-label">Good Rejections</span>
            <span class="da-stat-value">${rejected.length - rejectedWouldHaveWon}/${rejected.length} (${goodRejections}%)</span>
        </div>
        <div class="da-stat-row">
            <span class="da-stat-label">Missed Winners</span>
            <span class="da-stat-value ${rejectedWouldHaveWon > 0 ? 'negative' : ''}">${rejectedWouldHaveWon}</span>
        </div>
    `;
}

// =============================================
// ACCOUNT & POSITIONS
// =============================================
async function loadAccount() {
    try {
        const response = await fetch('/api/account');
        const data = await response.json();

        if (data.error) throw new Error(data.error);

        accountData = data;

        // Portfolio view elements
        const portfolioValueEl = document.getElementById('portfolioValue');
        if (portfolioValueEl) {
            portfolioValueEl.textContent = formatCurrency(data.portfolio_value);
        }
        const buyingPowerEl = document.getElementById('buyingPower');
        if (buyingPowerEl) buyingPowerEl.textContent = formatCurrency(data.buying_power);
        const cashEl = document.getElementById('cashBalance');
        if (cashEl) cashEl.textContent = formatCurrency(data.cash);

        const lastEquity = data.last_equity || data.portfolio_value;
        const dailyChange = data.portfolio_value - lastEquity;
        const dailyChangePercent = lastEquity > 0 ? (dailyChange / lastEquity) * 100 : 0;

        const changeElement = document.getElementById('portfolioChange');
        if (changeElement) {
            changeElement.querySelector('.change-amount').textContent = formatCurrency(dailyChange);
            changeElement.querySelector('.change-percent').textContent = `(${dailyChangePercent >= 0 ? '+' : ''}${dailyChangePercent.toFixed(2)}%)`;
            if (dailyChange < 0) {
                changeElement.classList.add('negative');
            } else {
                changeElement.classList.remove('negative');
            }
        }
    } catch (error) {
        console.error('Error loading account:', error);
    }
}

async function loadPositions() {
    try {
        const response = await fetch('/api/positions');
        positionsData = await response.json();

        const countEl = document.getElementById('positionCount');
        if (countEl) countEl.textContent = positionsData.length;

        if (activeView === 'portfolio') {
            renderPositions();
            updatePortfolioChart(positionsData);
        }
    } catch (error) {
        console.error('Error loading positions:', error);
    }
}

function renderPositions() {
    const tbody = document.getElementById('positionsBody');
    if (!tbody) return;
    tbody.innerHTML = '';

    if (positionsData.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" style="text-align:center;color:var(--text-secondary);">No positions yet</td></tr>';
        return;
    }

    const sorted = [...positionsData].sort((a, b) => {
        let valA, valB;
        const col = currentSort.column;
        if (col === 'symbol') {
            valA = a.symbol || '';
            valB = b.symbol || '';
            return currentSort.direction === 'asc' ? valA.localeCompare(valB) : valB.localeCompare(valA);
        }
        valA = parseFloat(a[col] || 0);
        valB = parseFloat(b[col] || 0);
        return currentSort.direction === 'asc' ? valA - valB : valB - valA;
    });

    sorted.forEach(pos => {
        const row = document.createElement('tr');
        const unrealizedPL = parseFloat(pos.unrealized_pl || 0);
        const unrealizedPLPC = parseFloat(pos.unrealized_plpc || 0);
        const thesis = thesisData[pos.symbol];
        const validationIcon = getThesisValidationIcon(thesis);

        row.innerHTML = `
            <td><span class="symbol">${pos.symbol}</span></td>
            <td>${parseFloat(pos.qty).toFixed(0)}</td>
            <td>${formatCurrency(parseFloat(pos.avg_entry_price))}</td>
            <td>${formatCurrency(parseFloat(pos.current_price))}</td>
            <td>${formatCurrency(parseFloat(pos.market_value))}</td>
            <td class="${unrealizedPL >= 0 ? 'positive' : 'negative'}">
                ${unrealizedPL >= 0 ? '+' : ''}${formatCurrency(unrealizedPL)}
            </td>
            <td class="${unrealizedPLPC >= 0 ? 'positive' : 'negative'}">
                ${unrealizedPLPC >= 0 ? '+' : ''}${unrealizedPLPC.toFixed(2)}%
            </td>
            <td>${validationIcon}</td>
            <td class="thesis-cell">
                ${thesis ? `<span class="thesis-snippet" onclick="expandThesis('${pos.symbol}')" title="Click to expand">${truncate(thesis.entry_thesis, 30)}</span>` : '<span class="no-thesis">--</span>'}
            </td>
            <td class="actions-cell">
                <button class="btn-small btn-buy-small" onclick="showTradeModal('${pos.symbol}', ${parseFloat(pos.current_price)}, 'buy')">Buy</button>
                <button class="btn-small btn-sell-small" onclick="showTradeModal('${pos.symbol}', ${parseFloat(pos.current_price)}, 'sell')">Sell</button>
                <button class="btn-small btn-view-small" onclick="viewStock('${pos.symbol}')">Info</button>
            </td>
        `;
        tbody.appendChild(row);
    });
}

function updateSortArrows() {
    document.querySelectorAll('.positions-table th.sortable').forEach(th => {
        const arrow = th.querySelector('.sort-arrow');
        if (th.dataset.sort === currentSort.column) {
            arrow.textContent = currentSort.direction === 'asc' ? ' \u25B2' : ' \u25BC';
            th.classList.add('sorted');
        } else {
            arrow.textContent = '';
            th.classList.remove('sorted');
        }
    });
}

// =============================================
// THESIS
// =============================================
function expandThesis(symbol) {
    const thesis = thesisData[symbol];
    const panel = document.getElementById('thesisPanel');

    if (!thesis) {
        showToast('No thesis data for ' + symbol, 'info');
        return;
    }

    document.getElementById('thesisPanelSymbol').textContent = symbol + ' - Investment Thesis';
    document.getElementById('thesisPanelEntry').textContent = thesis.entry_thesis || 'No entry thesis recorded';
    document.getElementById('thesisPanelStatus').textContent = thesis.current_status || thesis.status || 'Active';
    document.getElementById('thesisPanelScore').textContent = thesis.scanner_score ? thesis.scanner_score.toFixed(1) : '--';
    document.getElementById('thesisPanelVigl').textContent = thesis.vigl_match || thesis.vigl_pattern || '--';
    document.getElementById('thesisPanelDate').textContent = thesis.entry_date || '--';
    document.getElementById('thesisPanelTarget').textContent = thesis.price_target ? '$' + thesis.price_target.toFixed(2) : '--';

    // Validation section
    const validationSection = document.getElementById('thesisValidationSection');
    const badgeRow = document.getElementById('validationBadgeRow');
    const critiqueEl = document.getElementById('thesisCritique');

    if (thesis.validation_status) {
        validationSection.style.display = 'block';
        const status = thesis.validation_status;
        const badgeClass = `validation-badge-${status}`;
        const statusLabels = { working: 'Thesis Working', watch: 'Needs Watching', broken: 'Thesis Broken', unknown: 'Pending Validation' };

        badgeRow.innerHTML = `<span class="${badgeClass}">${statusLabels[status] || 'Unknown'}</span>`;

        if (thesis.validation_reason) {
            badgeRow.innerHTML += `<span style="font-size:12px;color:var(--text-secondary);">${thesis.validation_reason}</span>`;
        }

        critiqueEl.textContent = thesis.critique || '';
        critiqueEl.style.display = thesis.critique ? 'block' : 'none';
    } else {
        validationSection.style.display = 'none';
    }

    panel.style.display = 'block';
    panel.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

async function loadThesis() {
    try {
        const response = await fetch('/api/thesis');
        const data = await response.json();

        thesisData = {};
        if (data.active_positions) {
            data.active_positions.forEach(t => {
                thesisData[t.symbol] = t;
            });
        }
    } catch (error) {
        console.error('Error loading thesis:', error);
    }
}

// =============================================
// SCANNER STATUS & RESULTS
// =============================================
async function loadScannerStatus() {
    try {
        const response = await fetch('/api/scanner/status');
        const data = await response.json();

        // Update navbar dot
        const navDot = document.getElementById('scannerDotNav');

        // Update Research Lab banner elements (may not exist if view not active)
        const dot = document.getElementById('scannerDot');
        const statusText = document.getElementById('scannerStatusText');
        const version = document.getElementById('scannerVersion');

        if (data.error || data.offline) {
            scannerOnline = false;
            if (navDot) navDot.className = 'scanner-dot-nav offline';
            if (dot) dot.className = 'scanner-status-dot offline';
            if (statusText) statusText.textContent = 'Offline';
            return;
        }

        if (version) version.textContent = data.scanner_version || 'V4 Scanner';

        if (data.status === 'operational') {
            scannerOnline = true;
            if (navDot) navDot.className = 'scanner-dot-nav online';
            if (dot) dot.className = 'scanner-status-dot online';
            if (statusText) statusText.textContent = 'Operational';
        } else {
            scannerOnline = false;
            if (navDot) navDot.className = 'scanner-dot-nav';
            if (dot) dot.className = 'scanner-status-dot pending';
            if (statusText) statusText.textContent = data.status || 'Pending';
        }

        // Gate funnel
        const gates = data.gates || {};
        const gateA = document.getElementById('gateACount');
        const gateB = document.getElementById('gateBCount');
        const gateC = document.getElementById('gateCCount');
        if (gateA) gateA.textContent = gates.gate_a_passed || gates.gate_a || '--';
        if (gateB) gateB.textContent = gates.gate_b_passed || gates.gate_b || '--';
        if (gateC) gateC.textContent = data.total_candidates || gates.gate_c || '--';

        if (data.last_scan_time) {
            const lastScanEl = document.getElementById('lastScan');
            if (lastScanEl) lastScanEl.textContent = `Last scan: ${formatTimeAgo(data.last_scan_time)}`;
        }
    } catch (error) {
        console.error('Error loading scanner status:', error);
        scannerOnline = false;
        const navDot = document.getElementById('scannerDotNav');
        if (navDot) navDot.className = 'scanner-dot-nav offline';
        const dot = document.getElementById('scannerDot');
        if (dot) dot.className = 'scanner-status-dot offline';
        const statusText = document.getElementById('scannerStatusText');
        if (statusText) statusText.textContent = 'Error';
    }
}

async function loadScannerResults() {
    try {
        const response = await fetch('/api/scanner/results');
        const data = await response.json();

        const grid = document.getElementById('candidatesGrid');
        const tierSummary = document.getElementById('tierSummary');
        if (!grid || !tierSummary) return;
        grid.innerHTML = '';
        tierSummary.innerHTML = '';

        const candidates = data.candidates || [];

        if (candidates.length === 0) {
            grid.innerHTML = `
                <div class="no-candidates">
                    <div class="no-candidates-icon">\u{1F6E1}</div>
                    <h3>No candidates today</h3>
                    <p>${data.message || 'The V4 scanner found no stocks matching the stealth accumulation pattern. This is the system protecting your capital on a quiet day.'}</p>
                </div>
            `;

            if (data.scanner_version && data.scanner_version !== 'OFFLINE') {
                const philosophy = document.getElementById('scannerPhilosophy');
                if (philosophy) {
                    philosophy.querySelector('.philosophy-text').textContent =
                        'Wide net scanned, strict filter applied - 0 picks means no quality setups today';
                }
            }
            return;
        }

        // Tier summary badges
        const tiers = data.tiers || {};
        const tierOrder = ['S', 'A', 'B', 'C'];
        const tierLabels = { S: 'S-Tier', A: 'A-Tier', B: 'B-Tier', C: 'C-Tier' };
        const tierColors = { S: 'tier-s', A: 'tier-a', B: 'tier-b', C: 'tier-c' };

        tierOrder.forEach(tier => {
            const count = tiers[tier] || candidates.filter(c => c.tier === tier).length;
            if (count > 0) {
                const badge = document.createElement('span');
                badge.className = `tier-summary-badge ${tierColors[tier]}`;
                badge.textContent = `${tierLabels[tier]}: ${count}`;
                tierSummary.appendChild(badge);
            }
        });

        const totalBadge = document.createElement('span');
        totalBadge.className = 'tier-summary-badge tier-total';
        totalBadge.textContent = `Total: ${candidates.length}`;
        tierSummary.appendChild(totalBadge);

        candidates.sort((a, b) => (b.total_score || 0) - (a.total_score || 0));

        candidates.forEach(candidate => {
            const card = document.createElement('div');
            const tier = candidate.tier || 'C';
            const tierClass = tierColors[tier] || 'tier-c';

            card.className = `candidate-card ${tierClass}`;

            const score = candidate.total_score || candidate.base_score || 0;
            const explosion = candidate.explosion_probability || 0;
            const viglBonus = candidate.vigl_bonus || 0;
            const rvol = candidate.rvol || 0;
            const changePct = candidate.change_pct || 0;
            const price = candidate.price || 0;
            const reasoning = candidate.reasoning || candidate.gate_reasons || '';

            card.innerHTML = `
                <div class="candidate-header">
                    <div>
                        <div class="candidate-symbol">${candidate.symbol}</div>
                        <div class="candidate-price">$${price.toFixed(2)}</div>
                    </div>
                    <div class="candidate-tier-badge ${tierClass}">${tier}</div>
                </div>
                <div class="candidate-scores">
                    <div class="candidate-score-main">
                        <span class="score-number">${score.toFixed(1)}</span>
                        <span class="score-max">/100</span>
                    </div>
                    ${viglBonus > 0 ? `<span class="vigl-indicator vigl-${viglBonus >= 15 ? 'perfect' : viglBonus >= 10 ? 'near' : 'partial'}">VIGL +${viglBonus}</span>` : ''}
                </div>
                <div class="candidate-explosion">
                    <div class="explosion-mini-bar">
                        <div class="explosion-mini-fill" style="width:${Math.min(explosion, 100)}%"></div>
                    </div>
                    <span class="explosion-value">${explosion.toFixed(1)}% explosion</span>
                </div>
                ${reasoning ? `<div class="candidate-reasoning"><p>${reasoning}</p></div>` : ''}
                <div class="candidate-metrics">
                    <div class="candidate-metric">
                        <span class="cm-label">RVOL</span>
                        <span class="cm-value">${rvol.toFixed(2)}x</span>
                    </div>
                    <div class="candidate-metric">
                        <span class="cm-label">Change</span>
                        <span class="cm-value ${changePct >= 0 ? 'positive' : 'negative'}">${changePct >= 0 ? '+' : ''}${changePct.toFixed(2)}%</span>
                    </div>
                </div>
                <div class="candidate-actions">
                    <button class="btn-rec-buy" onclick="showTradeModal('${candidate.symbol}', ${price}, 'buy')">Buy</button>
                    <button class="btn-rec-sell" onclick="showTradeModal('${candidate.symbol}', ${price}, 'sell')">Sell</button>
                    <button class="btn-rec-view" onclick="viewStock('${candidate.symbol}')">Details</button>
                </div>
            `;
            grid.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading scanner results:', error);
    }
}

// =============================================
// LEARNING SYSTEM
// =============================================
async function loadLearning() {
    try {
        const [perfResponse, weightsResponse] = await Promise.all([
            fetch('/api/learning/performance'),
            fetch('/api/learning/weights')
        ]);

        const perf = await perfResponse.json();
        const weights = await weightsResponse.json();

        if (!perf.error && !perf.offline) {
            learningData = perf;

            // Render brain hero + insights
            renderBrainInsights(perf);

            // Score range bars
            const scoreRanges = perf.by_score_range || {};
            const barsContainer = document.getElementById('scoreRangeBars');
            if (barsContainer) {
                barsContainer.innerHTML = '';
                const rangeOrder = ['150+', '110-149', '60-109'];
                const rangeLabels = { '150+': 'High Conviction (150+)', '110-149': 'Strong (110-149)', '60-109': 'Watch (60-109)' };

                rangeOrder.forEach(range => {
                    const stats = scoreRanges[range];
                    if (stats) {
                        const barDiv = document.createElement('div');
                        barDiv.className = 'score-range-bar';
                        barDiv.innerHTML = `
                            <div class="sr-header">
                                <span class="sr-label">${rangeLabels[range]}</span>
                                <span class="sr-rate">${stats.win_rate.toFixed(0)}% (${stats.total_trades} trades)</span>
                            </div>
                            <div class="sr-bar">
                                <div class="sr-fill" style="width:${stats.win_rate}%"></div>
                            </div>
                        `;
                        barsContainer.appendChild(barDiv);
                    }
                });
            }

            // VIGL pattern stats
            const viglStats = perf.by_vigl_pattern || {};
            const viglContainer = document.getElementById('viglPatternStats');
            if (viglContainer) {
                viglContainer.innerHTML = '';
                const viglOrder = ['perfect', 'near', 'partial', 'none'];
                const viglLabels = { perfect: 'Perfect Match', near: 'Near Match', partial: 'Partial Match', none: 'No VIGL' };

                viglOrder.forEach(pattern => {
                    const stats = viglStats[pattern];
                    if (stats && stats.total_trades > 0) {
                        const row = document.createElement('div');
                        row.className = 'vigl-stat-row';
                        row.innerHTML = `
                            <span class="vigl-stat-label">${viglLabels[pattern]}</span>
                            <span class="vigl-stat-winrate">${stats.win_rate.toFixed(0)}%</span>
                            <span class="vigl-stat-trades">${stats.total_trades} trades</span>
                            <span class="vigl-stat-return ${stats.total_return >= 0 ? 'positive' : 'negative'}">${stats.total_return >= 0 ? '+' : ''}${stats.total_return.toFixed(1)}%</span>
                        `;
                        viglContainer.appendChild(row);
                    }
                });

                if (viglContainer.innerHTML === '') {
                    viglContainer.innerHTML = '<p class="no-data-text">No VIGL pattern data yet</p>';
                }
            }
        } else {
            const barsEl = document.getElementById('scoreRangeBars');
            if (barsEl) barsEl.innerHTML = '<p class="no-data-text">Learning system offline</p>';
            const viglEl = document.getElementById('viglPatternStats');
            if (viglEl) viglEl.innerHTML = '<p class="no-data-text">Learning system offline</p>';
        }

        // Weights breakdown
        if (!weights.error && !weights.offline) {
            const weightsContainer = document.getElementById('weightsBreakdown');
            if (weightsContainer) {
                weightsContainer.innerHTML = '';
                const components = weights.base_components || {};
                Object.entries(components).forEach(([key, comp]) => {
                    const weightDiv = document.createElement('div');
                    weightDiv.className = 'weight-component';
                    const name = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    weightDiv.innerHTML = `
                        <div class="weight-header">
                            <span class="weight-name">${name}</span>
                            <span class="weight-value">${comp.weight}pts</span>
                        </div>
                        <div class="weight-bar">
                            <div class="weight-fill" style="width:${comp.weight}%"></div>
                        </div>
                        <div class="weight-desc">${comp.description}</div>
                    `;
                    weightsContainer.appendChild(weightDiv);
                });

                const bonuses = weights.bonuses || {};
                if (Object.keys(bonuses).length > 0) {
                    const bonusDiv = document.createElement('div');
                    bonusDiv.className = 'weight-bonuses';
                    bonusDiv.innerHTML = `
                        <div class="weight-header">
                            <span class="weight-name">Bonuses</span>
                        </div>
                        <div class="bonus-items">
                            ${bonuses.vigl_perfect ? `<span class="bonus-item vigl-perfect">VIGL Perfect: +${bonuses.vigl_perfect}</span>` : ''}
                            ${bonuses.vigl_near ? `<span class="bonus-item vigl-near">VIGL Near: +${bonuses.vigl_near}</span>` : ''}
                            ${bonuses.vigl_partial ? `<span class="bonus-item vigl-partial">VIGL Partial: +${bonuses.vigl_partial}</span>` : ''}
                            ${bonuses.pre_explosion_multiplier ? `<span class="bonus-item multiplier">Pre-Explosion: x${bonuses.pre_explosion_multiplier}</span>` : ''}
                        </div>
                    `;
                    weightsContainer.appendChild(bonusDiv);
                }
            }
        } else {
            const weightsEl = document.getElementById('weightsBreakdown');
            if (weightsEl) weightsEl.innerHTML = '<p class="no-data-text">Weights data unavailable</p>';
        }

        // Decision accuracy
        renderDecisionAccuracy();
    } catch (error) {
        console.error('Error loading learning data:', error);
    }
}

// =============================================
// ORDERS
// =============================================
async function loadOrders() {
    try {
        const response = await fetch('/api/orders');
        ordersData = await response.json();
    } catch (error) {
        console.error('Error loading orders:', error);
        ordersData = [];
    }
}

function openOrdersPanel() {
    const panel = document.getElementById('ordersSlidePanel');
    const backdrop = document.getElementById('ordersSlideBackdrop');
    const body = document.getElementById('ordersSlideBody');

    body.innerHTML = '';

    if (ordersData.length === 0) {
        body.innerHTML = '<p style="color:var(--text-secondary);text-align:center;padding:24px;">No pending orders</p>';
    } else {
        ordersData.forEach(order => {
            const orderCard = document.createElement('div');
            orderCard.className = `order-card ${order.side}`;
            const orderType = order.type.toUpperCase();
            const side = order.side.toUpperCase();

            orderCard.innerHTML = `
                <div class="order-info">
                    <div class="order-symbol">${order.symbol}</div>
                    <div class="order-details">
                        ${side} ${order.qty} shares @ ${orderType}
                        ${order.limit_price ? `$${parseFloat(order.limit_price).toFixed(2)}` : 'Market'}
                    </div>
                </div>
                <div class="order-status">
                    <span class="status-badge">${order.status}</span>
                </div>
            `;
            body.appendChild(orderCard);
        });
    }

    panel.classList.add('active');
    backdrop.classList.add('active');
}

function closeOrdersPanel() {
    document.getElementById('ordersSlidePanel').classList.remove('active');
    document.getElementById('ordersSlideBackdrop').classList.remove('active');
}

// =============================================
// SEARCH & STOCK ANALYSIS
// =============================================
async function handleSearch() {
    const searchInput = document.getElementById('stockSearch');
    const symbol = searchInput.value.trim().toUpperCase();
    if (!symbol) {
        showToast('Please enter a stock symbol');
        return;
    }
    await viewStock(symbol);
}

async function viewStock(symbol) {
    try {
        showToast('Analyzing ' + symbol + '...', 'info');

        const response = await fetch(`/api/search?symbol=${symbol}`);
        const analysis = await response.json();

        if (analysis.error) {
            showToast('Error: ' + analysis.error, 'error');
            return;
        }

        currentSymbol = symbol;
        currentPrice = analysis.data.price;

        document.getElementById('modalSymbol').textContent = symbol;
        document.getElementById('modalPrice').textContent = formatCurrency(analysis.data.price);

        const changePercent = analysis.data.change_percent || 0;
        const changeElement = document.getElementById('modalChange');
        changeElement.textContent = `${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(2)}%`;
        changeElement.className = `price-change ${changePercent >= 0 ? '' : 'negative'}`;

        // V4 scanner data
        const v4Section = document.getElementById('v4Section');
        const tierBadge = document.getElementById('modalTier');
        const viglBadge = document.getElementById('modalVigl');

        if (analysis.scanner_match) {
            v4Section.style.display = 'block';
            const match = analysis.scanner_match;

            document.getElementById('modalV4Score').textContent = `${(match.total_score || 0).toFixed(1)}/100`;
            document.getElementById('modalExplosion').textContent = `${(match.explosion_probability || 0).toFixed(1)}%`;
            document.getElementById('modalRvol').textContent = `${(match.rvol || 0).toFixed(2)}x`;
            document.getElementById('modalViglBonus').textContent = match.vigl_bonus > 0 ? `+${match.vigl_bonus}` : 'None';

            const explosionPct = match.explosion_probability || 0;
            document.getElementById('explosionFill').style.width = `${Math.min(explosionPct, 100)}%`;
            document.getElementById('explosionLabel').textContent = `${explosionPct.toFixed(1)}% Explosion Probability`;

            const tier = match.tier || 'C';
            tierBadge.textContent = `${tier}-Tier`;
            tierBadge.className = `tier-badge tier-${tier.toLowerCase()}`;
            tierBadge.style.display = 'inline-block';

            if (match.vigl_bonus > 0) {
                viglBadge.textContent = `VIGL +${match.vigl_bonus}`;
                viglBadge.className = 'vigl-badge active';
                viglBadge.style.display = 'inline-block';
            } else {
                viglBadge.style.display = 'none';
            }
        } else {
            v4Section.style.display = 'none';
            tierBadge.style.display = 'none';
            viglBadge.style.display = 'none';
        }

        // Yahoo Finance metrics
        const yfMetrics = document.getElementById('yfMetrics');
        const d = analysis.data;
        yfMetrics.innerHTML = `
            <div class="yf-metric"><span class="yf-label">Market Cap</span><span class="yf-value">${d.market_cap ? formatLargeNumber(d.market_cap) : 'N/A'}</span></div>
            <div class="yf-metric"><span class="yf-label">Volume</span><span class="yf-value">${d.volume ? formatLargeNumber(d.volume) : 'N/A'}</span></div>
            <div class="yf-metric"><span class="yf-label">Avg Volume</span><span class="yf-value">${d.avg_volume ? formatLargeNumber(d.avg_volume) : 'N/A'}</span></div>
            <div class="yf-metric"><span class="yf-label">P/E Ratio</span><span class="yf-value">${d.pe_ratio ? d.pe_ratio.toFixed(1) : 'N/A'}</span></div>
            <div class="yf-metric"><span class="yf-label">RSI</span><span class="yf-value">${d.rsi ? d.rsi.toFixed(1) : 'N/A'}</span></div>
            <div class="yf-metric"><span class="yf-label">50-Day MA</span><span class="yf-value">${d.ma_50 ? '$' + d.ma_50.toFixed(2) : 'N/A'}</span></div>
            <div class="yf-metric"><span class="yf-label">Sector</span><span class="yf-value">${d.sector || 'N/A'}</span></div>
            <div class="yf-metric"><span class="yf-label">52W Range</span><span class="yf-value">$${(d['52w_low'] || 0).toFixed(2)} - $${(d['52w_high'] || 0).toFixed(2)}</span></div>
        `;

        await updateStockChart(symbol, analysis.data.historical_data);
        document.getElementById('analysisModal').classList.add('active');
    } catch (error) {
        console.error('Error viewing stock:', error);
        showToast('Error loading stock data', 'error');
    }
}

// =============================================
// TRADE MODAL
// =============================================
function showTradeModal(symbol, price, side) {
    currentSymbol = symbol;
    currentPrice = price || 0;
    tradeSide = side || 'buy';
    tradeOrderBy = 'shares';

    document.getElementById('tradeSymbol').value = symbol;
    document.getElementById('tradeShares').value = 10;
    document.getElementById('tradeDollars').value = 100;

    document.querySelectorAll('#sideToggle .toggle-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.value === tradeSide) btn.classList.add('active');
    });

    document.querySelectorAll('#orderByToggle .toggle-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.value === 'shares') btn.classList.add('active');
    });

    document.getElementById('sharesGroup').style.display = '';
    document.getElementById('dollarsGroup').style.display = 'none';

    updateTradeUI();
    updateTradeEstimate();

    document.getElementById('analysisModal').classList.remove('active');
    document.getElementById('tradeModal').classList.add('active');
}

function updateTradeUI() {
    const btn = document.getElementById('confirmTradeBtn');
    const title = document.getElementById('tradeModalTitle');

    if (tradeSide === 'buy') {
        btn.textContent = 'Confirm Buy';
        btn.className = 'btn-confirm-trade buy';
        title.textContent = 'Buy ' + (currentSymbol || '');
    } else {
        btn.textContent = 'Confirm Sell';
        btn.className = 'btn-confirm-trade sell';
        title.textContent = 'Sell ' + (currentSymbol || '');
    }
    updateTradeEstimate();
}

function updateTradeEstimate() {
    const estimate = document.getElementById('tradeEstimate');
    if (tradeOrderBy === 'shares') {
        const qty = parseInt(document.getElementById('tradeShares').value) || 0;
        const total = qty * currentPrice;
        estimate.textContent = tradeSide === 'buy'
            ? `Cost: ${formatCurrency(total)}`
            : `Proceeds: ${formatCurrency(total)}`;
    } else {
        const dollars = parseFloat(document.getElementById('tradeDollars').value) || 0;
        const approxShares = currentPrice > 0 ? (dollars / currentPrice).toFixed(2) : '0';
        estimate.textContent = `~${approxShares} shares at ${formatCurrency(currentPrice)}`;
    }
}

async function handleTrade() {
    const symbol = document.getElementById('tradeSymbol').value;
    if (!symbol) {
        showToast('Invalid order details', 'error');
        return;
    }

    const payload = { symbol, side: tradeSide, order_type: 'market' };

    if (tradeOrderBy === 'shares') {
        const qty = parseInt(document.getElementById('tradeShares').value);
        if (!qty || qty < 1) { showToast('Enter a valid number of shares', 'error'); return; }
        payload.qty = qty;
    } else {
        const notional = parseFloat(document.getElementById('tradeDollars').value);
        if (!notional || notional < 1) { showToast('Enter a valid dollar amount', 'error'); return; }
        payload.notional = notional;
    }

    try {
        showToast('Placing order...', 'info');
        const response = await fetch('/api/trade', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        const result = await response.json();
        if (result.error) { showToast('Error: ' + result.error, 'error'); return; }

        const desc = tradeOrderBy === 'shares' ? `${payload.qty} shares` : `$${payload.notional}`;
        showToast(`Order placed: ${tradeSide.toUpperCase()} ${desc} of ${symbol}`, 'success');
        document.getElementById('tradeModal').classList.remove('active');
        setTimeout(() => { loadDashboard(); }, 1000);
    } catch (error) {
        console.error('Error placing order:', error);
        showToast('Error placing order', 'error');
    }
}

// =============================================
// CHARTS
// =============================================
function updatePortfolioChart(positions) {
    const ctx = document.getElementById('portfolioChart');
    if (!ctx) return;

    if (portfolioChart) portfolioChart.destroy();
    if (positions.length === 0) return;

    const labels = positions.map(p => p.symbol);
    const values = positions.map(p => parseFloat(p.market_value));
    const colors = ['#00c805', '#00a804', '#008803', '#006802', '#004801',
        '#10c815', '#20c825', '#30c835', '#40c845', '#50c855'];

    portfolioChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels,
            datasets: [{ data: values, backgroundColor: colors.slice(0, positions.length), borderWidth: 0 }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: { padding: 12, usePointStyle: true, font: { family: 'Inter', size: 12 } }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const label = context.label || '';
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percent = ((value / total) * 100).toFixed(1);
                            return `${label}: ${formatCurrency(value)} (${percent}%)`;
                        }
                    }
                }
            }
        }
    });
}

async function updateStockChart(symbol, historicalData) {
    try {
        if (!historicalData || historicalData.length === 0) {
            const response = await fetch(`/api/historical/${symbol}`);
            historicalData = await response.json();
        }

        const ctx = document.getElementById('stockChart');
        if (!ctx) return;
        if (stockChart) stockChart.destroy();

        const labels = historicalData.map(d => {
            const date = new Date(d.date || d.Date);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });
        const prices = historicalData.map(d => d.close || d.Close);

        stockChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels,
                datasets: [{
                    label: symbol,
                    data: prices,
                    borderColor: '#00c805',
                    backgroundColor: 'rgba(0, 200, 5, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 0,
                    pointHoverRadius: 4
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                interaction: { intersect: false, mode: 'index' },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: { label: function(context) { return `$${context.parsed.y.toFixed(2)}`; } }
                    }
                },
                scales: {
                    x: { grid: { display: false }, ticks: { maxTicksLimit: 8, font: { family: 'Inter', size: 11 } } },
                    y: {
                        grid: { color: '#e6e9eb' },
                        ticks: {
                            callback: function(value) { return '$' + value.toFixed(0); },
                            font: { family: 'Inter', size: 11 }
                        }
                    }
                }
            }
        });
    } catch (error) {
        console.error('Error updating stock chart:', error);
    }
}

// =============================================
// UTILITY FUNCTIONS
// =============================================
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    toastMessage.textContent = message;
    toast.classList.add('active');
    setTimeout(() => { toast.classList.remove('active'); }, 3000);
}

function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency', currency: 'USD',
        minimumFractionDigits: 2, maximumFractionDigits: 2
    }).format(value);
}

function formatLargeNumber(num) {
    if (num >= 1e12) return `$${(num / 1e12).toFixed(1)}T`;
    if (num >= 1e9) return `$${(num / 1e9).toFixed(1)}B`;
    if (num >= 1e6) return `${(num / 1e6).toFixed(1)}M`;
    if (num >= 1e3) return `${(num / 1e3).toFixed(1)}K`;
    return num.toString();
}

function truncate(str, maxLen) {
    if (!str) return '';
    return str.length > maxLen ? str.substring(0, maxLen) + '...' : str;
}

function formatTimeAgo(dateStr) {
    try {
        const date = new Date(dateStr);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        if (diffMins < 1) return 'just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    } catch {
        return dateStr;
    }
}
