// Quick test script to register a student via WebSocket
const WebSocket = require('ws');

const ws = new WebSocket('ws://localhost:8000/ws');

ws.on('open', () => {
  console.log('Connected to backend');

  // Send PING first
  ws.send(JSON.stringify({ type: 'PING', payload: {} }));

  // Register student
  setTimeout(() => {
    ws.send(JSON.stringify({
      type: 'REGISTER_STUDENT',
      payload: {
        name: 'TestStudent',
        email: 'test@example.com'
      }
    }));
  }, 500);
});

ws.on('message', (data) => {
  console.log('Received:', data.toString());
});

ws.on('error', (err) => {
  console.error('WebSocket error:', err.message);
});

ws.on('close', () => {
  console.log('Disconnected');
});

// Close after 3 seconds
setTimeout(() => {
  ws.close();
  process.exit(0);
}, 3000);
