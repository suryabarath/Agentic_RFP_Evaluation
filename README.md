# Agentic RFP Evaluation and Supplier Ranking

An AI-powered application that reads supplier RFP proposals, scores them against
configurable criteria, benchmarks suppliers against their peers, and produces an
explainable, deterministic final leaderboard.

**Built for:** IIT Roorkee Agentic AI Programme — classroom mini project.

## The one rule everything else follows

> The LLM may judge proposal content. It must never decide arithmetic, benchmarks,
> tie-breaks, or rank.

Concretely: the LLM returns a score (0–10) and a justification with evidence per criterion,
as JSON. Every weighted score, benchmark, gap analysis, relative percentage, Peer Performance
Index (PPI), tie-break, and rank is computed by pure Python in `src/scorer.py`, `src/ppi.py`,
and `src/ranking.py` — files that have no LLM client, no API import, and cannot call one.
That is enforced by the module architecture, not just by convention.

## Quick start

```bash
# Clone and setup
git clone https://github.com/suryabarath/Agentic_RFP_Evaluation.git
cd Agentic_RFP_Evaluation

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
python database/init_db.py

# Run the application
streamlit run app.py
```

Open the app, tick **"Offline demo mode"** in the sidebar (on by default), upload
supplier PDFs, and click **Run Evaluation**. The whole pipeline runs with zero API
calls and zero cost, using simulated realistic evaluation results.

To use a real LLM instead, untick offline mode, pick a provider (Anthropic or OpenAI),
paste an API key (kept only in browser session memory, never written to disk), and
click **Test Connection** before evaluating.

Run the test suite:
```bash
pytest -q            # 39 tests: scorer, PPI, ranking, and pipeline
python test_data/run_e2e_test.py   # runs the full pipeline, prints the leaderboard
```

## Agentic design

| Component | Responsibility | Lives in |
|-----------|----------------|----------|
| Orchestrator | Controls the workflow, calls modules in order, handles errors | `src/orchestrator.py` |
| PDF Tool | Extracts clean text from uploaded PDFs | `src/pdf_tool.py` |
| Evaluator | Sends proposal to LLM, parses JSON response | `src/evaluator.py` |
| Validator | Schema check, score clamping, warning collection | `src/validator.py` |
| Scorer | Weighted score calculation per supplier | `src/scorer.py` |
| Benchmarks | Best/worst/average across all suppliers | `src/benchmarks.py` |
| Gap Analysis | Identifies improvement opportunities | `src/gaps.py` |
| Relative Performance | Percentile and tier classification | `src/relative_performance.py` |
| PPI Calculator | Composite performance index | `src/ppi.py` |
| Ranking Engine | Deterministic ranking with tie-breaks | `src/ranking.py` |

**Why a plain Python orchestrator instead of a graph framework** (e.g., LangGraph):
this workflow is a fixed pipeline — every run executes the same steps in the same
order, it never re-plans itself. That is a DAG, not an autonomous agent deciding
its own control flow. A graph framework would earn its keep if this workflow needed
durable checkpoints, human-in-the-loop pauses, or dynamic re-planning — it doesn't.

```
┌─────────────────────────────────────────────────────────────────────┐
│                         EVALUATION PIPELINE                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Upload PDFs ──► Extract Text ──► LLM Evaluation ──► Validation     │
│                                                                      │
│       ┌──────────────────────────────────────────────────────┐      │
│       │                    For Each Supplier                  │      │
│       │  Score ──► Benchmark ──► Gaps ──► Relative ──► PPI   │      │
│       └──────────────────────────────────────────────────────┘      │
│                                                                      │
│  ──► Final Ranking ──► Persist to Database ──► Display Results      │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Database schema

SQLite database with three core tables:

- **`evaluation_criteria`**: `criterion_id`, `name`, `description`, `weight`, `max_score`, `is_active`.
  Weights must sum to 100%. The database is seeded with 5 default criteria.

- **`rfp_runs`**: `rfp_run_id`, `created_at`, `status`, `notes`.
  Tracks each evaluation batch. Status: `pending` → `in_progress` → `completed`/`failed`.

- **`supplier_results`**: One row per supplier per run — `supplier_name`, `absolute_score`,
  `ppi`, `final_rank`, `result_json` (complete evaluation data), `validation_warnings`.

## Evaluation criteria (seeded defaults)

| Criterion | Weight | Max Score | Description |
|-----------|--------|-----------|-------------|
| Technical Capability | 30% | 10 | Architecture, integrations, scalability, technical fit |
| Implementation Plan | 20% | 10 | Timeline, milestones, staffing, risk plan |
| Commercial Value | 20% | 10 | Pricing clarity, total cost, assumptions |
| Security & Compliance | 20% | 10 | Controls, certifications, privacy, auditability |
| Support & Experience | 10% | 10 | Support model, similar projects, references |

Total weight: **100%** (required for valid scoring)

## Formulas

### Weighted Score Calculation

```
Criterion Weighted Score = (raw_score / max_score) × weight
Total Weighted Score = Σ (criterion weighted scores)
```

**Worked example:**
```
Technical:      8/10 × 30 = 24.00
Implementation: 7/10 × 20 = 14.00
Commercial:     8/10 × 20 = 16.00
Security:       9/10 × 20 = 18.00
Support:        8/10 × 10 =  8.00
─────────────────────────────────
Total Weighted Score:      80.00
```

### PPI (Proposal Performance Index)

The PPI is a composite metric that goes beyond raw scores:

```
PPI = (WeightedScore × 0.70) + (ConsistencyBonus × 0.15) + (QualityBonus × 0.15) - RiskPenalty
```

Where:
- **WeightedScore**: The total weighted score (0-100)
- **ConsistencyBonus**: Rewards consistent performance across criteria (low variance)
- **QualityBonus**: Based on validation quality (fewer warnings = higher bonus)
- **RiskPenalty**: Deduction for identified risks (1 point per risk, max 10)

**PPI Grades:**
| Grade | PPI Range | Interpretation |
|-------|-----------|----------------|
| A | 90-100 | Excellent proposal |
| B | 80-89 | Good proposal |
| C | 70-79 | Adequate proposal |
| D | 60-69 | Below average |
| F | 0-59 | Poor proposal |

## Tie-break rules (deterministic)

When suppliers have the same weighted score, ties are broken in this order:

1. **Higher PPI Score** — composite quality wins
2. **Fewer Risks** — lower risk count wins
3. **Fewer Validation Warnings** — cleaner data wins
4. **Higher score on top-weight criterion** — strongest on most important criterion
5. **Alphabetical by supplier name** — final deterministic fallback

This ensures the same inputs **always** produce the same ranking.

## LLM providers

The application supports multiple LLM providers through a unified interface:

| Provider | Models Available |
|----------|-----------------|
| **Anthropic** | claude-sonnet-4, claude-opus-4, claude-3-5-sonnet, claude-3-5-haiku |
| **OpenAI** | gpt-4o, gpt-4o-mini, gpt-4-turbo, gpt-3.5-turbo |

Provider and model are selectable in the sidebar. API keys are stored in session
memory only — never persisted to disk or database.

## Offline demo mode

Streamlit deployments and graded demos share one risk: an API outage, rate limit,
or missing key shouldn't make the submission undemonstrable. The mock evaluator
in `src/evaluator.py` returns realistic, deterministic evaluation JSON — same
schema a real model returns, run through the identical Validation, Scoring, and
Ranking pipeline.

This lets the README demonstrate a real leaderboard, real scores, and real
tie-break resolution with zero dependency on model or network availability.
Untick "Offline demo mode" to use a live model.

## Validation & error handling

### Response validation

The validator (`src/validator.py`) ensures LLM responses are well-formed:

- **Schema validation**: All required fields present
- **Score clamping**: Scores capped to `max_score` (never exceed maximum)
- **Missing criteria**: Filled with score 0 and warning
- **Evidence checking**: Justifications must meet minimum length

Warnings are surfaced in the UI, never silently swallowed.

### Pipeline error handling

- One failed supplier does **not** sink the entire batch
- Failed evaluations are logged with error details
- Successful evaluations proceed to ranking
- Status becomes `failed` only if database persistence fails

## Testing

```bash
pytest -q
```

**39 tests** covering:
- `test_scorer.py`: Weighted score calculations, edge cases
- `test_ppi.py`: PPI formula, consistency scoring, grading
- `test_ranking.py`: Deterministic ordering, tie-break rules

```bash
python test_data/run_e2e_test.py
```

Runs the full pipeline outside Streamlit (no browser needed), prints the leaderboard.

## Folder structure

```
Agentic_RFP_Evaluation/
├── app.py                      # Streamlit web UI
├── requirements.txt            # Python dependencies
├── README.md                   # This file
│
├── database/
│   ├── init_db.py              # Database initialization & seeding
│   └── rfp.db                  # SQLite database (generated)
│
├── src/
│   ├── __init__.py
│   ├── config.py               # Multi-provider configuration
│   ├── database.py             # Database helper functions
│   ├── pdf_tool.py             # PDF text extraction (PyMuPDF)
│   ├── schemas.py              # Pydantic validation models
│   ├── evaluator.py            # LLM evaluation (Anthropic/OpenAI)
│   ├── validator.py            # Response validation & clamping
│   ├── scorer.py               # Weighted score calculation
│   ├── benchmarks.py           # Best/worst/average computation
│   ├── gaps.py                 # Gap analysis per supplier
│   ├── relative_performance.py # Percentile & tier classification
│   ├── ppi.py                  # Proposal Performance Index
│   ├── ranking.py              # Deterministic ranking engine
│   ├── orchestrator.py         # Pipeline coordinator
│   ├── export.py               # JSON export functions
│   └── errors.py               # Custom exception hierarchy
│
├── tests/
│   ├── conftest.py             # Pytest fixtures
│   ├── test_scorer.py          # Scorer unit tests
│   ├── test_ppi.py             # PPI unit tests
│   └── test_ranking.py         # Ranking unit tests
│
└── test_data/
    ├── generate_test_pdfs.py   # Synthetic PDF generator
    ├── run_e2e_test.py         # End-to-end pipeline test
    └── *.pdf                   # Sample proposal PDFs
```

## Environment variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LLM_PROVIDER` | `anthropic` | LLM provider (`anthropic` or `openai`) |
| `LLM_MODEL` | `claude-sonnet-4-20250514` | Model to use |
| `ANTHROPIC_API_KEY` | - | Anthropic API key (for live mode) |
| `OPENAI_API_KEY` | - | OpenAI API key (for live mode) |
| `USE_MOCK_LLM` | `true` | Enable offline demo mode |
| `MAX_TOKENS` | `4000` | Max tokens for LLM response |
| `TEMPERATURE` | `0.2` | LLM temperature (lower = more deterministic) |

## Assumptions & design decisions

1. **LLM judges content, Python computes numbers**: The LLM evaluates proposals
   qualitatively; all arithmetic (scores, rankings, benchmarks) is deterministic Python.

2. **Criteria weights must sum to 100%**: Enforced at database seed time.

3. **Scores are 0-10 scale**: Configurable per criterion via `max_score`.

4. **API keys are session-only**: Never persisted to disk or database.
   BYOK (Bring Your Own Key) model.

5. **PDFs must be text-based**: Scanned/image-only PDFs will extract no text.
   OCR is out of scope.

6. **Single-run evaluation**: No incremental re-evaluation. Each run is independent.

## Known limitations

- **SQLite is file-based**: On Streamlit Community Cloud, the filesystem resets
  on redeploy. Historical runs will not survive a redeploy.

- **No OCR**: Image-based PDFs will fail to extract text. Use text-based PDFs.

- **Provider abstraction**: Currently supports Anthropic and OpenAI. Adding a
  third provider requires extending `src/evaluator.py`.

- **No authentication**: The app has no user login. Suitable for demos, not
  production multi-tenant use.

## Tech stack

| Component | Technology |
|-----------|------------|
| Web Framework | Streamlit 1.39 |
| Database | SQLite 3 |
| PDF Processing | PyMuPDF 1.24 |
| Data Validation | Pydantic 2.10 |
| LLM Integration | Anthropic SDK, OpenAI SDK |
| Testing | pytest 8.3 |

## License

MIT License — See LICENSE file for details.

## Acknowledgments

- **IIT Roorkee** — Agentic AI Programme
- **Anthropic** — Claude API
- **OpenAI** — GPT API
- **Streamlit** — Web framework
- **PyMuPDF** — PDF processing
