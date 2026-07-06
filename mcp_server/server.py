#!/usr/bin/env python3
"""
MCP server that exposes Unreal Engine 5.7 documentation to LLMs.

Tools:
  search_docs   — search by keyword or topic
  get_doc       — retrieve a specific page by slug
  list_sections — browse top-level categories

Usage:
  python -m mcp_server.server
  python -m mcp_server.server --docs-dir /path/to/docs-md-py
"""

import argparse
import re
import sys
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    sys.exit(
        "The 'mcp' package is required.\n"
        "Install it with:  pip install -e '.[mcp]'  or  pip install mcp"
    )

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_DOCS_DIR = Path(__file__).parent.parent / "docs-md-py"
_DOCS_DIR: Path = DEFAULT_DOCS_DIR


def _ue_dir() -> Path:
    return _DOCS_DIR / "en-us" / "unreal-engine"


def _index_file() -> Path:
    return _DOCS_DIR / "INDEX.md"


# ---------------------------------------------------------------------------
# Index parsing
# ---------------------------------------------------------------------------

_index_cache: list[tuple[str, str]] | None = None  # [(title, slug), ...]


def _load_index() -> list[tuple[str, str]]:
    """Parse INDEX.md and return (title, slug) pairs."""
    global _index_cache
    if _index_cache is not None:
        return _index_cache

    index_path = _index_file()
    if not index_path.exists():
        _index_cache = []
        return _index_cache

    entries: list[tuple[str, str]] = []
    link_re = re.compile(r"\[([^\]]+)\]\(([^)]+\.md)\)")

    for line in index_path.read_text(encoding="utf-8").splitlines():
        for title, path in link_re.findall(line):
            slug = Path(path).stem
            entries.append((title, slug))

    _index_cache = entries
    return _index_cache


# ---------------------------------------------------------------------------
# File lookup
# ---------------------------------------------------------------------------

def _find_doc(slug: str) -> Path | None:
    ue = _ue_dir()
    if not ue.exists():
        return None

    # Exact match
    exact = ue / f"{slug}.md"
    if exact.exists():
        return exact

    # Case-insensitive exact match
    slug_lower = slug.lower()
    for candidate in ue.glob("*.md"):
        if candidate.stem.lower() == slug_lower:
            return candidate

    # Partial match (slug is a suffix or substring)
    matches = [f for f in ue.glob(f"*{slug}*.md")]
    if matches:
        return matches[0]

    return None


# ---------------------------------------------------------------------------
# MCP server
# ---------------------------------------------------------------------------

mcp = FastMCP(
    "ue5-docs",
    instructions=(
        "Use search_docs to find relevant Unreal Engine documentation pages, "
        "then use get_doc to read the full content of a specific page. "
        "Use list_sections to browse the available top-level categories."
    ),
)


@mcp.tool()
def search_docs(query: str, max_results: int = 10) -> str:
    """
    Search Unreal Engine 5.7 documentation by topic, keyword, or class name.

    Returns a list of matching page titles and their slugs.
    Use the returned slug with get_doc() to read the full content.

    Args:
        query: Search term — topic, class name, feature, Blueprint node, etc.
               Examples: "Gameplay Ability System", "replication", "Niagara", "UCharacterMovementComponent"
        max_results: Maximum pages to return (default 10, max 20).
    """
    max_results = min(max(1, max_results), 20)
    query_lower = query.lower()

    index = _load_index()
    if not index:
        return (
            "Index file not found. "
            "Make sure docs-md-py/INDEX.md exists or regenerate it with:\n"
            "  python scripts/scrape_epic_docs.py --out-dir docs-md-py"
        )

    # Score: title match scores higher than slug match
    scored: list[tuple[int, str, str]] = []
    for title, slug in index:
        title_lower = title.lower()
        slug_lower = slug.lower()
        if query_lower in title_lower:
            score = 2 if title_lower.startswith(query_lower) else 1
            scored.append((score, title, slug))
        elif query_lower in slug_lower:
            scored.append((0, title, slug))

    scored.sort(key=lambda x: -x[0])
    results = scored[:max_results]

    if not results:
        # Fuzzy fallback: match individual words
        words = query_lower.split()
        for title, slug in index:
            combined = (title + " " + slug).lower()
            if all(w in combined for w in words):
                results.append((0, title, slug))
                if len(results) >= max_results:
                    break

    if not results:
        return (
            f'No results for "{query}".\n'
            "Tips:\n"
            "- Try shorter terms: 'replication' instead of 'how to replicate actors'\n"
            "- Use class names: 'UGameplayAbility', 'ACharacter', 'UUserWidget'\n"
            "- Use list_sections() to browse categories"
        )

    lines = [f"Search results for: **{query}** ({len(results)} found)\n"]
    for _, title, slug in results:
        lines.append(f"- {title}  →  slug: `{slug}`")

    lines.append("\nUse get_doc(slug) to read the full content of any page.")
    return "\n".join(lines)


@mcp.tool()
def get_doc(slug: str, max_chars: int = 8000) -> str:
    """
    Retrieve the full content of a specific Unreal Engine documentation page.

    Args:
        slug: The page identifier from search_docs results.
              Examples: "gameplay-ability-system-overview", "actor-communication-in-unreal-engine"
        max_chars: Truncate output at this many characters (default 8000).
                   Increase to 20000 for long pages like API references.
    """
    slug = slug.strip().strip("/")
    if not slug:
        return "Please provide a document slug (from search_docs results)."

    doc_path = _find_doc(slug)

    if doc_path is None:
        ue = _ue_dir()
        if not ue.exists():
            return (
                f"Documentation directory not found: {ue}\n"
                "Clone the repository and run the scraper, or set --docs-dir correctly."
            )
        return (
            f'Page not found: "{slug}"\n'
            "Use search_docs() to find the correct slug."
        )

    content = doc_path.read_text(encoding="utf-8")

    if len(content) > max_chars:
        truncated = len(content) - max_chars
        content = (
            content[:max_chars]
            + f"\n\n[… {truncated:,} characters truncated. "
            f"Call get_doc with max_chars={max_chars + 8000} to read more.]"
        )

    return content


@mcp.tool()
def list_sections() -> str:
    """
    List the top-level documentation sections available in the UE5 corpus.

    Useful for exploring the documentation structure before searching.
    """
    index = _load_index()
    if not index:
        return "Index not found. Run the scraper to generate docs-md-py/INDEX.md."

    # Group by first path segment (derived from slug prefix patterns)
    # Since files are flat, we group by common slug prefix words
    seen: list[str] = []
    section_hints = [
        "getting-started", "understanding", "unreal-editor", "blueprint",
        "programming", "gameplay", "input", "animation", "physics", "rendering",
        "materials", "lighting", "audio", "niagara", "networking", "ai",
        "ui", "umg", "world", "landscape", "foliage", "chaos", "packaging",
        "platform", "tools", "working-with", "designing-visuals",
    ]

    lines = ["## Unreal Engine 5.7 — Documentation Categories\n"]
    lines.append(f"Total pages: {len(index):,}\n")

    for hint in section_hints:
        matches = [(t, s) for t, s in index if hint in s.lower()]
        if matches:
            first_title = matches[0][0]
            lines.append(f"- **{first_title.split(' in Unreal')[0]}** ({len(matches)} pages, slug prefix: `{hint}`)")
            seen.append(hint)

    lines.append(
        "\nUse search_docs(query) to find pages within any category.\n"
        "Example: search_docs('Niagara') or search_docs('UGameplayAbility')"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="UE5 Docs MCP Server")
    parser.add_argument(
        "--docs-dir",
        type=Path,
        default=DEFAULT_DOCS_DIR,
        help="Path to docs-md-py directory (default: auto-detect from script location)",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    global _DOCS_DIR
    _DOCS_DIR = args.docs_dir.resolve()

    if not _DOCS_DIR.exists():
        print(f"Warning: docs directory not found: {_DOCS_DIR}", file=sys.stderr)
        print("The server will start but tools will return errors until docs are available.", file=sys.stderr)

    mcp.run()


if __name__ == "__main__":
    main()
