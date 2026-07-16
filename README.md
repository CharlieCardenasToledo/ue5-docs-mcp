# UE5 Docs — Offline Documentation & LLM Context for Unreal Engine 5.7

[![Deploy MkDocs](https://github.com/CharlieCardenasToledo/ue5-docs-mcp/actions/workflows/deploy.yml/badge.svg)](https://github.com/CharlieCardenasToledo/ue5-docs-mcp/actions/workflows/deploy.yml)
[![Docs Version](https://img.shields.io/badge/Unreal%20Engine-5.7-blue)](https://dev.epicgames.com/documentation/en-us/unreal-engine)
[![Pages Scraped](https://img.shields.io/badge/pages-3%2C444%2F3%2C470-green)](docs-md-py/en-us/unreal-engine)
[![License](https://img.shields.io/badge/license-MIT-orange)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-yellow)](https://python.org)

> **3,444 pages of Unreal Engine 5.7 official documentation in clean Markdown — purpose-built for LLMs, RAG pipelines, offline reading, and AI-assisted development.**

---

## Why this project?

Official Unreal Engine documentation lives behind a JavaScript-heavy web interface. This project downloads the entire documentation corpus and converts it to clean, structured Markdown — the native format preferred by LLMs and embedding models.

| Format | Use case |
|--------|----------|
| 3,444 individual `.md` files | RAG pipelines, AI code assistants, semantic search |
| `GUIDE_BOOK.md` (~30 MB) | Full-corpus context, local LLM input, `Ctrl+F` search |
| `GUIDE_INDEX.md` | Hierarchical overview, LLM navigation hints |
| MkDocs site | Interactive offline browser with full-text search |
| **MCP Server** | Direct integration with Claude Code and any MCP-compatible LLM |

---

## Quick Start

### Option 1 — MCP Server (for Claude Code users)

Install the MCP server so Claude can search and read UE5 docs in any session:

```bash
# 1. Clone the repository
git clone https://github.com/CharlieCardenasToledo/ue5-docs-mcp.git
cd ue5-docs-mcp

# 2. Install the MCP server package
pip install -e ".[mcp]"

# 3. Register it with Claude Code
claude mcp add --transport stdio ue5-docs -- python -m mcp_server.server --docs-dir ./docs-md-py
```

Then in any Claude Code session:

```
What is the Gameplay Ability System in Unreal Engine?
How do I implement replication for a custom Actor?
```

Claude will automatically query the MCP server for relevant documentation.

### Option 2 — Interactive Web Browser (MkDocs)

```bash
pip install -r requirements.txt
python scripts/build_guide.py --mode mkdocs --docs-dir docs-md-py
mkdocs serve
# Open http://127.0.0.1:8000
```

### Option 3 — RAG Pipeline Input

The `docs-md-py/en-us/unreal-engine/` directory contains 3,444 clean Markdown files ready to embed:

```python
from langchain_community.document_loaders import DirectoryLoader
from langchain_text_splitters import MarkdownHeaderTextSplitter

loader = DirectoryLoader("./docs-md-py", glob="**/*.md", show_progress=True)
docs = loader.load()

splitter = MarkdownHeaderTextSplitter(headers_to_split_on=[("#", "H1"), ("##", "H2")])
chunks = [chunk for doc in docs for chunk in splitter.split_text(doc.page_content)]
# Feed chunks into ChromaDB, Pinecone, FAISS, etc.
```

### Option 4 — Offline Index (No server)

```bash
python scripts/build_guide.py --mode index --docs-dir docs-md-py
# Opens GUIDE_INDEX.md in any Markdown viewer (VS Code, Obsidian, etc.)
```

---

## MCP Server Details

The included MCP server exposes three tools to any MCP-compatible LLM:

| Tool | Description |
|------|-------------|
| `search_docs` | Search docs by keyword, topic, or class name |
| `get_doc` | Read the full content of a specific page |
| `list_sections` | Browse top-level documentation categories |

**Installation options:**

```bash
# stdio transport (local)
claude mcp add --transport stdio ue5-docs -- python -m mcp_server.server

# With custom docs path
claude mcp add --transport stdio ue5-docs -- python -m mcp_server.server --docs-dir /path/to/docs-md-py

# Via pip (once published)
pip install ue5-docs-mcp
claude mcp add --transport stdio ue5-docs -- python -m ue5_docs_mcp
```

---

## Dual MCP Setup — Docs + Unreal Editor (UE 5.8+)

> Unreal Engine 5.8 ships with a built-in MCP server inside the editor. Combine it with this docs server for a complete AI-assisted workflow.

**With both servers active, Claude can:**

1. **Look up documentation** (this server) — *"What parameters does SpawnActorDeferred take?"*
2. **Control the Unreal Editor** (Epic's server) — *"Spawn a PointLight at (100, 0, 500) and set intensity to 5000"*

**Setup:**

1. Enable the `Unreal MCP` plugin in UE 5.8+
2. Run `ModelContextProtocol.GenerateClientConfig ClaudeCode` in the Output Log
3. Add our docs server to the generated `.mcp.json` — see [`.mcp.json.template`](.mcp.json.template)

Full setup guide in [`LLM_INTEGRATION.md`](LLM_INTEGRATION.md).

---

## LLM Integration Guide

See [`LLM_INTEGRATION.md`](LLM_INTEGRATION.md) for detailed strategies:

- **Cursor / GitHub Copilot / Cline** — Index the `docs-md-py` folder as a workspace
- **Google NotebookLM / Custom GPTs / Claude Projects** — Upload the ZIP of `docs-md-py`
- **RAG pipelines (LangChain, LlamaIndex)** — Embed individual `.md` files
- **Large context models (Gemini 1.5 Pro, Claude)** — Feed `GUIDE_INDEX.md` first, then specific pages

---

## Versioning

Each Unreal Engine release is frozen as a **git tag**. `main` always contains the latest version.

| Tag | UE Version | Status |
|-----|-----------|--------|
| `v5.7` | Unreal Engine 5.7 | Current (3,444 pages) |
| `v5.8` | Unreal Engine 5.8 | Planned |

```bash
# Use UE 5.7 docs (frozen)
git checkout v5.7

# Use latest docs
git checkout main
```

---

## Updating or Scraping a New Version

```bash
# Scrape UE 5.8 (when released)
python scripts/scrape_epic_docs.py --out-dir docs-md-py --workers 4 --application-version 5.8

# Resume an interrupted download
python scripts/scrape_epic_docs.py --out-dir docs-md-py --workers 4 --skip-existing

# Force re-download all pages
python scripts/scrape_epic_docs.py --out-dir docs-md-py --force
```

**Scraper features:**
- Multi-threaded (configurable workers)
- Resumable — skips already-downloaded pages
- Exponential backoff on failures
- Generates `INDEX.md`, `FAILURES.md`, and `pending-routes.json` on completion

---

## Repository Structure

```
ue5-docs-mcp/
├── docs-md-py/
│   └── en-us/unreal-engine/     ← 3,444 Markdown files (the corpus)
│       ├── INDEX.md              ← Hierarchical page index
│       ├── FAILURES.md           ← 26 pages that returned 404
│       └── mkdocs.yml            ← Auto-generated MkDocs config
├── mcp_server/
│   ├── __init__.py
│   └── server.py                 ← MCP server (search + retrieval)
├── scripts/
│   ├── scrape_epic_docs.py       ← Web scraper (HTML → Markdown)
│   └── build_guide.py            ← Compiler (index / book / mkdocs)
├── .github/workflows/deploy.yml  ← CI/CD → GitHub Pages
├── GUIDE_BOOK.md                 ← Full corpus as single file (~30 MB)
├── GUIDE_INDEX.md                ← Hierarchical index
├── LLM_INTEGRATION.md            ← Detailed LLM usage guide
├── llms.txt                      ← LLM discovery metadata
├── pyproject.toml                ← Package config for MCP server
├── requirements.txt              ← Python dependencies
└── README.md
```

---

## Documentation Coverage

| Metric | Value |
|--------|-------|
| UE version | 5.7 |
| Pages downloaded | 3,444 |
| Failed pages (404) | 26 (deprecated tools/removed sections) |
| Success rate | 99.25% |
| Corpus size | ~40 MB (individual files) |
| GUIDE_BOOK.md | ~30 MB |

The 26 failed pages are all confirmed deprecated or removed sections from Epic's servers (e.g., `vertex-sculpt-tool`, `dynamic-sculpt-tool`, `variant-manager-template-overview`).

---

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for guidelines. In short:

- Open an issue before implementing a large change
- Keep PRs focused and small
- Run `pip install -r requirements.txt` before working on scripts

---

## Legal Notice

The documentation content in `docs-md-py/` is the intellectual property of **Epic Games, Inc.** and is subject to Epic Games' terms of use and copyright. This repository provides open-source tooling (scraper, builder, MCP server) for offline access and personal/educational use only. It does not distribute commercial content or claim authorship of the original documentation.

---

## License

The **scripts and tooling** in this repository (everything except the content in `docs-md-py/`) are licensed under the [MIT License](LICENSE).

The **documentation content** in `docs-md-py/` remains the property of Epic Games, Inc.
