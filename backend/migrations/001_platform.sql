-- Additive migration: preserves all pre-existing farms, fields and messages.
CREATE TABLE IF NOT EXISTS posts(
 id INTEGER PRIMARY KEY AUTOINCREMENT, author_farm INTEGER NOT NULL REFERENCES farms(id),
 body TEXT NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS post_likes(
 post_id INTEGER NOT NULL REFERENCES posts(id), farm_id INTEGER NOT NULL REFERENCES farms(id),
 PRIMARY KEY(post_id,farm_id));
CREATE TABLE IF NOT EXISTS comments(
 id INTEGER PRIMARY KEY AUTOINCREMENT, post_id INTEGER NOT NULL REFERENCES posts(id),
 author_farm INTEGER NOT NULL REFERENCES farms(id), body TEXT NOT NULL, created REAL NOT NULL);
CREATE TABLE IF NOT EXISTS notifications(
 id INTEGER PRIMARY KEY AUTOINCREMENT, farm_id INTEGER NOT NULL REFERENCES farms(id),
 category TEXT NOT NULL, text TEXT NOT NULL, target TEXT NOT NULL DEFAULT '',
 created REAL NOT NULL, is_read INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS appeears_tasks(
 id INTEGER PRIMARY KEY AUTOINCREMENT, field_id INTEGER NOT NULL REFERENCES fields(id),
 remote_id TEXT UNIQUE NOT NULL, status TEXT NOT NULL, products TEXT NOT NULL,
 created REAL NOT NULL, checked REAL, error TEXT);
CREATE TABLE IF NOT EXISTS satellite_observations(
 id INTEGER PRIMARY KEY AUTOINCREMENT, field_id INTEGER NOT NULL REFERENCES fields(id),
 source TEXT NOT NULL, product TEXT NOT NULL, indicator TEXT NOT NULL,
 observed_at TEXT NOT NULL, value REAL NOT NULL, unit TEXT NOT NULL,
 resolution TEXT NOT NULL DEFAULT 'check product', quality TEXT NOT NULL DEFAULT 'not validated',
 task_id INTEGER REFERENCES appeears_tasks(id),
 UNIQUE(field_id,product,indicator,observed_at));
CREATE INDEX IF NOT EXISTS idx_posts_new ON posts(created DESC);
CREATE INDEX IF NOT EXISTS idx_comments_post ON comments(post_id);
CREATE INDEX IF NOT EXISTS idx_notif_farm ON notifications(farm_id,is_read,created DESC);
CREATE INDEX IF NOT EXISTS idx_sat_field ON satellite_observations(field_id,indicator,observed_at);
