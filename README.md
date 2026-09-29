# RFP Proposal Evaluation System

A Streamlit-based web application that automates supplier proposal evaluation using Large Language Models. Upload PDF proposals, get AI-generated scores, and view ranked results with detailed analytics.

**Project:** IIT Roorkee — Agentic AI Mini Project

---

## Core Principle

This system separates **qualitative judgment** from **quantitative computation**:

- **AI does**: Read proposals, assess quality, provide scores (0-10) with justifications
- **Python does**: Calculate weighted totals, compare suppliers, break ties, assign ranks

No mathematical operation depends on AI output interpretation. Scoring formulas, benchmarking logic, and ranking algorithms are implemented in isolated Python modules with no LLM dependencies.

---

## Getting Started

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

```bash
git clone https://github.com/suryabarath/Agentic_RFP_Evaluation.git
cd Agentic_RFP_Evaluation

python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate

pip install -r requirements.txt
python database/init_db.py
streamlit run app.py
```

### First Run

1. Open `http://localhost:8501` in your browser
2. The sidebar shows **AI Configuration** — leave "Offline demo mode" checked for testing
3. Go to **New Evaluation**, upload PDFs, and click **Run Evaluation**
4. View rankings and detailed scorecards

### Using Real AI

1. Uncheck "Offline demo mode" in sidebar
2. Select provider: **Anthropic** or **OpenAI**
3. Enter your API key
4. Click **Test Connection** to verify
5. Run evaluation — real AI analyzes your documents

---

## How It Works

### Processing Pipeline

```
PDF Upload → Text Extraction → AI Evaluation → Validation → Scoring
                                                              ↓
                                            Benchmarking ← Gap Analysis
                                                              ↓
                                            PPI Calculation → Ranking → Results
```

### Module Breakdown

| Module | Purpose |
|--------|---------|
| `src/pdf_tool.py` | Extracts readable text from PDF documents |
| `src/evaluator.py` | Communicates with AI providers (Claude/GPT) |
| `src/validator.py` | Checks AI responses for correctness |
| `src/scorer.py` | Computes weighted scores from raw evaluations |
| `src/benchmarks.py` | Calculates best/worst/average across suppliers |
| `src/gaps.py` | Identifies where each supplier can improve |
| `src/ppi.py` | Generates composite performance index |
| `src/ranking.py` | Produces final ordered leaderboard |
| `src/orchestrator.py` | Coordinates all modules in sequence |

---

## Scoring System

### Criteria Weights

| Category | Weight | What's Evaluated |
|----------|--------|------------------|
| Technical Capability | 30% | System design, technology choices, scalability |
| Implementation Plan | 20% | Project timeline, team structure, milestones |
| Commercial Value | 20% | Pricing structure, cost breakdown, value proposition |
| Security & Compliance | 20% | Data protection, certifications, audit readiness |
| Support & Experience | 10% | Past projects, support availability, references |

### Score Calculation

Each criterion receives a score from 0-10. The weighted total is computed as:

```
Weighted Score = Σ (criterion_score ÷ 10) × criterion_weight
```

**Example:**
- Technical: 8/10 × 30% = 24 points
- Implementation: 7/10 × 20% = 14 points
- Commercial: 9/10 × 20% = 18 points
- Security: 8/10 × 20% = 16 points
- Support: 7/10 × 10% = 7 points
- **Total: 79 points**

### Performance Index (PPI)

Beyond raw scores, PPI incorporates:

| Factor | Weight | Description |
|--------|--------|-------------|
| Weighted Score | 70% | Primary scoring component |
| Consistency | 15% | Rewards uniform performance across categories |
| Data Quality | 15% | Based on validation warnings |
| Risk Penalty | Deduction | -1 point per identified risk (max -10) |

**Grade Scale:**
- **A**: 90+ (Exceptional)
- **B**: 80-89 (Strong)
- **C**: 70-79 (Acceptable)
- **D**: 60-69 (Weak)
- **F**: Below 60 (Poor)

### Ranking Tiebreakers

When weighted scores match, suppliers are ordered by:

1. PPI score (higher wins)
2. Risk count (fewer wins)
3. Warning count (fewer wins)
4. Top criterion performance (higher wins)
5. Alphabetical name (final fallback)

---

## Database Structure

Three SQLite tables store all data:

**evaluation_criteria**
- Stores the five scoring categories
- Each has name, description, weight percentage, and max score
- Weights must total 100%

**rfp_runs**
- Records each evaluation session
- Tracks status: pending → in_progress → completed/failed
- Timestamps all operations

**supplier_results**
- One row per supplier per evaluation run
- Contains final score, PPI, rank
- Stores complete JSON with all evaluation details

---

## AI Provider Support

### Available Providers

| Provider | Supported Models |
|----------|-----------------|
| Anthropic | Claude Sonnet 4, Claude Opus 4, Claude 3.5 Sonnet, Claude 3.5 Haiku |
| OpenAI | GPT-4o, GPT-4o Mini, GPT-4 Turbo, GPT-3.5 Turbo |

### Configuration

Set via sidebar UI or environment variables:

| Variable | Purpose |
|----------|---------|
| `LLM_PROVIDER` | `anthropic` or `openai` |
| `ANTHROPIC_API_KEY` | Your Anthropic key |
| `OPENAI_API_KEY` | Your OpenAI key |
| `USE_MOCK_LLM` | `true` for offline testing |

API keys entered in the UI are stored only in browser session memory — never saved to disk.

---

## Offline Mode

For demonstrations and testing without API access:

- Generates realistic mock evaluations
- Uses document content to vary scores (same PDF = same scores)
- Runs through identical validation and ranking pipeline
- Zero cost, zero network dependency

This ensures the application remains fully demonstrable even without active API credentials.

---

## Project Layout

```
├── app.py                    # Main Streamlit application
├── requirements.txt          # Package dependencies
│
├── database/
│   ├── init_db.py           # Creates tables and seeds data
│   └── rfp.db               # SQLite file (auto-generated)
│
├── src/
│   ├── config.py            # Provider and model settings
│   ├── database.py          # Database query functions
│   ├── pdf_tool.py          # PDF text extraction
│   ├── schemas.py           # Data validation models
│   ├── evaluator.py         # AI communication layer
│   ├── validator.py         # Response verification
│   ├── scorer.py            # Score computation
│   ├── benchmarks.py        # Cross-supplier comparison
│   ├── gaps.py              # Improvement identification
│   ├── relative_performance.py  # Percentile calculation
│   ├── ppi.py               # Performance index
│   ├── ranking.py           # Leaderboard generation
│   ├── orchestrator.py      # Pipeline controller
│   ├── export.py            # JSON report generation
│   └── errors.py            # Exception definitions
│
├── tests/
│   ├── test_scorer.py       # Scoring logic tests
│   ├── test_ppi.py          # PPI calculation tests
│   └── test_ranking.py      # Ranking algorithm tests
│
└── test_data/
    ├── generate_test_pdfs.py    # Creates sample PDFs
    └── run_e2e_test.py          # Full pipeline test
```

---

## Running Tests

```bash
# Unit tests (39 total)
pytest -q

# End-to-end pipeline test
python test_data/run_e2e_test.py

# Generate sample PDFs
python test_data/generate_test_pdfs.py
```

---

## Synthetic Test Data

Four sample supplier proposals are included for testing and demonstration:

| Supplier | Profile | Expected Rank |
|----------|---------|---------------|
| **TechCorp Solutions** | Strong technical depth, detailed architecture, comprehensive security | High |
| **GlobalSystems Corp** | Enterprise focus, extensive compliance documentation, proven track record | High |
| **CloudFirst Inc** | Cloud-native approach, modern tech stack, competitive pricing | Medium-High |
| **BudgetTech Ltd** | Budget-focused, minimal documentation, basic features | Low |

### Generating Test PDFs

```bash
python test_data/generate_test_pdfs.py
```

This creates realistic proposal documents with varying quality levels:
- Different content lengths (7KB to 35KB)
- Varying detail in technical sections
- Different pricing structures
- Diverse experience levels

### Using Test Data

1. Generate PDFs: `python test_data/generate_test_pdfs.py`
2. Run the app: `streamlit run app.py`
3. Upload the PDFs from `test_data/` folder
4. Run evaluation to see rankings

The mock evaluator produces consistent scores based on document content, so the same PDFs will always rank in the same order.

---

## Technical Constraints

**Current Scope:**
- Text-based PDFs only (no OCR for scanned documents)
- SQLite database (resets on cloud platform redeploys)
- No user authentication system
- Two AI providers (Anthropic, OpenAI)

**Design Choices:**
- Session-only API key storage
- Independent evaluation runs (no incremental updates)
- Strict 100% weight requirement for criteria
- Fixed 0-10 scoring scale

---

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| streamlit | 1.39.0 | Web framework |
| PyMuPDF | 1.24.13 | PDF processing |
| pandas | 2.2.3 | Data handling |
| pydantic | 2.10.3 | Data validation |
| python-dotenv | 1.0.1 | Environment variables |
| openai | 1.57.4 | OpenAI API client |
| anthropic | 0.40.0 | Anthropic API client |
| requests | 2.32.3 | HTTP requests |
| pytest | 8.3.4 | Testing framework |

---

## License

MIT License

---

## Credits

Developed for IIT Roorkee Agentic AI Programme

Built with Streamlit, PyMuPDF, and Claude/GPT APIs
