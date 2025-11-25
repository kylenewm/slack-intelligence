# Simulation Testing PRD

## Problem Statement

Before migrating Traverse.ai to production work Slack, we need to validate:
- Scoring accuracy across varied message types and senders
- End-to-end integration reliability (Jira, Notion, Exa)
- Graceful handling of edge cases
- System stability under realistic load

**Goal:** Build confidence to get approval for work Slack migration, with ability to catch bugs and tune prompts/weights.

---

## Simulation Design

### Personas (6)

| Persona | Role | Message Style | Expected Scoring |
|---------|------|---------------|------------------|
| **Kyle (You)** | AI PM | Product questions, decisions needed, @mentions | Test @mention detection |
| **Jordan** | CTO | Strategic decisions, company priorities, approvals | VIP boost → HIGH/CRITICAL |
| **Marcus** | Engineer | Bug reports, technical questions, code reviews | Context-dependent |
| **Lisa** | Engineering Manager | Sprint updates, escalations, resource asks | VIP boost → HIGH |
| **Dave** | Random Coworker | Casual chat, off-topic, social | Should score LOW |
| **AlertBot** | Automated System | Deploy notifications, monitoring alerts, CI/CD | Context-dependent |

### Channels (6)

| Channel | Type | Expected Behavior |
|---------|------|-------------------|
| `#engineering-alerts` | Priority | Boost scores +15 |
| `#incidents` | Priority | Boost scores +20 |
| `#general` | Normal | No modifier |
| `#product` | Normal | No modifier |
| `#random` | Muted | Reduce scores -20 |
| `#watercooler` | Muted | Reduce scores -20 |

*Note: Channel names/IDs can be updated in config without changing simulation logic.*

### Message Types

**High Priority (should score 70+):**
- Production incidents / outages
- Blocking bugs with customer impact
- Urgent decisions needed from Kyle
- CTO requests / escalations
- Deployment failures

**Medium Priority (should score 50-70):**
- PR review requests
- Technical questions (non-blocking)
- Sprint planning discussions
- Feature clarifications

**Low Priority (should score <50):**
- Meeting scheduling (non-urgent)
- Casual chat / social messages
- FYI announcements
- Automated metrics/dashboards
- Off-topic / watercooler

**Edge Cases (should not crash):**
- Emoji-only messages
- Code blocks (short snippets, <100 chars)
- Messages with file attachment references
- Thread replies vs. standalone
- Messages with multiple @mentions
- Typos / informal language

---

## Generation Approach

### LLM-First (High Temperature)

```
Model: GPT-4o-mini
Temperature: 0.9 (high variance for realism)
Max Length: 300 characters
```

**Prompt structure:**
```
Generate a realistic Slack message for a {persona} in #{channel}.
Scenario: {scenario_type}
Tone: {tone}
Keep message under 300 characters. Real Slack messages are short and punchy.
```

### Scenario Distribution (50 messages)

| Category | Count | Examples |
|----------|-------|----------|
| Urgent/Critical | 8 | Production down, blocking bug, CTO escalation |
| High Priority | 10 | PR reviews, technical questions, decisions |
| Medium Priority | 12 | Sprint updates, feature questions, planning |
| Low/Noise | 12 | Casual chat, FYI, social |
| Edge Cases | 8 | Emoji, code blocks, threads |

### Storage & Reproducibility

```
simulations/
├── runs/
│   ├── 2024-11-25_14-30-00.json    # Full run with inputs + outputs
│   └── ...
├── config/
│   ├── personas.json               # Persona definitions
│   └── channels.json               # Channel config
└── failures/
    └── auto-saved when errors occur
```

**Run file contains:**
```json
{
  "timestamp": "2024-11-25T14:30:00Z",
  "config": { "personas": [...], "channels": [...] },
  "messages": [...],
  "results": [...]
}
```

**Reproducibility:** Re-run any saved simulation by loading messages from JSON instead of generating new ones.

---

## Integration Testing

Each simulation run also tests:

| Integration | Test |
|-------------|------|
| **Jira** | Create tickets for 3-5 high-scoring messages |
| **Notion** | Sync tasks for messages above threshold |
| **Exa** | Research enrichment on technical bug messages |
| **Context Engine** | Verify institutional memory is injected |

---

## Validation Workflow

1. **Run simulation** (`python scripts/simulation_runner.py`)
2. **Review in dashboard** - Streamlit shows all 50 messages with scores
3. **Manual spot-check:**
   - Do urgent messages score 80+?
   - Does CTO get VIP boost?
   - Is Dave's noise scoring low?
   - Did integrations complete without errors?
4. **Flag issues** - Note any obvious misses
5. **Tune and re-run** - Adjust prompts/weights, run again

---

## Success Criteria (Qualitative)

- [ ] Urgent/production messages consistently hit 80+ scores
- [ ] CTO (Jordan) and EM (Lisa) messages get visible VIP boost
- [ ] Casual noise from Dave consistently scores <50
- [ ] Muted channel messages are deprioritized
- [ ] @mentions of Kyle are detected and boosted
- [ ] Jira/Notion integrations complete on 5+ test messages without error
- [ ] No crashes on edge case messages
- [ ] Can reproduce a previous run from saved JSON

---

## Cost Estimate

**Per 50-message run:**
- Generation: ~$0.02 (GPT-4o-mini input/output)
- Prioritization: ~$0.05 (batch of 50)
- Exa research (5 messages): ~$0.10
- **Total: ~$0.20 per simulation run**

---

## Out of Scope

- Automated accuracy metrics / dashboards
- Performance benchmarking
- Load testing beyond 50 messages
- Real Slack posting (simulation only writes to local DB)

---

## Future Enhancements

- Confluence integration for pulling real PRDs into context
- Accuracy metrics once baseline is stable
- Larger scale testing (200+ messages)
- A/B testing different prompt versions
