#!/usr/bin/env python3
"""Validates the azerothcore-deploy repo's actual content: SQL idempotency,
docs ledger consistency, and Python syntax. Prints "[ FAILED ] <check>" for
each failure and exits non-zero if any check fails.
"""
import glob
import os
import py_compile
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
failures = []


def fail(check, detail):
    failures.append(check)
    print(f"[ FAILED ] {check}: {detail}")


def ok(check):
    print(f"[ OK ] {check}")


def check_sql_idempotency():
    """Every INSERT INTO <table> should have a preceding DELETE FROM <table>
    somewhere earlier in the same file, matching AzerothCore's own SQL
    convention (idempotent re-apply)."""
    sql_files = glob.glob(os.path.join(REPO_ROOT, "**", "*.sql"), recursive=True)
    if not sql_files:
        ok("SQL idempotency check (no .sql files found)")
        return

    insert_re = re.compile(r"INSERT\s+(?:IGNORE\s+)?INTO\s+`?([\w.]+)`?", re.IGNORECASE)
    delete_re = re.compile(r"DELETE\s+FROM\s+`?([\w.]+)`?", re.IGNORECASE)

    any_fail = False
    for path in sql_files:
        rel = os.path.relpath(path, REPO_ROOT)
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            lines = f.readlines()

        deleted_tables = set()
        for line in lines:
            for m in delete_re.finditer(line):
                deleted_tables.add(m.group(1).lower())
            for m in insert_re.finditer(line):
                table = m.group(1).lower()
                if table not in deleted_tables:
                    fail(
                        "SQL idempotency check",
                        f"{rel}: INSERT INTO {table} with no preceding DELETE FROM {table}",
                    )
                    any_fail = True
    if not any_fail:
        ok(f"SQL idempotency check ({len(sql_files)} files)")


def check_docs_ledger_consistency():
    """Every docs/prs, docs/issues, docs/modules file should be referenced in
    docs/README.md, and vice versa (no orphaned files, no dead links)."""
    readme_path = os.path.join(REPO_ROOT, "docs", "README.md")
    if not os.path.isfile(readme_path):
        fail("Docs ledger consistency", "docs/README.md does not exist")
        return

    with open(readme_path, "r", encoding="utf-8") as f:
        readme_text = f.read()

    referenced_links = set(re.findall(r"\(((?:prs|issues|modules|findings|incidents)/[\w.-]+\.md)\)", readme_text))

    any_fail = False
    for subdir in ("prs", "issues", "modules"):
        dir_path = os.path.join(REPO_ROOT, "docs", subdir)
        if not os.path.isdir(dir_path):
            continue
        for fname in os.listdir(dir_path):
            if not fname.endswith(".md"):
                continue
            rel_link = f"{subdir}/{fname}"
            if rel_link not in referenced_links:
                fail(
                    "Docs ledger consistency",
                    f"docs/{rel_link} exists but is not referenced in docs/README.md",
                )
                any_fail = True

    for link in referenced_links:
        full_path = os.path.join(REPO_ROOT, "docs", link)
        if not os.path.isfile(full_path):
            fail(
                "Docs ledger consistency",
                f"docs/README.md references {link} but the file does not exist",
            )
            any_fail = True

    if not any_fail:
        ok("Docs ledger consistency")


def check_no_placeholders():
    """No TBD/TODO/FIXME placeholders left in committed findings/incidents docs."""
    placeholder_re = re.compile(r"\b(TBD|TODO|FIXME)\b")
    any_fail = False
    for subdir in ("findings", "incidents"):
        dir_path = os.path.join(REPO_ROOT, "docs", subdir)
        if not os.path.isdir(dir_path):
            continue
        for fname in os.listdir(dir_path):
            if not fname.endswith(".md"):
                continue
            full_path = os.path.join(dir_path, fname)
            with open(full_path, "r", encoding="utf-8") as f:
                for lineno, line in enumerate(f, start=1):
                    m = placeholder_re.search(line)
                    if m:
                        fail(
                            "No-placeholders check",
                            f"docs/{subdir}/{fname}:{lineno} contains '{m.group(1)}'",
                        )
                        any_fail = True
    if not any_fail:
        ok("No-placeholders check")


def check_python_syntax():
    py_files = glob.glob(os.path.join(REPO_ROOT, "**", "*.py"), recursive=True)
    any_fail = False
    for path in py_files:
        rel = os.path.relpath(path, REPO_ROOT)
        try:
            py_compile.compile(path, doraise=True)
        except py_compile.PyCompileError as e:
            fail("Python syntax check", f"{rel}: {e.msg}")
            any_fail = True
    if not any_fail:
        ok(f"Python syntax check ({len(py_files)} files)")


def main():
    check_sql_idempotency()
    check_docs_ledger_consistency()
    check_no_placeholders()
    check_python_syntax()

    print()
    if failures:
        print(f"{len(failures)} check(s) failed.")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
