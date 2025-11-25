# 🔗 Notion Integration Guide

Connect Slack Intelligence to Notion to automatically create tasks from high-priority messages.

## 📚 What It Does

- Monitors Slack messages as they're prioritized
- Extracts high-priority messages (70+ score) as actionable tasks
- Automatically creates tasks in your Notion "Slack Inbox" database
- Includes full context: message text, sender, channel, priority score

## 🎯 Perfect For

- **AI PMs:** Track action items from team discussions
- **Busy professionals:** Centralize work from Slack into your task system
- **Interview projects:** Showcase integration and automation skills

## 🚀 Quick Setup (10 minutes)

### Step 1: Create Notion Integration

1. Go to https://notion.so/my-integrations
2. Click **"Create new integration"**
3. **Name:** `Slack Intelligence`
4. **Logo:** (optional)
5. Click **"Create integration"**
6. **Copy the Internal Integration Token** (starts with `ntn_...`)

### Step 2: Create Notion Database

1. In Notion, create a new database (blank)
2. **Name it:** `Slack Inbox`
3. **Properties needed:**
   - **Name** (Title) - Task title
   - **Description** (Rich text) - Full message context
   - **Priority** (Select) - Critical, High, Medium, Low
   - **Source** (Select) - Slack
   - **Status** (Select) - Not Started, In Progress, Done

**Optional properties:**
   - **Created** (Date) - Auto-created
   - **Updated** (Date) - Auto-updated
   - **Assignee** (Person) - Assign to yourself

### Step 3: Share Database with Integration

1. In your Notion database, click **Share** (top right)
2. Click **"Invite"**
3. Find and select **Slack Intelligence** (the integration)
4. Click **"Invite"**

### Step 4: Get Database ID

Your Notion database URL looks like:
```
https://notion.so/abc123def456?v=xyz789
```

The **Database ID** is: `abc123def456` (remove dashes if present)

### Step 5: Configure Slack Intelligence

Add to your `.env`:
```bash
NOTION_API_KEY=ntn_your-api-key-here
NOTION_DATABASE_ID=abc123def456
NOTION_SYNC_ENABLED=true
NOTION_MIN_PRIORITY_SCORE=70
```

### Step 6: Test Integration

```bash
# Test with sample data
python scripts/test_notion_integration.py

# Should see:
# - Task extraction test
# - Configuration validation
# - Sample tasks created in Notion
```

## 🔄 How It Works

```
Slack Message
    ↓
AI Prioritization (0-100 score)
    ↓
If score >= 70:
    ↓
Extract task (title + context)
    ↓
Create in Notion database
    ↓
Review in your Notion workspace
```

## ⚙️ Configuration Options

| Setting | Default | Description |
|---------|---------|-------------|
| `NOTION_API_KEY` | - | Your Notion integration token |
| `NOTION_DATABASE_ID` | - | Your Slack Inbox database ID |
| `NOTION_SYNC_ENABLED` | false | Enable/disable sync |
| `NOTION_MIN_PRIORITY_SCORE` | 70 | Only create tasks for scores >= this |

## 📊 What Gets Created

Each Notion task includes:

- **Title** - First line of the Slack message (max 100 chars)
- **Description** - Full context:
  - Who sent it (user name)
  - Where it came from (channel name)
  - Priority score (0-100)
  - Full message text
- **Priority** - Auto-set based on score:
  - 90+ → Critical
  - 70-89 → High
  - 50-69 → Medium
  - <50 → Low (not created)
- **Status** - Always starts as "Not Started"
- **Source** - Always "Slack"

## 🧪 Testing

### Test with Sample Data

No Notion setup needed:
```bash
python scripts/test_notion_integration.py
```

Shows what tasks would be extracted.

### Test with Real Notion

After setup:
```bash
# Enable in .env
NOTION_SYNC_ENABLED=true

# Restart server
cd backend && python main.py

# In another terminal
curl -X POST "http://localhost:8000/api/slack/sync?hours_ago=1"

# Check Notion database - should have new tasks!
```

## 💡 Best Practices

### Task Extraction

- Tasks are only created for **high priority** messages (70+)
- Low priority messages are ignored (keeps database clean)
- Adjust `NOTION_MIN_PRIORITY_SCORE` if needed

### Database Organization

- Use **Status** to track progress (Not Started → In Progress → Done)
- Use **Priority** to sort urgent items
- Periodically **archive done tasks**

### Monitoring

Check logs for sync status:
```bash
tail -f logs/slack_intelligence.log | grep Notion
```

Example output:
```
✅ Created Notion task: URGENT: Production database is down!
🔄 Syncing 5 messages to Notion...
✅ Notion sync complete: 3 created, 1 skipped, 0 errors
```