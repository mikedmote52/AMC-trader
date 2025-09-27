// AMC-TRADER Frontend Application
class AMCTrader {
    constructor() {
        this.candidates = [];
        this.filteredCandidates = [];
        this.currentFilter = 'all';
        this.currentSort = 'score';
        this.API_BASE = window.location.origin;

        this.init();
    }

    init() {
        this.setupEventListeners();
        this.checkSystemHealth();
        this.loadDiscoveryData();

        // Auto-refresh every 5 minutes
        setInterval(() => this.loadDiscoveryData(), 5 * 60 * 1000);
    }

    setupEventListeners() {
        // Refresh button
        document.getElementById('refreshBtn').addEventListener('click', () => {
            this.loadDiscoveryData();
        });

        // Filter tabs
        document.querySelectorAll('.tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                this.setActiveFilter(e.target.dataset.filter);
            });
        });

        // Sort dropdown
        document.getElementById('sortBy').addEventListener('change', (e) => {
            this.currentSort = e.target.value;
            this.renderCandidates();
        });

        // Modal close buttons
        document.querySelectorAll('.modal-close').forEach(btn => {
            btn.addEventListener('click', () => {
                this.closeModals();
            });
        });

        // Modal backgrounds
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('click', (e) => {
                if (e.target === modal) {
                    this.closeModals();
                }
            });
        });

        // Trade modal buttons
        document.getElementById('tradeCancelBtn').addEventListener('click', () => {
            this.closeModals();
        });

        document.getElementById('tradeConfirmBtn').addEventListener('click', () => {
            this.executeTrade();
        });

        // Trade amount input
        document.getElementById('tradeAmount').addEventListener('input', () => {
            this.updateTradeSummary();
        });
    }

    async checkSystemHealth() {
        try {
            const response = await fetch(`${this.API_BASE}/health`);
            const health = await response.json();

            const statusEl = document.getElementById('systemStatus');
            if (health.status === 'healthy') {
                statusEl.textContent = '✅ Healthy';
                statusEl.style.color = 'var(--primary-color)';
            } else {
                statusEl.textContent = '⚠️ Degraded';
                statusEl.style.color = 'var(--warning-color)';
            }
        } catch (error) {
            document.getElementById('systemStatus').textContent = '❌ Error';
            document.getElementById('systemStatus').style.color = 'var(--secondary-color)';
        }
    }

    async loadDiscoveryData() {
        const loadingEl = document.getElementById('loadingSpinner');
        const refreshBtn = document.getElementById('refreshBtn');

        // Show loading state
        loadingEl.classList.add('active');
        refreshBtn.classList.add('loading');

        const startTime = Date.now();

        try {
            const response = await fetch(`${this.API_BASE}/discovery/contenders?limit=50`);

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}`);
            }

            const data = await response.json();
            this.candidates = data.candidates || [];

            const endTime = Date.now();
            const discoveryTime = ((endTime - startTime) / 1000).toFixed(1);

            // Update header stats
            document.getElementById('discoveryTime').textContent = `${discoveryTime}s`;
            document.getElementById('candidateCount').textContent = this.candidates.length;

            // Process and render candidates
            this.processCandidate();
            this.filterAndRenderCandidates();

            this.showToast(`Discovery complete: ${this.candidates.length} candidates found`, 'success');

        } catch (error) {
            console.error('Discovery failed:', error);
            this.showToast('Discovery failed. Please try again.', 'error');

            // Show empty state
            document.getElementById('emptyState').classList.add('active');
        } finally {
            loadingEl.classList.remove('active');
            refreshBtn.classList.remove('loading');
        }
    }

    processCandidate() {
        this.candidates.forEach(candidate => {
            // Normalize score (convert to 0-100 if needed)
            if (candidate.total_score && candidate.total_score <= 1) {
                candidate.total_score = candidate.total_score * 100;
            }

            // Determine action category
            const score = candidate.total_score || 0;
            if (score >= 75) {
                candidate.category = 'trade_ready';
            } else if (score >= 60) {
                candidate.category = 'watchlist';
            } else {
                candidate.category = 'monitor';
            }

            // Extract regime from AlphaStack data
            candidate.regime = candidate.alphastack_regime ||
                             (candidate.consecutive_up_days >= 3 ? 'builder' : 'spike');

            // Ensure price and change data
            candidate.price = candidate.price || candidate.day?.c || 0;
            candidate.change_pct = candidate.change_pct || candidate.todaysChangePerc || 0;

            // Calculate IRV if not present
            if (!candidate.intraday_relative_volume) {
                candidate.intraday_relative_volume = candidate.volume_ratio || 1.0;
            }
        });
    }

    setActiveFilter(filter) {
        this.currentFilter = filter;

        // Update active tab
        document.querySelectorAll('.tab').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.filter === filter);
        });

        this.filterAndRenderCandidates();
    }

    filterAndRenderCandidates() {
        // Filter candidates
        this.filteredCandidates = this.candidates.filter(candidate => {
            switch (this.currentFilter) {
                case 'trade_ready':
                    return candidate.category === 'trade_ready';
                case 'watchlist':
                    return candidate.category === 'watchlist';
                case 'builder':
                    return candidate.regime === 'builder';
                case 'spike':
                    return candidate.regime === 'spike';
                default:
                    return true;
            }
        });

        this.renderCandidates();
    }

    renderCandidates() {
        // Sort candidates
        this.filteredCandidates.sort((a, b) => {
            switch (this.currentSort) {
                case 'score':
                    return (b.total_score || 0) - (a.total_score || 0);
                case 'volume':
                    return (b.intraday_relative_volume || 0) - (a.intraday_relative_volume || 0);
                case 'momentum':
                    return (b.consecutive_up_days || 0) - (a.consecutive_up_days || 0);
                case 'price':
                    return (a.price || 0) - (b.price || 0);
                default:
                    return 0;
            }
        });

        // Separate by category
        const tradeReady = this.filteredCandidates.filter(c => c.category === 'trade_ready');
        const watchlist = this.filteredCandidates.filter(c => c.category === 'watchlist');
        const monitor = this.filteredCandidates.filter(c => c.category === 'monitor');

        // Update counts
        document.getElementById('tradeReadyCount').textContent = tradeReady.length;
        document.getElementById('watchlistCount').textContent = watchlist.length;
        document.getElementById('monitorCount').textContent = monitor.length;

        // Render each section
        this.renderCandidateGrid('tradeReadyGrid', tradeReady);
        this.renderCandidateGrid('watchlistGrid', watchlist);
        this.renderCandidateGrid('monitorGrid', monitor);

        // Show/hide empty state
        const hasResults = this.filteredCandidates.length > 0;
        document.getElementById('emptyState').classList.toggle('active', !hasResults);

        // Show/hide sections based on filter
        if (this.currentFilter === 'all') {
            document.getElementById('tradeReadySection').style.display = 'block';
            document.getElementById('watchlistSection').style.display = 'block';
            document.getElementById('monitorSection').style.display = 'block';
        } else {
            document.getElementById('tradeReadySection').style.display =
                this.currentFilter === 'trade_ready' ? 'block' : 'none';
            document.getElementById('watchlistSection').style.display =
                this.currentFilter === 'watchlist' ? 'block' : 'none';
            document.getElementById('monitorSection').style.display =
                this.currentFilter === 'monitor' ? 'block' : 'none';
        }
    }

    renderCandidateGrid(gridId, candidates) {
        const grid = document.getElementById(gridId);

        if (candidates.length === 0) {
            grid.innerHTML = '<p style="text-align: center; color: var(--text-muted); padding: 40px;">No candidates in this category</p>';
            return;
        }

        grid.innerHTML = candidates.map(candidate => this.renderStockCard(candidate)).join('');
    }

    renderStockCard(candidate) {
        const score = candidate.total_score || 0;
        const scoreClass = score >= 75 ? 'excellent' : score >= 60 ? 'good' : 'fair';
        const changeClass = candidate.change_pct >= 0 ? 'positive' : 'negative';
        const changeSymbol = candidate.change_pct >= 0 ? '+' : '';

        const subscores = candidate.subscores || {};

        return `
            <div class="stock-card ${candidate.category} fade-in" onclick="window.amcTrader.showStockDetails('${candidate.ticker}')">
                <div class="regime-badge ${candidate.regime}">${candidate.regime}</div>

                <div class="stock-header">
                    <div>
                        <div class="stock-symbol">${candidate.ticker}</div>
                    </div>
                    <div class="stock-price">
                        <div class="price">$${candidate.price.toFixed(2)}</div>
                        <div class="change ${changeClass}">${changeSymbol}${candidate.change_pct.toFixed(1)}%</div>
                    </div>
                </div>

                <div class="score-section">
                    <div class="total-score">
                        <span class="score-label">AlphaStack Score</span>
                        <span class="score-value ${scoreClass}">${score.toFixed(0)}/100</span>
                    </div>
                    <div class="subscores">
                        <div class="subscore">
                            <span>Volume</span>
                            <span>${subscores.volume_momentum || 0}</span>
                        </div>
                        <div class="subscore">
                            <span>Squeeze</span>
                            <span>${subscores.squeeze || 0}</span>
                        </div>
                        <div class="subscore">
                            <span>Catalyst</span>
                            <span>${subscores.catalyst || 0}</span>
                        </div>
                        <div class="subscore">
                            <span>Options</span>
                            <span>${subscores.options || 0}</span>
                        </div>
                        <div class="subscore">
                            <span>Technical</span>
                            <span>${subscores.technical || 0}</span>
                        </div>
                        <div class="subscore">
                            <span>Sentiment</span>
                            <span>${subscores.sentiment || 0}</span>
                        </div>
                    </div>
                </div>

                <div class="key-metrics">
                    <div class="metric">
                        <span class="metric-label">Volume</span>
                        <span class="metric-value">${candidate.intraday_relative_volume.toFixed(1)}x</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Up Days</span>
                        <span class="metric-value">${candidate.consecutive_up_days || 0}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Entry</span>
                        <span class="metric-value">$${candidate.entry || candidate.price.toFixed(2)}</span>
                    </div>
                    <div class="metric">
                        <span class="metric-label">Target</span>
                        <span class="metric-value">$${candidate.tp1 || (candidate.price * 1.2).toFixed(2)}</span>
                    </div>
                </div>

                <div class="action-buttons" onclick="event.stopPropagation()">
                    ${candidate.category === 'trade_ready' ?
                        `<button class="btn btn-primary" onclick="window.amcTrader.showTradeModal('${candidate.ticker}')">
                            <i class="fas fa-shopping-cart"></i> Trade
                        </button>` :
                        `<button class="btn btn-watch" onclick="window.amcTrader.addToWatchlist('${candidate.ticker}')">
                            <i class="fas fa-eye"></i> Watch
                        </button>`
                    }
                    <button class="btn btn-secondary" onclick="window.amcTrader.showStockDetails('${candidate.ticker}')">
                        <i class="fas fa-chart-line"></i> Details
                    </button>
                </div>
            </div>
        `;
    }

    showStockDetails(ticker) {
        const candidate = this.candidates.find(c => c.ticker === ticker);
        if (!candidate) return;

        document.getElementById('modalTicker').textContent = ticker;

        const modalBody = document.getElementById('modalBody');
        modalBody.innerHTML = `
            <div class="stock-details">
                <div class="detail-section">
                    <h4>AlphaStack Analysis</h4>
                    <p><strong>Regime:</strong> ${candidate.regime.toUpperCase()}</p>
                    <p><strong>Score:</strong> ${(candidate.total_score || 0).toFixed(0)}/100</p>
                    <p><strong>Action:</strong> ${candidate.alphastack_action || candidate.category}</p>
                </div>

                <div class="detail-section">
                    <h4>Key Metrics</h4>
                    <p><strong>Price:</strong> $${candidate.price.toFixed(2)}</p>
                    <p><strong>Change:</strong> ${candidate.change_pct >= 0 ? '+' : ''}${candidate.change_pct.toFixed(1)}%</p>
                    <p><strong>Volume Surge:</strong> ${candidate.intraday_relative_volume.toFixed(1)}x</p>
                    <p><strong>Consecutive Up Days:</strong> ${candidate.consecutive_up_days || 0}</p>
                </div>

                <div class="detail-section">
                    <h4>Trading Levels</h4>
                    <p><strong>Entry:</strong> $${candidate.entry || candidate.price.toFixed(2)}</p>
                    <p><strong>Stop:</strong> $${candidate.stop || (candidate.price * 0.9).toFixed(2)}</p>
                    <p><strong>Target 1:</strong> $${candidate.tp1 || (candidate.price * 1.2).toFixed(2)}</p>
                    <p><strong>Target 2:</strong> $${candidate.tp2 || (candidate.price * 1.5).toFixed(2)}</p>
                </div>

                <div class="detail-section">
                    <h4>Thesis</h4>
                    <p>${candidate.thesis || `${ticker} shows ${candidate.regime} regime characteristics with strong momentum potential.`}</p>
                </div>
            </div>
        `;

        document.getElementById('stockModal').classList.add('active');
    }

    showTradeModal(ticker) {
        const candidate = this.candidates.find(c => c.ticker === ticker);
        if (!candidate) return;

        document.getElementById('tradeTicker').textContent = ticker;
        this.currentTradeCandidate = candidate;

        this.updateTradeSummary();
        document.getElementById('tradeModal').classList.add('active');
    }

    updateTradeSummary() {
        if (!this.currentTradeCandidate) return;

        const amount = parseFloat(document.getElementById('tradeAmount').value) || 100;
        const price = this.currentTradeCandidate.price;
        const shares = Math.floor(amount / price);
        const actualAmount = shares * price;

        const summaryEl = document.getElementById('tradeSummary');
        summaryEl.innerHTML = `
            <h4>Trade Summary</h4>
            <p><strong>Stock:</strong> ${this.currentTradeCandidate.ticker}</p>
            <p><strong>Price:</strong> $${price.toFixed(2)}</p>
            <p><strong>Shares:</strong> ${shares}</p>
            <p><strong>Total Cost:</strong> $${actualAmount.toFixed(2)}</p>
            <p><strong>Entry Target:</strong> $${this.currentTradeCandidate.entry || price.toFixed(2)}</p>
            <p><strong>Stop Loss:</strong> $${this.currentTradeCandidate.stop || (price * 0.9).toFixed(2)}</p>
        `;
    }

    async executeTrade() {
        if (!this.currentTradeCandidate) return;

        const amount = parseFloat(document.getElementById('tradeAmount').value) || 100;
        const orderType = document.getElementById('tradeType').value;

        const tradeData = {
            symbol: this.currentTradeCandidate.ticker,
            action: 'BUY',
            mode: 'paper', // Default to paper trading for safety
            notional_usd: amount,
            order_type: orderType
        };

        try {
            const response = await fetch(`${this.API_BASE}/trades/execute`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(tradeData)
            });

            const result = await response.json();

            if (result.success) {
                this.showToast(`Trade executed: ${this.currentTradeCandidate.ticker}`, 'success');
                this.closeModals();
            } else {
                this.showToast(`Trade failed: ${result.error || 'Unknown error'}`, 'error');
            }
        } catch (error) {
            console.error('Trade execution failed:', error);
            this.showToast('Trade execution failed. Please try again.', 'error');
        }
    }

    addToWatchlist(ticker) {
        // For now, just show a toast. In a real implementation, this would save to a watchlist
        this.showToast(`${ticker} added to watchlist`, 'success');
    }

    closeModals() {
        document.querySelectorAll('.modal').forEach(modal => {
            modal.classList.remove('active');
        });
        this.currentTradeCandidate = null;
    }

    showToast(message, type = 'success') {
        const toast = document.getElementById('toast');
        const toastMessage = document.getElementById('toastMessage');

        toastMessage.textContent = message;

        // Update icon based on type
        const icon = toast.querySelector('i');
        if (type === 'error') {
            icon.className = 'fas fa-exclamation-circle';
            toast.style.background = 'var(--secondary-color)';
        } else {
            icon.className = 'fas fa-check-circle';
            toast.style.background = 'var(--primary-color)';
        }

        toast.classList.add('active');

        setTimeout(() => {
            toast.classList.remove('active');
        }, 3000);
    }
}

// Initialize the application
window.amcTrader = new AMCTrader();

// Global functions for easier access
window.refreshDiscovery = () => window.amcTrader.loadDiscoveryData();