# Quick Start - Get Bot Working in 5 Minutes

## Option 1: Fully Automated Test (Recommended)

This creates a meeting automatically and joins it.

### Step 1: Get OAuth Credentials (2 minutes)

1. Go to: https://marketplace.zoom.us/develop/create
2. Click **"Server-to-Server OAuth"**
3. Fill in:
   - App Name: `Bot Test`
   - Company Name: `Test`
   - Developer Email: your email
4. Click **Create**
5. Copy the 3 credentials shown
6. Add them to `.env` file:

```bash
# Add these lines to .env:
ZOOM_ACCOUNT_ID=your_account_id_here
ZOOM_CLIENT_ID=your_client_id_here
ZOOM_CLIENT_SECRET=your_client_secret_here
```

7. Click **"Scopes" tab**, click **"+ Add Scopes"**
8. Search for and add:
   - `meeting:write`
   - `meeting:read`
9. Click **"Continue"**, then **"Activate your app"**

### Step 2: Run Auto-Test

```bash
# Start the bot service
npm start

# In another terminal, run:
curl -X POST http://localhost:3001/test-auto
```

That's it! The bot will create a meeting and join it automatically.

---

## Option 2: Manual Test (1 minute, no OAuth needed)

If you don't want to set up OAuth:

### Step 1: Start a Meeting

- Go to zoom.us and click "Host a Meeting"
- Note your meeting number (like `123 456 7890`)

### Step 2: Join with Bot

```bash
# Start the bot service
npm start

# In another terminal:
node test-join.js YOUR_MEETING_NUMBER YOUR_PASSCODE
```

Example:
```bash
node test-join.js 1234567890 abc123
```

---

## Verify It's Working

- A browser window will open (non-headless so you can see)
- You should see the bot join your meeting
- Check the console for status updates
- If successful, you'll see: ✅ SUCCESS! Bot joined the meeting!

## Troubleshooting

**"Missing OAuth credentials"** - Follow Option 1 setup above

**"Join failed"** - Make sure your meeting is actually running and the number/passcode are correct

**"Timeout"** - Check that your SDK credentials are correct in .env file
