/**
 * BMS Discovery Page
 * Clean unified discovery page based on June-July winner patterns
 * Replaces: DiscoveryPage.tsx, SqueezePage.tsx
 */

import React, { useState, useEffect } from 'react';
import BMSDiscovery from '../components/BMSDiscovery';
import { getJSON } from '../lib/api';

interface SystemHealth {
  status: string;
  engine: string;
  price_bounds: {
    min: number;
    max: number;
  };
  dollar_volume_min_m: number;
  options_required: boolean;
  components: {
    bms_engine: string;
    polygon_api: string;
    config: string;
  };
}

interface WinnersAnalysis {
  analysis_summary: {
    total_symbols: number;
    would_catch_now: number;
    catch_rate: number;
    big_winners_total: number;
    big_winners_caught: number;
    big_winner_catch_rate: number;
  };
}

const BMSDiscoveryPage: React.FC = () => {
  const [viewMode, setViewMode] = useState<'all' | 'trade-ready' | 'monitor'>('all');
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [winnersAnalysis, setWinnersAnalysis] = useState<WinnersAnalysis | null>(null);
  const [showSystemInfo, setShowSystemInfo] = useState(false);

  useEffect(() => {
    // Fetch system health
    const fetchHealth = async () => {
      try {
        const health = await getJSON('/discovery/health');
        setSystemHealth(health);
      } catch (err) {
        console.error('Failed to fetch system health:', err);
      }
    };

    // Fetch winners analysis
    const fetchWinnersAnalysis = async () => {
      try {
        const analysis = await getJSON('/discovery/winners-analysis');
        setWinnersAnalysis(analysis);
      } catch (err) {
        console.error('Failed to fetch winners analysis:', err);
      }
    };

    fetchHealth();
    fetchWinnersAnalysis();
  }, []);

  const getHealthStatusColor = (status: string): string => {
    switch (status) {
      case 'healthy': return 'text-green-600';
      case 'degraded': return 'text-yellow-600';
      default: return 'text-red-600';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        
        {/* Page Header */}
        <div className="mb-8">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                AMC-TRADER Discovery
              </h1>
              <p className="text-lg text-gray-600 mb-4">
                Breakout Momentum Score (BMS) System • Based on June-July 2025 Winners
              </p>
              
              {/* System Health Indicator */}
              {systemHealth && (
                <div className="flex items-center space-x-4">
                  <div className="flex items-center space-x-2">
                    <div className={`h-3 w-3 rounded-full ${
                      systemHealth.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'
                    }`}></div>
                    <span className={`text-sm font-medium ${getHealthStatusColor(systemHealth.status)}`}>
                      {systemHealth.engine}
                    </span>
                  </div>
                  <button
                    onClick={() => setShowSystemInfo(!showSystemInfo)}
                    className="text-sm text-blue-600 hover:text-blue-800"
                  >
                    System Info
                  </button>
                </div>
              )}
            </div>

            {/* Winners Analysis Summary */}
            {winnersAnalysis && (
              <div className="bg-white border rounded-lg p-4 min-w-[300px]">
                <h3 className="font-semibold text-gray-900 mb-2">Historical Validation</h3>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Overall Catch Rate:</span>
                    <span className="font-medium text-green-600">
                      {winnersAnalysis.analysis_summary.catch_rate.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Big Winners (100%+):</span>
                    <span className="font-medium text-blue-600">
                      {winnersAnalysis.analysis_summary.big_winners_caught}/{winnersAnalysis.analysis_summary.big_winners_total}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Big Winner Rate:</span>
                    <span className="font-medium text-purple-600">
                      {winnersAnalysis.analysis_summary.big_winner_catch_rate.toFixed(1)}%
                    </span>
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* System Info Panel */}
          {showSystemInfo && systemHealth && (
            <div className="mt-4 bg-blue-50 border border-blue-200 rounded-lg p-4">
              <h4 className="font-semibold text-blue-900 mb-2">System Status</h4>
              
              {/* Universe Configuration */}
              <div className="mb-3 p-2 bg-white rounded">
                <span className="text-blue-700 font-medium">Universe: </span>
                <span className="text-gray-900">
                  ${systemHealth.price_bounds.min} – ${systemHealth.price_bounds.max}, 
                  ≥ ${systemHealth.dollar_volume_min_m}M $Vol
                  {systemHealth.options_required && ', Liquid Options Required'}
                </span>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-sm">
                <div>
                  <span className="text-blue-600">BMS Engine:</span>
                  <span className={`ml-2 ${getHealthStatusColor(systemHealth.components.bms_engine)}`}>
                    {systemHealth.components.bms_engine}
                  </span>
                </div>
                <div>
                  <span className="text-blue-600">Polygon API:</span>
                  <span className={`ml-2 ${getHealthStatusColor(systemHealth.components.polygon_api)}`}>
                    {systemHealth.components.polygon_api}
                  </span>
                </div>
                <div>
                  <span className="text-blue-600">Configuration:</span>
                  <span className={`ml-2 ${getHealthStatusColor(systemHealth.components.config)}`}>
                    {systemHealth.components.config}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* View Mode Selector */}
        <div className="mb-6">
          <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg inline-flex">
            <button
              onClick={() => setViewMode('all')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                viewMode === 'all'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              All Candidates
            </button>
            <button
              onClick={() => setViewMode('trade-ready')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                viewMode === 'trade-ready'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              🚀 Trade Ready (75+)
            </button>
            <button
              onClick={() => setViewMode('monitor')}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                viewMode === 'monitor'
                  ? 'bg-white text-gray-900 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              👁️ Monitor (60-74)
            </button>
          </div>
        </div>

        {/* BMS Discovery Component */}
        <div className="bg-white rounded-lg shadow">
          <div className="p-6">
            {viewMode === 'all' && (
              <BMSDiscovery
                maxResults={25}
                showOnlyTradeReady={false}
                autoRefresh={true}
                refreshInterval={30000}
              />
            )}
            {viewMode === 'trade-ready' && (
              <BMSDiscovery
                maxResults={15}
                showOnlyTradeReady={true}
                autoRefresh={true}
                refreshInterval={15000} // Faster refresh for trade-ready
              />
            )}
            {viewMode === 'monitor' && (
              <div>
                <div className="mb-4 text-center">
                  <h3 className="text-lg font-semibold text-gray-900">Monitor Candidates</h3>
                  <p className="text-gray-600">Opportunities to watch (BMS Score 60-74)</p>
                </div>
                <BMSDiscovery
                  maxResults={20}
                  showOnlyTradeReady={false}
                  autoRefresh={true}
                  refreshInterval={60000} // Slower refresh for monitor
                />
              </div>
            )}
          </div>
        </div>

        {/* Winner Pattern Analysis */}
        <div className="mt-8 bg-white rounded-lg shadow">
          <div className="p-6">
            <h3 className="text-xl font-semibold text-gray-900 mb-4">
              System Foundation: June-July 2025 Winners
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4 text-sm">
              <div className="bg-green-50 p-4 rounded-lg">
                <h4 className="font-semibold text-green-900">Big Winners (100%+)</h4>
                <ul className="mt-2 space-y-1 text-green-800">
                  <li>• VIGL: +324% (Volume surge pattern)</li>
                  <li>• CRWV: +171% (Squeeze setup)</li>
                  <li>• AEVA: +162% (Volatility expansion)</li>
                  <li>• CRDO: +108% (Momentum acceleration)</li>
                </ul>
              </div>
              
              <div className="bg-blue-50 p-4 rounded-lg">
                <h4 className="font-semibold text-blue-900">Solid Gains (15-66%)</h4>
                <ul className="mt-2 space-y-1 text-blue-800">
                  <li>• SEZL: +66% (Float tightness)</li>
                  <li>• SMCI: +35% (Momentum + catalyst)</li>
                  <li>• TSLA, REKR, AMD, NVDA: +15-21%</li>
                  <li>• QUBT, AVGO, RGTI, SPOT: +7-15%</li>
                </ul>
              </div>
              
              <div className="bg-red-50 p-4 rounded-lg">
                <h4 className="font-semibold text-red-900">Risk Filter Success</h4>
                <div className="mt-2 text-red-800">
                  <p>• WOLF: -25% (Only loser)</p>
                  <p className="mt-2 text-sm">
                    The BMS system would have identified and rejected WOLF based on poor momentum and risk factors.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer Info */}
        <div className="mt-8 text-center text-gray-500 text-sm">
          <p>
            BMS Discovery System v1.0 • Real-time scanning of 5000+ stocks • 
            Based on June-July 2025 winner patterns
          </p>
        </div>
      </div>
    </div>
  );
};

export default BMSDiscoveryPage;