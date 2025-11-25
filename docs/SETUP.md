# Slack Intelligence Setup Guide

## Step-by-Step Setup

### 1. Create Slack App

1. Go to https://api.slack.com/apps
2. Click **"Create New App"** → **"From scratch"**
3. Name: `Slack Intelligence`
4. Select your workspace

### 2. Configure OAuth Scopes

Go to **OAuth & Permissions** in your app settings.

**Add Bot Token Scopes:**
```
channels:history    - Read messages from public channels
channels:read       - View basic channel info
groups:history      - Read messages from private channels
groups:read         - View basic private channel info
im:history          - Read direct messages
im:read             - View DM list
mpim:history        - Read group DMs
mpim:read           - View group DM list
users:read          - View user information
```

**Add User Token Scopes:**
```
search:read         - Search messages (for @mentions)
```

### 3. Install App to Workspace

1. Scroll up to **OAuth Tokens**
2. Click **"Install to Workspace"**
3. Review permissions and click **"Allow"**
4. Copy **Bot User OAuth Token** (starts with `xoxb-`)
5. Copy **User OAuth Token** (starts with `xoxp-`)

### 4. Add Bot to Channels

The bot needs to be added to channels to read messages:

In Slack, for each channel you want to monitor:
```
/invite @Slack Intelligence
```

Or right-click channel → View channel details → Integrations → Add apps → Select Slack Intelligence

### 5. Get User and Channel IDs

**User IDs (for KEY_PEOPLE):**
1. Right-click user in Slack
2. View profile
3. Click "More" (three dots)
4. Copy member ID (format: U123ABC456)

**Channel IDs (for KEY_CHANNELS):**
1. Right-click channel name
2. View channel details
3. Scroll down, copy Channel ID (format: C123ABC456)

### 6. Configure Environment

```bash
cd slack-intelligence
cp .env.example .env
```

Edit `.env` with your values:
```bash
SLACK_BOT_TOKEN=xoxb-your-actual-bot-token
SLACK_USER_TOKEN=xoxp-your-actual-user-token
OPENAI_API_KEY=sk-your-openai-key

# Customize these (optional)
KEY_PEOPLE=U123456,U789012
KEY_CHANNELS=C123456,C789012
KEY_KEYWORDS=launch,production,urgent,deployment
```

### 7. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 8. Initialize Database

```bash
cd backend
python -c "from database import init_db; init_db()"
```

### 9. Start Server

```bash
python main.py
```

Server will start at http://localhost:8000

### 10. First Sync

In another terminal:
```bash
# Sync last 24 hours
curl -X POST "http://localhost:8000/api/slack/sync?hours_ago=24"
```

Wait for it to complete (may take 1-2 minutes for large workspaces).

### 11. Check Your Inbox

```bash
# Messages needing response
curl "http://localhost:8000/api/slack/inbox?view=needs_response"

# All messages sorted by priority
curl "http://localhost:8000/api/slack/inbox?view=all&limit=20"
```

## Troubleshooting

### "Configuration validation failed"
- Make sure `.env` file exists
- Check all required tokens are set
- Verify no extra spaces in tokens

### "Error fetching channel"
- Bot must be invited to channel first
- Use `/invite @Slack Intelligence` in channel

### "Could not fetch user"
- Bot needs `users:read` scope
- Reinstall app if you added scopes after installation

### "search:read" permission error
- User token needs `search:read` scope
- Go to OAuth & Permissions → User Token Scopes → Add search:read
- Reinstall app to workspace

### No messages found
- Check bot is added to channels
- Verify hours_ago parameter
- Check server logs for API errors

## Next Steps

1. **Set up automation** - See SYSTEMD_SETUP.md or use cron
2. **Customize preferences** - Tune KEY_PEOPLE, KEY_KEYWORDS in .env
3. **Monitor costs** - Check OpenAI usage dashboard
4. **Build UI** (optional) - Create dashboard to view inbox

## Getting Help

- Check server logs: `tail -f backend.log`
- Test Slack connection: `curl http://localhost:8000/health`
- Verify tokens: Check they start with `xoxb-` and `xoxp-`
- OpenAI errors: Check API key and credits at platform.openai.com

