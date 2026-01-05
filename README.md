# Slack Intelligence

AI-powered Slack inbox prioritization and smart search system. Turn your overwhelming Slack notifications into a manageable, prioritized inbox using AI.

## 🎯 What It Does

**Slack Intelligence** automatically:
1. **Fetches** messages from your Slack channels and DMs
2. **Analyzes** each message with AI to determine priority (0-100 score)
3. **Categorizes** messages: Needs Response, High Priority, FYI, Low Priority
4. **Provides** a smart inbox API to retrieve prioritized messages

### The Problem It Solves

- **500+ Slack messages/day** is overwhelming
- Important messages get buried in noise
- No way to know what actually needs your attention
- Finding old discussions is painful

### The Solution

AI-powered prioritization that understands:
- Direct questions requiring your response
- Messages from key people/channels
- Time-sensitive content with deadlines
- Context about your projects and topics

**Result:** Spend 30 seconds checking your "Needs Response" view instead of 30 minutes scanning all messages.

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- Slack workspace (admin access to create app)
- OpenAI API key

### Installation

```bash
cd slack-intelligence
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Configuration

1. Copy `.env.example` to `.env`
2. Add your Slack tokens and OpenAI API key
3. Customize KEY_PEOPLE, KEY_CHANNELS, KEY_KEYWORDS

### Run

```bash
cd backend
python main.py
```

Visit http://localhost:8000/docs for API documentation.

## 🎬 Demo

**Quick demo (5 messages, simulation only):**
```bash
python scripts/demo.py
```

**Full demo (12 messages, with Notion sync):**
```bash
python scripts/demo.py --full --notion
```

**Complete demo (post to Slack, fetch back, prioritize, sync to Notion):**
```bash
python scripts/demo.py --full --slack --notion --channel C123ABC
```

See [docs/guides/DEMO_GUIDE.md](docs/guides/DEMO_GUIDE.md) for detailed demo instructions.

## 🏭 Deployment

**Deploy to Railway in 5 minutes:**
```bash
railway login && railway init && railway up
```

See [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) for full deployment guide including environment variables and production migration.


## 📚 Documentation

| Doc | Description |
|-----|-------------|
| [docs/SETUP.md](docs/SETUP.md) | Complete setup guide |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | Railway deployment & production |
| [docs/SYSTEM_ARCHITECTURE.md](docs/SYSTEM_ARCHITECTURE.md) | System design & architecture |
| [docs/guides/DEMO_GUIDE.md](docs/guides/DEMO_GUIDE.md) | Interview demo walkthrough |
| [docs/guides/STREAMLIT_GUIDE.md](docs/guides/STREAMLIT_GUIDE.md) | Dashboard usage |
| [docs/guides/NOTION_INTEGRATION.md](docs/guides/NOTION_INTEGRATION.md) | Notion setup |
| [docs/guides/TESTING_GUIDE.md](docs/guides/TESTING_GUIDE.md) | Testing guide |
| [CONTEXT_ENGINE_README.md](CONTEXT_ENGINE_README.md) | AI context system |

## 🖥️ Streamlit Dashboard

Visual management interface for your inbox:

```bash
streamlit run streamlit_dashboard.py
```

Features:
- Priority-sorted message inbox with filtering
- One-click Jira ticket creation with Exa research
- Notion task sync
- Context Engine debugger (identity, memory, codebase awareness)
- User preferences configuration

## 🔌 Integrations

| Integration | Status | Description |
|-------------|--------|-------------|
| **Slack** | ✅ Live | Message ingestion via Slack SDK |
| **OpenAI** | ✅ Live | GPT-4o-mini for prioritization and analysis |
| **Jira** | ✅ Live | Auto-create tickets with Exa research context |
| **Notion** | ✅ Live | Sync high-priority items as tasks |
| **Exa AI** | ✅ Live | Web research for technical issues |
| **Streamlit** | ✅ Live | Visual dashboard for inbox management |

## 🧪 Simulation Testing

Stress test the system before production migration:

```bash
python scripts/simulation_runner.py
```

Features:
- 6 realistic personas (CTO, Engineer, PM, etc.)
- 6 channel types (priority, normal, muted)
- 50 LLM-generated messages per run
- Reproducible runs from saved JSON
- Integration testing (Jira, Notion, Exa)

See [backend/context/plans/simulation_testing.md](backend/context/plans/simulation_testing.md) for the full PRD.

## 🔮 Planned Features

| Feature | Description | Status |
|---------|-------------|--------|
| **Conversation Stitching** | Link related messages across threads to existing Jira tickets | [PRD](backend/context/plans/conversation_stitching.md) |
| **Confluence Integration** | Pull PRDs and documentation into Context Engine | Planned |
| **GitHub PR Integration** | Link Slack discussions to pull requests | Planned |

See [backend/context/plans/](backend/context/plans/) for detailed PRDs.
