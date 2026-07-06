"""
build_guide.py — Genera un libro/guía ordenada a partir de los Markdown descargados.

Modos:
  index   — GUIDE_INDEX.md  con tabla de contenidos jerárquica numerada (1., 1.1., ...)
  book    — GUIDE_BOOK.md   con todo el contenido concatenado en orden correcto
  mkdocs  — mkdocs.yml      listo para servir con MkDocs Material

Uso rápido:
  python scripts/build_guide.py --mode index
  python scripts/build_guide.py --mode book --out GUIDE_BOOK.md
  python scripts/build_guide.py --mode mkdocs --out mkdocs.yml
"""

import argparse
import json
import re
import time
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional, Tuple

BASE_API_URL = "https://dev.epicgames.com/community/api/documentation"
BASE_DOC_URL = "https://dev.epicgames.com/documentation"

# ---------------------------------------------------------------------------
# ToC fetch / parse
# ---------------------------------------------------------------------------

def _make_scraper() -> Any:
    try:
        import cloudscraper  # type: ignore
    except ImportError:
        raise ImportError(
            "cloudscraper no está instalado. "
            "Instálalo con: pip install cloudscraper\n"
            "O proporciona un toc-tree.json con --toc-file para evitar esta dependencia."
        )
    return cloudscraper.create_scraper(
        browser={"browser": "chrome", "platform": "windows", "mobile": False}
    )


def fetch_toc(scraper: Any, start_path: str, app_version: str) -> Dict[str, Any]:
    params: Dict[str, str] = {"path": start_path}
    if app_version:
        params["application_version"] = app_version
    resp = scraper.get(f"{BASE_API_URL}/table_of_content.json", params=params, timeout=90)
    resp.raise_for_status()
    return resp.json()


def load_toc_from_file(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_entries_from_index(index_path: Path) -> Tuple[List[Dict[str, Any]], str]:
    """Parse docs-md-py/INDEX.md as a flat entry list when the API is unavailable.

    Returns (entries, app_version).
    """
    link_re = re.compile(r"\[([^\]]+)\]\(([^)]+\.md)\)")
    version_re = re.compile(r"Application version[:`\s]+([0-9.]+)", re.IGNORECASE)

    entries: List[Dict[str, Any]] = []
    app_version = ""

    for line in index_path.read_text(encoding="utf-8").splitlines():
        m = version_re.search(line)
        if m:
            app_version = m.group(1)
        for title, rel_path in link_re.findall(line):
            page_path = rel_path.replace("\\", "/").removesuffix(".md")
            slug = Path(rel_path).stem
            entries.append({
                "title": title,
                "slug": slug,
                "page_path": page_path,
                "sub_entries": [],
            })

    return entries, app_version


def safe_file_segment(seg: str) -> str:
    seg = seg.strip().lower()
    seg = re.sub(r"[^a-z0-9._-]+", "-", seg)
    seg = re.sub(r"-{2,}", "-", seg).strip("-")
    return seg or "untitled"


def entry_to_rel_path(entry: Dict[str, Any], locale: str, app_slug: str) -> str:
    """Convert a ToC entry to its expected relative .md path."""
    page_path = entry.get("page_path") or f"{locale}/{app_slug}/{entry.get('slug', '')}"
    parts = [p for p in page_path.strip("/").split("/") if p]
    if len(parts) >= 3:
        return (
            f"{safe_file_segment(parts[0])}/{safe_file_segment(parts[1])}/"
            f"{safe_file_segment(parts[-1])}.md"
        )
    slug = safe_file_segment(entry.get("slug") or "")
    return f"{safe_file_segment(locale)}/{safe_file_segment(app_slug)}/{slug}.md"


# ---------------------------------------------------------------------------
# Tree walker (DFS, yields (depth, section_number, entry))
# ---------------------------------------------------------------------------

def walk_toc(
    entries: List[Dict[str, Any]],
    prefix: Tuple[int, ...] = (),
) -> Generator[Tuple[int, str, Dict[str, Any]], None, None]:
    """
    DFS walk of the ToC tree.
    Yields (depth, section_number_str, entry).
    section_number_str examples: "1", "1.2", "3.4.5"
    """
    for i, entry in enumerate(entries or [], start=1):
        nums = prefix + (i,)
        section = ".".join(str(n) for n in nums)
        depth = len(nums)
        yield depth, section, entry
        sub = entry.get("sub_entries") or []
        if sub:
            yield from walk_toc(sub, prefix=nums)


# ---------------------------------------------------------------------------
# Mode: index
# ---------------------------------------------------------------------------

def build_index(
    entries: List[Dict[str, Any]],
    docs_dir: Path,
    locale: str,
    app_slug: str,
    app_version: str,
    start_path: str,
) -> str:
    lines: List[str] = [
        "# Unreal Engine — Guía Completa: Índice",
        "",
        f"> **Versión:** `{app_version}`  ",
        f"> **Start path:** `{start_path}`  ",
        f"> **Generado:** {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}",
        "",
        "---",
        "",
    ]

    current_h2: Optional[str] = None

    for depth, section, entry in walk_toc(entries):
        title = entry.get("title") or entry.get("slug") or "Untitled"
        rel_path = entry_to_rel_path(entry, locale, app_slug)
        local_file = docs_dir / rel_path
        # Link to local file if it exists, else to the remote URL
        if local_file.exists():
            link = rel_path.replace("\\", "/")
        else:
            page_path = entry.get("page_path") or f"{locale}/{app_slug}/{entry.get('slug', '')}"
            link = f"{BASE_DOC_URL}/{page_path}"
        exists_mark = "✓" if local_file.exists() else "✗"

        if depth == 1:
            # Top-level: render as H2 section
            lines.append("")
            lines.append(f"## {section}. {title}")
            lines.append("")
            current_h2 = section
        elif depth == 2:
            lines.append(f"- **{section}.** [{title}]({link}) {exists_mark}")
        else:
            # Deeper levels: indent proportionally
            indent = "  " * (depth - 2)
            lines.append(f"{indent}- {section}. [{title}]({link}) {exists_mark}")

    lines += [
        "",
        "---",
        "",
        "> ✓ = archivo local disponible  ✗ = solo enlace remoto",
        "",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Mode: book
# ---------------------------------------------------------------------------

def build_book(
    entries: List[Dict[str, Any]],
    docs_dir: Path,
    locale: str,
    app_slug: str,
    app_version: str,
    start_path: str,
    verbose: bool = False,
) -> Generator[str, None, None]:
    """Yields chunks of text to write to the book file (generator for memory efficiency)."""
    yield f"# Unreal Engine — Guía Completa\n\n"
    yield f"> **Versión:** `{app_version}`  \n"
    yield f"> **Start path:** `{start_path}`  \n"
    yield f"> **Generado:** {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}\n\n"
    yield "---\n\n"

    for depth, section, entry in walk_toc(entries):
        title = entry.get("title") or entry.get("slug") or "Untitled"
        rel_path = entry_to_rel_path(entry, locale, app_slug)
        local_file = docs_dir / rel_path

        # Chapter/section header
        md_level = min(depth + 1, 6)  # depth 1 → ##, depth 2 → ###, etc.
        yield f"\n{'#' * md_level} {section}. {title}\n\n"

        if local_file.exists():
            content = local_file.read_text(encoding="utf-8")
            # Strip the first H1 (already included as chapter header) and metadata lines
            lines = content.splitlines()
            body_lines: List[str] = []
            skip_header = True
            for line in lines:
                if skip_header:
                    # Skip the # Title line
                    if line.startswith("# "):
                        skip_header = False
                        continue
                # Skip blockquote metadata lines (Source: / Application Version:)
                if re.match(r"^> (Source:|Application Version:)", line):
                    continue
                body_lines.append(line)
            body = "\n".join(body_lines).strip()
            if body:
                yield body + "\n\n"
            else:
                yield "_[No content available]_\n\n"
        else:
            page_path = entry.get("page_path") or f"{locale}/{app_slug}/{entry.get('slug', '')}"
            source_url = f"{BASE_DOC_URL}/{page_path}"
            yield f"_[Archivo no descargado — ver online: [{source_url}]({source_url})]_\n\n"
            if verbose:
                print(f"  MISSING: {rel_path}")

        yield "---\n\n"


# ---------------------------------------------------------------------------
# Mode: mkdocs
# ---------------------------------------------------------------------------

def build_mkdocs_nav(
    entries: List[Dict[str, Any]],
    docs_dir: Path,
    locale: str,
    app_slug: str,
    site_name: str = "Unreal Engine Docs",
    app_version: str = "",
) -> str:
    """Generate a mkdocs.yml with the full navigation hierarchy."""

    def render_nav(nodes: List[Dict[str, Any]], indent: int = 2) -> List[str]:
        nav_lines: List[str] = []
        pad = " " * indent
        for entry in nodes or []:
            title = entry.get("title") or entry.get("slug") or "Untitled"
            rel_path = entry_to_rel_path(entry, locale, app_slug)
            local_file = docs_dir / rel_path
            sub = entry.get("sub_entries") or []

            # Escape single quotes in titles for YAML
            title_safe = title.replace("'", "''")

            if sub:
                nav_lines.append(f"{pad}- '{title_safe}':")
                nav_lines.extend(render_nav(sub, indent + 4))
            else:
                rel_posix = rel_path.replace("\\", "/")
                if local_file.exists():
                    nav_lines.append(f"{pad}- '{title_safe}': {rel_posix}")
                else:
                    nav_lines.append(f"{pad}- '{title_safe}': {rel_posix}  # NOT DOWNLOADED")
        return nav_lines

    version_comment = f"  # Unreal Engine {app_version}" if app_version else ""

    header = f"""site_name: '{site_name}'{version_comment}
docs_dir: '{docs_dir.name}'
theme:
  name: material
  palette:
    - scheme: default
      primary: deep purple
      accent: purple
  features:
    - navigation.tabs
    - navigation.sections
    - navigation.expand
    - navigation.top
    - search.highlight
    - content.code.annotate
plugins:
  - search
nav:
"""

    nav_lines = render_nav(entries)
    return header + "\n".join(nav_lines) + "\n"


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Genera un libro/guía ordenada a partir de los Markdown scrapeados.\n"
            "Modos: index (tabla de contenidos jerarquica), "
            "book (libro completo), mkdocs (mkdocs.yml)"
        )
    )
    parser.add_argument(
        "--mode",
        choices=["index", "book", "mkdocs"],
        default="index",
        help="Tipo de salida a generar (default: index)",
    )
    parser.add_argument(
        "--docs-dir",
        default="docs-md-py",
        help="Carpeta con los archivos .md descargados (default: docs-md-py)",
    )
    parser.add_argument(
        "--start-path",
        default="en-us/unreal-engine/understanding-the-basics-of-unreal-engine",
        help="Path del ToC en formato locale/application/slug",
    )
    parser.add_argument("--application-version", default="")
    parser.add_argument(
        "--toc-file",
        default="",
        help="Ruta a toc-tree.json guardado previamente (evita re-fetchear el ToC)",
    )
    parser.add_argument(
        "--out",
        default="",
        help=(
            "Archivo de salida. "
            "Default: GUIDE_INDEX.md, GUIDE_BOOK.md o mkdocs.yml según el modo."
        ),
    )
    parser.add_argument(
        "--site-name",
        default="Unreal Engine Docs",
        help="Nombre del sitio para mkdocs.yml (solo en modo mkdocs)",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        default=False,
        help="Mostrar archivos faltantes durante la generación del libro",
    )
    args = parser.parse_args()

    docs_dir = Path(args.docs_dir).resolve()
    if not docs_dir.exists():
        raise FileNotFoundError(f"docs-dir no existe: {docs_dir}")

    # Determine output path
    default_out = {
        "index": "GUIDE_INDEX.md",
        "book": "GUIDE_BOOK.md",
        "mkdocs": "mkdocs.yml",
    }
    out_path = Path(args.out).resolve() if args.out else (docs_dir.parent / default_out[args.mode]).resolve()

    # Load ToC
    toc_file = Path(args.toc_file).resolve() if args.toc_file else docs_dir / "toc-tree.json"
    if toc_file.exists():
        print(f"Cargando ToC desde {toc_file} ...")
        toc_data = load_toc_from_file(toc_file)
        app_version = args.application_version or toc_data.get("application_version") or ""
        start_path = args.start_path or toc_data.get("start_path") or args.start_path
        entries = toc_data.get("entries") or []
    else:
        index_fallback = docs_dir / "INDEX.md"
        try:
            print("toc-tree.json no encontrado. Fetcheando ToC desde la API ...")
            scraper = _make_scraper()
            toc = fetch_toc(scraper, args.start_path, args.application_version)
            app_version = args.application_version or (toc.get("all_versions") or [""])[0]
            start_path = args.start_path
            entries = toc.get("entries") or []
        except Exception as api_err:
            if not index_fallback.exists():
                raise RuntimeError(
                    f"API no disponible ({api_err}) y no se encontró {index_fallback}.\n"
                    "Proporciona --toc-file o asegúrate de que INDEX.md exista."
                ) from api_err
            print(f"API no disponible ({api_err}).")
            print(f"Usando {index_fallback} como fallback ...")
            entries, detected_version = load_entries_from_index(index_fallback)
            app_version = args.application_version or detected_version
            start_path = args.start_path

    start_parts = [p for p in start_path.strip("/").split("/") if p]
    if len(start_parts) < 2:
        raise ValueError("start-path debe tener al menos locale/application")
    locale, app_slug = start_parts[0], start_parts[1]

    # Count entries for reporting
    def count_entries(nodes: List[Dict[str, Any]]) -> int:
        total = 0
        for e in nodes or []:
            total += 1
            total += count_entries(e.get("sub_entries") or [])
        return total

    total_entries = count_entries(entries)
    print(f"Entradas en el ToC: {total_entries} | Modo: {args.mode} | Salida: {out_path}")

    # Generate
    if args.mode == "index":
        content = build_index(
            entries=entries,
            docs_dir=docs_dir,
            locale=locale,
            app_slug=app_slug,
            app_version=app_version,
            start_path=start_path,
        )
        out_path.write_text(content, encoding="utf-8")
        lines = content.count("\n")
        print(f"✓ Índice generado: {out_path} ({lines} líneas)")

    elif args.mode == "book":
        print("Generando libro completo (esto puede tardar unos segundos) ...")
        with out_path.open("w", encoding="utf-8") as f:
            for chunk in build_book(
                entries=entries,
                docs_dir=docs_dir,
                locale=locale,
                app_slug=app_slug,
                app_version=app_version,
                start_path=start_path,
                verbose=args.verbose,
            ):
                f.write(chunk)
        size_mb = out_path.stat().st_size / (1024 * 1024)
        print(f"✓ Libro generado: {out_path} ({size_mb:.1f} MB)")

    elif args.mode == "mkdocs":
        content = build_mkdocs_nav(
            entries=entries,
            docs_dir=docs_dir,
            locale=locale,
            app_slug=app_slug,
            site_name=args.site_name,
            app_version=app_version,
        )
        out_path.write_text(content, encoding="utf-8")
        lines = content.count("\n")
        print(f"✓ mkdocs.yml generado: {out_path} ({lines} líneas)")
        print("   Para servir: pip install mkdocs-material && mkdocs serve -f mkdocs.yml")


if __name__ == "__main__":
    main()
