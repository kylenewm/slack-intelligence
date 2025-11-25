# Testing Guide - Slack Intelligence

Complete guide for testing the Slack Intelligence system end-to-end.

## Quick Test (5 minutes)

### Prerequisites
- `.env` file configured
- Virtual environment active
- Personal Slack workspace with bot invited to a channel

### Run End-to-End Demo
```bash
python scripts/demo.py --channel C09P1KU5WMP
```

**What this tests:**
- ✅ Slack API integration (posting & fetching)
- ✅ Database operations
- ✅ AI prioritization with GPT-4o-mini
- ✅ Notion integration
- ✅ Full workflow: Slack → AI → Notion

**Expected output:**
- Posted 5 messages to Slack
- Fetched 30+ messages from Slack
- Prioritized messages with scores
- Created tasks in Notion (score ≥70)

---

## Test Components Individually

### 1. Test Slack Connection
```bash
python test_slack_connection.py
```

**Checks:**
- Bot authentication
- Channel access
- List channels bot is member of

**Expected output:**
```
✅ Bot connected!
   Bot ID: U09PH0DCWF2
   Bot Name: slack_intelligence
   Team: Slack Simulation Tool

📋 Channels bot has access to:
   ✅ MEMBER - #general (ID: C09P1KU5WMP)
```

### 2. Test Configuration
```bash
python scripts/validate_demo.py
```

**Checks:**
- Environment variables set
- Slack tokens valid
- OpenAI API key present
- Notion credentials configured

**Expected output:**
```
✅ Configuration valid
✅ All required tokens present
```

### 3. Test Notion Integration
```bash
python scripts/test_notion_integration.py
```

**Checks:**
- Notion API connection
- Database access
- Property schema

**Expected output:**
```
✅ Notion connection successful
✅ Database schema valid
```

### 4. Get Available Channels
```bash
python scripts/get_channels.py
```

**Shows:**
- All channels bot can see
- Which channels bot is member of
- Channel IDs for testing

---

## Testing Different Scenarios

### Test with AI-Generated Messages
```bash
python scripts/demo.py --channel C09P1KU5WMP --ai-generated
```
Uses OpenAI to generate different messages each run.

### Test with Full Dataset (12 messages)
```bash
python scripts/demo.py --full --channel C09P1KU5WMP
```
More comprehensive test with varied priority levels.

### Test with Verbose Logging
```bash
python scripts/demo.py --channel C09P1KU5WMP --verbose
```
Shows detailed logs for debugging.

---

## Clean Up Between Tests

### Clean Demo Messages Only
```bash
python -c "
from backend.database.db import init_db, SessionLocal
from backend.database.models import SlackMessage, MessageInsight

init_db()
session = SessionLocal()

demo_messages = session.query(SlackMessage).filter(
    SlackMessage.message_id.like('demo_%')
).all()

for msg in demo_messages:
    session.query(MessageInsight).filter(MessageInsight.message_id == msg.message_id).delete()
    session.delete(msg)

session.commit()
print(f'✅ Cleaned {len(demo_messages)} demo messages')
session.close()
"
```

### Clean All Messages (Fresh Start)
```bash
python -c "
from backend.database.db import init_db, SessionLocal
from backend.database.models import SlackMessage, MessageInsight

init_db()
session = SessionLocal()

all_messages = session.query(SlackMessage).all()
for msg in all_messages:
    session.query(MessageInsight).filter(MessageInsight.message_id == msg.message_id).delete()
    session.delete(msg)

session.commit()
print(f'✅ Cleaned {len(all_messages)} messages')
session.close()
"
```

---

## Troubleshooting Tests

### Issue: "Channel not found"
**Cause:** Bot not invited to channel  
**Fix:** In Slack, type `/invite @your_bot_name` in the channel

### Issue: "Fetched 0 messages"
**Cause:** Messages not indexed yet or all cached  
**Fix:** 
- Wait 5-10 seconds after posting
- Or clean database and re-run

### Issue: "OPENAI_API_KEY not set"
**Cause:** Missing environment variable  
**Fix:** Add to `.env`:
```bash
OPENAI_API_KEY=sk-proj-your-key
```

### Issue: "Notion API error: From is not a property"
**Cause:** Notion database missing properties  
**Fix:** Add these properties to your Notion database:
- From (Text)
- Channel (Text)
- Score (Number)

### Issue: "SLACK_BOT_TOKEN" connects to wrong workspace
**Cause:** Multiple tokens in `.env`  
**Fix:** Ensure only one `SLACK_BOT_TOKEN` line (personal workspace token)

---

## Validation Checklist

After running tests, verify:

- [ ] Messages appear in Slack channel
- [ ] Messages saved to database with real Slack IDs (timestamps)
- [ ] AI prioritization scores make sense (100=urgent, 75=high, etc)
- [ ] High-priority messages (≥70) synced to Notion
- [ ] Notion tasks have all properties populated
- [ ] No errors in terminal output

---

## Performance Benchmarks

Expected times for demo run:

| Step | Time |
|------|------|
| Post 5 messages to Slack | ~3 seconds |
| Fetch messages from Slack | ~2 seconds |
| AI prioritization (5 msgs) | ~3 seconds |
| Notion sync (3-5 tasks) | ~2 seconds |
| **Total** | **~10 seconds** |

**Cost per run:** ~$0.03 (OpenAI API)

---

## Simulation Testing (Stress Test)

For thorough stress testing before production, use the simulation framework:

```bash
python scripts/simulation_runner.py
```

**What it does:**
- Generates 50 LLM-created realistic messages
- Uses 6 personas (CTO, Engineer, PM, etc.)
- Covers 6 channel types (priority, normal, muted)
- Inserts directly to database (no Slack API needed)
- Validates AI prioritization accuracy

**Simulation config:** See `simulations/config/` for personas and channels.

**PRD:** See `backend/context/plans/simulation_testing.md` for full specification.

---

## Integration Tests

```bash
# Test all integrations
python scripts/test_all_integrations.py

# Full end-to-end test
python scripts/test_end_to_end.py
```

---

## Production Validation

```bash
# Test deployed Railway instance
./scripts/test_production.sh https://your-app.railway.app
```

---

## Need Help?

**Common commands:**
- Validate setup: `python scripts/validate_demo.py`
- Run demo: `python scripts/demo.py --channel CHANNEL_ID`
- Run simulation: `python scripts/simulation_runner.py`

**Documentation:**
- Setup: `docs/SETUP.md`
- Architecture: `docs/SYSTEM_ARCHITECTURE.md`
- Notion: `docs/guides/NOTION_INTEGRATION.md`

