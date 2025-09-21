#!/usr/bin/env typescript
/**
 * Circuit Breaker Pattern for Enhanced Portfolio System
 * Provides safe fallback to current system when enhancements fail
 */

export type CircuitBreakerState = "closed" | "open" | "half-open";

export type FailureEvent = {
  timestamp: string;
  component: "unified_decision" | "learning_system" | "thesis_evolution" | "general";
  error: string;
  severity: "low" | "medium" | "high" | "critical";
};

class CircuitBreaker {
  private state: CircuitBreakerState = "closed";
  private failures: FailureEvent[] = [];
  private lastFailureTime: number = 0;
  private consecutiveFailures: number = 0;

  // Circuit breaker thresholds
  private readonly maxFailures = 5;
  private readonly timeoutDuration = 60000; // 1 minute
  private readonly halfOpenRetryTimeout = 30000; // 30 seconds

  constructor() {
    this.loadState();
    this.startHealthCheck();
  }

  /**
   * Execute a function with circuit breaker protection
   */
  public async execute<T>(
    operation: () => Promise<T>,
    fallback: () => T,
    component: FailureEvent["component"]
  ): Promise<T> {
    if (this.state === "open") {
      console.warn(`🔒 Circuit breaker OPEN for ${component} - using fallback`);
      return fallback();
    }

    try {
      const result = await operation();

      // Success - reset if we were in half-open state
      if (this.state === "half-open") {
        this.reset();
      }

      return result;
    } catch (error) {
      const failureEvent: FailureEvent = {
        timestamp: new Date().toISOString(),
        component,
        error: error instanceof Error ? error.message : String(error),
        severity: this.determineSeverity(error, component)
      };

      this.recordFailure(failureEvent);

      console.warn(`⚠️ Circuit breaker recorded failure for ${component}:`, error);
      return fallback();
    }
  }

  /**
   * Execute synchronous function with circuit breaker protection
   */
  public executeSync<T>(
    operation: () => T,
    fallback: () => T,
    component: FailureEvent["component"]
  ): T {
    if (this.state === "open") {
      console.warn(`🔒 Circuit breaker OPEN for ${component} - using fallback`);
      return fallback();
    }

    try {
      const result = operation();

      // Success - reset if we were in half-open state
      if (this.state === "half-open") {
        this.reset();
      }

      return result;
    } catch (error) {
      const failureEvent: FailureEvent = {
        timestamp: new Date().toISOString(),
        component,
        error: error instanceof Error ? error.message : String(error),
        severity: this.determineSeverity(error, component)
      };

      this.recordFailure(failureEvent);

      console.warn(`⚠️ Circuit breaker recorded failure for ${component}:`, error);
      return fallback();
    }
  }

  /**
   * Record a failure and update circuit breaker state
   */
  private recordFailure(failure: FailureEvent): void {
    this.failures.push(failure);
    this.consecutiveFailures++;
    this.lastFailureTime = Date.now();

    // Keep only recent failures (last 10 minutes)
    const tenMinutesAgo = Date.now() - 10 * 60 * 1000;
    this.failures = this.failures.filter(f =>
      new Date(f.timestamp).getTime() > tenMinutesAgo
    );

    // Check if we should open the circuit
    if (this.shouldOpenCircuit(failure)) {
      this.open();
    }

    this.saveState();
  }

  /**
   * Determine if circuit should be opened
   */
  private shouldOpenCircuit(latestFailure: FailureEvent): boolean {
    // Immediate open for critical failures
    if (latestFailure.severity === "critical") {
      return true;
    }

    // Open if too many consecutive failures
    if (this.consecutiveFailures >= this.maxFailures) {
      return true;
    }

    // Open if too many failures in recent time window
    const recentFailures = this.failures.filter(f =>
      Date.now() - new Date(f.timestamp).getTime() < this.timeoutDuration
    );

    return recentFailures.length >= this.maxFailures;
  }

  /**
   * Open the circuit breaker
   */
  private open(): void {
    this.state = "open";
    console.warn("🚨 Circuit breaker OPENED - Enhanced features disabled, using fallback system");

    // Schedule transition to half-open state
    setTimeout(() => {
      if (this.state === "open") {
        this.halfOpen();
      }
    }, this.halfOpenRetryTimeout);

    this.saveState();
  }

  /**
   * Transition to half-open state
   */
  private halfOpen(): void {
    this.state = "half-open";
    console.info("🔄 Circuit breaker HALF-OPEN - Testing enhanced features");
    this.saveState();
  }

  /**
   * Reset circuit breaker to closed state
   */
  private reset(): void {
    this.state = "closed";
    this.consecutiveFailures = 0;
    console.info("✅ Circuit breaker CLOSED - Enhanced features fully operational");
    this.saveState();
  }

  /**
   * Determine failure severity
   */
  private determineSeverity(error: any, component: FailureEvent["component"]): FailureEvent["severity"] {
    const errorMessage = error instanceof Error ? error.message : String(error);

    // Critical errors that should immediately open circuit
    if (errorMessage.includes("Cannot read properties") ||
        errorMessage.includes("TypeError") ||
        errorMessage.includes("ReferenceError")) {
      return "critical";
    }

    // High severity for core components
    if (component === "unified_decision" || component === "learning_system") {
      return "high";
    }

    // Medium severity for thesis evolution
    if (component === "thesis_evolution") {
      return "medium";
    }

    return "low";
  }

  /**
   * Get current circuit breaker status
   */
  public getStatus(): {
    state: CircuitBreakerState;
    consecutiveFailures: number;
    recentFailures: number;
    lastFailureTime: string | null;
    isOperational: boolean;
  } {
    const recentFailures = this.failures.filter(f =>
      Date.now() - new Date(f.timestamp).getTime() < this.timeoutDuration
    );

    return {
      state: this.state,
      consecutiveFailures: this.consecutiveFailures,
      recentFailures: recentFailures.length,
      lastFailureTime: this.lastFailureTime > 0 ? new Date(this.lastFailureTime).toISOString() : null,
      isOperational: this.state === "closed"
    };
  }

  /**
   * Get failure history for debugging
   */
  public getFailureHistory(): FailureEvent[] {
    return [...this.failures];
  }

  /**
   * Manually reset circuit breaker (for emergency recovery)
   */
  public manualReset(): void {
    console.info("🔧 Manual circuit breaker reset requested");
    this.failures = [];
    this.consecutiveFailures = 0;
    this.lastFailureTime = 0;
    this.reset();
  }

  /**
   * Health check to transition from open to half-open
   */
  private startHealthCheck(): void {
    setInterval(() => {
      if (this.state === "open" &&
          Date.now() - this.lastFailureTime > this.halfOpenRetryTimeout) {
        this.halfOpen();
      }
    }, 10000); // Check every 10 seconds
  }

  /**
   * Save state to localStorage
   */
  private saveState(): void {
    try {
      const state = {
        state: this.state,
        failures: this.failures,
        consecutiveFailures: this.consecutiveFailures,
        lastFailureTime: this.lastFailureTime
      };
      localStorage.setItem('amc-circuit-breaker', JSON.stringify(state));
    } catch (error) {
      console.warn('Failed to save circuit breaker state:', error);
    }
  }

  /**
   * Load state from localStorage
   */
  private loadState(): void {
    try {
      const stored = localStorage.getItem('amc-circuit-breaker');
      if (stored) {
        const state = JSON.parse(stored);
        this.state = state.state || "closed";
        this.failures = state.failures || [];
        this.consecutiveFailures = state.consecutiveFailures || 0;
        this.lastFailureTime = state.lastFailureTime || 0;

        // Reset if too much time has passed
        if (Date.now() - this.lastFailureTime > 24 * 60 * 60 * 1000) { // 24 hours
          this.reset();
        }
      }
    } catch (error) {
      console.warn('Failed to load circuit breaker state:', error);
      this.reset();
    }
  }
}

// Global instance
export const circuitBreaker = new CircuitBreaker();

// Hook for React components
export const useCircuitBreaker = () => {
  return {
    execute: circuitBreaker.execute.bind(circuitBreaker),
    executeSync: circuitBreaker.executeSync.bind(circuitBreaker),
    getStatus: () => circuitBreaker.getStatus(),
    getFailureHistory: () => circuitBreaker.getFailureHistory(),
    manualReset: () => circuitBreaker.manualReset()
  };
};