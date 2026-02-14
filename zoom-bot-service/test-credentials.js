/**
 * Test if Zoom API credentials work at all
 */
const jwt = require('jsonwebtoken');
const axios = require('axios');
require('dotenv').config();

async function test() {
  console.log('\n🔍 Testing Zoom Credentials\n');

  // Test 1: API Key/Secret (for REST API)
  const API_KEY = process.env.ZOOM_API_KEY;
  const API_SECRET = process.env.ZOOM_API_SECRET;

  if (API_KEY && API_SECRET) {
    console.log('1️⃣ Testing API credentials (REST API access)...');
    try {
      const token = jwt.sign({ iss: API_KEY, exp: Math.floor(Date.now() / 1000) + 3600 }, API_SECRET);
      const response = await axios.get('https://api.zoom.us/v2/users/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      console.log('✅ API credentials WORK!');
      console.log('   Account:', response.data.email);
      console.log('   Type:', response.data.type);
      console.log('   Account ID:', response.data.account_id);
    } catch (error) {
      console.log('❌ API credentials FAILED:', error.response?.data || error.message);
    }
  } else {
    console.log('⚠️  No API credentials found');
  }

  console.log('');

  // Test 2: SDK Key/Secret (for Meeting SDK)
  const SDK_KEY = process.env.ZOOM_SDK_KEY;
  const SDK_SECRET = process.env.ZOOM_SDK_SECRET;

  if (SDK_KEY && SDK_SECRET) {
    console.log('2️⃣ SDK credentials found:');
    console.log('   SDK Key:', SDK_KEY);
    console.log('   Note: SDK credentials can only be validated by actually joining a meeting');
  } else {
    console.log('❌ No SDK credentials found');
  }

  console.log('\n');
}

test().catch(console.error);
