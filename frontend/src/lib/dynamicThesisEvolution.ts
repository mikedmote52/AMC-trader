#!/usr/bin/env typescript
/**
 * Dynamic Thesis Evolution System
 * Updates thesis reasoning based on market conditions and learning outcomes
 */

import { API_BASE } from "../config";

export type ThesisStatus = "developing" | "confirmed" | "invalidated" | "evolved";

export type DynamicThesis = {
  symbol: string;
  original_thesis: string;
  current_thesis: string;
  evolution_history: ThesisEvolution[];
  status: ThesisStatus;
  confidence: number;
  last_updated: string;
  market_conditions: MarketCondition[];
  performance_impact: number; // How much the thesis evolution affected returns
};

export type ThesisEvolution = {
  timestamp: string;
  reason: string;
  old_thesis: string;
  new_thesis: string;
  trigger: "market_change" | "performance_data" | "learning_insight" | "manual";
  confidence_change: number;
};

export type MarketCondition = {
  type: "volatility" | "volume" | "momentum" | "sector_rotation" | "news_sentiment";
  value: number;
  change_pct: number;
  impact_on_thesis: "positive" | "negative" | "neutral";
};

class DynamicThesisEvolutionEngine {
  private theses: Map<string, DynamicThesis> = new Map();

  constructor() {
    this.loadTheses();
  }

  /**
   * Get evolved thesis for a symbol
   */
  public getEvolutionData(symbol: string): DynamicThesis | null {
    return this.theses.get(symbol) || null;
  }

  /**
   * Update thesis based on market conditions
   */
  public async evolveThesis(symbol: string, marketData: any): Promise<DynamicThesis | null> {
    const existing = this.theses.get(symbol);
    if (!existing) {
      return null;
    }

    const marketConditions = this.analyzeMarketConditions(marketData);
    const shouldEvolve = this.shouldEvolveThesis(existing, marketConditions);

    if (shouldEvolve) {
      const newThesis = await this.generateEvolvedThesis(existing, marketConditions);
      return this.updateThesis(symbol, newThesis, marketConditions);
    }

    return existing;
  }

  /**
   * Analyze current market conditions
   */
  private analyzeMarketConditions(marketData: any): MarketCondition[] {
    const conditions: MarketCondition[] = [];

    // Volatility analysis
    if (marketData.atr_pct) {
      conditions.push({
        type: "volatility",
        value: marketData.atr_pct,
        change_pct: marketData.atr_change_pct || 0,
        impact_on_thesis: marketData.atr_pct > 0.08 ? "positive" :
                         marketData.atr_pct < 0.03 ? "negative" : "neutral"
      });
    }

    // Volume analysis
    if (marketData.relative_volume) {
      conditions.push({
        type: "volume",
        value: marketData.relative_volume,
        change_pct: marketData.volume_change_pct || 0,
        impact_on_thesis: marketData.relative_volume > 2.0 ? "positive" :
                         marketData.relative_volume < 0.5 ? "negative" : "neutral"
      });
    }

    // Momentum analysis
    if (marketData.price_change_pct) {
      conditions.push({
        type: "momentum",
        value: marketData.price_change_pct,
        change_pct: marketData.momentum_change || 0,
        impact_on_thesis: Math.abs(marketData.price_change_pct) > 5 ? "positive" : "neutral"
      });
    }

    return conditions;
  }

  /**
   * Determine if thesis should evolve
   */
  private shouldEvolveThesis(thesis: DynamicThesis, conditions: MarketCondition[]): boolean {
    // Don't evolve too frequently
    const timeSinceUpdate = Date.now() - new Date(thesis.last_updated).getTime();
    if (timeSinceUpdate < 4 * 60 * 60 * 1000) { // 4 hours minimum
      return false;
    }

    // Check for significant market condition changes
    const significantChanges = conditions.filter(c =>
      Math.abs(c.change_pct) > 20 || // 20%+ change in condition
      (c.type === "volatility" && c.value > 0.12) || // Very high volatility
      (c.type === "volume" && c.value > 5.0) // Exceptional volume
    );

    return significantChanges.length > 0;
  }

  /**
   * Generate evolved thesis based on conditions
   */
  private async generateEvolvedThesis(existing: DynamicThesis, conditions: MarketCondition[]): Promise<string> {
    // Enhanced thesis evolution logic
    const volatility = conditions.find(c => c.type === "volatility");
    const volume = conditions.find(c => c.type === "volume");
    const momentum = conditions.find(c => c.type === "momentum");

    let evolution = existing.current_thesis;

    // Volatility-based evolution
    if (volatility) {
      if (volatility.value > 0.10 && volatility.impact_on_thesis === "positive") {
        evolution += ` Volatility expansion (${(volatility.value * 100).toFixed(1)}% ATR) supports breakout potential.`;
      } else if (volatility.value < 0.03) {
        evolution += ` Low volatility (${(volatility.value * 100).toFixed(1)}% ATR) suggests consolidation phase.`;
      }
    }

    // Volume-based evolution
    if (volume) {
      if (volume.value > 3.0) {
        evolution += ` Exceptional volume surge (${volume.value.toFixed(1)}x avg) indicates institutional interest.`;
      } else if (volume.value < 0.7) {
        evolution += ` Below-average volume suggests lack of conviction in current move.`;
      }
    }

    // Momentum-based evolution
    if (momentum) {
      if (Math.abs(momentum.value) > 8) {
        evolution += ` Strong ${momentum.value > 0 ? 'upward' : 'downward'} momentum (${momentum.value.toFixed(1)}%) creates ${momentum.value > 0 ? 'continuation' : 'reversal'} potential.`;
      }
    }

    return evolution;
  }

  /**
   * Update thesis with evolution
   */
  private updateThesis(symbol: string, newThesis: string, conditions: MarketCondition[]): DynamicThesis {
    const existing = this.theses.get(symbol)!;

    const evolution: ThesisEvolution = {
      timestamp: new Date().toISOString(),
      reason: this.generateEvolutionReason(conditions),
      old_thesis: existing.current_thesis,
      new_thesis: newThesis,
      trigger: "market_change",
      confidence_change: this.calculateConfidenceChange(conditions)
    };

    const updated: DynamicThesis = {
      ...existing,
      current_thesis: newThesis,
      evolution_history: [...existing.evolution_history, evolution],
      confidence: Math.max(0.1, Math.min(1.0, existing.confidence + evolution.confidence_change)),
      last_updated: new Date().toISOString(),
      market_conditions: conditions,
      status: this.determineThesisStatus(existing, evolution)
    };

    this.theses.set(symbol, updated);
    this.saveTheses();

    return updated;
  }

  /**
   * Generate human-readable evolution reason
   */
  private generateEvolutionReason(conditions: MarketCondition[]): string {
    const reasons: string[] = [];

    conditions.forEach(condition => {
      switch (condition.type) {
        case "volatility":
          if (condition.value > 0.10) {
            reasons.push("volatility expansion");
          } else if (condition.value < 0.03) {
            reasons.push("volatility compression");
          }
          break;
        case "volume":
          if (condition.value > 3.0) {
            reasons.push("exceptional volume surge");
          } else if (condition.value < 0.7) {
            reasons.push("volume deterioration");
          }
          break;
        case "momentum":
          if (Math.abs(condition.value) > 8) {
            reasons.push(`strong ${condition.value > 0 ? 'bullish' : 'bearish'} momentum`);
          }
          break;
      }
    });

    return reasons.length > 0 ? reasons.join(", ") : "market condition changes";
  }

  /**
   * Calculate confidence change based on conditions
   */
  private calculateConfidenceChange(conditions: MarketCondition[]): number {
    let change = 0;

    conditions.forEach(condition => {
      switch (condition.impact_on_thesis) {
        case "positive":
          change += 0.1;
          break;
        case "negative":
          change -= 0.15;
          break;
        default:
          // neutral - no change
      }
    });

    return Math.max(-0.3, Math.min(0.3, change)); // Cap changes at ±30%
  }

  /**
   * Determine thesis status after evolution
   */
  private determineThesisStatus(existing: DynamicThesis, evolution: ThesisEvolution): ThesisStatus {
    // If confidence dropped significantly, thesis may be invalidated
    if (evolution.confidence_change < -0.2) {
      return "invalidated";
    }

    // If this is a major evolution
    if (evolution.new_thesis.length > existing.original_thesis.length * 1.5) {
      return "evolved";
    }

    // If confidence is high after evolution
    if (existing.confidence + evolution.confidence_change > 0.8) {
      return "confirmed";
    }

    return "developing";
  }

  /**
   * Get thesis evolution summary for display
   */
  public getEvolutionSummary(symbol: string): {
    hasEvolved: boolean;
    evolutionCount: number;
    latestEvolution?: ThesisEvolution;
    confidenceTrend: "improving" | "declining" | "stable";
  } {
    const thesis = this.theses.get(symbol);
    if (!thesis) {
      return { hasEvolved: false, evolutionCount: 0, confidenceTrend: "stable" };
    }

    const evolutionCount = thesis.evolution_history.length;
    const latestEvolution = evolutionCount > 0 ? thesis.evolution_history[evolutionCount - 1] : undefined;

    // Determine confidence trend
    let confidenceTrend: "improving" | "declining" | "stable" = "stable";
    if (evolutionCount >= 2) {
      const recent = thesis.evolution_history.slice(-2);
      const avgChange = recent.reduce((sum, e) => sum + e.confidence_change, 0) / recent.length;
      confidenceTrend = avgChange > 0.05 ? "improving" : avgChange < -0.05 ? "declining" : "stable";
    }

    return {
      hasEvolved: evolutionCount > 0,
      evolutionCount,
      latestEvolution,
      confidenceTrend
    };
  }

  /**
   * Load theses from storage
   */
  private loadTheses(): void {
    try {
      const stored = localStorage.getItem('amc-dynamic-theses');
      if (stored) {
        const thesesArray: DynamicThesis[] = JSON.parse(stored);
        for (const thesis of thesesArray) {
          this.theses.set(thesis.symbol, thesis);
        }
      }

      // Load mock theses for demonstration
      this.loadMockTheses();
    } catch (error) {
      console.warn('Failed to load dynamic theses:', error);
      this.loadMockTheses();
    }
  }

  /**
   * Load mock theses for demonstration
   */
  private loadMockTheses(): void {
    const mockTheses: DynamicThesis[] = [
      {
        symbol: "QUBT",
        original_thesis: "Quantum computing breakthrough potential with institutional backing",
        current_thesis: "Quantum computing breakthrough potential with institutional backing. Volatility expansion (8.2% ATR) supports breakout potential. Exceptional volume surge (4.3x avg) indicates institutional interest.",
        evolution_history: [
          {
            timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
            reason: "volatility expansion, exceptional volume surge",
            old_thesis: "Quantum computing breakthrough potential with institutional backing",
            new_thesis: "Quantum computing breakthrough potential with institutional backing. Volatility expansion (8.2% ATR) supports breakout potential. Exceptional volume surge (4.3x avg) indicates institutional interest.",
            trigger: "market_change",
            confidence_change: 0.2
          }
        ],
        status: "evolved",
        confidence: 0.85,
        last_updated: new Date().toISOString(),
        market_conditions: [
          { type: "volatility", value: 0.082, change_pct: 45, impact_on_thesis: "positive" },
          { type: "volume", value: 4.3, change_pct: 330, impact_on_thesis: "positive" }
        ],
        performance_impact: 12.5
      },
      {
        symbol: "VIGL",
        original_thesis: "VIGL pattern development with float squeeze potential",
        current_thesis: "VIGL pattern development with float squeeze potential. Low volatility (2.8% ATR) suggests consolidation phase. Below-average volume suggests lack of conviction in current move.",
        evolution_history: [
          {
            timestamp: new Date(Date.now() - 6 * 60 * 60 * 1000).toISOString(),
            reason: "volume deterioration",
            old_thesis: "VIGL pattern development with float squeeze potential",
            new_thesis: "VIGL pattern development with float squeeze potential. Low volatility (2.8% ATR) suggests consolidation phase. Below-average volume suggests lack of conviction in current move.",
            trigger: "market_change",
            confidence_change: -0.15
          }
        ],
        status: "developing",
        confidence: 0.62,
        last_updated: new Date().toISOString(),
        market_conditions: [
          { type: "volatility", value: 0.028, change_pct: -35, impact_on_thesis: "negative" },
          { type: "volume", value: 0.6, change_pct: -40, impact_on_thesis: "negative" }
        ],
        performance_impact: -3.2
      }
    ];

    for (const thesis of mockTheses) {
      this.theses.set(thesis.symbol, thesis);
    }

    this.saveTheses();
  }

  /**
   * Save theses to storage
   */
  private saveTheses(): void {
    try {
      const thesesArray = Array.from(this.theses.values());
      localStorage.setItem('amc-dynamic-theses', JSON.stringify(thesesArray));
    } catch (error) {
      console.warn('Failed to save dynamic theses:', error);
    }
  }
}

// Global instance
export const dynamicThesisEngine = new DynamicThesisEvolutionEngine();

// Hook for React components
export const useThesisEvolution = () => {
  return {
    getEvolutionData: (symbol: string) => dynamicThesisEngine.getEvolutionData(symbol),
    getEvolutionSummary: (symbol: string) => dynamicThesisEngine.getEvolutionSummary(symbol),
    evolveThesis: (symbol: string, marketData: any) => dynamicThesisEngine.evolveThesis(symbol, marketData)
  };
};