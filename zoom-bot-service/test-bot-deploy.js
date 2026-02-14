/**
 * Test Script - Deploy HeyGen Bots to Zoom Meeting
 * 
 * This script:
 * 1. Deploys multiple bots to a Zoom meeting (one per breakout room)
 * 2. Each bot joins with a HeyGen avatar
 * 3. You can make each bot speak
 * 
 * Usage: node test-bot-deploy.js
 * 
 * Or with custom meeting:
 *   ZOOM_MEETING_ID=xxx ZOOM_PASSCODE=xxx node test-bot-deploy.js
 */

const { BotOrchestrator } = require('./src/BotOrchestrator');
const readline = require('readline');
require('dotenv').config();

const MEETING_ID = process.env.ZOOM_MEETING_ID || '89711545987';
const PASSCODE = process.env.ZOOM_PASSCODE || '926454';

// Simulate breakout rooms with students
const ROOMS = [
  { roomId: 1, roomName: 'Room 1 - Calculus Help', studentName: 'Alice' },
  { roomId: 2, roomName: 'Room 2 - Algebra Review', studentName: 'Bob' },
  // Add more rooms as needed
  // { roomId: 3, roomName: 'Room 3 - Linear Algebra', studentName: 'Charlie' },
];

async function main() {
  console.log('\n🧪 Bot Deployment Test');
  console.log('═'.repeat(50));
  console.log(`Meeting ID: ${MEETING_ID}`);
  console.log(`Passcode: ${PASSCODE}`);
  console.log(`Rooms to deploy: ${ROOMS.length}`);
  console.log('═'.repeat(50));

  // Check for HeyGen API key
  if (!process.env.HEYGEN_API_KEY) {
    console.error('\n❌ HEYGEN_API_KEY not set in .env file');
    process.exit(1);
  }

  // Create orchestrator
  const orchestrator = new BotOrchestrator();

  // Listen for events
  orchestrator.on('bot_ready', (data) => {
    console.log(`\n🎉 Bot ${data.botId} is ready!`);
    console.log('   You can now share the HeyGen tab as screen in Zoom');
  });

  orchestrator.on('bot_error', (data) => {
    console.error(`\n❌ Bot ${data.botId} error: ${data.error}`);
  });

  console.log('\n🚀 Starting deployment...\n');

  try {
    // Deploy bots
    const result = await orchestrator.deployBots({
      meetingId: MEETING_ID,
      passcode: PASSCODE,
      rooms: ROOMS
    });

    console.log('\n' + '═'.repeat(50));
    console.log('📊 Deployment Summary:');
    console.log(`   ✅ Successful: ${result.successful.length}`);
    console.log(`   ❌ Failed: ${result.failed.length}`);
    console.log('═'.repeat(50));

    if (result.successful.length === 0) {
      console.log('\n❌ No bots deployed successfully');
      process.exit(1);
    }

    // Interactive mode - let user control bots
    console.log('\n📝 Commands:');
    console.log('   speak <botId> <text>  - Make a bot speak');
    console.log('   status                - Show all bots status');
    console.log('   remove <botId>        - Remove a bot');
    console.log('   quit                  - Exit and cleanup');
    console.log('');

    const rl = readline.createInterface({
      input: process.stdin,
      output: process.stdout
    });

    const prompt = () => {
      rl.question('> ', async (input) => {
        const parts = input.trim().split(' ');
        const cmd = parts[0].toLowerCase();

        try {
          switch (cmd) {
            case 'speak':
              if (parts.length < 3) {
                console.log('Usage: speak <botId> <text>');
              } else {
                const botId = parts[1];
                const text = parts.slice(2).join(' ');
                await orchestrator.speakText(botId, text);
                console.log(`✓ Sent speech to ${botId}`);
              }
              break;

            case 'status':
              const bots = orchestrator.getAllBotsStatus();
              console.log('\n📊 Bot Status:');
              bots.forEach(bot => {
                console.log(`   ${bot.id}: ${bot.status} (${bot.roomName})`);
              });
              console.log('');
              break;

            case 'remove':
              if (parts.length < 2) {
                console.log('Usage: remove <botId>');
              } else {
                await orchestrator.removeBot(parts[1]);
              }
              break;

            case 'quit':
            case 'exit':
            case 'q':
              console.log('\n🛑 Cleaning up...');
              await orchestrator.removeAllBots();
              rl.close();
              process.exit(0);
              break;

            default:
              if (cmd) console.log('Unknown command:', cmd);
          }
        } catch (err) {
          console.error('Error:', err.message);
        }

        prompt();
      });
    };

    prompt();

  } catch (err) {
    console.error('\n❌ Deployment failed:', err.message);
    await orchestrator.removeAllBots();
    process.exit(1);
  }
}

main();
