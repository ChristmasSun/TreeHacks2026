/**
 * Test script: Create a Zoom meeting and have bot join it
 */
const axios = require('axios');

async function test() {
  console.log('Creating test meeting via Zoom REST API...');

  // Create meeting via bot service (which will use Zoom API)
  const createResponse = await axios.post('http://localhost:3001/bots/test-create-meeting');

  console.log('Meeting created:', createResponse.data);
  console.log('\nBot should now be joining the meeting...');
  console.log('Check logs for status.');
}

test().catch(console.error);
