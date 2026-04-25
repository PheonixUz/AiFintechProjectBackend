# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AI-powered business analysis platform for Коммерческий банк Узбекистана (KMB). Given a business niche, GPS coordinates, and starting capital, the system answers: **"Should I open this business, at this location, right now?"** — with a YES/NO recommendation in Uzbek and a full analytical breakdown.

**Core approach:** No custom ML training. Instead: bank transaction data → deterministic algorithms → Claude LLM synthesizes a final decision via `tool_use`.

## Commands

```bash
# Setup
uv sync                          # Install all dependencies
uv sync --group dev              # Include dev dependencies

# Run server
uv run uvicorn app.main:app --reload --app-dir src

# Tests
uv run pytest                                              # All tests
uv run pytest tests/unit/                                  # Unit tests only
uv run pytest tests/integration/                           # Integration tests only
uv run pytest tests/unit/algorithms/test_viability.py     # Single file
uv run pytest -k "test_monte_carlo"                        # Single test by name
uv run pytest --cov=src/app --cov-report=term-missing      # With coverage

# Linting / formatting
uv run ruff check src/ tests/
uv run ruff format src/ tests/
```

## Architecture

### MVP: Agent-Based Design

The MVP uses **5 models** (not all 35 from the full spec). A single Claude agent orchestrates everything via `tool_use` — it decides which data to fetch and which algorithms to run, then synthesizes a final YES/NO answer.

```
POST /api/v1/analyze
  { nisha, koordinata, kapital }
        │
  AgentOrchestrator
    Claude (tool_use loop)
        │
    ┌───┴──────────────────────┐
    │  MCP Tools (DB queries)  │   ←── PostgreSQL via MCP server
    │  Algorithm Tools (math)  │   ←── Pure Python functions
    └───┬──────────────────────┘
        │
  Final YES/NO + Uzbek explanation
        │
  AnalysisResponse (JSON)
```

### Layer Responsibilities

| Layer | Location | Responsibility |
|---|---|---|
| `api/routes/` | HTTP boundary | Request validation, response serialization |
| `agent/` | AI orchestration | Claude `tool_use` loop; decides which tools to call and in what order |
| `mcp/tools/` | DB gateway | MCP server tools that execute SQL queries; the only layer that touches the DB |
| `algorithms/` | Pure math | Stateless functions — no I/O, no side effects; trivially unit-testable |
| `db/repositories/` | Data access | Async SQL queries called exclusively by MCP tools |
| `schemas/` | Contracts | Pydantic models for requests, responses, and algorithm inputs/outputs |

### The 5 MVP Models

| Code | Name | Algorithm | What it answers |
|---|---|---|---|
| M-A3 | Saturation Index | Composite index | Is the niche overcrowded? (0–100) |
| M-C1 | Location Score | Weighted composite | Is this specific spot attractive? (0–100) |
| M-D1 | Viability Check | Monte Carlo + break-even | Will the business survive 2 years? |
| M-D3 | ROI Estimator | DCF / NPV / IRR | Is the investment financially worthwhile? |
| M-E2 | Churn Prediction | Scoring model | What is the closure probability in 2 years? |

### Agent Tool Types

**MCP Tools** (data fetching — all DB access goes through here):
- `get_niche_transactions(niche, radius)` — MCC transaction volume for the niche
- `get_market_size(niche)` — TAM/SAM estimates
- `get_competitors(lat, lon, radius)` — nearby competitors with metadata
- `get_closure_stats(niche)` — historical closure rates for the niche
- `get_location_poi(lat, lon)` — points of interest around the coordinate
- `get_traffic_data(lat, lon)` — pedestrian/vehicle traffic estimates
- `get_sector_benchmarks(niche)` — industry cost/margin norms
- `get_cost_data(lat, lon)` — local rent, labor, supply costs

**Algorithm Tools** (pure computation — called with data from MCP tools):
- `run_saturation_index(data)` → `float`
- `run_location_score(data)` → `float` + sub-scores
- `run_viability_check(data)` → survival %, break-even months, runway
- `run_roi_estimator(data)` → NPV, ROI, payback months
- `run_churn_prediction(data)` → `float` (0–1)

### LLM Usage Pattern

The agent uses `tool_use` (not just text generation):
1. Agent receives user request
2. Claude calls MCP tools to fetch structured data from PostgreSQL
3. Claude calls algorithm tools with that data
4. Claude synthesizes all numeric results → YES/NO + Uzbek-language explanation

System prompts (bank context, model descriptions) use **prompt caching** (`cache_control: ephemeral`) — reduces API cost ~80% on repeated calls. See `agent/prompts/system.py`.

### Key Environment Variables

```
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/fintech_db
ANTHROPIC_API_KEY=sk-ant-...
REDIS_URL=redis://localhost:6379
```

Redis caches full agent responses — identical `{nisha, koordinata, kapital}` inputs skip re-computation within a TTL window.

## Testing Conventions

- `tests/unit/algorithms/` — test pure algorithm functions with synthetic data; no DB, no agent
- `tests/integration/` — require a real PostgreSQL test DB; agent is mocked
- `conftest.py` provides: async DB session fixture, mock agent fixture, sample `AnalysisRequest` fixtures

Algorithm modules in `src/app/algorithms/` must be pure functions (no I/O) — they receive only plain Python data and return results.
