CREATE TABLE IF NOT EXISTS sg_users (
  id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
  salt TEXT NOT NULL, password TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sg_sessions (
  token TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES sg_users(id),
  csrf TEXT NOT NULL, expires TIMESTAMPTZ NOT NULL
);
CREATE TABLE IF NOT EXISTS sg_records (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES sg_users(id),
  kind TEXT NOT NULL, payload JSONB NOT NULL, version INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS sg_records_owner ON sg_records(user_id);
CREATE TABLE IF NOT EXISTS sg_audit (
  id BIGSERIAL PRIMARY KEY, user_id TEXT NOT NULL REFERENCES sg_users(id),
  at TIMESTAMPTZ NOT NULL DEFAULT now(), action TEXT NOT NULL, record_id TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS sg_audit_owner ON sg_audit(user_id,id DESC);
CREATE TABLE IF NOT EXISTS sg_evidence (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES sg_users(id),
  record_id TEXT NOT NULL REFERENCES sg_records(id), name TEXT NOT NULL,
  blob_key TEXT NOT NULL, size INTEGER NOT NULL CHECK(size>0)
);
CREATE INDEX IF NOT EXISTS sg_evidence_owner ON sg_evidence(user_id);
CREATE TABLE IF NOT EXISTS sg_login_limits (
  key TEXT PRIMARY KEY, window_start TIMESTAMPTZ NOT NULL DEFAULT now(), attempts INTEGER NOT NULL DEFAULT 0
);
