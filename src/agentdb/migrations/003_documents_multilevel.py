"""Documentation multilevel schema."""

import sqlite3

DESCRIPTION = "Add documents_multilevel tables and FTS triggers"
CHECKSUM = "sha256:ef8774735aecc657b3824e14e8d1483732476654ec8d5dac83ad4bac50145aaf"


DOCUMENTS_SQL = """
CREATE TABLE IF NOT EXISTS documents_multilevel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_path TEXT NOT NULL,
    section_id TEXT NOT NULL,
    section_title TEXT,
    doc_type TEXT NOT NULL,
    file_hash TEXT NOT NULL,
    section_hash TEXT NOT NULL,
    summary_l0 TEXT,
    contract_l1 TEXT,
    outline_l2 TEXT,
    excerpt_l3 TEXT,
    content_l4 TEXT,
    start_line INTEGER,
    end_line INTEGER,
    word_count INTEGER,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    UNIQUE(doc_path, section_id, file_hash),
    CHECK(doc_type IN ('guide', 'reference', 'tutorial', 'spec', 'api', 'architecture'))
);

CREATE INDEX IF NOT EXISTS idx_documents_multilevel_doc_path
    ON documents_multilevel(doc_path);
CREATE INDEX IF NOT EXISTS idx_documents_multilevel_section
    ON documents_multilevel(doc_path, section_id);
CREATE INDEX IF NOT EXISTS idx_documents_multilevel_doc_type
    ON documents_multilevel(doc_type);

CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(
    doc_path,
    section_id,
    section_title,
    summary_l0,
    contract_l1,
    outline_l2,
    content='documents_multilevel',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS documents_fts_insert
AFTER INSERT ON documents_multilevel
BEGIN
    INSERT INTO documents_fts(rowid, doc_path, section_id, section_title, summary_l0, contract_l1, outline_l2)
    VALUES (new.id, new.doc_path, new.section_id, new.section_title, new.summary_l0, new.contract_l1, new.outline_l2);
END;

CREATE TRIGGER IF NOT EXISTS documents_fts_update
AFTER UPDATE ON documents_multilevel
BEGIN
    UPDATE documents_fts SET
        doc_path = new.doc_path,
        section_id = new.section_id,
        section_title = new.section_title,
        summary_l0 = new.summary_l0,
        contract_l1 = new.contract_l1,
        outline_l2 = new.outline_l2
    WHERE rowid = new.id;
END;

CREATE TRIGGER IF NOT EXISTS documents_fts_delete
AFTER DELETE ON documents_multilevel
BEGIN
    DELETE FROM documents_fts WHERE rowid = old.id;
END;

CREATE TRIGGER IF NOT EXISTS documents_multilevel_update_timestamp
AFTER UPDATE ON documents_multilevel
BEGIN
    UPDATE documents_multilevel
    SET updated_at = datetime('now')
    WHERE id = new.id;
END;

CREATE TABLE IF NOT EXISTS documents_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doc_path TEXT NOT NULL UNIQUE,
    file_hash TEXT NOT NULL,
    db_state TEXT NOT NULL,
    doc_type TEXT NOT NULL,
    section_count INTEGER DEFAULT 0,
    total_words INTEGER DEFAULT 0,
    ingested_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    CHECK(db_state IN ('missing', 'indexed'))
);

CREATE INDEX IF NOT EXISTS idx_documents_files_path
    ON documents_files(doc_path);

CREATE VIEW IF NOT EXISTS documents_overview AS
SELECT
    df.doc_path,
    df.file_hash,
    df.db_state,
    df.doc_type,
    df.section_count,
    df.total_words,
    COUNT(dm.id) AS sections_indexed,
    SUM(CASE WHEN dm.summary_l0 IS NOT NULL THEN 1 ELSE 0 END) AS l0_complete,
    SUM(CASE WHEN dm.contract_l1 IS NOT NULL THEN 1 ELSE 0 END) AS l1_complete,
    SUM(CASE WHEN dm.outline_l2 IS NOT NULL THEN 1 ELSE 0 END) AS l2_complete,
    SUM(CASE WHEN dm.excerpt_l3 IS NOT NULL THEN 1 ELSE 0 END) AS l3_complete,
    SUM(CASE WHEN dm.content_l4 IS NOT NULL THEN 1 ELSE 0 END) AS l4_complete
FROM documents_files df
LEFT JOIN documents_multilevel dm ON df.doc_path = dm.doc_path
GROUP BY df.doc_path;
