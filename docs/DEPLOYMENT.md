# Deployment Guide

## Backend Deployment to Render

### Prerequisites

1. **Render Account**: Sign up at [render.com](https://render.com)
2. **GitHub Repository**: Push your code to GitHub
3. **Environment Variables**: Have your API keys ready

### Step 1: Prepare Backend for Production

The backend is already configured for Render deployment with:
- `render.yaml` - Render configuration
- PostgreSQL database support
- Health check endpoint
- Production logging

### Step 2: Create Render Web Service

#### Option A: Using render.yaml (Recommended)

1. Push code to GitHub
2. Go to Render Dashboard → "New" → "Blueprint"
3. Connect your GitHub repository
4. Render will auto-detect `render.yaml` and create services
5. Configure environment variables (see below)

#### Option B: Manual Setup

1. Go to Render Dashboard → "New" → "Web Service"
2. Connect your GitHub repository
3. Configure:
   - **Name**: `ai-professor-backend`
   - **Environment**: `Python 3.11`
   - **Build Command**: `cd backend && pip install -r requirements.txt`
   - **Start Command**: `cd backend && uvicorn app:app --host 0.0.0.0 --port $PORT`
   - **Instance Type**: Free (or paid for production)

### Step 3: Create PostgreSQL Database

1. Render Dashboard → "New" → "PostgreSQL"
2. Configure:
   - **Name**: `ai-professor-db`
   - **Database**: `breakout_system`
   - **User**: (auto-generated)
   - **Region**: Same as web service
   - **Plan**: Free or Starter

3. Copy the **Internal Database URL** (starts with `postgresql://`)

### Step 4: Configure Environment Variables

In Render Web Service settings → Environment:

```bash
# Zoom API
ZOOM_ACCOUNT_ID=your_zoom_account_id
ZOOM_CLIENT_ID=your_zoom_client_id
ZOOM_CLIENT_SECRET=your_zoom_client_secret

# HeyGen API
HEYGEN_API_KEY=your_heygen_api_key

# Deepgram API
DEEPGRAM_API_KEY=your_deepgram_api_key

# Database (use Internal Database URL from Render PostgreSQL)
DATABASE_URL=postgresql://user:password@hostname/database

# Application
DEBUG=False
LOG_LEVEL=INFO
```

### Step 5: Deploy

1. Click "Create Web Service" or "Deploy"
2. Render will:
   - Clone your repo
   - Install dependencies
   - Start the server
   - Run health checks

3. Wait for deployment to complete (~2-5 minutes)
4. Your backend will be live at: `https://ai-professor-backend.onrender.com`

### Step 6: Initialize Database

After first deployment, run database migrations:

```bash
# SSH into Render shell (or use Render Dashboard → Shell)
python scripts/init_db.py
python scripts/seed_data.py
```

### Step 7: Test Deployment

1. Check health endpoint:
   ```bash
   curl https://ai-professor-backend.onrender.com/health
   ```

2. Expected response:
   ```json
   {
     "status": "healthy",
     "timestamp": "2026-02-14T...",
     "active_connections": 0
   }
   ```

### Step 8: Update Electron App

Update WebSocket URL in Electron app:

**src/electron/main/index.ts**:
```typescript
// Change from:
wsClient = new WebSocketClient('ws://localhost:8000/ws');

// To:
const WS_URL = process.env.NODE_ENV === 'production'
  ? 'wss://ai-professor-backend.onrender.com/ws'
  : 'ws://localhost:8000/ws';

wsClient = new WebSocketClient(WS_URL);
```

---

## Database Migration (SQLite → PostgreSQL)

### Update Database Configuration

**backend/models/database.py** is already configured to support PostgreSQL via `DATABASE_URL` environment variable.

SQLite (dev):
```python
DATABASE_URL = "sqlite+aiosqlite:///./breakout_system.db"
```

PostgreSQL (production):
```python
DATABASE_URL = "postgresql+asyncpg://user:pass@host/db"
```

### Migration Steps

1. Export data from SQLite (if needed):
   ```bash
   sqlite3 backend/breakout_system.db .dump > backup.sql
   ```

2. Render will automatically use PostgreSQL when `DATABASE_URL` is set

3. Run initialization script on Render to create tables

---

## Render Configuration File

**render.yaml** (already created):

```yaml
services:
  - type: web
    name: ai-professor-backend
    env: python
    region: oregon
    plan: free
    buildCommand: cd backend && pip install -r requirements.txt
    startCommand: cd backend && uvicorn app:app --host 0.0.0.0 --port $PORT
    healthCheckPath: /health
    envVars:
      - key: DATABASE_URL
        fromDatabase:
          name: ai-professor-db
          property: connectionString
      - key: ZOOM_ACCOUNT_ID
        sync: false
      - key: ZOOM_CLIENT_ID
        sync: false
      - key: ZOOM_CLIENT_SECRET
        sync: false
      - key: HEYGEN_API_KEY
        sync: false
      - key: DEEPGRAM_API_KEY
        sync: false
      - key: DEBUG
        value: False
      - key: LOG_LEVEL
        value: INFO

databases:
  - name: ai-professor-db
    databaseName: breakout_system
    plan: free
    region: oregon
```

---

## Troubleshooting

### Deployment Fails

**Error**: `ModuleNotFoundError`
- **Fix**: Ensure all dependencies are in `requirements.txt`
- Check build logs for missing packages

**Error**: `Port already in use`
- **Fix**: Render automatically sets `$PORT` - ensure you're using it:
  ```python
  uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
  ```

### Database Connection Fails

**Error**: `could not connect to server`
- **Fix**: Use Internal Database URL (not External)
- Verify `DATABASE_URL` environment variable is set
- Check PostgreSQL service is running

### WebSocket Connection Issues

**Error**: `WebSocket connection failed`
- **Fix**: Use `wss://` (not `ws://`) for production
- Verify CORS settings in `app.py`
- Check Render logs for WebSocket errors

### Health Check Fails

**Error**: `Health check timeout`
- **Fix**: Ensure `/health` endpoint returns quickly
- Check server is binding to `0.0.0.0:$PORT`
- Verify no blocking operations in startup

---

## Monitoring & Logs

### View Logs

1. Render Dashboard → Your Service → Logs
2. Real-time log streaming
3. Search and filter logs

### Metrics

1. Render Dashboard → Your Service → Metrics
2. View:
   - CPU usage
   - Memory usage
   - Request latency
   - Error rates

### Alerts

Set up alerts in Render for:
- Service down
- High error rates
- Resource usage spikes

---

## Scaling

### Free Tier Limitations

- Spins down after 15 minutes of inactivity
- 750 hours/month free
- Shared CPU/memory

### Upgrade to Paid Plan

For production use:
1. Render Dashboard → Service → Settings
2. Change Instance Type to "Starter" or higher
3. Benefits:
   - Always-on (no spin down)
   - Dedicated resources
   - Better performance
   - Custom domains

---

## Security Best Practices

1. **Environment Variables**
   - Never commit API keys to Git
   - Use Render's environment variable management
   - Rotate keys regularly

2. **CORS**
   - Update `allow_origins` in production:
     ```python
     app.add_middleware(
         CORSMiddleware,
         allow_origins=["https://your-electron-app.com"],  # Specific origins
         allow_credentials=True,
         allow_methods=["*"],
         allow_headers=["*"],
     )
     ```

3. **HTTPS**
   - Render provides free SSL certificates
   - Always use `wss://` for WebSocket connections

4. **Rate Limiting**
   - Implement rate limiting for API endpoints
   - Use `slowapi` or similar library

---

## Next Steps

After backend is deployed:

1. ✅ Test all endpoints
2. ✅ Verify WebSocket connections
3. ✅ Update Electron app with production URL
4. ✅ Test end-to-end session creation
5. 🔄 Set up monitoring and alerts
6. 🔄 Configure custom domain (optional)
7. 🔄 Enable auto-deploy on Git push

---

## Useful Commands

```bash
# Local development
npm run dev

# Build for production
npm run build

# Test backend health
curl https://ai-professor-backend.onrender.com/health

# Check WebSocket connection
wscat -c wss://ai-professor-backend.onrender.com/ws
```

---

*For issues, check Render logs and [Render documentation](https://render.com/docs)*
