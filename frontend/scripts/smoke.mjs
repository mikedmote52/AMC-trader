#!/usr/bin/env node
/**
 * AlphaStack API Smoke Test
 * Quick verification script for local testing
 */

const API = process.env.VITE_API_BASE || 'https://amc-trader.onrender.com';

console.log('🔍 AlphaStack API Smoke Test');
console.log(`API Base: ${API}`);
console.log('');

async function testEndpoint(endpoint, description) {
  try {
    console.log(`Testing: ${description}`);
    const url = `${API}${endpoint}`;
    console.log(`URL: ${url}`);

    const response = await fetch(url, {
      cache: 'no-store',
      headers: {
        'Accept': 'application/json'
      }
    });

    console.log(`Status: ${response.status} ${response.statusText}`);

    if (!response.ok) {
      console.log('❌ Failed');
      console.log('');
      return false;
    }

    const data = await response.json();
    console.log('✅ Success');
    console.log('Response:', JSON.stringify(data, null, 2));
    console.log('');
    return true;

  } catch (error) {
    console.log('❌ Error:', error.message);
    console.log('');
    return false;
  }
}

async function main() {
  const tests = [
    ['/v1/candidates/top?limit=3', 'Top 3 Candidates'],
    ['/v1/explosive', 'Explosive Candidates'],
    ['/v1/telemetry', 'System Telemetry']
  ];

  let passed = 0;

  for (const [endpoint, description] of tests) {
    if (await testEndpoint(endpoint, description)) {
      passed++;
    }
  }

  console.log('📊 Results:');
  console.log(`Passed: ${passed}/${tests.length}`);

  if (passed === tests.length) {
    console.log('🎉 All tests passed!');
    process.exit(0);
  } else {
    console.log('❌ Some tests failed');
    process.exit(1);
  }
}

main().catch(console.error);