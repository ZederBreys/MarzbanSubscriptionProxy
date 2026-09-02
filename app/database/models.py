SUBSCRIPTION_URL_SCHEMA = """
CREATE TABLE IF NOT EXISTS subscription_url (
    sud_id TEXT NOT NULL UNIQUE,
    config TEXT NOT NULL,
    profile_title TEXT,
    profile_update_interval INTEGER DEFAULT 12
)
"""

ADMIN_USERS_SCHEMA = """
CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    login TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    last_login_at REAL,
    last_login_ip TEXT,
    created_at REAL DEFAULT (CAST(strftime('%s', 'now') AS REAL))
)
"""

ADMIN_USERS_MIGRATIONS = [
    "ALTER TABLE admin_users ADD COLUMN last_login_at REAL",
    "ALTER TABLE admin_users ADD COLUMN last_login_ip TEXT",
    "ALTER TABLE admin_users ADD COLUMN created_at REAL DEFAULT (CAST(strftime('%s', 'now') AS REAL))",
]

ADMIN_SESSIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS admin_sessions (
    session_hash TEXT PRIMARY KEY,
    admin_id INTEGER NOT NULL,
    ip_address TEXT NOT NULL DEFAULT '',
    csrf_token_hash TEXT NOT NULL DEFAULT '',
    expires_at REAL NOT NULL,
    last_accessed_at REAL DEFAULT (CAST(strftime('%s', 'now') AS REAL)),
    created_at REAL DEFAULT (CAST(strftime('%s', 'now') AS REAL)),
    FOREIGN KEY (admin_id) REFERENCES admin_users(id) ON DELETE CASCADE
)
"""

ADMIN_SESSIONS_MIGRATIONS = [
    "ALTER TABLE admin_sessions ADD COLUMN ip_address TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE admin_sessions ADD COLUMN csrf_token_hash TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE admin_sessions ADD COLUMN last_accessed_at REAL DEFAULT (CAST(strftime('%s', 'now') AS REAL))",
]

ADMIN_SESSIONS_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_sessions_admin_id ON admin_sessions(admin_id)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_expires ON admin_sessions(expires_at)",
]

AUDIT_LOG_SCHEMA = """
CREATE TABLE IF NOT EXISTS admin_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp REAL DEFAULT (CAST(strftime('%s', 'now') AS REAL)),
    admin_login TEXT NOT NULL,
    ip_address TEXT,
    action TEXT NOT NULL,
    object_type TEXT NOT NULL,
    object_id TEXT,
    old_value_json TEXT,
    new_value_json TEXT,
    description TEXT,
    result TEXT NOT NULL DEFAULT 'SUCCESS'
)
"""

AUDIT_LOG_MIGRATIONS = [
    "ALTER TABLE admin_audit_log ADD COLUMN ip_address TEXT",
    "ALTER TABLE admin_audit_log ADD COLUMN old_value_json TEXT",
    "ALTER TABLE admin_audit_log ADD COLUMN new_value_json TEXT",
]

AUDIT_LOG_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_audit_timestamp ON admin_audit_log(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_audit_admin ON admin_audit_log(admin_login)",
]
