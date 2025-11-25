# System Architecture

> **Traverse.ai** - AI-Powered Slack Intelligence Platform

---

## High-Level Overview

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              TRAVERSE.AI ARCHITECTURE                           │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│    ┌──────────────┐     ┌──────────────┐     ┌──────────────┐                  │
│    │    SLACK     │     │   STREAMLIT  │     │  SIMULATION  │                  │
│    │  Workspace   │     │  Dashboard   │     │   Runner     │                  │
│    └──────┬───────┘     └──────┬───────┘     └──────┬───────┘                  │
│           │                    │                    │                          │
│           ▼                    ▼                    ▼                          │
│    ┌────────────────────────────────────────────────────────────────┐          │
│    │                     FASTAPI BACKEND                            │          │
│    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐           │          │
│    │  │ Routes  │  │  Sync   │  │  Inbox  │  │ Integr. │           │          │
│    │  │  API    │  │ Service │  │ Service │  │ Routes  │           │          │
│    │  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘           │          │
│    └───────┼────────────┼───────────┼────────────┼──────────────────┘          │
│            │            │           │            │                             │
│            ▼            ▼           ▼            ▼                             │
│    ┌───────────────────────────────────────────────────────────────┐           │
│    │                      CORE SERVICES                            │           │
│    │                                                               │           │
│    │  ┌────────────┐  ┌────────────┐  ┌────────────┐              │           │
│    │  │ Ingestion  │  │   AI       │  │  Context   │              │           │
│    │  │ (Parser)   │  │ Prioritizer│  │  Engine    │              │           │
│    │  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘              │           │
│    │        │               │               │                      │           │
│    │        ▼               ▼               ▼                      │           │
│    │  ┌─────────────────────────────────────────────────────┐     │           │
│    │  │                   SQLite DATABASE                    │     │           │
│    │  │  Messages │ Insights │ Preferences │ Sync Logs      │     │           │
│    │  └─────────────────────────────────────────────────────┘     │           │
│    └───────────────────────────────────────────────────────────────┘           │
│                                                                                 │
│    ┌───────────────────────────────────────────────────────────────┐           │
│    │                   EXTERNAL INTEGRATIONS                       │           │
│    │                                                               │           │
│    │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐         │           │
│    │  │ OpenAI  │  │  Jira   │  │ Notion  │  │  Exa    │         │           │
│    │  │ GPT-4o  │  │  API    │  │  API    │  │  Search │         │           │
│    │  └─────────┘  └─────────┘  └─────────┘  └─────────┘         │           │
│    └───────────────────────────────────────────────────────────────┘           │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

---

## Data Flow

### 1. Message Ingestion Flow

```
Slack Workspace                    Backend                         Database
     │                               │                                │
     │  GET /conversations.history   │                                │
     │◄──────────────────────────────│                                │
     │                               │                                │
     │   [Messages JSON]             │                                │
     │──────────────────────────────►│                                │
     │                               │                                │
     │                               │  Parse & Validate              │
     │                               │──────────────────►             │
     │                               │                                │
     │                               │  INSERT/UPDATE                 │
     │                               │───────────────────────────────►│
     │                               │                                │
```

### 2. AI Prioritization Flow

```
Database          Prioritizer           OpenAI            Database
    │                  │                   │                  │
    │  Get Unscored    │                   │                  │
    │◄─────────────────│                   │                  │
    │                  │                   │                  │
    │  [Messages]      │                   │                  │
    │─────────────────►│                   │                  │
    │                  │                   │                  │
    │                  │  Batch Request    │                  │
    │                  │  (with Context)   │                  │
    │                  │──────────────────►│                  │
    │                  │                   │                  │
    │                  │  [Scores 0-100]   │                  │
    │                  │◄──────────────────│                  │
    │                  │                   │                  │
    │                  │  Update Scores                       │
    │                  │─────────────────────────────────────►│
    │                  │                   │                  │
```

### 3. Jira Ticket Creation Flow

```
Dashboard         Backend           Exa            Jira           Notion
    │                │               │              │                │
    │  Create Ticket │               │              │                │
    │───────────────►│               │              │                │
    │                │               │              │                │
    │                │  Research     │              │                │
    │                │──────────────►│              │                │
    │                │               │              │                │
    │                │  [Web Results]│              │                │
    │                │◄──────────────│              │                │
    │                │               │              │                │
    │                │  Summarize    │              │                │
    │                │  (OpenAI)     │              │                │
    │                │               │              │                │
    │                │  Create Issue │              │                │
    │                │─────────────────────────────►│                │
    │                │               │              │                │
    │                │  PROJ-123     │              │                │
    │                │◄─────────────────────────────│                │
    │                │               │              │                │
    │                │  Link Ticket  │              │                │
    │                │──────────────────────────────────────────────►│
    │                │               │              │                │
    │  ✅ Created    │               │              │                │
    │◄───────────────│               │              │                │
```

---

## Component Details

### Backend Services

```
backend/
├── main.py                 # FastAPI app entry point
├── config.py               # Environment & settings
│
├── api/
│   ├── routes.py           # All REST endpoints
│   ├── schemas.py          # Pydantic models
│   ├── slack_events.py     # Webhook handlers
│   └── slack_blocks.py     # Slack UI components
│
├── ai/
│   └── prioritizer.py      # GPT-4o-mini scoring engine
│
├── services/
│   ├── sync_service.py     # Orchestrates ingestion + prioritization
│   ├── inbox_service.py    # Smart inbox queries
│   ├── context_service.py  # Context Engine (identity, memory, plans)
│   ├── memory_service.py   # Pinecone vector storage
│   ├── alert_service.py    # Critical message alerts
│   └── action_item_service.py
│
├── integrations/
│   ├── jira_service.py     # Jira ticket creation
│   ├── notion_service.py   # Notion task sync
│   └── exa_service.py      # Web research
│
├── ingestion/
│   ├── slack_ingester.py   # Fetch from Slack API
│   └── message_parser.py   # Parse & normalize messages
│
├── database/
│   ├── models.py           # SQLAlchemy models
│   ├── db.py               # Database connection
│   └── cache_service.py    # CRUD operations
│
└── context/
    ├── identity.md         # Company identity for AI
    ├── institutional_memory.json  # Past issues/solutions
    └── plans/              # PRDs for AI context
        ├── simulation_testing.md
        └── conversation_stitching.md
```

### Frontend (Streamlit Dashboard)

```
streamlit_dashboard.py
│
├── Main Navigation
│   ├── 📥 Smart Inbox      # Prioritized message list
│   ├── 🧠 Context Engine   # View AI knowledge base
│   ├── 📊 Analytics        # (Coming soon)
│   └── ⚙️ Settings         # User preferences
│
├── Inbox Features
│   ├── Priority filtering (score slider)
│   ├── Channel filtering
│   ├── View modes (all, needs_response, high_priority, etc.)
│   ├── Jira ticket creation
│   ├── Notion task creation
│   └── Mark as done
│
└── Context Engine Tabs
    ├── 🏢 Identity & Values
    ├── 🧠 Institutional Memory
    ├── 👁️ Self-Awareness (codebase)
    └── 📋 PRDs/Plans
```

### Simulation Framework

```
simulations/
├── config/
│   ├── personas.json       # 6 personas (Kyle, Jordan, Marcus, Lisa, Dave, AlertBot)
│   └── channels.json       # 6 channels (priority, normal, muted)
│
├── runs/
│   └── YYYY-MM-DD_HH-MM-SS.json  # Saved simulation results
│
└── failures/               # Auto-saved on errors

scripts/
└── simulation_runner.py    # Main simulation script
    ├── Generate conversations (LLM, temp=0.9)
    ├── Insert to database
    ├── Trigger prioritization
    ├── Analyze results
    └── Save run for replay
```

---

## API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/api/slack/sync` | POST | Ingest + prioritize messages |
| `/api/slack/inbox` | GET | Get prioritized inbox |
| `/api/slack/stats` | GET | System statistics |
| `/api/slack/preferences` | GET/POST | User preferences |

### Integration Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/slack/integrations/jira/detect-type` | POST | Detect ticket type |
| `/api/slack/integrations/jira/research` | POST | Exa research for ticket |
| `/api/slack/integrations/jira/create` | POST | Create Jira ticket |
| `/api/slack/notion/sync` | POST | Sync to Notion |

---

## Data Models

### SlackMessage

```python
class SlackMessage:
    id: int                    # Primary key
    message_id: str            # Slack timestamp (unique)
    channel_id: str            # Channel ID
    channel_name: str          # Channel name
    user_id: str               # Sender ID
    user_name: str             # Sender name
    text: str                  # Message content
    timestamp: datetime        # When sent
    thread_ts: str             # Parent thread (if reply)
    priority_score: int        # 0-100 (from AI)
    priority_reason: str       # AI explanation
    category: str              # needs_response, high_priority, fyi, low_priority
```

### UserPreference

```python
class UserPreference:
    slack_user_id: str         # User ID
    key_people: List[str]      # VIP senders (boost score)
    key_channels: List[str]    # Priority channels (boost score)
    key_keywords: List[str]    # Priority keywords (boost score)
    mute_channels: List[str]   # Muted channels (lower score)
```

---

## External Services

| Service | Purpose | API |
|---------|---------|-----|
| **Slack** | Message ingestion, alerts | Bolt SDK |
| **OpenAI** | AI prioritization, summaries | GPT-4o-mini |
| **Jira** | Ticket creation | REST API v3 |
| **Notion** | Task sync | Official API |
| **Exa** | Web research | Search API |
| **Pinecone** | Vector memory (optional) | Python SDK |

---

## Priority Scoring

```
Score Range    Category           Action
─────────────────────────────────────────────────
90-100         CRITICAL           🔴 Immediate attention, alert user
70-89          HIGH               🟠 Important, surface to top
50-69          MEDIUM             🟡 Normal priority
0-49           LOW                ⚪ Can wait, deprioritize
```

### Scoring Factors

| Factor | Impact |
|--------|--------|
| Direct @mention | +20-30 points |
| VIP sender | +15-20 points |
| Priority channel | +10-15 points |
| Urgent keywords | +10-20 points |
| Muted channel | -15-20 points |
| Casual/social content | -10-20 points |

---

## Deployment

```
Local Development:
├── uvicorn backend.main:app --port 8000
├── streamlit run streamlit_dashboard.py --port 8502
└── SQLite database (slack_intelligence.db)

Production (Railway):
├── FastAPI backend (Procfile)
├── PostgreSQL database
└── Environment variables from Railway dashboard
```

---

## Future Architecture (Planned)

```
┌─────────────────────────────────────────────────────────────────┐
│                    CONVERSATION STITCHING                       │
│                                                                 │
│  New Message ──► Embed ──► Search Similar ──► Confidence Score  │
│                                                    │            │
│                              ┌────────────────────┼────────┐    │
│                              │                    ▼        │    │
│                              │  >90%: Auto-link to ticket  │    │
│                              │  50-90%: Ask human         │    │
│                              │  <50%: Create new / ignore │    │
│                              └─────────────────────────────┘    │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

See `backend/context/plans/conversation_stitching.md` for full PRD.
