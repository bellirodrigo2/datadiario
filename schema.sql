-- Schema for Links Repository
-- Compatible with both SQLite and PostgreSQL

-- Links Entry table
CREATE TABLE IF NOT EXISTS links_entry (
    id INTEGER PRIMARY KEY,
    entity TEXT NOT NULL,
    group_name TEXT NOT NULL,
    date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(entity, group_name, date)
);

-- Links table
CREATE TABLE IF NOT EXISTS links (
    id INTEGER PRIMARY KEY,
    links_entry_id INTEGER NOT NULL,
    link TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'success', 'failed')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (links_entry_id) REFERENCES links_entry(id) ON DELETE CASCADE,
    UNIQUE(links_entry_id, link)
);

-- Indexes for better performance
CREATE INDEX IF NOT EXISTS idx_links_entry_entity_group_date ON links_entry(entity, group_name, date);
CREATE INDEX IF NOT EXISTS idx_links_status ON links(status);
CREATE INDEX IF NOT EXISTS idx_links_entry_id ON links(links_entry_id);

-- PostgreSQL specific: Auto-increment sequences (SQLite handles this automatically with INTEGER PRIMARY KEY)
-- For PostgreSQL, you would need:
-- ALTER TABLE links_entry ALTER COLUMN id SET DEFAULT nextval('links_entry_id_seq');
-- ALTER TABLE links ALTER COLUMN id SET DEFAULT nextval('links_id_seq');