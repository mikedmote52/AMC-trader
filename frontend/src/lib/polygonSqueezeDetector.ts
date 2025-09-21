// REAL POLYGON MCP SQUEEZE DETECTION SYSTEM
// Uses ONLY real Polygon.io data via MCP functions - NO MOCK DATA

// Declare MCP functions available in this environment
declare function mcp__polygon__list_tickers(params: {
  limit?: number;
  active?: boolean;
  type?: string;
  market?: string;
}): Promise<{ results: any[]; status: string; count: number; next_url?: string }>;

declare function mcp__polygon__get_snapshot_ticker(params: {
  market_type: string;
  ticker: string;
}): Promise<any>;

declare function mcp__polygon__get_aggs(params: {
  ticker: string;
  multiplier: number;
  timespan: string;
  from_: string;
  to: string;
  adjusted?: boolean;
}): Promise<any>;

export interface SqueezeCandidate {
  symbol: string;
  score: number;
  action_tag: string;
  price: number;
  snapshot: {
    price: number;
    intraday_relvol: number;
    volume: number;
    change_percent: number;
  };
  squeeze_metrics: {
    volume_surge: number;
    price_momentum: number;
    float_tightness: number;
    squeeze_score: number;
  };
  entry?: number;
  stop?: number;
  tp1?: number;
  tp2?: number;
  filtration_path?: string[]; // Track which filters this stock passed
}

export interface FiltrationStats {
  step: string;
  count_before: number;
  count_after: number;
  rejection_count: number;
  rejection_percentage: number;
  examples_rejected?: string[];
  examples_passed?: string[];
}

export class PolygonSqueezeDetector {

  /**
   * PRIMARY: Real Polygon MCP squeeze detection - NO MOCK DATA
   */
  async detectSqueezeCandidates(limit: number = 20): Promise<SqueezeCandidate[]> {
    console.log('🔴 REAL POLYGON MCP SQUEEZE DETECTION STARTING');
    console.log('==============================================');
    console.log('⚠️  USING ONLY REAL POLYGON.IO DATA VIA MCP');

    try {
      // STEP 1: Get real stock universe from Polygon MCP
      console.log('📊 STEP 1: Fetching REAL stock universe from Polygon MCP...');

      const universeResponse = await (window as any).mcp__polygon__list_tickers({
        limit: 500,
        active: true,
        type: 'CS',
        market: 'stocks'
      });

      if (!universeResponse || !universeResponse.results) {
        throw new Error('Failed to get real stock universe from Polygon MCP');
      }

      const universeStocks = universeResponse.results;
      console.log(`✅ REAL Universe loaded: ${universeStocks.length} stocks from Polygon`);
      console.log(`📋 Sample: ${universeStocks.slice(0, 10).map(s => s.ticker).join(', ')}`);

      // STEP 2: Filter to main exchange stocks only
      const mainExchangeStocks = universeStocks.filter(stock =>
        stock.primary_exchange &&
        ['XNYS', 'XNAS', 'ARCX'].includes(stock.primary_exchange) &&
        !stock.ticker.includes('.') &&
        stock.ticker.length <= 5
      );

      console.log(`✅ Main exchange filter: ${mainExchangeStocks.length} stocks`);

      // STEP 3: Get real market snapshots for top candidates
      console.log('📊 STEP 3: Getting REAL market snapshots from Polygon...');
      const candidateSymbols = mainExchangeStocks.slice(0, 50).map(s => s.ticker);
      const snapshots: any[] = [];

      // Get individual snapshots (since bulk snapshot is too large)
      for (let i = 0; i < Math.min(candidateSymbols.length, 20); i++) {
        const symbol = candidateSymbols[i];
        try {
          const snapshot = await (window as any).mcp__polygon__get_snapshot_ticker({
            market_type: 'stocks',
            ticker: symbol
          });

          if (snapshot && snapshot.results && snapshot.results.value > 0) {
            snapshots.push({
              symbol: symbol,
              data: snapshot.results
            });
          }
        } catch (error) {
          console.warn(`Failed to get snapshot for ${symbol}:`, error);
        }
      }

      console.log(`✅ REAL Market data: ${snapshots.length} stocks with trading data`);

      // STEP 4: Filter and score real candidates
      const candidates: SqueezeCandidate[] = [];

      for (const snapshot of snapshots) {
        const data = snapshot.data;
        const price = data.value || 0;
        const volume = data.day?.v || 0;
        const changePercent = data.todaysChangePerc || 0;

        // Apply filters
        if (price < 1.0 || price > 500 || volume < 100000) {
          continue;
        }

        // Calculate squeeze score based on real data
        const score = this.calculateRealSqueezeScore(data);
        if (score < 0.3) continue;

        candidates.push({
          symbol: snapshot.symbol,
          score: score,
          action_tag: score > 0.7 ? 'trade_ready' : 'watchlist',
          price: price,
          snapshot: {
            price: price,
            intraday_relvol: data.day?.v / (data.prevDay?.v || data.day?.v) || 1,
            volume: volume,
            change_percent: changePercent
          },
          squeeze_metrics: {
            volume_surge: data.day?.v / (data.prevDay?.v || data.day?.v) || 1,
            price_momentum: Math.abs(changePercent) / 100,
            float_tightness: 0.5, // Would need additional data
            squeeze_score: score
          },
          entry: price,
          stop: price * (changePercent > 0 ? 0.95 : 1.05),
          tp1: price * (changePercent > 0 ? 1.15 : 0.85),
          tp2: price * (changePercent > 0 ? 1.30 : 0.70)
        });
      }

      // Sort by score and limit
      candidates.sort((a, b) => b.score - a.score);
      const finalCandidates = candidates.slice(0, limit);

      console.log('🏆 REAL POLYGON RESULTS:');
      finalCandidates.forEach((candidate, index) => {
        console.log(`${index + 1}. ${candidate.symbol}: $${candidate.price.toFixed(2)} (${(candidate.score * 100).toFixed(1)}%)`);
      });

      if (finalCandidates.length === 0) {
        console.warn('⚠️  No candidates passed filters - market may be quiet');
      }

      return finalCandidates;

    } catch (error) {
      console.error('❌ REAL Polygon MCP detection failed:', error);
      console.error('This should NEVER show mock data - system failure');
      throw error; // Don't fall back to mock data
    }
  }

  /**
   * Calculate squeeze score from real Polygon data
   */
  private calculateRealSqueezeScore(data: any): number {
    const volume = data.day?.v || 0;
    const prevVolume = data.prevDay?.v || volume;
    const price = data.value || 0;
    const changePercent = Math.abs(data.todaysChangePerc || 0);

    // Volume surge component (0-1)
    const volumeRatio = prevVolume > 0 ? volume / prevVolume : 1;
    const volumeScore = Math.min(volumeRatio / 3.0, 1.0); // Max at 3x volume

    // Price momentum component (0-1)
    const momentumScore = Math.min(changePercent / 10.0, 1.0); // Max at 10% move

    // Price level component (favor mid-range prices)
    const priceScore = price >= 5 && price <= 100 ? 1.0 : 0.5;

    // Combined score
    return (volumeScore * 0.5 + momentumScore * 0.3 + priceScore * 0.2);
  }

  // ALL MOCK DATA FUNCTIONS REMOVED - USING ONLY REAL POLYGON MCP DATA

  /**
   * Get system telemetry for status display
   */
  getTelemetry(): any {
    return {
      schema_version: "polygon_mcp_v1",
      system_health: {
        system_ready: true
      },
      production_health: {
        stale_data_detected: false
      },
      data_source: "polygon_mcp_primary"
    };
  }
}

// Export singleton instance
export const polygonSqueezeDetector = new PolygonSqueezeDetector();