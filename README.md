# Research Studio

A web application for deep research and knowledge artifact generation. Define a topic, provide guiding questions, and generate a polished PowerPoint presentation or HTML research document — powered by Claude AI.

## Features

- **LLM-powered research**: Claude generates substantive, expert-level content for every topic
- **Guiding questions**: Ask specific questions and receive detailed, multi-paragraph answers — not just restatements
- **Two output formats**: PowerPoint slides (`.pptx`) or a structured HTML research document
- **Context file upload**: Enrich research with your own PDF, DOCX, TXT, or Markdown files
- **Notion-inspired UI**: Clean, minimal interface with a familiar aesthetic
- **Async generation**: Jobs run in the background with live status polling

## Setup

### 1. Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure your API key

Create a `.env` file in the project root:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Get a key at [console.anthropic.com](https://console.anthropic.com).

### 3. Run the app

```bash
uvicorn app:app --reload
```

Open [http://localhost:8000](http://localhost:8000).

## How It Works

1. **Enter a topic** and optional author name
2. **Add guiding questions** to direct the research (e.g. "What are the ethical implications?")
3. **Upload context files** (optional) — PDFs, Word docs, or plain text to enrich the output
4. **Choose an output format** — PowerPoint slides or an HTML research document
5. **Generate** — the app researches the topic, calls Claude, and builds the artifact

### Research pipeline

1. Fetches background context from Wikipedia and DuckDuckGo
2. Combines web context + uploaded files into a prompt for Claude
3. Claude generates a structured research brief:
   - **Guiding question responses** — thorough expert answers to each of your questions
   - Summary, talking points, learning objectives, prerequisites
   - Curriculum modules, case studies, lab exercises, misconceptions
4. The brief is rendered into a downloadable PowerPoint or HTML document

If no API key is set, the app falls back to template-based content generation.

## Output Formats

### PowerPoint Slides
- Notion-inspired aesthetic: clean white layouts, Calibri Light headings, accent blue dividers
- Opens with a **Research Findings** section — one slide per guiding question with the full answer
- Sections for core concepts, key insights, historical foundations, applications, case studies, ethics, pitfalls, labs, and discussion
- Speaker notes on every slide

### HTML Research Document
- Self-contained single file, no external dependencies
- **Research Findings** section renders each guiding question with a full prose response
- Summary displayed as proper paragraphs, module grid, callout blocks, and scored citations

## Supported File Types (Context Upload)

| Format | Extension |
|--------|-----------|
| PDF | `.pdf` |
| Word | `.docx` |
| Plain text | `.txt` |
| Markdown | `.md`, `.markdown` |

## Project Structure

```
app.py                  # FastAPI application
src/
  topic_research.py     # Web research pipeline + TopicResearchBrief dataclass
  llm_enrichment.py     # Anthropic Claude integration
  slide_deck_generator.py  # python-pptx deck builder
  document_generator.py    # Self-contained HTML generator
  course_parser.py      # Uploaded file ingestion
static/
  index.html            # Single-page UI
  style.css             # Notion-inspired design system
  app.js                # Frontend logic (polling, file upload, form handling)
output/                 # Generated artifacts (gitignored)
uploads/                # Uploaded context files (gitignored)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/generate` | Start a generation job |
| `GET` | `/api/status/{job_id}` | Poll job status |
| `GET` | `/api/download/{job_id}` | Download completed artifact |
| `GET` | `/` | Serve the web UI |
