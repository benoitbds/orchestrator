// Simple test script to verify proxy configuration
// Run this after starting the dev server with: node test-proxy.js

async function testProxy() {
  try {
    console.log('Testing proxy configuration...');
    
    // Test /api/projects endpoint
    const response = await fetch('http://localhost:3000/api/projects');
    console.log(`Response status: ${response.status}`);
    console.log(`Response headers:`, Object.fromEntries(response.headers.entries()));
    
    if (response.ok) {
      const data = await response.json();
      console.log('✅ Proxy working! Received data:', data);
    } else {
      console.log('❌ Proxy failed with status:', response.status);
      console.log('Response text:', await response.text());
    }
  } catch (error) {
    console.error('❌ Network error:', error.message);
  }
}

testProxy();