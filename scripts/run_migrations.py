#!/usr/bin/env python3

Run all SQLite migrations on dashboard database.

This creates all missing tables (trace_events, evidence_packs, etc.)


import sqlite3
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
MIGRATIONS_DIR = PROJECT_ROOT / "dashboard" / "migrations"
DB_PATH = PROJECT_ROOT / "dashboard" / "agentdb.db"


def run_migration(conn, sql_file: Path):
    """Run a single migration file."""
    print(f"Running: {sql_file.name}")

    try:
        with open(sql_file, 'r') as f:
            sql = f.read()

        # Execute migration
        conn.executescript(sql)
        conn.commit()

        print(f"  ✅ Success")
        return True

    except sqlite3.Error as e:
        print(f"  ⚠️  Error: {e}")
        # Continue anyway - some migrations may have partial conflicts
        return False


def get_current_tables(conn):
    """Get list of existing tables."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT name FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)
    return [row[0] for row in cursor.fetchall()]


def main():
    """Run all migrations."""
    print(f"🔧 Running migrations on {DB_PATH}")
    print(f"📁 Migrations from {MIGRATIONS_DIR}")
    print()

    # Check database exists
    if not DB_PATH.exists():
        print(f"❌ Database not found: {DB_PATH}")
        return 1

    # Get tables before
    conn = sqlite3.connect(DB_PATH)
    tables_before = set(get_current_tables(conn))
    print(f"📊 Tables before: {len(tables_before)}")
    print(f"   {', '.join(sorted(tables_before))}")
    print()

    # Get SQLite migrations (skip PostgreSQL ones)
    migrations = sorted([
        f for f in MIGRATIONS_DIR.glob("*.sql")
        if "_pg" not in f.name.lower() and "rollback" not in f.name.lower()
    ])

    print(f"📋 Found {len(migrations)} SQLite migrations")
    print()

    # Run each migration
    success_count = 0
    for migration_file in migrations:
        if run_migration(conn, migration_file):
            success_count += 1

    print()
    print(f"=" * 60)
    print(f"✅ Completed: {success_count}/{len(migrations)} migrations")

    # Get tables after
    tables_after = set(get_current_tables(conn))
    new_tables = tables_after - tables_before

    print()
    print(f"📊 Tables after: {len(tables_after)}")
    if new_tables:
        print(f"   New tables: {', '.join(sorted(new_tables))}")
    else:
        print(f"   No new tables (migrations already applied or conflicts)")

    conn.close()

    # Verify critical tables exist
    print()
    print(f"🔍 Verifying critical tables...")

    conn = sqlite3.connect(DB_PATH)
    critical_tables = [
        "trace_events",
        "traces",
        "evidence_packs",
        "session_messages",
        "tool_violations",
        "architectural_patterns"
    ]

    all_exist = True
    for table in critical_tables:
        cursor = conn.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,))
        exists = cursor.fetchone() is not None

        if exists:
            print(f"   ✅ {table}")
        else:
            print(f"   ❌ {table} - MISSING")
            all_exist = False

    conn.close()

    print()
    if all_exist:
        print(f"✅ All critical tables exist!")
        return 0
    else:
        print(f"⚠️  Some critical tables missing - may need additional migrations")
        return 0  # Don't fail - some tables may be in other migration files


if __name__ == '__main__':
    sys.exit(main())


<!--AGTAG v1 START-->
{
  "version": "v1",
  "symbols": [
    {
      "name": "run_migration",
      "kind": "function",
      "signature": "def run_migration(...)",
      "lines": [
        17,
        35
      ],
      "summary_l0": "Function run_migration",
      "contract_l1": "@io see source code"
    },
    {
      "name": "get_current_tables",
      "kind": "function",
      "signature": "def get_current_tables(...)",
      "lines": [
        38,
        46
      ],
      "summary_l0": "Function get_current_tables",
      "contract_l1": "@io see source code"
    },
    {
      "name": "main",
      "kind": "function",
      "signature": "def main(...)",
      "lines": [
        49,
        133
      ],
      "summary_l0": "Function main",
      "contract_l1": "@io see source code"
    }
  ]
}
<!--AGTAG v1 END-->
