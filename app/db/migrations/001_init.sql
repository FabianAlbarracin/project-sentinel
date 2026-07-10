-- 001_init.sql
-- Schema inicial de Project Sentinel
-- Ejecutar contra la base de datos 'sentinel'

CREATE TABLE IF NOT EXISTS sources (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS watch_items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    enabled BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS watch_terms (
    id SERIAL PRIMARY KEY,
    watch_item_id INTEGER NOT NULL REFERENCES watch_items(id),
    term VARCHAR(255) NOT NULL,
    term_type VARCHAR(50) NOT NULL DEFAULT 'ANCHOR',
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (watch_item_id, term)
);

CREATE TABLE IF NOT EXISTS observations (
    id SERIAL PRIMARY KEY,
    source_id INTEGER NOT NULL REFERENCES sources(id),
    watch_item_id INTEGER REFERENCES watch_items(id),
    external_id VARCHAR(512),
    observed_at TIMESTAMP NOT NULL DEFAULT NOW(),
    observation_type VARCHAR(50) NOT NULL DEFAULT 'UNKNOWN',
    title TEXT,
    price DECIMAL,
    currency VARCHAR(10),
    coupon VARCHAR(255),
    url TEXT,
    raw_content TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_observations_external_id
    ON observations (source_id, external_id);
CREATE INDEX IF NOT EXISTS idx_observations_watch_item
    ON observations (watch_item_id);

CREATE TABLE IF NOT EXISTS notifications (
    id SERIAL PRIMARY KEY,
    observation_id INTEGER NOT NULL REFERENCES observations(id),
    channel VARCHAR(50) NOT NULL DEFAULT 'telegram',
    status VARCHAR(50) NOT NULL DEFAULT 'SUCCESS',
    telegram_message_id BIGINT,
    sent_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS notification_feedback (
    id SERIAL PRIMARY KEY,
    notification_id INTEGER NOT NULL REFERENCES notifications(id),
    reaction VARCHAR(50) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT (NOW() AT TIME ZONE 'UTC')
);

CREATE INDEX IF NOT EXISTS idx_feedback_notification
    ON notification_feedback (notification_id);

CREATE TABLE IF NOT EXISTS settings (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT
);

-- Seed data
INSERT INTO sources (name, enabled) VALUES ('woot', TRUE)
    ON CONFLICT (name) DO NOTHING;

INSERT INTO sources (name, enabled) VALUES ('reddit', TRUE)
    ON CONFLICT (name) DO NOTHING;

INSERT INTO sources (name, enabled) VALUES ('telegram', TRUE)
    ON CONFLICT (name) DO NOTHING;

INSERT INTO watch_items (name, enabled) VALUES ('Kindle', TRUE)
    ON CONFLICT (name) DO NOTHING;

-- Anchor terms for Kindle
INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'kindle', 'ANCHOR' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'paperwhite', 'ANCHOR' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'scribe', 'ANCHOR' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

-- Exclude terms for Kindle
INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'case', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'cover', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'protector', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'skin', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'sleeve', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'charger', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'cable', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'adapter', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'screen protector', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'stand', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'holder', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'mount', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'strap', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'ebook', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'free book', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'kindle edition', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'kindle ebook', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'pdf', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'software', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'app', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'digest', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;

INSERT INTO watch_terms (watch_item_id, term, term_type)
    SELECT id, 'free ebook', 'EXCLUDE' FROM watch_items WHERE name = 'Kindle'
    ON CONFLICT (watch_item_id, term) DO NOTHING;
