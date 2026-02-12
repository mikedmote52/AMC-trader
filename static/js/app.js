// SqueezeSeeker Trading Dashboard - Open Claw V4 Integration

let portfolioChart = null;
let stockChart = null;
let currentSymbol = null;
let currentPrice = 0;
let thesisData = {};

// Initialize dashboard
document.addEventListener('DOMContentLoaded', async () => {
    await loadDashboard();
    setupEventListeners();

    // Refresh data every 30 seconds
    setInterval(() => {
        loadDashboard();
    }, 30000);
});

// Setup event listeners
function setupEventListeners() {
    const searchBtn = document.getElementById('searchBtn');
    const searchInput = document.getElementById('stockSearch');

    searchBtn.addEventListener('click', handleSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });

    document.getElementById('modalClose').addEventListener('click', () => {
        document.getElementById('analysisModal').classList.remove('active');
    });

    document.getElementById('buyModalClose').addEventListener('click', () => {
        document.getElementById('buyModal').classList.remove('active');
    });

    document.getElementById('modalBuyBtn').addEventListener('click', () => {
        showBuyModal(currentSymbol, currentPrice);
    });

    document.getElementById('confirmBuyBtn').addEventListener('click', handleBuy);
    document.getElementById('buyQuantity').addEventListener('input', updateEstimatedCost);

    document.getElementById('analysisModal').addEventListener('click', (e) => {
        if (e.target.id === 'analysisModal') {
            document.getElementById('analysisModal').classList.remove('active');
        }
    });

    document.getElementById('buyModal').addEventListener('click', (e) => {
        if (e.target.id === 'buyModal') {
            document.getElementById('buyModal').classList.remove('active');
        }
    });
}

// Load all dashboard data
async function loadDashboard() {
    try {
        await Promise.all([
            loadAccount(),
            loadPositions(),
            loadOrders(),
            loadScannerStatus(),
            loadScannerResults(),
            loadLearning(),
            loadThesis()
        ]);
    } catch (error) {
        console.error('Error loading dashboard:', error);
        showToast('Error loading dashboard data', 'error');
    }
}

// Load account information
async function loadAccount() {
    try {
        const response = await fetch('/api/account');
        const data = await response.json();

        if (data.error) {
            throw new Error(data.error);
        }

        document.getElementById('portfolioValue').textContent = formatCurrency(data.portfolio_value);
        document.getElementById('buyingPower').textContent = formatCurrency(data.buying_power);
        document.getElementById('cashBalance').textContent = formatCurrency(data.cash);

        const lastEquity = data.last_equity || data.portfolio_value;
        const dailyChange = data.portfolio_value - lastEquity;
        const dailyChangePercent = lastEquity > 0 ? (dailyChange / lastEquity) * 100 : 0;

        const changeElement = document.getElementById('portfolioChange');
        changeElement.querySelector('.change-amount').textContent = formatCurrency(dailyChange);
        changeElement.querySelector('.change-percent').textContent = `(${dailyChangePercent >= 0 ? '+' : ''}${dailyChangePercent.toFixed(2)}%)`;

        if (dailyChange < 0) {
            changeElement.classList.add('negative');
        } else {
            changeElement.classList.remove('negative');
        }
    } catch (error) {
        console.error('Error loading account:', error);
    }
}

// Load positions with thesis integration
async function loadPositions() {
    try {
        const response = await fetch('/api/positions');
        const positions = await response.json();

        document.getElementById('positionCount').textContent = positions.length;

        const tbody = document.getElementById('positionsBody');
        tbody.innerHTML = '';

        if (positions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="9" style="text-align:center;color:var(--text-secondary);">No positions yet</td></tr>';
            return;
        }

        positions.forEach(pos => {
            const row = document.createElement('tr');
            const unrealizedPL = parseFloat(pos.unrealized_pl || 0);
            const unrealizedPLPC = parseFloat(pos.unrealized_plpc || 0);
            const thesis = thesisData[pos.symbol];

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
                <td class="thesis-cell">
                    ${thesis ? `<span class="thesis-snippet" title="${thesis.entry_thesis}">${truncate(thesis.entry_thesis, 30)}</span>` : '<span class="no-thesis">--</span>'}
                </td>
                <td style="text-align:center;">
                    <button class="btn-small btn-buy-small" onclick="viewStock('${pos.symbol}')">View</button>
                </td>
            `;

            tbody.appendChild(row);
        });

        updatePortfolioChart(positions);
    } catch (error) {
        console.error('Error loading positions:', error);
    }
}

// Load thesis data from Open Claw
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

// Load scanner status banner
async function loadScannerStatus() {
    try {
        const response = await fetch('/api/scanner/status');
        const data = await response.json();

        const dot = document.getElementById('scannerDot');
        const statusText = document.getElementById('scannerStatusText');
        const version = document.getElementById('scannerVersion');

        if (data.error || data.offline) {
            dot.className = 'scanner-status-dot offline';
            statusText.textContent = 'Offline';
            return;
        }

        version.textContent = data.scanner_version || 'V4 Scanner';

        if (data.status === 'operational') {
            dot.className = 'scanner-status-dot online';
            statusText.textContent = 'Operational';
        } else {
            dot.className = 'scanner-status-dot pending';
            statusText.textContent = data.status || 'Pending';
        }

        // Gate funnel
        const gates = data.gates || {};
        document.getElementById('gateACount').textContent = gates.gate_a_passed || gates.gate_a || '--';
        document.getElementById('gateBCount').textContent = gates.gate_b_passed || gates.gate_b || '--';
        document.getElementById('gateCCount').textContent = data.total_candidates || gates.gate_c || '--';

        // Last scan time
        if (data.last_scan_time) {
            document.getElementById('lastScan').textContent = `Last scan: ${formatTimeAgo(data.last_scan_time)}`;
        }
    } catch (error) {
        console.error('Error loading scanner status:', error);
        document.getElementById('scannerDot').className = 'scanner-status-dot offline';
        document.getElementById('scannerStatusText').textContent = 'Error';
    }
}

// Load V4 scanner candidates
async function loadScannerResults() {
    try {
        const response = await fetch('/api/scanner/results');
        const data = await response.json();

        const grid = document.getElementById('candidatesGrid');
        const tierSummary = document.getElementById('tierSummary');
        grid.innerHTML = '';
        tierSummary.innerHTML = '';

        const candidates = data.candidates || [];

        if (candidates.length === 0) {
            grid.innerHTML = `
                <div class="no-candidates">
                    <div class="no-candidates-icon">&#x1F6E1;</div>
                    <h3>No candidates today</h3>
                    <p>${data.message || 'The V4 scanner found no stocks matching the stealth accumulation pattern. This is the system protecting your capital on a quiet day.'}</p>
                </div>
            `;

            // Show scanner version info even with 0 results
            if (data.scanner_version && data.scanner_version !== 'OFFLINE') {
                const philosophy = document.getElementById('scannerPhilosophy');
                philosophy.querySelector('.philosophy-text').textContent =
                    'Wide net scanned, strict filter applied - 0 picks means no quality setups today';
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

        // Total count
        const totalBadge = document.createElement('span');
        totalBadge.className = 'tier-summary-badge tier-total';
        totalBadge.textContent = `Total: ${candidates.length}`;
        tierSummary.appendChild(totalBadge);

        // Sort by total_score descending
        candidates.sort((a, b) => (b.total_score || 0) - (a.total_score || 0));

        // Render candidate cards
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
                    <button class="btn-rec-buy" onclick="showBuyModal('${candidate.symbol}', ${price})">Buy</button>
                    <button class="btn-rec-view" onclick="viewStock('${candidate.symbol}')">Details</button>
                </div>
            `;

            grid.appendChild(card);
        });
    } catch (error) {
        console.error('Error loading scanner results:', error);
    }
}

// Load learning system data
async function loadLearning() {
    try {
        const [perfResponse, weightsResponse] = await Promise.all([
            fetch('/api/learning/performance'),
            fetch('/api/learning/weights')
        ]);

        const perf = await perfResponse.json();
        const weights = await weightsResponse.json();

        // Overall stats
        if (!perf.error && !perf.offline) {
            document.getElementById('totalTrades').textContent = perf.total_trades || 0;
            document.getElementById('winRate').textContent = `${(perf.overall_win_rate || 0).toFixed(1)}%`;
            document.getElementById('avgReturn').textContent = `${(perf.avg_return || 0).toFixed(1)}%`;
            document.getElementById('avgHoldDays').textContent = (perf.avg_hold_days || 0).toFixed(1);

            // Score range bars
            const scoreRanges = perf.by_score_range || {};
            const barsContainer = document.getElementById('scoreRangeBars');
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

            // VIGL pattern stats
            const viglStats = perf.by_vigl_pattern || {};
            const viglContainer = document.getElementById('viglPatternStats');
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
        } else {
            document.getElementById('scoreRangeBars').innerHTML = '<p class="no-data-text">Learning system offline</p>';
            document.getElementById('viglPatternStats').innerHTML = '<p class="no-data-text">Learning system offline</p>';
        }

        // Weights breakdown
        if (!weights.error && !weights.offline) {
            const weightsContainer = document.getElementById('weightsBreakdown');
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

            // Bonuses
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
        } else {
            document.getElementById('weightsBreakdown').innerHTML = '<p class="no-data-text">Weights data unavailable</p>';
        }
    } catch (error) {
        console.error('Error loading learning data:', error);
    }
}

// Load pending orders
async function loadOrders() {
    try {
        const response = await fetch('/api/orders');
        const orders = await response.json();

        const ordersList = document.getElementById('ordersList');
        ordersList.innerHTML = '';

        if (orders.length === 0) {
            ordersList.innerHTML = '<p style="color:var(--text-secondary);text-align:center;padding:24px;">No pending orders</p>';
            return;
        }

        orders.forEach(order => {
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

            ordersList.appendChild(orderCard);
        });
    } catch (error) {
        console.error('Error loading orders:', error);
    }
}

// Handle stock search
async function handleSearch() {
    const searchInput = document.getElementById('stockSearch');
    const symbol = searchInput.value.trim().toUpperCase();

    if (!symbol) {
        showToast('Please enter a stock symbol');
        return;
    }

    await viewStock(symbol);
}

// View stock details with V4 + Yahoo Finance data
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

        // Modal header
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

            // Explosion bar
            const explosionPct = match.explosion_probability || 0;
            document.getElementById('explosionFill').style.width = `${Math.min(explosionPct, 100)}%`;
            document.getElementById('explosionLabel').textContent = `${explosionPct.toFixed(1)}% Explosion Probability`;

            // Tier badge
            const tier = match.tier || 'C';
            tierBadge.textContent = `${tier}-Tier`;
            tierBadge.className = `tier-badge tier-${tier.toLowerCase()}`;
            tierBadge.style.display = 'inline-block';

            // VIGL badge
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

        // Chart
        await updateStockChart(symbol, analysis.data.historical_data);

        // Show modal
        document.getElementById('analysisModal').classList.add('active');
    } catch (error) {
        console.error('Error viewing stock:', error);
        showToast('Error loading stock data', 'error');
    }
}

// Show buy modal
function showBuyModal(symbol, price) {
    currentSymbol = symbol;
    currentPrice = price;

    document.getElementById('buySymbol').value = symbol;
    document.getElementById('buyQuantity').value = 10;
    updateEstimatedCost();

    document.getElementById('buyModal').classList.add('active');
}

// Update estimated cost
function updateEstimatedCost() {
    const qty = parseInt(document.getElementById('buyQuantity').value) || 0;
    const cost = qty * currentPrice;
    document.getElementById('estimatedCost').textContent = formatCurrency(cost);
}

// Handle buy order
async function handleBuy() {
    const symbol = document.getElementById('buySymbol').value;
    const qty = parseInt(document.getElementById('buyQuantity').value);

    if (!symbol || !qty || qty < 1) {
        showToast('Invalid order details', 'error');
        return;
    }

    try {
        showToast('Placing order...', 'info');

        const response = await fetch('/api/buy', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol, qty })
        });

        const result = await response.json();

        if (result.error) {
            showToast('Error: ' + result.error, 'error');
            return;
        }

        showToast(`Order placed: BUY ${qty} ${symbol}`, 'success');
        document.getElementById('buyModal').classList.remove('active');

        setTimeout(() => { loadDashboard(); }, 1000);
    } catch (error) {
        console.error('Error placing order:', error);
        showToast('Error placing order', 'error');
    }
}

// Update portfolio chart
function updatePortfolioChart(positions) {
    const ctx = document.getElementById('portfolioChart');
    if (!ctx) return;

    if (portfolioChart) {
        portfolioChart.destroy();
    }

    if (positions.length === 0) return;

    const labels = positions.map(p => p.symbol);
    const values = positions.map(p => parseFloat(p.market_value));
    const colors = [
        '#00c805', '#00a804', '#008803', '#006802', '#004801',
        '#10c815', '#20c825', '#30c835', '#40c845', '#50c855'
    ];

    portfolioChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: values,
                backgroundColor: colors.slice(0, positions.length),
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        padding: 12,
                        usePointStyle: true,
                        font: { family: 'Inter', size: 12 }
                    }
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

// Update stock chart
async function updateStockChart(symbol, historicalData) {
    try {
        if (!historicalData || historicalData.length === 0) {
            const response = await fetch(`/api/historical/${symbol}`);
            historicalData = await response.json();
        }

        const ctx = document.getElementById('stockChart');
        if (!ctx) return;

        if (stockChart) {
            stockChart.destroy();
        }

        const labels = historicalData.map(d => {
            const date = new Date(d.date || d.Date);
            return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
        });

        const prices = historicalData.map(d => d.close || d.Close);

        stockChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
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
                        callbacks: {
                            label: function(context) { return `$${context.parsed.y.toFixed(2)}`; }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: { display: false },
                        ticks: { maxTicksLimit: 8, font: { family: 'Inter', size: 11 } }
                    },
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

// Utility functions
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    toastMessage.textContent = message;
    toast.classList.add('active');
    setTimeout(() => { toast.classList.remove('active'); }, 3000);
}

function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
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

// Smooth scroll for navigation
document.querySelectorAll('.nav-links a').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const targetId = link.getAttribute('href').substring(1);
        const target = document.getElementById(targetId);

        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            document.querySelectorAll('.nav-links a').forEach(l => l.classList.remove('active'));
            link.classList.add('active');
        }
    });
});
