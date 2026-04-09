# Shelf

Convert PDF and EPUB textbooks into nested, grep-friendly markdown directories — optimized for AI agents.

**Core idea:** The filesystem _is_ the index. No RAG, no vector databases, no embeddings. Just a clean directory tree that any agent (or human) can navigate with glob, grep, and read.

---

## Installation

Requires Python 3.10+. Install shelf once — you don't need to repeat this for each project.

**From the shelf repo directory:**

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install -e .
```

**Or from anywhere, passing the path to the repo:**

```bash
python -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
pip install /path/to/shelf
```

Once installed, activate this environment whenever you want to use the `shelf` command.

---

## Real-World Workflow

Here's what a typical session looks like using this with Claude Code:

**1. Convert your textbook from your notes/project directory:**

```bash
cd ~/law-school-notes          # wherever you keep your notes
shelf ~/Downloads/con-law.pdf  # creates con-law/ here
```

Shelf creates the output directory (`con-law/`) in your current working directory. **You don't move the textbook** — just pass its path.

**2. Tell Claude Code it exists** by adding one line to your project's `CLAUDE.md`:

```markdown
Reference textbooks are in ./con-law/
```

Shelf prints this suggested line after conversion. Shelf also generates its own `CLAUDE.md` inside `con-law/` that Claude Code loads automatically when it reads files in that directory.

**3. Ask Claude Code questions about the textbook:**

```
> What does the textbook say about rational basis review?

[Claude globs con-law/*/*.md, greps for "rational basis", reads the relevant sections]

The textbook distinguishes two flavors of rational basis...
```

No retrieval pipeline. No context window stuffed with irrelevant chunks.

---

## What it produces

```
constitutional-law/
├── INDEX.md                          # Linked table of contents
├── CLAUDE.md                         # Agent navigation guide (auto-generated)
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

The `INDEX.md` is a full linked table of contents. The `CLAUDE.md` describes the book's structure so Claude Code knows how to navigate it — it's loaded only when the agent reads files in that directory, so it doesn't clutter your project context.

---

## Usage

```bash
# Convert a PDF (output goes to ./textbook/ in your current directory)
shelf textbook.pdf

# Convert an EPUB
shelf textbook.epub

# Custom output directory and heading depth
shelf textbook.pdf --output my-notes --depth 2

# With AI-generated summaries (requires Ollama or API key — see below)
shelf textbook.pdf --summarize
```

## Options

| Flag                | Default           | Description                          |
| ------------------- | ----------------- | ------------------------------------ |
| `--output`, `-o`    | textbook filename | Output directory                     |
| `--depth`           | `3`               | Heading levels to split (1–6)        |
| `--summarize`, `-s` | off               | Prepend AI summaries to each section |

---

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

---

## How it works

1. **Convert** — PDF or EPUB → single markdown string (`pymupdf4llm` for PDF, `markitdown` for EPUB)
2. **Split** — Parse ATX headers, build nested `Section` tree up to `--depth`
3. **Output** — Write numbered directories, section files, `INDEX.md`, and `CLAUDE.md`
4. **Summarize** _(optional)_ — Walk the tree, call LLM, prepend summaries
