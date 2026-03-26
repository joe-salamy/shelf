# Shelf

Convert PDF and EPUB textbooks into nested, grep-friendly markdown directories — optimized for AI agents.

**Core idea:** The filesystem _is_ the index. No RAG, no vector databases, no embeddings. Just a clean directory tree that any agent (or human) can navigate with glob, grep, and read.

## What it produces

```
constitutional-law/
├── INDEX.md                          # Linked table of contents
├── CLAUDE.md                         # Agent navigation guide
├── 01-introduction/
│   ├── README.md
│   ├── 01-what-is-constitutional-law.md
│   └── 02-structure-of-government.md
├── 02-judicial-review/
│   ├── README.md
│   ├── 01-marbury-v-madison.md
│   └── 02-standards-of-scrutiny.md
└── ...
```

## Setup

Requires Python 3.10+.

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install
pip install -e .

# Install dev dependencies (for running tests)
pip install -e ".[dev]"
```

## Usage

### CLI

```bash
# Convert a PDF
shelf textbook.pdf

# Convert an EPUB
shelf textbook.epub

# Custom output directory and heading depth
shelf textbook.pdf --output my-notes --depth 2

# With AI-generated summaries (requires Ollama or API key — see below)
shelf textbook.pdf --summarize
```

### Python API

```python
from shelf import shelf

output_dir = shelf("textbook.pdf", output_dir="output", depth=3, summarize=False)
```

### Run as a module

```bash
python -m shelf textbook.pdf
```

## Options

| Flag                | Default           | Description                          |
| ------------------- | ----------------- | ------------------------------------ |
| `--output`, `-o`    | textbook filename | Output directory                     |
| `--depth`           | `3`               | Heading levels to split (1–6)        |
| `--summarize`, `-s` | off               | Prepend AI summaries to each section |

## AI Summaries (optional)

The `--summarize` flag is opt-in and requires a local [Ollama](https://ollama.com) instance or an OpenAI-compatible API.

**Ollama (local, recommended):**

```bash
# Install Ollama, then pull a model
ollama pull llama3

# Shelf will use it automatically
shelf textbook.pdf --summarize
```

**OpenAI-compatible API:**

```bash
export SHELF_LLM_API_KEY="sk-..."
export SHELF_LLM_BASE_URL="https://api.openai.com/v1"
export SHELF_LLM_MODEL="gpt-4o-mini"

shelf textbook.pdf --summarize
```

## Running Tests

```bash
pytest
pytest --cov=shelf     # with coverage
```

## How it works

1. **Convert** — PDF or EPUB → single markdown string (`pymupdf4llm` for PDF, `markitdown` for EPUB)
2. **Split** — Parse ATX headers, build nested `Section` tree up to `--depth`
3. **Output** — Write numbered directories, section files, `INDEX.md`, and `CLAUDE.md`
4. **Summarize** _(optional)_ — Walk the tree, call LLM, prepend summaries

## Project layout

```
src/shelf/
├── cli.py          # Click CLI
├── models.py       # Section, BookTree data models
├── split.py        # Markdown → tree parser
├── output.py       # Tree → filesystem writer
├── slugify.py      # Text → filename
├── convert/        # PDF and EPUB backends
└── summarize/      # Ollama and OpenAI-compatible LLM backends
```
