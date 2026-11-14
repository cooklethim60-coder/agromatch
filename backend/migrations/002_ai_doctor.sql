CREATE TABLE IF NOT EXISTS ai_field_insights(
 id INTEGER PRIMARY KEY AUTOINCREMENT,
 field_id INTEGER NOT NULL REFERENCES fields(id),
 provider TEXT NOT NULL, content TEXT NOT NULL, created REAL NOT NULL);
CREATE INDEX IF NOT EXISTS idx_ai_field ON ai_field_insights(field_id,created DESC);
