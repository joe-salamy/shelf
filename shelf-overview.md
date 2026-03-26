# Shelf — Turn Any Textbook into an Agent's Bookshelf

A command-line tool that converts PDF and EPUB textbooks into nested, grep-friendly markdown knowledge bases — built for the age of coding agents.

---

## The Friction We're Removing

Agents are remarkably good at navigating codebases. They glob for files, grep for symbols, read targeted sections, and build a mental model incrementally. That workflow is fast, cheap, and accurate.

Now try giving an agent a textbook.

The options are bleak. You can paste chapters into the context window and burn tokens on boilerplate front matter. You can stand up a vector database, embed everything, and hope retrieval surfaces the right chunk at query time — a setup that takes an afternoon and introduces a new failure mode (wrong chunks, stale embeddings, silent degradation). Or you can point the agent at a raw PDF and watch it fail silently because PDF text extraction is, charitably, a disaster of two-column layouts, ligatures, and invisible hyphenation.

This is the RAG tax: the cost in infrastructure, latency, and cognitive overhead that every developer pays just to let an agent read a book. For exploratory use — a student building a study tool, a developer who wants their agent to reference a technical manual, a lawyer giving Claude access to a statute — the tax is prohibitive.

The gap in the agentic ecosystem isn't a missing embedding model. It's the missing step between "I have a PDF" and "my agent can navigate it like a codebase."

---

## The Shelf Philosophy: Filesystem-First, Zero-RAG

Agents already know how to read files. The question is whether your files are worth reading.

Shelf's bet is simple: if you give an agent a well-structured directory of markdown files — one per chapter, one per section, with a smart index at the root — it doesn't need a retrieval layer. It can grep for concepts, glob for sections by title, read a chapter, and decide what to read next. That's the same loop it uses for code. No embeddings. No vector store. No API calls to a retrieval service that may or may not return the right passage.

This is a deliberate stance against what's become the default architecture for "AI + documents": the RAG industrial complex. RAG is appropriate for large, dynamic document collections where you can't know in advance what the agent will need. Textbooks aren't that. A textbook has a table of contents. It has chapters. It has a known structure. You can represent that structure directly on the filesystem, and when you do, the agent can navigate it without any retrieval machinery.

The Shelf philosophy has three rules:

1. **Filesystem is the index.** Directory structure mirrors the book's table of contents. The agent can discover what exists by listing files.
2. **Markdown is the format.** No custom formats, no database records. Everything is readable by any tool in the agent's toolkit.
3. **AI is opt-in.** The baseline pipeline requires no API keys, no models, no internet connection. AI enhancements — summaries, CLAUDE.md generation — are flags the user chooses to enable.

---

## The Core Loop: What Using Shelf Looks Like

### Step 1: Convert

```
$ shelf textbook.pdf
```

That's it. Shelf reads the PDF, extracts text using pymupdf4llm (which handles the edge cases that break naive extraction), detects the table of contents from markdown header structure, and writes a nested directory tree.

```
textbook/
├── INDEX.md
├── 01-introduction/
│   ├── README.md
│   └── 01-what-is-constitutional-law.md
├── 02-judicial-review/
│   ├── README.md
│   ├── 01-marbury-v-madison.md
│   ├── 02-scope-of-review.md
│   └── 03-standards-of-scrutiny.md
├── 03-the-commerce-clause/
│   ├── README.md
│   ├── 01-original-understanding.md
│   ├── 02-the-new-deal-shift.md
│   └── 03-modern-doctrine.md
...
```

The `INDEX.md` at the root is a navigable table of contents with relative links to every section file — something like:

```markdown
# Constitutional Law: A Textbook Index

## Part I: Foundations

- [Introduction](01-introduction/README.md)
  - [What Is Constitutional Law?](01-introduction/01-what-is-constitutional-law.md)

## Part II: Judicial Power

- [Judicial Review](02-judicial-review/README.md)
  - [Marbury v. Madison](02-judicial-review/01-marbury-v-madison.md)
  - [Scope of Review](02-judicial-review/02-scope-of-review.md)
  - [Standards of Scrutiny](02-judicial-review/03-standards-of-scrutiny.md)
    ...
```

### Step 2: The Agent Navigates

Once the shelf output exists, an agent navigates it the same way it navigates any codebase:

```
# Find all sections mentioning "rational basis"
$ grep -r "rational basis" textbook/ --include="*.md" -l

# Read the section on standards of scrutiny
$ cat textbook/02-judicial-review/03-standards-of-scrutiny.md

# List all chapters in Part III
$ ls textbook/03-the-commerce-clause/
```

In Claude Code, this looks like:

```
> What does this textbook say about the limits of the commerce clause
  after Lopez?

[Claude globs textbook/03-the-commerce-clause/, reads the relevant
sections, synthesizes an answer grounded in the actual text]
```

No retrieval pipeline. No context window stuffed with irrelevant chunks. The agent reads exactly what it needs, when it needs it.

### Step 3 (Optional): AI-Enhanced Index

```
$ shelf textbook.pdf --summarize
```

With `--summarize`, Shelf makes an additional pass using a language model (local or via API key) to generate:

- One-paragraph summaries for each chapter, prepended to the section file
- An enriched `INDEX.md` with those summaries inline

A `CLAUDE.md` is generated inside the output directory by default — no flag required. It reflects the actual book structure: section count, chapter names, and suggested search targets.

The `--summarize` flag is strictly opt-in. The baseline Shelf output — including the `CLAUDE.md` — is useful without it.

---

## Under the Hood: The Architecture

Shelf's pipeline has four layers, each independently replaceable.

### Convert Layer

**PDF → Markdown:** [pymupdf4llm](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) handles PDF extraction. It's chosen over alternatives because it preserves semantic structure (headings, lists, tables) rather than dumping a flat text stream. Two-column layouts, ligatures, and complex formatting are handled at this layer.

**EPUB → Markdown:** [markitdown](https://github.com/microsoft/markitdown) handles EPUB conversion. EPUBs are structurally cleaner than PDFs (they're already HTML under the hood), so this conversion is more reliable and produces better heading hierarchy.

The convert layer outputs a single large markdown string. Everything downstream is format-agnostic.

### Split Layer

The split layer walks the markdown output and detects section boundaries using header heuristics: `#`, `##`, `###` markers, with configurable depth. It maps each section to a filename (slugified header text, prefixed with an index for sort order) and a directory (determined by heading depth).

No AI required here. The structural information is already present in the markdown — it just needs to be materialized as a filesystem.

### Output Layer

The output layer writes the directory tree, creates `README.md` files for each chapter directory (containing the chapter's introductory content), and generates `INDEX.md` with the full linked table of contents.

Filename conventions are configurable: slug style (default), numbered, or title-cased. Output directory defaults to `<input-filename>/` in the current directory.

### Optional AI Layer

When `--summarize` is passed, Shelf runs a second pass with a configurable LLM backend:

- **Local (default):** Uses Ollama or llama.cpp if present — no API key required
- **Cloud:** Uses the Gemini API, OpenAI API, or any OpenAI-compatible endpoint via `SHELF_LLM_*` environment variables

The AI layer generates per-section summaries. A `CLAUDE.md` is always generated inside the book's output directory — containing navigation instructions specific to this book's structure, including section count, chapter names, and grep targets. It does not modify the core section content — summaries are prepended as a distinct block.

### Plugin Architecture

Convert backends and LLM backends are both pluggable. A `shelf.backends` entry point allows third parties to register new converters (e.g., a Marker-based high-fidelity PDF backend) without forking Shelf. The same pattern applies to LLM providers.

---

## Agent-Native by Design: The Claude Code Story

Shelf's first-class integration target is Claude Code — Anthropic's agentic coding CLI. The integration has two parts.

### Subdirectory CLAUDE.md

Shelf generates a `CLAUDE.md` _inside_ each book's output directory — not at the project root. Claude Code auto-loads subdirectory CLAUDE.md files on demand, when the agent reads files in that directory. That means the file is loaded only when relevant, and only for that book.

```markdown
# CLAUDE.md — Constitutional Law Textbook

This directory contains a shelf-structured version of "Constitutional Law"
by Kathleen Sullivan and Noah Feldman (19th ed.).

## Navigation

- Start with INDEX.md for the full table of contents with section links
- Chapter directories follow the pattern `NN-chapter-name/`
- Each section is a standalone markdown file: `NN-section-name.md`

## How to Find Things

- Grep for case names, doctrines, or key terms across all sections
- Use the INDEX.md summaries to identify relevant chapters before reading
- The `## Key Cases` block at the top of each section file is a reliable
  anchor for case-specific queries

## What's Here

- 42 sections across 8 chapters
- Coverage: judicial review, federalism, separation of powers,
  individual rights, equal protection
- Source: PDF converted via Shelf v0.1
```

This file lives at `constitutional-law/CLAUDE.md`. Ten textbooks means ten self-contained CLAUDE.md files — each loaded only when the agent enters that book's directory. No context bloat at the project level.

### Discovery

After conversion, Shelf prints a one-liner the user can paste into their root CLAUDE.md:

```
$ shelf constitutional-law.pdf

✓ Wrote 42 sections across 8 chapters → constitutional-law/
✓ Generated constitutional-law/CLAUDE.md

Add this to your root CLAUDE.md to make this book discoverable:

  Reference textbooks are in ./constitutional-law/
```

Non-invasive. Shelf doesn't touch your project's root CLAUDE.md — it just tells you what to add.

### An Agent Navigation Session

What this looks like in practice, inside Claude Code:

```
> What's the textbook's treatment of rational basis review?

[Glob: constitutional-law/*/**.md → 42 files found]
[Grep: "rational basis" → 8 matches in 4 files]
[Read: constitutional-law/02-judicial-review/03-standards-of-scrutiny.md]
[Read: constitutional-law/05-equal-protection/02-tiered-scrutiny.md]

The textbook distinguishes two flavors of rational basis...
```

Four tool calls. No retrieval service. Grounded in the actual text.

---

## What Makes Shelf Different

| Feature             | Shelf                        | Marker        | pdf-to-chapters    | RAG Pipelines        |
| ------------------- | ---------------------------- | ------------- | ------------------ | -------------------- |
| Output format       | Nested markdown dirs         | Flat markdown | Flat text/markdown | Vector DB / index    |
| TOC navigation      | Smart INDEX.md with links    | None          | None               | Semantic search only |
| Hierarchy preserved | Yes (dir structure)          | No            | Partial            | No                   |
| Zero-setup baseline | Yes                          | Yes           | Yes                | No                   |
| Agent-native output | Yes (subdirectory CLAUDE.md) | No            | No                 | Partial              |
| AI requirement      | None (opt-in)                | None          | None               | Required             |
| EPUB support        | Yes                          | No            | No                 | Via preprocessing    |
| Pluggable backends  | Yes                          | N/A           | N/A                | Varies               |

The key differentiator is the combination: markdown-native chapter files + smart TOC with file links + nested hierarchy that mirrors the book's structure + zero-setup baseline. Each of those exists somewhere in the ecosystem. None of them exist together, designed for agentic navigation.

---

## The Roadmap

### v1 — The Baseline That Works

- PDF + EPUB input
- pymupdf4llm and markitdown convert backends
- Heuristic header detection and split
- Nested directory output with smart `INDEX.md`
- `--summarize` flag for optional AI pass
- Subdirectory `CLAUDE.md` generated by default for every conversion
- Importable Python library (`from shelf import convert`)
- Click-based CLI

### v1.1 — Better Fidelity, More Agents

- Marker backend plugin for high-fidelity PDF extraction (better on academic papers, complex layouts)
- Cursor integration (`.cursorrules` generation)
- Aider integration (repo-map-compatible output)
- Configurable split depth and filename conventions
- Progress output and `--verbose` mode

### v2 — The Ecosystem Play

- Community textbook vaults: curated pre-converted shelves for common textbooks, hosted and versioned
- MCP server mode: expose a shelf output as a Model Context Protocol server for frameworks that speak MCP natively
- Hybrid semantic search layer: optional, additive — a lightweight local index layered on top of the filesystem, not replacing it
- Watch mode: auto-reprocess on source file change (useful during authoring workflows)

---

## Built With

| Component       | Library                                                              | Why                                                           |
| --------------- | -------------------------------------------------------------------- | ------------------------------------------------------------- |
| CLI             | [Click](https://click.palletsprojects.com/)                          | Clean API, automatic help generation, composable commands     |
| PDF extraction  | [pymupdf4llm](https://pymupdf.readthedocs.io/en/latest/pymupdf4llm/) | Preserves semantic structure; purpose-built for LLM pipelines |
| EPUB conversion | [markitdown](https://github.com/microsoft/markitdown)                | Handles EPUB and a broad range of document formats            |
| Optional LLM    | Gemini API / Ollama                                                  | Cloud or local; local preferred for zero-cost baseline        |
| Language        | Python 3.11+                                                         | Ecosystem fit; the tooling all lives here                     |

Shelf has no runtime dependencies beyond its convert backends. The core pipeline — convert, split, write — is pure Python. The optional AI layer is imported only when the relevant flags are passed.

---

_Shelf is in active development. The v1 milestone targets PDF and EPUB conversion with heuristic TOC detection and Claude Code integration._
