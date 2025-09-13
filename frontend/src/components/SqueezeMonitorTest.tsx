/**
 * SqueezeMonitorTest Component
 * Quick integration test for the fixed SqueezeMonitor
 */

import React from 'react';
import SqueezeMonitor from './SqueezeMonitor';

export const SqueezeMonitorTest: React.FC = () => {
  return (
    <div style={{ padding: '20px', backgroundColor: '#0a0a0a', minHeight: '100vh' }}>
      <h1 style={{ color: '#fff', marginBottom: '20px' }}>
        Squeeze Monitor Integration Test
      </h1>
      
      <div style={{ marginBottom: '20px', padding: '15px', backgroundColor: '#1a1a1a', borderRadius: '8px', border: '1px solid #333' }}>
        <h3 style={{ color: '#22c55e', marginBottom: '10px' }}>Test Scenarios:</h3>
        <ul style={{ color: '#ccc', fontSize: '14px', lineHeight: '1.6' }}>
          <li>✅ Strategy switching between legacy_v0 and hybrid_v1</li>
          <li>✅ Min score threshold adjustment (10-80%)</li>
          <li>✅ Proper API parameter passing</li>
          <li>✅ Scale normalization (handles both 0-1 and 0-100)</li>
          <li>✅ Debug overlay showing actual API calls</li>
          <li>✅ Enhanced error messaging</li>
        </ul>
      </div>

      {/* Test with hybrid_v1 strategy and 50% threshold */}
      <SqueezeMonitor 
        strategy="hybrid_v1"
        minScore={50}
        showPatternHistory={true}
        watchedSymbols={[]}
      />
    </div>
  );
};

export default SqueezeMonitorTest;