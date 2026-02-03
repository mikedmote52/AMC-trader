// SqueezeSeeker Trading Dashboard - Frontend JavaScript

let portfolioChart = null;
let stockChart = null;
let currentSymbol = null;
let currentPrice = 0;

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
    // Search functionality
    const searchBtn = document.getElementById('searchBtn');
    const searchInput = document.getElementById('stockSearch');
    
    searchBtn.addEventListener('click', handleSearch);
    searchInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSearch();
    });
    
    // Modal controls
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
    
    // Update estimated cost when quantity changes
    document.getElementById('buyQuantity').addEventListener('input', updateEstimatedCost);
    
    // Close modals on background click
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
            loadRecommendations()
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
        
        // Update portfolio value
        document.getElementById('portfolioValue').textContent = formatCurrency(data.portfolio_value);
        document.getElementById('buyingPower').textContent = formatCurrency(data.buying_power);
        document.getElementById('cashBalance').textContent = formatCurrency(data.cash);
        
        // Calculate daily change (placeholder - would need historical data)
        const dailyChange = data.portfolio_value - 100000; // Assuming starting value
        const dailyChangePercent = (dailyChange / 100000) * 100;
        
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

// Load positions
async function loadPositions() {
    try {
        const response = await fetch('/api/positions');
        const positions = await response.json();
        
        document.getElementById('positionCount').textContent = positions.length;
        
        const tbody = document.getElementById('positionsBody');
        tbody.innerHTML = '';
        
        if (positions.length === 0) {
            tbody.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-secondary);">No positions yet</td></tr>';
            return;
        }
        
        positions.forEach(pos => {
            const row = document.createElement('tr');
            const unrealizedPL = parseFloat(pos.unrealized_pl || 0);
            const unrealizedPLPC = parseFloat(pos.unrealized_plpc || 0);
            
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
                <td style="text-align:center;">
                    <button class="btn-small btn-buy-small" onclick="viewStock('${pos.symbol}')">View</button>
                </td>
            `;
            
            tbody.appendChild(row);
        });
        
        // Update portfolio chart with positions
        updatePortfolioChart(positions);
        
    } catch (error) {
        console.error('Error loading positions:', error);
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

// Load recommended stocks
async function loadRecommendations() {
    try {
        const response = await fetch('/api/recommendations');
        const recommendations = await response.json();
        
        const grid = document.getElementById('recommendationsGrid');
        grid.innerHTML = '';
        
        recommendations.forEach(rec => {
            const card = document.createElement('div');
            const convictionClass = rec.total_score === 10 ? 'max-conviction' : rec.total_score >= 9 ? 'high-conviction' : '';
            card.className = `rec-card ${convictionClass}`;
            
            const changePercent = rec.change_percent || 0;
            const changeClass = changePercent >= 0 ? 'positive' : 'negative';
            
            const scoreClass = rec.total_score >= 9 ? 'excellent' : rec.total_score >= 7 ? 'good' : '';
            
            card.innerHTML = `
                <div class="rec-header">
                    <div>
                        <div class="rec-symbol">${rec.symbol}</div>
                        <div class="rec-name">${rec.name}</div>
                    </div>
                    <div class="rec-score ${scoreClass}">
                        ${rec.total_score}/10
                    </div>
                </div>
                <div class="rec-price-section">
                    <div class="rec-price">$${rec.current_price ? rec.current_price.toFixed(2) : rec.price.toFixed(2)}</div>
                    <div class="rec-change ${changeClass}">
                        ${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(2)}%
                    </div>
                </div>
                <div class="rec-thesis">${rec.thesis}</div>
                <div class="rec-metrics">
                    <div class="rec-metric">
                        <span class="rec-metric-label">Catalyst</span>
                        <span class="rec-metric-value">${rec.catalyst_type}</span>
                    </div>
                    <div class="rec-metric">
                        <span class="rec-metric-label">Target</span>
                        <span class="rec-metric-value">$${rec.price_target_low.toFixed(0)}-$${rec.price_target_high.toFixed(0)}</span>
                    </div>
                    <div class="rec-metric">
                        <span class="rec-metric-label">Risk/Reward</span>
                        <span class="rec-metric-value">${rec.risk_reward}</span>
                    </div>
                    <div class="rec-metric">
                        <span class="rec-metric-label">Sector</span>
                        <span class="rec-metric-value">${rec.sector}</span>
                    </div>
                </div>
                <div class="rec-actions">
                    <button class="btn-rec-buy" onclick="showBuyModal('${rec.symbol}', ${rec.current_price || rec.price})">
                        Buy Shares
                    </button>
                    <button class="btn-rec-view" onclick="viewStock('${rec.symbol}')">
                        Details
                    </button>
                </div>
            `;
            
            grid.appendChild(card);
        });
        
    } catch (error) {
        console.error('Error loading recommendations:', error);
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

// View stock details with analysis
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
        
        // Update modal header
        document.getElementById('modalSymbol').textContent = symbol;
        document.getElementById('modalPrice').textContent = formatCurrency(analysis.data.price);
        
        const changePercent = analysis.data.change_percent || 0;
        const changeElement = document.getElementById('modalChange');
        changeElement.textContent = `${changePercent >= 0 ? '+' : ''}${changePercent.toFixed(2)}%`;
        changeElement.className = `price-change ${changePercent >= 0 ? '' : 'negative'}`;
        
        // Update recommendation
        const recElement = document.getElementById('modalRecommendation');
        recElement.textContent = analysis.recommendation;
        recElement.className = `stock-recommendation ${analysis.recommendation.replace(' ', '-')}`;
        
        // Update score
        document.getElementById('modalScore').textContent = analysis.total_score;
        const scoreFill = document.getElementById('scoreFill');
        scoreFill.style.width = `${(analysis.total_score / 10) * 100}%`;
        
        // Update score factors
        const factorsContainer = document.getElementById('scoreFactors');
        factorsContainer.innerHTML = '';
        
        for (const [key, value] of Object.entries(analysis.scores)) {
            const factor = analysis.scoring_factors[key];
            const passed = value > 0;
            
            const factorDiv = document.createElement('div');
            factorDiv.className = `score-factor ${passed ? 'pass' : 'fail'}`;
            factorDiv.innerHTML = `
                <span class="factor-icon">${passed ? '✓' : '○'}</span>
                <span>${factor.name}</span>
            `;
            factorDiv.title = factor.description;
            
            factorsContainer.appendChild(factorDiv);
        }
        
        // Update analysis notes
        const notesContainer = document.getElementById('analysisNotes');
        notesContainer.innerHTML = '';
        
        analysis.analysis_notes.forEach(note => {
            const li = document.createElement('li');
            li.textContent = note;
            notesContainer.appendChild(li);
        });
        
        // Load and display chart
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
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ symbol, qty })
        });
        
        const result = await response.json();
        
        if (result.error) {
            showToast('Error: ' + result.error, 'error');
            return;
        }
        
        showToast(`Order placed: BUY ${qty} ${symbol}`, 'success');
        document.getElementById('buyModal').classList.remove('active');
        
        // Refresh data
        setTimeout(() => {
            loadDashboard();
        }, 1000);
        
    } catch (error) {
        console.error('Error placing order:', error);
        showToast('Error placing order', 'error');
    }
}

// Update portfolio chart
function updatePortfolioChart(positions) {
    const ctx = document.getElementById('portfolioChart');
    
    if (!ctx) return;
    
    // Destroy existing chart
    if (portfolioChart) {
        portfolioChart.destroy();
    }
    
    // Prepare data
    const labels = positions.map(p => p.symbol);
    const values = positions.map(p => parseFloat(p.market_value));
    const colors = [
        '#00c805', '#00a804', '#008803', '#006802', '#004801',
        '#10c815', '#20c825', '#30c835', '#40c845', '#50c855',
        '#60c865', '#70c875', '#80c885', '#90c895', '#a0c8a5'
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
                        font: {
                            family: 'Inter',
                            size: 12
                        }
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
        // If no historical data provided, fetch it
        if (!historicalData || historicalData.length === 0) {
            const response = await fetch(`/api/historical/${symbol}`);
            historicalData = await response.json();
        }
        
        const ctx = document.getElementById('stockChart');
        
        if (!ctx) return;
        
        // Destroy existing chart
        if (stockChart) {
            stockChart.destroy();
        }
        
        // Prepare data
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
                interaction: {
                    intersect: false,
                    mode: 'index'
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `$${context.parsed.y.toFixed(2)}`;
                            }
                        }
                    }
                },
                scales: {
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            maxTicksLimit: 8,
                            font: {
                                family: 'Inter',
                                size: 11
                            }
                        }
                    },
                    y: {
                        grid: {
                            color: '#e6e9eb'
                        },
                        ticks: {
                            callback: function(value) {
                                return '$' + value.toFixed(0);
                            },
                            font: {
                                family: 'Inter',
                                size: 11
                            }
                        }
                    }
                }
            }
        });
        
    } catch (error) {
        console.error('Error updating stock chart:', error);
    }
}

// Show toast notification
function showToast(message, type = 'info') {
    const toast = document.getElementById('toast');
    const toastMessage = document.getElementById('toastMessage');
    
    toastMessage.textContent = message;
    toast.classList.add('active');
    
    setTimeout(() => {
        toast.classList.remove('active');
    }, 3000);
}

// Format currency
function formatCurrency(value) {
    return new Intl.NumberFormat('en-US', {
        style: 'currency',
        currency: 'USD',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    }).format(value);
}

// Smooth scroll for navigation
document.querySelectorAll('.nav-links a').forEach(link => {
    link.addEventListener('click', (e) => {
        e.preventDefault();
        const targetId = link.getAttribute('href').substring(1);
        const target = document.getElementById(targetId);
        
        if (target) {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
            
            // Update active link
            document.querySelectorAll('.nav-links a').forEach(l => l.classList.remove('active'));
            link.classList.add('active');
        }
    });
});
