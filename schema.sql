-- SQLite schema for agentdb MVP
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS files (
  repo_path TEXT PRIMARY KEY,
  file_hash TEXT,
  db_state TEXT CHECK(db_state IN ('missing','indexed')) NOT NULL DEFAULT 'missing',
  last_seen TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS symbols (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  repo_path TEXT NOT NULL,
  name TEXT,
  kind TEXT,
  signature TEXT,
  start_line INTEGER,
  end_line INTEGER,
  content_hash TEXT,
  l0_overview TEXT,
  l1_contract TEXT,
  l2_pseudocode TEXT,
  l3_ast_json TEXT,
  l4_full_code TEXT
);

CREATE TABLE IF NOT EXISTS edges (
  src_id INTEGER,
  dst_id INTEGER,
  edge_type TEXT,
  PRIMARY KEY (src_id, dst_id, edge_type)
);

CREATE TABLE IF NOT EXISTS ops_log (
  ts TEXT DEFAULT CURRENT_TIMESTAMP,
  op TEXT,
  details TEXT
);

-- FTS5 for quick name/overview/contract search (contentless index referencing symbols)
CREATE VIRTUAL TABLE IF NOT EXISTS symbols_fts USING fts5(
  repo_path, name, l0_overview, l1_contract
);

-- Database version tracking for schema migrations
CREATE TABLE IF NOT EXISTS db_version (
  version INTEGER PRIMARY KEY,
  upgraded_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Current schema version
INSERT OR IGNORE INTO db_version (version) VALUES (1);
