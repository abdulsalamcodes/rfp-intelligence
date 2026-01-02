# RFP Intelligence & Proposal Assistant

A production-grade, AI-driven system for analyzing RFP documents, extracting requirements, coordinating drafting, and ensuring compliance using **CrewAI**, **n8n**, and **Streamlit**.

## Features

- **Multi-Agent Analysis**: 5 specialized AI agents for comprehensive RFP processing
- **Multi-Provider LLM Support**: OpenAI, Anthropic, and Google Gemini
- **OCR Integration**: Tesseract OCR for scanned PDF documents
- **Workflow Orchestration**: n8n workflows for automated processing
- **Human-in-the-Loop**: Streamlit UI for review and editing

## Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Streamlit UI  │────▶│  FastAPI Server │────▶│  CrewAI Agents  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                               │
                               ▼
                        ┌─────────────────┐
                        │   n8n Webhooks  │
                        └─────────────────┘
```

## Quick Start

### Prerequisites

- Python 3.10-3.13
- Tesseract OCR (for scanned PDFs)
- n8n instance (optional, for workflow automation)

### Installation

```bash
# Clone and enter directory
cd rfp-intelligence

# Create virtual environment
python -m venv venv

# Activate (Windows)
.\venv\Scripts\activate

# Activate (Unix/macOS)
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

1. Copy `.env.example` to `.env`
2. Set your LLM provider and API key
3. Configure n8n webhook URL (if using)

```bash
cp .env.example .env
# Edit .env with your settings
```

### Running

**Start the API Server:**
```bash
uvicorn api.main:app --reload --port 8000
```

**Start the Streamlit App:**
```bash
cd streamlit_app
streamlit run app.py
```

## Project Structure

```
rfp-intelligence/
├── config/           # Configuration management
├── agents/           # CrewAI agent definitions
├── crew/             # Crew orchestration
├── api/              # FastAPI backend
├── services/         # Document processing, storage
├── schemas/          # Pydantic schemas
├── streamlit_app/    # Streamlit UI
├── n8n_workflows/    # n8n workflow JSON files
├── data/             # RFPs, outputs, exports
└── tests/            # Unit tests
```

## Agents

| Agent | Responsibility |
|-------|---------------|
| **RFP Analysis** | Parse documents, extract requirements |
| **Compliance** | Generate compliance matrix, flag risks |
| **Technical Drafting** | Draft proposal sections |
| **Experience Matching** | Match to past projects/personnel |
| **Risk Review** | Quality review, identify issues |

## LLM Providers

Configure in `.env`:

| Provider | Model Examples |
|----------|---------------|
| OpenAI | gpt-4o-mini, gpt-4o |
| Anthropic | claude-3-sonnet, claude-3-opus |
| Gemini | gemini-1.5-pro, gemini-1.5-flash |

## Known Limitations

- JSON file storage (no database)
- No built-in authentication
- OCR works best with clear, high-resolution scans
- Complex layouts may need manual review

## License

MIT
