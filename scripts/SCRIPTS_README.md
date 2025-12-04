# Scripts Directory

Quick reference for all Slack Intelligence scripts.

## 🎯 Demo & Testing

| Script | Description |
|--------|-------------|
| `demo.py` | **Main demo** - Posts to Slack → AI prioritization → Notion sync |
| `validate_demo.py` | Validate environment configuration |

### Demo Usage
```bash
python scripts/demo.py --channel C123ABC
python scripts/demo.py --full --channel C123ABC --ai-generated
```

---

## 🧪 Simulation Testing

### Database Simulations (Fast, No Slack)
| Script | Description |
|--------|-------------|
| `simulation_runner.py` | 50 LLM-generated messages → direct DB insert |
| `insert_test_messages.py` | Insert predefined test data |

```bash
python scripts/simulation_runner.py
```

### Slack Simulations (End-to-End with Real Slack)
| Script | Description |
|--------|-------------|
| `realistic_conversations.py` | Posts threaded conversations to Slack |
| `enhanced_simulation.py` | Posts conversations + sends DM summary |
| `llm_simulation_generator.py` | LLM-generated messages posted to Slack |
| `run_comprehensive_simulation.py` | Full workflow: generate → post → sync → validate |

```bash
# When ready to test against real Slack
python scripts/realistic_conversations.py
python scripts/run_comprehensive_simulation.py
```

**Use DB simulations** for fast stress testing.  
**Use Slack simulations** when testing actual Slack API integration before production.

---

## 🔧 Integration Tests

| Script | Description |
|--------|-------------|
| `test_all_integrations.py` | Test Slack, OpenAI, Notion, Jira, Exa |
| `test_end_to_end.py` | Full E2E workflow test |
| `test_notion_integration.py` | Notion API connection test |
| `test_jira.py` | Jira integration test |
| `test_context_awareness.py` | Basic Context Engine test |
| `test_context_engine.py` | **Comprehensive Context Engine test** - Full process visibility, edge cases |
| `view_context_engine_results.py` | View detailed results from context engine tests |
| `test_slack_events.py` | Slack Events API test |
| `test_dependencies.py` | Dependency validation |
| `test_production.sh` | Production deployment validation |

---

## 📊 Operations

| Script | Description |
|--------|-------------|
| `sync_once.py` | One-time Slack sync |
| `check_inbox.py` | View prioritized inbox (CLI) |
| `production_monitor.py` | Monitor production status |
| `validate_production.py` | Validate production setup |

---

## 🔨 Jira Tools

| Script | Description |
|--------|-------------|
| `create_jira_ticket.py` | Interactive Jira ticket creation |
| `create_jira_ticket_auto.py` | Auto-create ticket with Exa research |

---

## 🛠️ Setup & Utilities

| Script | Description |
|--------|-------------|
| `setup.sh` | Create venv, install deps, init DB |
| `start.sh` | Start backend + Streamlit |
| `setup_ngrok.sh` | Configure ngrok for remote access |
| `update_env.sh` | Update environment variables |
| `push_to_github.sh` | Git commit and push |
| `get_channels.py` | List accessible Slack channels |
| `demo_cleanup.py` | Clean up demo messages |

---

## 📁 Archive

Older/deprecated scripts are in `scripts/archive/`. These are kept for reference but superseded by newer versions.

---

## Quick Reference

```bash
# Validate setup
python scripts/validate_demo.py

# Run demo
python scripts/demo.py --channel CHANNEL_ID

# Run stress test
python scripts/simulation_runner.py

# Test integrations
python scripts/test_all_integrations.py

# Test context engine (comprehensive)
python scripts/test_context_engine.py

# View context engine test results
python scripts/view_context_engine_results.py simulations/context_engine_test_*.json

# Check inbox
python scripts/check_inbox.py
```

---

## Documentation

- Setup: `docs/SETUP.md`
- Testing: `docs/guides/TESTING_GUIDE.md`
- Deployment: `docs/DEPLOYMENT.md`
