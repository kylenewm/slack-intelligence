# Conversation Stitching PRD

**Status:** Designed / Ready for Implementation  
**Complexity:** Medium-High  
**Priority:** v2 Feature

---

## Problem Statement

Real Slack conversations don't stay neatly organized. A single incident can span:
- Multiple messages in the same channel (not in a thread)
- Messages across different channels
- Different timestamps over minutes or hours

**Without conversation stitching, the system creates duplicate tickets for the same incident.**

### Example: The Duplicate Problem

```
#engineering-alerts [10:00]: "🚨 500 errors on checkout API"     → Ticket PROD-001
#engineering-alerts [10:02]: "looking into it"                   → Ticket PROD-002?
#general            [10:03]: "hey is checkout down?"             → Ticket PROD-003?
#incidents          [10:05]: "checkout incident - investigating" → Ticket PROD-004?
#engineering-alerts [10:08]: "found it, bad deploy"              → Ticket PROD-005?
```

**Result without stitching:** 5 tickets for 1 incident.

---

## Solution: Confidence-Based Routing with Human-in-the-Loop

### Core Principle

**Don't review everything. Only review what the AI is uncertain about.**

```
┌─────────────────────────────────────────────────────────────┐
│                   CONFIDENCE-BASED ROUTING                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   > 90% Confidence   →   AUTO-ACTION (no human needed)      │
│     "Definitely related to PROD-123"                        │
│     Action: Auto-link as comment                            │
│                                                             │
│   50-90% Confidence  →   ASK HUMAN                          │
│     "Might be related to PROD-123, not sure"                │
│     Action: Show in review queue                            │
│                                                             │
│   < 50% Confidence   →   AUTO-SKIP (no human needed)        │
│     "Probably noise or unrelated"                           │
│     Action: Don't create ticket, don't link                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Why This Works

| Daily Messages | Auto-Handled (80%) | Human Review (20%) |
|----------------|--------------------|--------------------|
| 50 | 40 | 10 |
| 100 | 80 | 20 |
| 200 | 160 | 40 |

**You only see the edge cases where your judgment actually matters.**

---

## Data Model

### Active Incidents Registry

Track ongoing incidents to match new messages against:

```json
{
  "active_incidents": [
    {
      "id": "INC-001",
      "jira_ticket": "PROD-123",
      "title": "Checkout API 500 errors",
      "started_at": "2024-11-25T10:00:00Z",
      "last_activity": "2024-11-25T10:08:00Z",
      "status": "active",
      "keywords": ["checkout", "500", "API", "deploy"],
      "channels": ["engineering-alerts", "general", "incidents"],
      "messages": [
        {"id": "msg_001", "confidence": 1.0, "status": "original"},
        {"id": "msg_002", "confidence": 0.95, "status": "auto_linked"},
        {"id": "msg_003", "confidence": 0.72, "status": "pending_review"}
      ]
    }
  ]
}
```

### Pending Review Queue

Messages the AI is uncertain about:

```json
{
  "pending_reviews": [
    {
      "message_id": "msg_003",
      "message_text": "hey is checkout down?",
      "user": "Jordan",
      "channel": "general",
      "timestamp": "2024-11-25T10:03:00Z",
      "proposed_match": {
        "incident_id": "INC-001",
        "jira_ticket": "PROD-123",
        "confidence": 0.72,
        "reason": "Mentions 'checkout', similar timeframe to active incident"
      },
      "alternatives": [
        {"action": "link_to_existing", "target": "PROD-123"},
        {"action": "create_new_ticket", "target": null},
        {"action": "ignore", "target": null}
      ],
      "status": "pending"
    }
  ]
}
```

---

## Dashboard UI: Ticket Triage Section

### Option A: New Navigation Section (Recommended)

Add "🔗 Ticket Triage" as Section 5 in the sidebar navigation:

```
Sidebar Navigation:
├── 📥 Smart Inbox
├── 🧠 Context Engine  
├── 📊 Analytics
├── ⚙️ Settings
└── 🔗 Ticket Triage  ← NEW (shows badge with pending count)
```

### Triage Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  🔗 Ticket Triage                                           [3 pending] │
│  Review AI-uncertain message classifications                            │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  🎫 PROD-123: Checkout API 500 errors                           │   │
│  │  Status: Active | Created: 10:00am | Last activity: 10:08am     │   │
│  │                                                                  │   │
│  │  📎 Pending Review (sorted by confidence):                       │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │  72% │ "hey is checkout down?" - Jordan (#general)        │  │   │
│  │  │      │ 10:03am                                            │  │   │
│  │  │      │ [✓ Link to PROD-123] [✗ Not Related] [🆕 New Ticket]│  │   │
│  │  ├───────────────────────────────────────────────────────────┤  │   │
│  │  │  65% │ "API issues anyone?" - Dave (#random)              │  │   │
│  │  │      │ 10:04am                                            │  │   │
│  │  │      │ [✓ Link to PROD-123] [✗ Not Related] [🆕 New Ticket]│  │   │
│  │  └───────────────────────────────────────────────────────────┘  │   │
│  │                                                                  │   │
│  │  ✅ Auto-Linked (high confidence):                               │   │
│  │  • "looking into it" - Marcus (95%)                             │   │
│  │  • "found it, bad deploy" - Lisa (91%)                          │   │
│  │                                                                  │   │
│  │  [Bulk: Link All Pending] [Bulk: Dismiss All]                   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  🆕 Unmatched Messages (potential new tickets)                   │   │
│  │  ┌───────────────────────────────────────────────────────────┐  │   │
│  │  │  "Can we discuss OAuth integration this sprint?" - Kyle   │  │   │
│  │  │  #product | 10:15am | Score: 68                           │  │   │
│  │  │  [🎫 Create Ticket] [❌ Ignore]                            │  │   │
│  │  └───────────────────────────────────────────────────────────┘  │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### UI Features

| Feature | Description |
|---------|-------------|
| **Confidence % badge** | Shows AI certainty for each proposed link |
| **Sort by confidence** | Highest confidence items first (most likely correct) |
| **One-click actions** | ✓ Link, ✗ Not Related, 🆕 New Ticket |
| **Bulk actions** | Link All, Dismiss All, Select multiple |
| **Auto-linked section** | Shows what AI did automatically (transparency) |
| **Pending count badge** | Sidebar shows number of items needing review |
| **Source context** | Shows channel, timestamp, user for each message |

---

## Alternative: Slack Notification (Zero Dashboard)

For users who don't want to check a dashboard, AI can ask directly in Slack:

```
┌─────────────────────────────────────────────────────────────┐
│  🤖 Traverse Bot                                   10:03 AM │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  I found a message that might be related to PROD-123       │
│  (Checkout API 500 errors):                                │
│                                                             │
│  > "hey is checkout down?" - Jordan in #general            │
│                                                             │
│  Confidence: 72%                                           │
│                                                             │
│  React to decide:                                          │
│  👍 = Link to PROD-123                                     │
│  🆕 = Create new ticket                                    │
│  ❌ = Ignore (not important)                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Benefits:**
- No context switching to dashboard
- Quick emoji reaction to decide
- Works on mobile

**Drawbacks:**
- Can get noisy if many uncertain items
- No bulk actions
- Interrupts flow

**Recommendation:** Offer both. Dashboard for batch review, Slack for urgent/time-sensitive.

---

## Classification Algorithm

### Step 1: Message Arrives

```python
async def classify_message(message: dict) -> Classification:
    # Get embedding for the message
    embedding = await get_embedding(message["text"])
    
    # Get active incidents from registry
    active_incidents = await get_active_incidents(max_age_hours=4)
    
    # Calculate similarity to each active incident
    matches = []
    for incident in active_incidents:
        similarity = calculate_similarity(embedding, incident.embedding)
        keyword_match = check_keyword_overlap(message["text"], incident.keywords)
        time_proximity = calculate_time_proximity(message["timestamp"], incident.last_activity)
        
        # Weighted confidence score
        confidence = (
            similarity * 0.5 +           # Embedding similarity
            keyword_match * 0.3 +         # Keyword overlap
            time_proximity * 0.2          # Recent = more likely related
        )
        
        if confidence > 0.5:
            matches.append({"incident": incident, "confidence": confidence})
    
    return Classification(
        message=message,
        matches=sorted(matches, key=lambda x: x["confidence"], reverse=True),
        best_match=matches[0] if matches else None
    )
```

### Step 2: Route Based on Confidence

```python
async def route_message(classification: Classification):
    if not classification.best_match:
        # No match found - evaluate for new ticket
        if classification.message["priority_score"] >= 70:
            return Action.CREATE_NEW_TICKET
        else:
            return Action.IGNORE
    
    confidence = classification.best_match["confidence"]
    
    if confidence >= 0.90:
        # High confidence - auto-link
        await auto_link_to_incident(
            classification.message,
            classification.best_match["incident"]
        )
        return Action.AUTO_LINKED
    
    elif confidence >= 0.50:
        # Uncertain - ask human
        await add_to_review_queue(
            classification.message,
            classification.best_match
        )
        return Action.PENDING_REVIEW
    
    else:
        # Low confidence - treat as unrelated
        if classification.message["priority_score"] >= 70:
            return Action.CREATE_NEW_TICKET
        else:
            return Action.IGNORE
```

### Step 3: Handle Human Decision

```python
async def handle_review_decision(message_id: str, decision: str, target: str = None):
    if decision == "link":
        # User confirmed link
        await add_comment_to_jira(target, message)
        await update_incident_messages(target, message_id, status="confirmed")
        
    elif decision == "new_ticket":
        # User wants new ticket
        await create_jira_ticket(message)
        await create_new_incident(message)
        
    elif decision == "ignore":
        # User says not important
        await mark_as_ignored(message_id)
    
    # Remove from review queue
    await remove_from_review_queue(message_id)
```

---

## Incident Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                    INCIDENT LIFECYCLE                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  [New high-priority message, no match]                      │
│           ↓                                                 │
│  CREATE INCIDENT                                            │
│  • Create Jira ticket                                       │
│  • Add to active incidents registry                         │
│  • Extract keywords for matching                            │
│           ↓                                                 │
│  ACTIVE (accepting related messages)                        │
│  • New messages matched → auto-link or review               │
│  • Keywords updated as conversation evolves                 │
│           ↓                                                 │
│  [2 hours of no activity]                                   │
│           ↓                                                 │
│  AUTO-CLOSE                                                 │
│  • Mark incident as resolved                                │
│  • Keep in history for future reference                     │
│  • Stop matching new messages                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Implementation Phases

### Phase 1: Foundation (4-6 hours)
- [ ] Create `incident_registry.py` service
- [ ] Add incident tracking to database models
- [ ] Implement basic similarity matching
- [ ] Add `review_queue` table

### Phase 2: Dashboard UI (4-6 hours)
- [ ] Add "Ticket Triage" to sidebar navigation
- [ ] Build pending review list component
- [ ] Implement ✓/✗ action buttons
- [ ] Add bulk action support
- [ ] Show auto-linked messages (transparency)

### Phase 3: Classification Logic (3-4 hours)
- [ ] Implement confidence scoring algorithm
- [ ] Add keyword extraction
- [ ] Build time-proximity weighting
- [ ] Test and tune thresholds

### Phase 4: Jira Integration (2-3 hours)
- [ ] Add `add_comment()` to JiraService
- [ ] Link comments with attribution
- [ ] Update ticket status based on activity

### Phase 5: Slack Notifications (Optional, 2-3 hours)
- [ ] Build notification message for uncertain items
- [ ] Handle emoji reactions as decisions
- [ ] Rate limit to avoid spam

**Total Estimate:** 15-22 hours

---

## Success Criteria

- [ ] 80%+ of messages auto-handled (high/low confidence)
- [ ] <20% of messages require human review
- [ ] Zero duplicate tickets for the same incident
- [ ] Review queue cleared within 1 hour during work hours
- [ ] User can bulk-process 10 items in <30 seconds

---

## Open Questions

1. **Confidence thresholds:** Is 90%/50% right, or should it be tunable per user?
2. **Incident timeout:** 2 hours default, but should ongoing issues stay open longer?
3. **Cross-workspace:** If using multiple Slack workspaces, how to handle?
4. **Training data:** Should user decisions improve the model over time?

---

## Related Files

- `backend/integrations/jira_service.py` - Needs `add_comment()` method
- `backend/services/memory_service.py` - Embedding storage
- `backend/database/models.py` - New tables for incidents, review queue
- `streamlit_dashboard.py` - New Ticket Triage section
