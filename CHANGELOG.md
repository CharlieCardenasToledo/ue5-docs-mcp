# Changelog

All notable changes to this project are documented here.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).
Version tags map to Unreal Engine versions (e.g. `v5.7` = UE 5.7 docs).

---

## [Unreleased]

### Planned
- UE 5.8 documentation scrape (tag: `v5.8`)
- Dual MCP setup guide for UE 5.8 built-in MCP server

---

## [v5.7.0] — 2026-03-10

### Added
- Complete UE 5.7 documentation corpus (3,444 pages, 99.25% success rate)
- MCP server (`mcp_server/server.py`) for direct LLM integration
- `llms.txt` for LLM discovery
- `LLM_INTEGRATION.md` with 5 integration strategies including UE 5.8 dual-MCP setup
- `.mcp.json.template` for configuring both docs + Unreal Editor MCP servers
- `pyproject.toml` — installable as `pip install -e ".[mcp]"`
- `CONTRIBUTING.md`, `LICENSE` (MIT, tooling only)
- `.gitattributes` for consistent line endings

### Changed
- Rewrote `README.md` — developer-first, LLM-focused, English
- Improved `.gitignore` — excludes generated files and RTFM index

### Tooling
- `scrape_epic_docs.py` — multi-threaded scraper with resumable downloads
- `build_guide.py` — generates index, book, and MkDocs config
- GitHub Actions CI/CD for GitHub Pages deployment

---

## Versioning Policy

Each Unreal Engine version gets a **git tag** on the commit where that version's documentation was last updated.

| Tag | UE Version | Docs Date |
|-----|-----------|-----------|
| `v5.7` | Unreal Engine 5.7 | 2026-03-10 |
| `v5.8` | Unreal Engine 5.8 | TBD |

To access a specific version:

```bash
# UE 5.7 docs
git checkout v5.7

# Latest docs (main branch)
git checkout main
```

To scrape a new version yourself:

```bash
# UE 5.8 (when available)
python scripts/scrape_epic_docs.py \
  --out-dir docs-md-py \
  --application-version 5.8 \
  --workers 4
```
