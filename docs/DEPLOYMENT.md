# 🚀 Deployment Guide

Complete guide to deploying Slack Intelligence to production.

---

## Quick Deploy to Railway

### 1. Install Railway CLI
```bash
brew install railway
# or: npm install -g @railway/cli
```

### 2. Login & Deploy
```bash
cd /Users/kylenewman/slack-automation
railway login
railway init    # Select "Create new project"
railway up      # Deploy!
```

### 3. Add Environment Variables

In Railway dashboard (Variables tab) or via CLI:

```bash
# Required
railway variables set SLACK_BOT_TOKEN="xoxb-your-token"
railway variables set SLACK_USER_TOKEN="xoxp-your-token"
railway variables set OPENAI_API_KEY="sk-your-key"

# Notion (recommended)
railway variables set NOTION_API_KEY="secret_your-key"
railway variables set NOTION_DATABASE_ID="your-database-id"
railway variables set NOTION_SYNC_ENABLED="true"
railway variables set NOTION_MIN_PRIORITY_SCORE="80"

# Jira
railway variables set JIRA_API_KEY="your-api-key"
railway variables set JIRA_EMAIL="your-email@example.com"
railway variables set JIRA_DOMAIN="your-domain"
railway variables set JIRA_PROJECT_KEY="PROJ"
railway variables set JIRA_SYNC_ENABLED="true"

# Exa
railway variables set EXA_API_KEY="your-exa-key"

# Auto-sync (start with false, enable after testing)
railway variables set AUTO_SYNC_ENABLED="false"
railway variables set SYNC_INTERVAL_MINUTES="15"
railway variables set SLACK_ALERT_USER_ID="your-slack-user-id"
```

### 4. Test Deployment
```bash
# Get your URL
railway domain

# Test health
curl https://your-app.railway.app/health
# Expected: {"status":"healthy","service":"slack-intelligence"}

# View API docs
open https://your-app.railway.app/docs

# Trigger manual sync
curl -X POST https://your-app.railway.app/api/slack/sync
```

### 5. Enable Auto-Sync
```bash
railway variables set AUTO_SYNC_ENABLED="true"
```

---

## Production Migration

### Pre-Migration Checklist

**1. Create Production Slack App:**
1. Go to https://api.slack.com/apps → Create New App
2. Name: `Slack Intelligence Production`
3. Add OAuth scopes:
   - Bot: `channels:history`, `channels:read`, `groups:history`, `groups:read`, `im:history`, `im:read`, `mpim:history`, `mpim:read`, `users:read`
   - User: `search:read`
4. Install to workspace
5. Copy Bot Token (xoxb-...) and User Token (xoxp-...)

**2. Get Production IDs:**
- Your User ID: Right-click profile → View profile → More → Copy member ID
- Channel IDs: Right-click channel → View channel details → Copy ID
- Important People IDs: Right-click profile → Copy member ID

**3. Add Bot to Channels:**
```
/invite @Slack Intelligence Production
```

### Switching Environments

**Backup current setup:**
```bash
cp .env .env.backup
cp slack_intelligence.db slack_intelligence.db.backup
```

**Restore test environment:**
```bash
cp .env.backup .env
cp slack_intelligence.db.backup slack_intelligence.db
```

---

## Production Features

### Auto-Sync Scheduler
- Runs every 15 minutes (configurable)
- Set `AUTO_SYNC_ENABLED=true` to enable
- Adjust with `SYNC_INTERVAL_MINUTES=30`

### Action Item Extraction
- AI extracts tasks from high-priority messages (80+)
- Auto-syncs to Notion

### Instant Alerts
- DM for critical messages (score >= 90)
- Requires `SLACK_ALERT_USER_ID` in env

### Context Enrichment
- Thread context included in Jira tickets
- Better resolution with full context

---

## Railway Commands

```bash
railway login          # Authenticate
railway init           # Initialize project
railway up             # Deploy
railway logs           # View logs
railway logs --tail    # Stream logs
railway open           # Open dashboard
railway domain         # Get public URL
railway variables      # List env vars
railway variables set KEY="value"  # Set env var
railway status         # Check status
```

---

## Database Options

**Option 1: Railway PostgreSQL (Recommended for production)**
1. Railway dashboard → New → Database → PostgreSQL
2. Set: `DATABASE_URL=${{Postgres.DATABASE_URL}}`

**Option 2: SQLite (Simple, for testing)**
- Works out of box
- Data resets on each deploy

---

## Cost Management

| Interval | OpenAI Cost |
|----------|-------------|
| 15 min   | ~$15/month  |
| 30 min   | ~$2/month   |
| 60 min   | ~$1/month   |

**Kill switch:** `AUTO_SYNC_ENABLED=false`

Monitor: https://platform.openai.com/usage

---

## Streamlit Dashboard (Local)

Since localhost may be blocked, use ngrok:

```bash
# Terminal 1: Start Streamlit
streamlit run streamlit_dashboard.py --server.port 8501

# Terminal 2: Start ngrok
ngrok http 8501
```

Access via the ngrok URL: `https://abc123.ngrok.io`

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Bot not in channel" | `/invite @Slack Intelligence` |
| "Permission denied" | Check bot scopes, reinstall app |
| Auto-sync not running | Verify `AUTO_SYNC_ENABLED=true` |
| Alerts not sending | Check `SLACK_ALERT_USER_ID` is set |
| Build fails | Check `requirements.txt` versions |

---

## Success Criteria

- [ ] Health endpoint returns `{"status":"healthy"}`
- [ ] API docs accessible at `/docs`
- [ ] Manual sync works
- [ ] Auto-sync runs every 15 minutes
- [ ] Important messages never missed
- [ ] Inbox review: 30 seconds instead of 30 minutes

---

**Ready to deploy? Run `railway up`!** 🚀

