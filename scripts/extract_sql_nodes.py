#!/usr/bin/env python3
"""
extract_sql_nodes.py
====================
Scans Python (.py) and SQL (.sql) files in the repository, extracts every
SQL query found, and injects them as ``sql_query`` nodes into an existing
``graph.json`` produced by Graphify.

Usage (from repo root):
    python scripts/extract_sql_nodes.py [--root <repo_root>] [--graph <path_to_graph.json>]

Defaults:
    --root  .                          (current directory)
    --graph graphify-out/graph.json    (matches CI upload path)
"""

import ast
import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Keywords that identify a string as an SQL statement
SQL_KEYWORDS = ("SELECT", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP",
                "ALTER", "WITH", "MERGE", "TRUNCATE", "CALL", "EXECUTE")

# Regex that matches "-- Query N:" style separator comments in .sql files
SQL_SEPARATOR_RE = re.compile(r"^\s*--\s*Query\s+\d+", re.IGNORECASE)

# Directories to skip entirely
SKIP_DIRS = {".git", ".github", "__pycache__", "graphify-out", ".venv", "venv",
             "node_modules", ".mypy_cache", ".pytest_cache"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_sql(text: str) -> bool:
    """Return True if *text* looks like a SQL statement."""
    stripped = text.strip()
    upper = stripped.upper()
    return any(upper.startswith(kw) for kw in SQL_KEYWORDS)


def slugify(path: str) -> str:
    """Convert a relative file path to a safe identifier prefix."""
    # Remove extension, replace separators and dots with underscores
    stem = re.sub(r"[^\w]", "_", os.path.splitext(path)[0])
    stem = re.sub(r"_+", "_", stem).strip("_")
    return stem.lower()


def make_id(file_slug: str, index: int) -> str:
    return f"{file_slug}_query_{index}"


# ---------------------------------------------------------------------------
# Python file extraction (AST-based)
# ---------------------------------------------------------------------------

def extract_from_python(filepath: Path, rel_path: str) -> list[dict]:
    """
    Walk the AST of a Python file and collect every string-literal
    assignment whose value matches an SQL pattern.

    Handles:
      - ``query = "SELECT ..."``         (single-line string)
      - ``query = \"\"\"SELECT ...\"\"\"``  (triple-quoted string)
    """
    try:
        source = filepath.read_text(encoding="utf-8", errors="replace")
        tree = ast.parse(source, filename=str(filepath))
    except SyntaxError:
        print(f"  [WARN] Could not parse {rel_path} — skipping", file=sys.stderr)
        return []

    nodes = []
    slug = slugify(rel_path)
    counter = 1
    lines = source.splitlines()

    for node in ast.walk(tree):
        # Look for   <name> = <str_literal>   at any scope level
        if isinstance(node, ast.Assign):
            value = node.value
        elif isinstance(node, (ast.AnnAssign,)):
            value = node.value if node.value else None
        else:
            continue

        if not isinstance(value, ast.Constant) or not isinstance(value.value, str):
            continue

        sql_text = value.value
        if not is_sql(sql_text):
            continue

        # line_start: the line of the opening quote (ast gives us the constant node line)
        line_start = value.lineno
        line_end = value.end_lineno if value.end_lineno else line_start

        nodes.append({
            "id": make_id(slug, counter),
            "type": "sql_query",
            "file": rel_path,
            "line_start": line_start,
            "line_end": line_end,
            "extracted_sql": sql_text.strip(),
        })
        counter += 1

    return nodes


# ---------------------------------------------------------------------------
# SQL file extraction (line-based)
# ---------------------------------------------------------------------------

def extract_from_sql(filepath: Path, rel_path: str) -> list[dict]:
    """
    Split a .sql file into logical query blocks and return one node per block.

    Splitting strategy (in priority order):
      1. Lines matching ``-- Query N:`` style headers are used as boundaries.
      2. If no such headers exist, split on statement-ending semicolons (``; ``
         on its own line or at end of a non-comment, non-blank line).
      3. If neither delimiter found, treat the whole file as one query.
    """
    try:
        content = filepath.read_text(encoding="utf-8", errors="replace")
    except OSError:
        print(f"  [WARN] Could not read {rel_path} — skipping", file=sys.stderr)
        return []

    raw_lines = content.splitlines()
    if not raw_lines:
        return []

    slug = slugify(rel_path)
    blocks: list[tuple[int, int, str]] = []  # (line_start, line_end, text)

    # --- Strategy 1: "-- Query N:" separator comments ---
    separator_indices = [
        i for i, ln in enumerate(raw_lines) if SQL_SEPARATOR_RE.match(ln)
    ]

    if separator_indices:
        for idx, start in enumerate(separator_indices):
            end = separator_indices[idx + 1] - 1 if idx + 1 < len(separator_indices) else len(raw_lines) - 1
            block_text = "\n".join(raw_lines[start:end + 1]).strip()
            if is_sql(block_text) or any(is_sql(ln) for ln in raw_lines[start:end + 1]):
                blocks.append((start + 1, end + 1, block_text))  # 1-indexed
    else:
        # --- Strategy 2: semicolon-based splitting ---
        block_lines: list[str] = []
        block_start = 1  # 1-indexed
        found_semi = False

        for i, line in enumerate(raw_lines, start=1):
            block_lines.append(line)
            stripped = line.strip()
            if stripped.endswith(";") and not stripped.startswith("--"):
                text = "\n".join(block_lines).strip()
                # Trim leading comment lines to check for SQL content
                non_comment = "\n".join(
                    l for l in block_lines if not l.strip().startswith("--")
                ).strip()
                if is_sql(non_comment):
                    blocks.append((block_start, i, text))
                block_start = i + 1
                block_lines = []
                found_semi = True

        # Collect any trailing content after the last semicolon
        if block_lines:
            text = "\n".join(block_lines).strip()
            non_comment = "\n".join(
                l for l in block_lines if not l.strip().startswith("--")
            ).strip()
            if text and is_sql(non_comment):
                blocks.append((block_start, len(raw_lines), text))

        if not found_semi and not blocks:
            # --- Strategy 3: whole file as one query ---
            non_comment = "\n".join(
                l for l in raw_lines if not l.strip().startswith("--")
            ).strip()
            if is_sql(non_comment):
                blocks.append((1, len(raw_lines), content.strip()))

    nodes = []
    for counter, (line_start, line_end, text) in enumerate(blocks, start=1):
        nodes.append({
            "id": make_id(slug, counter),
            "type": "sql_query",
            "file": rel_path,
            "line_start": line_start,
            "line_end": line_end,
            "extracted_sql": text,
        })

    return nodes


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def collect_files(root: Path) -> tuple[list[Path], list[Path]]:
    """Return (python_files, sql_files) under *root*, skipping SKIP_DIRS."""
    py_files: list[Path] = []
    sql_files: list[Path] = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Prune skipped directories in-place so os.walk won't descend into them
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for fname in filenames:
            fpath = Path(dirpath) / fname
            if fname.endswith(".py"):
                py_files.append(fpath)
            elif fname.endswith(".sql"):
                sql_files.append(fpath)

    return sorted(py_files), sorted(sql_files)


# ---------------------------------------------------------------------------
# Graph merging
# ---------------------------------------------------------------------------

def load_graph(graph_path: Path) -> dict:
    """Load an existing graph.json, or return an empty graph skeleton."""
    if graph_path.exists():
        try:
            with graph_path.open(encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as exc:
            print(f"  [WARN] Could not read {graph_path}: {exc} — starting fresh",
                  file=sys.stderr)
    return {"nodes": [], "edges": [], "hyperedges": []}


def inject_sql_nodes(graph: dict, new_nodes: list[dict]) -> dict:
    """
    Merge *new_nodes* into *graph*, deduplicating by ``id``.
    Existing ``sql_query`` nodes are removed first so re-runs are idempotent.
    """
    existing = [n for n in graph.get("nodes", []) if n.get("type") != "sql_query"]
    graph["nodes"] = existing + new_nodes
    return graph


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract SQL queries from .py and .sql files and inject "
                    "them as sql_query nodes into a Graphify graph.json."
    )
    parser.add_argument(
        "--root", default=".", metavar="DIR",
        help="Repository root to scan (default: current directory)",
    )
    parser.add_argument(
        "--graph", default="graphify-out/graph.json", metavar="FILE",
        help="Path to the graph.json to update (default: graphify-out/graph.json)",
    )
    args = parser.parse_args()

    root = Path(args.root).resolve()
    graph_path = Path(args.graph)
    if not graph_path.is_absolute():
        graph_path = root / graph_path

    print(f"Scanning repository root : {root}")
    print(f"Target graph.json        : {graph_path}")

    py_files, sql_files = collect_files(root)
    print(f"\nDiscovered {len(py_files)} Python file(s) and {len(sql_files)} SQL file(s)")

    all_nodes: list[dict] = []

    print("\n── Python files ──────────────────────────────────────────────────────")
    for fpath in py_files:
        rel = str(fpath.relative_to(root))
        nodes = extract_from_python(fpath, rel)
        if nodes:
            for n in nodes:
                print(f"  ✓  {n['id']}  (lines {n['line_start']}–{n['line_end']})")
            all_nodes.extend(nodes)
        else:
            print(f"  –  {rel}  (no SQL found)")

    print("\n── SQL files ─────────────────────────────────────────────────────────")
    for fpath in sql_files:
        rel = str(fpath.relative_to(root))
        nodes = extract_from_sql(fpath, rel)
        if nodes:
            for n in nodes:
                print(f"  ✓  {n['id']}  (lines {n['line_start']}–{n['line_end']})")
            all_nodes.extend(nodes)
        else:
            print(f"  –  {rel}  (no SQL found)")

    print(f"\nTotal sql_query nodes extracted: {len(all_nodes)}")

    # Ensure output directory exists
    graph_path.parent.mkdir(parents=True, exist_ok=True)

    graph = load_graph(graph_path)
    graph = inject_sql_nodes(graph, all_nodes)

    with graph_path.open("w", encoding="utf-8") as f:
        json.dump(graph, f, indent=2)

    print(f"\n✅  graph.json updated → {graph_path}")
    print(f"   Total nodes now: {len(graph['nodes'])} "
          f"({len(all_nodes)} sql_query + "
          f"{len(graph['nodes']) - len(all_nodes)} other)")


if __name__ == "__main__":
    main()
