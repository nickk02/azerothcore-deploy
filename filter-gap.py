#!/usr/bin/env python3
"""
Concatenates the 43 upstream db_world update files (2026-07-18 through
2026-07-24) and strips out any statement that targets `spell_script_names`
or `command` -- both bind to C++ handlers the playerbots fork's older
source tree does not have (verified: 15/16 referenced spell scripts and
all `command` handlers are absent from ~/playerbots-wotlk/src).

Everything else (creature_template, conditions, smart_scripts,
reference_loot_template, creature, waypoint_data, etc.) is pure content
and passes through unchanged.
"""
import re
import sys
from pathlib import Path

UPDATE_DIR = Path("/home/azerothcore/azerothcore-wotlk/data/sql/updates/db_world")
OUT_FILE = Path("/home/azerothcore/overnight2-sql/illidan-gap-filtered.sql")

DROP_TABLES = {"spell_script_names", "command"}

TARGET_RE = re.compile(
    r"^\s*(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM)\s+`?([a-zA-Z_]+)`?",
    re.IGNORECASE,
)

def split_statements(sql_text):
    """Split on semicolons that end a statement (i.e. at end of line),
    since multi-row INSERT ... VALUES (...), (...); blocks contain
    commas but the terminating ';' is always the last char before a
    newline in this codebase's SQL style."""
    # Normalize line endings, then split keeping it simple: statements
    # in these files always end with ";\n" or ";" at EOF.
    text = sql_text.replace("\r\n", "\n")
    parts = re.split(r";\s*\n", text)
    stmts = []
    for p in parts:
        p = p.strip()
        if p:
            stmts.append(p + ";")
    return stmts

def main():
    files = sorted(
        f for f in UPDATE_DIR.glob("*.sql")
        if f.name > "2026_07_16_01.sql"
    )
    if len(files) != 43:
        print(f"WARNING: expected 43 files, found {len(files)}", file=sys.stderr)

    kept, dropped = [], []

    for f in files:
        text = f.read_text(encoding="utf-8", errors="replace")
        for stmt in split_statements(text):
            m = TARGET_RE.match(stmt)
            table = m.group(1).lower() if m else None
            if table in DROP_TABLES:
                dropped.append((f.name, table, stmt[:80]))
            else:
                kept.append(stmt)

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with OUT_FILE.open("w", encoding="utf-8") as out:
        out.write(f"-- Filtered union of {len(files)} upstream db_world files\n")
        out.write(f"-- ({files[0].name} .. {files[-1].name})\n")
        out.write(f"-- {len(dropped)} statements dropped (spell_script_names/command), {len(kept)} kept\n\n")
        for stmt in kept:
            out.write(stmt + "\n")

    print(f"files processed: {len(files)}")
    print(f"statements kept: {len(kept)}")
    print(f"statements dropped: {len(dropped)}")
    for fname, table, preview in dropped:
        print(f"  DROPPED [{table}] {fname}: {preview}")
    print(f"output: {OUT_FILE}")

if __name__ == "__main__":
    main()
