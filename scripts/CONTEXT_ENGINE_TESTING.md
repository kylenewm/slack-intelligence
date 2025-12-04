# Context Engine Testing Guide

## Overview

This guide explains how to test the Context Engine with comprehensive edge cases and full process visibility.

## Scripts

### 1. `test_context_engine.py` - Main Test Script

Comprehensive test suite that:
- Tests multiple edge cases (easy, medium, hard)
- Shows full process flow (context assembly → detection → query → research → synthesis)
- Analyzes context usage to verify the engine is using available context
- Provides detailed logging of each step

**Usage:**
```bash
python scripts/test_context_engine.py
```

**Features:**
- **7 Test Cases** covering different scenarios:
  - Easy: Generic questions (no context needed)
  - Medium: Context-aware questions (should use institutional memory, codebase)
  - Hard: Architecture decisions (needs full context)
  - Edge cases: Ambiguous questions, tech comparisons, bug reports, product questions

- **Full Process Visibility:**
  - Step 1: Context Assembly (shows all components)
  - Step 2: Ticket Type Detection
  - Step 3: Search Query Building (with quality analysis)
  - Step 4: Exa Research (if available)
  - Step 5: Research Synthesis
  - Step 6: Final Research Summary
  - Step 7: Context Usage Analysis

- **Output:**
  - Rich terminal output with colors and formatting
  - Detailed statistics and analysis
  - Results saved to `simulations/context_engine_test_YYYY-MM-DD_HH-MM-SS.json`

### 2. `view_context_engine_results.py` - Results Viewer

View detailed results from saved test runs.

**Usage:**
```bash
# List available test results
python scripts/view_context_engine_results.py

# View specific test result file
python scripts/view_context_engine_results.py simulations/context_engine_test_2025-11-29_21-37-30.json
```

**Features:**
- Lists all available test result files
- Displays full process flow for each test case
- Shows context components, detection results, queries, sources, synthesis
- Context usage analysis

## Test Cases Explained

### Easy Cases (No Context Needed)
These test basic functionality without requiring context:
- Generic questions that can be answered with general knowledge

### Medium Cases (Context-Aware)
These should use available context:
- **429 Errors**: Should reference institutional memory (tenacity, exponential backoff)
- **Bug Reports**: Should use codebase structure to identify affected files

### Hard Cases (Full Context Required)
These require multiple context components:
- **Architecture Decisions**: Need identity (company mission) + product plans
- **Tech Comparisons**: Should consider our stack (Python/FastAPI) from identity
- **Product Questions**: Should reference PRDs from product plans

### Edge Cases
These test robustness:
- **Ambiguous Questions**: "How do we handle this?" - needs context to understand
- **Vague Bug Reports**: Should trigger codebase analysis

## What Gets Tested

### Context Assembly
- ✅ Identity loading (Traverse.ai mission, values, tech stack)
- ✅ Institutional memory (past issues & solutions)
- ✅ Product plans (PRDs)
- ✅ Codebase structure (self-awareness)
- ✅ Team context (active users)

### Query Quality
- ✅ Specificity (not too generic)
- ✅ Technology context (mentions relevant techs)
- ✅ Question format (proper question structure)
- ✅ Length (appropriate word count)

### Context Usage
- ✅ Verifies expected context components are actually used
- ✅ Checks if company identity appears in results
- ✅ Checks if past solutions are referenced
- ✅ Checks if codebase components are mentioned
- ✅ Checks if product plans are referenced

## Understanding the Output

### Context Statistics
Shows the size of each context component:
- Identity: Company mission, values, tech stack
- Institutional Memory: Past issues and solutions
- Product Plans: PRDs and feature plans
- Codebase Structure: File/class/method mapping
- Team Context: Active team members

### Query Quality Analysis
- **Specificity**: Is the query specific enough?
- **Technology Context**: Does it mention relevant technologies?
- **Query Length**: Is it an appropriate length?
- **Question Format**: Is it properly formatted as a question?

### Context Usage Analysis
For each expected context component:
- ✅ **Found**: The context was used in the results
- ❌ **Not Found**: The context was available but not used

## Edge Cases That Test "Not Spoonfed" Scenarios

1. **Ambiguous Questions**: "How do we handle this?"
   - Requires context to understand what "this" refers to
   - Should use codebase structure and institutional memory

2. **Technology Comparisons**: "pgvector vs Pinecone?"
   - Should consider our stack (Python/FastAPI) from identity
   - Should reference codebase if we're already using one

3. **Architecture Decisions**: "OAuth vs SAML?"
   - Needs company identity (target customers, enterprise focus)
   - Needs product plans (enterprise features roadmap)

4. **Bug Reports**: "Getting 400 errors"
   - Should use codebase structure to find relevant files
   - Should reference institutional memory for similar past issues

## Requirements

- `OPENAI_API_KEY`: Required for LLM operations (detection, query building, synthesis)
- `EXA_API_KEY`: Optional, enables actual research (tests will skip if not available)
- `PINECONE_API_KEY`: Optional, enables RAG memory search (falls back to JSON if not available)

## Example Output

```
🧠 CONTEXT ASSEMBLY TEST
================================================================================
Assembling full context...

Step 0: Identity Component
┌─ Identity ────────────────────────────────────────────────────────────────┐
│ Traverse.ai - Intelligent Slack Middleware Platform...                      │
└─────────────────────────────────────────────────────────────────────────────┘

Step 1: Context Assembly
Step 2: Ticket Type Detection
Step 3: Search Query Building
Generated Query: What are the tradeoffs between OAuth and SAML for B2B SaaS enterprise authentication?

Step 4: Exa Research
Found 5 sources

Step 5: Research Synthesis
┌─ Synthesis & Recommendation ───────────────────────────────────────────────┐
│ ## 🎯 Synthesis & Recommendation                                           │
│ ...                                                                         │
└─────────────────────────────────────────────────────────────────────────────┘

Step 7: Context Usage Analysis
┌─ Context Usage Analysis ──────────────────────────────────────────────────┐
│ Context Component │ Found │ Details                                        │
│ Identity          │ ✅ Yes │ Company identity terms found                  │
│ Product Plans     │ ✅ Yes │ Product plans available in context            │
└─────────────────────────────────────────────────────────────────────────────┘
```

## Tips

1. **Run with Exa**: For full testing, ensure `EXA_API_KEY` is set
2. **Check Context Usage**: Look for ❌ in context usage analysis - these indicate missed opportunities
3. **Review Query Quality**: Warnings in query quality suggest the query might be too generic
4. **Compare Results**: Run tests multiple times to see consistency
5. **View Saved Results**: Use the viewer script to review detailed results later

## Troubleshooting

- **"Exa client not available"**: Set `EXA_API_KEY` environment variable
- **"OpenAI client not available"**: Set `OPENAI_API_KEY` environment variable
- **"No context found"**: Check that `backend/context/` directory exists with proper files
- **"No test results"**: Run `test_context_engine.py` first to generate results


