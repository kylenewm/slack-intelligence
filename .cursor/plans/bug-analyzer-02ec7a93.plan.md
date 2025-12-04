<!-- 02ec7a93-6a27-4882-b815-21895de8b250 956d8f7a-a904-4b5d-941b-3a61df38ed62 -->
# Comprehensive Test Suite Plan

## Directory Structure

```
tests/
├── conftest.py              # Shared fixtures (DB, mocks, test data)
├── unit/                    # Fast, isolated tests
│   ├── test_timestamp_utils.py
│   ├── test_classifier.py
│   ├── test_message_parser.py
│   └── test_cache_service.py
├── integration/             # Tests with real DB, mocked external APIs
│   ├── test_exa_service.py
│   ├── test_jira_service.py
│   ├── test_inbox_api.py
│   └── test_sync_service.py
├── e2e/                     # Full flow tests
│   ├── test_jira_creation_flow.py
│   ├── test_dashboard_flows.py
│   └── test_research_trigger.py
└── fixtures/                # Test data
    ├── sample_messages.json
    └── mock_responses.py
```

## Phase 1: Test Infrastructure (conftest.py)

- Create test database fixture (SQLite in-memory)
- Create mock fixtures for Slack, Jira, Exa, OpenAI APIs
- Create sample message fixtures covering all ticket types
- Add pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.e2e`

Key file: `tests/conftest.py`

## Phase 2: Unit Tests

Focus: Pure logic, no external dependencies

1. **test_timestamp_utils.py** - Verify UTC handling

   - Test `datetime.utcfromtimestamp()` conversion
   - Test filter calculations with various hours_ago values
   - Test `format_time_ago()` display logic

2. **test_classifier.py** - Verify ticket type detection

   - Test all ticket types: bug, product_decision, architecture, etc.
   - Test `needs_research` logic with edge cases
   - Test with 20+ sample messages

3. **test_message_parser.py** - Verify Slack message parsing

   - Test timestamp extraction
   - Test mention detection
   - Test thread handling

4. **test_cache_service.py** - Verify DB operations

   - Test `get_messages_by_score_range()` with time filters
   - Test `archive_message()`
   - Test message insertion/retrieval

## Phase 3: Integration Tests

Focus: Real DB, mocked external APIs

1. **test_exa_service.py**

   - Test `detect_ticket_type()` with mocked OpenAI
   - Test `research_for_ticket()` with mocked Exa API
   - Test `synthesize_research()` output format

2. **test_jira_service.py**

   - Test `create_ticket()` with mocked Jira API
   - Test ADF formatting
   - Test bug analysis formatting

3. **test_inbox_api.py**

   - Test `/api/slack/inbox` endpoint
   - Test filtering by hours_ago, view, limit
   - Test response schema

4. **test_sync_service.py**

   - Test message sync with mocked Slack API
   - Test deduplication logic

## Phase 4: End-to-End Tests

Focus: Full flows as user would experience

1. **test_jira_creation_flow.py**

   - Insert test message -> Call Jira create -> Verify research triggered -> Verify ticket created
   - Test bug ticket flow (no research)
   - Test research ticket flow (with Exa)

2. **test_dashboard_flows.py**

   - Test inbox returns correct messages for time filter
   - Test archive functionality
   - Test Notion task creation

3. **test_research_trigger.py**

   - Test specific messages that SHOULD trigger research
   - Test specific messages that should NOT trigger research
   - Verify classifier + Exa integration

## Phase 5: Test Runner Configuration

- `pytest.ini` with default options
- `requirements-test.txt` with pytest, pytest-asyncio, pytest-mock, httpx
- Single command: `pytest` runs all, `pytest tests/unit -v` for subset
- Environment variable `TEST_MODE=true` to use test DB

## Key Files to Modify

- `backend/database/db.py` - Add test DB support
- `requirements.txt` - Add test dependencies

## Success Criteria

- All tests pass with `pytest`
- Running `pytest tests/e2e/test_jira_creation_flow.py` before any change catches regressions
- Test suite completes in under 60 seconds

### To-dos

- [ ] Create tests/ directory structure and conftest.py with fixtures
- [ ] Write unit tests for timestamp handling and filters
- [ ] Write unit tests for classifier with 20+ sample messages
- [ ] Write unit tests for message parser
- [ ] Write unit tests for cache service DB operations
- [ ] Write integration tests for Exa service with mocked APIs
- [ ] Write integration tests for Jira service
- [ ] Write integration tests for inbox API endpoint
- [ ] Write e2e test for full Jira creation flow
- [ ] Write e2e test for research trigger scenarios
- [ ] Create pytest.ini and requirements-test.txt