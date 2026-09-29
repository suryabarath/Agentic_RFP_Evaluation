# Agentic RFP Evaluation and Supplier Ranking

An intelligent RFP (Request for Proposal) evaluation system that uses LLM-powered analysis to score and rank supplier proposals. Built as a classroom mini-project for IIT Roorkee.

## Features

- **PDF Proposal Processing**: Upload supplier proposals in PDF format
- **LLM-Powered Evaluation**: Automated scoring using OpenAI GPT models
- **Weighted Criteria Scoring**: Configurable evaluation criteria with customizable weights
- **Deterministic Ranking**: Consistent tie-breaking rules for fair rankings
- **Peer Performance Index (PPI)**: Composite quality score combining multiple factors
- **Gap Analysis**: Identifies strengths and weaknesses per supplier
- **Benchmarking**: Compares suppliers against best/worst/average performance
- **JSON Export**: Export results for external analysis
- **Mock Mode**: Test without API credits using simulated responses

## Architecture

```
+-------------------------------------------------------------+
|                      Streamlit Web UI                        |
|   (Upload PDFs, View Results, Export Reports)                |
+-------------------------------------------------------------+
                              |
+-------------------------------------------------------------+
|                      Orchestrator                            |
|   (Coordinates the full evaluation pipeline)                 |
+-------------------------------------------------------------+
                              |
     +------------------------+------------------------+
     |                        |                        |
+----v----+            +------v------+          +-----v-----+
|   PDF   |            |     LLM     |          |  Scoring  |
| Extract |  --------> |  Evaluator  | -------> |  Engine   |
+---------+            +-------------+          +-----------+
                                                      |
     +------------------+------------------+----------+--------+
     |                  |                  |                   |
+----v----+      +------v------+    +------v------+    +------v------+
|Benchmark|      |     Gap     |    |  Relative   |    |     PPI     |
| Compute |      |  Analysis   |    | Performance |    |    Score    |
+---------+      +-------------+    +-------------+    +-------------+
                                                              |
                                                       +------v------+
                                                       |   Ranking   |
                                                       |   Engine    |
                                                       +-------------+
                                                              |
                                                       +------v------+
                                                       |   SQLite    |
                                                       |  Database   |
                                                       +-------------+
```

**Key Design Principle**: The LLM only evaluates proposals and provides justifications. All calculations (scores, rankings, benchmarks) are done deterministically in Python.

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/suryabarath/Agentic_RFP_Evaluation.git
   cd Agentic_RFP_Evaluation
   ```

2. **Create and activate virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the database**
   ```bash
   python database/init_db.py
   ```

5. **Configure environment** (optional - for live LLM mode)
   ```bash
   cp .env.example .env
   # Edit .env and add your OPENAI_API_KEY
   ```

## Usage

### Running the Application

```bash
streamlit run app.py
```

The application will open in your browser at `http://localhost:8501`.

### Mock Mode vs Live Mode

- **Mock Mode** (default): Uses simulated LLM responses for testing
  - Set `USE_MOCK_LLM=true` in `.env`
  - No API key required
  - Consistent, reproducible results

- **Live Mode**: Uses actual OpenAI API
  - Set `USE_MOCK_LLM=false` in `.env`
  - Requires valid `OPENAI_API_KEY`
  - Real AI-powered evaluations

### Uploading Proposals

1. Navigate to "New Evaluation" page
2. Enter supplier name
3. Upload PDF proposal
4. Click "Add Supplier" (repeat for multiple suppliers)
5. Click "Run Evaluation"

### Viewing Results

- **Leaderboard**: Overall rankings with scores
- **Scorecards**: Detailed per-supplier analysis
- **Export**: Download JSON reports

## Project Structure

```
Agentic_RFP_Evaluation/
|-- app.py                    # Streamlit web application
|-- requirements.txt          # Python dependencies
|-- .env.example              # Environment template
|-- database/
|   |-- init_db.py            # Database initialization
|   +-- rfp.db                # SQLite database (generated)
|-- src/
|   |-- database.py           # Database helper functions
|   |-- pdf_tool.py           # PDF text extraction
|   |-- schemas.py            # Pydantic data models
|   |-- evaluator.py          # LLM evaluation logic
|   |-- validator.py          # Response validation
|   |-- scorer.py             # Weighted score calculation
|   |-- benchmarks.py         # Benchmark computation
|   |-- gaps.py               # Gap analysis
|   |-- relative_performance.py   # Percentile rankings
|   |-- ppi.py                # Proposal Performance Index
|   |-- ranking.py            # Deterministic ranking
|   |-- orchestrator.py       # Pipeline coordinator
|   |-- export.py             # JSON export functions
|   +-- errors.py             # Custom exceptions
+-- test_data/
    |-- generate_test_pdfs.py     # Test PDF generator
    |-- run_e2e_test.py           # End-to-end test
    +-- *.pdf                     # Sample proposals
```

## Evaluation Criteria

Default criteria (configurable in database):

| Criterion | Weight | Description |
|-----------|--------|-------------|
| Technical Capability | 30% | Architecture, technology stack, scalability |
| Implementation Plan | 20% | Timeline, methodology, milestones |
| Commercial Value | 20% | Pricing, ROI, cost-effectiveness |
| Security & Compliance | 20% | Certifications, data protection, standards |
| Support & Experience | 10% | Track record, support offerings |

## Scoring Algorithm

### Weighted Score Calculation
```
weighted_score = SUM(raw_score / max_score * weight)
```

### PPI (Proposal Performance Index)
```
PPI = (weighted_score * 0.70) + (consistency * 0.15) + (quality * 0.15) - risk_penalty
```

### Tie-Breaking Rules (in order)
1. Total Weighted Score (higher wins)
2. PPI Score (higher wins)
3. Fewer Risks (lower wins)
4. Fewer Validation Warnings (lower wins)
5. Higher score on top-weight criterion
6. Alphabetical by name (deterministic fallback)

## Running Tests

### End-to-End Test
```bash
python test_data/run_e2e_test.py
```

### Generate Test PDFs
```bash
python test_data/generate_test_pdfs.py
```

## API Reference

### Orchestrator
```python
from src.orchestrator import Orchestrator, SupplierInput

orch = Orchestrator()
suppliers = [
    SupplierInput(name="Vendor A", pdf_file=file_a),
    SupplierInput(name="Vendor B", pdf_file=file_b),
]
result = orch.run(suppliers)
winner = result.get_winner()
```

### Export
```python
from src.export import export_full_report, to_json_string

report = export_full_report(pipeline_result)
json_data = to_json_string(report)
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | - | OpenAI API key for live mode |
| `USE_MOCK_LLM` | `true` | Enable mock mode (no API needed) |
| `OPENAI_MODEL` | `gpt-4` | Model to use in live mode |

## Contributing

This is a classroom project. Feel free to fork and extend!

## License

MIT License - See LICENSE file for details.

## Acknowledgments

- IIT Roorkee - Classroom mini-project
- OpenAI - GPT API
- Streamlit - Web framework
- PyMuPDF - PDF processing
