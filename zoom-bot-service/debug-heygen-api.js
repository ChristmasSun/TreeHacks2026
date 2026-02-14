/**
 * Debug HeyGen API response structure
 */
const https = require('https');
require('dotenv').config();

const HEYGEN_API_KEY = process.env.HEYGEN_API_KEY;

async function createHeyGenSession() {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      quality: 'medium',
      avatar_name: 'Angela-inblackskirt-20220820',
      voice: { voice_id: '1bd001e7e50f421d891986aad5158bc8' },
      version: 'v2',
      video_encoding: 'H264'
    });

    const req = https.request({
      hostname: 'api.heygen.com',
      path: '/v1/streaming.new',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'x-api-key': HEYGEN_API_KEY,
        'Content-Length': body.length
      }
    }, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        console.log('\n📥 RAW RESPONSE:');
        console.log(data);
        console.log('\n📋 PARSED:');
        try {
          const j = JSON.parse(data);
          console.log(JSON.stringify(j, null, 2));
          resolve(j);
        } catch (e) {
          reject(e);
        }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

createHeyGenSession().then(data => {
  console.log('\n🔍 Key fields:');
  console.log('data.data:', !!data.data);
  if (data.data) {
    console.log('session_id:', data.data.session_id);
    console.log('sdp:', data.data.sdp ? 'present' : 'missing');
    console.log('ice_servers2:', data.data.ice_servers2 ? 'present' : 'missing');
    console.log('access_token:', data.data.access_token ? 'present' : 'missing');
    console.log('url:', data.data.url);
    console.log('\nAll keys in data.data:', Object.keys(data.data));
  }
}).catch(console.error);
