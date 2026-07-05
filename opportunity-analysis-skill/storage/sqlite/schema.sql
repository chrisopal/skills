PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS accounts (
    id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    normalized_name TEXT,
    industry TEXT,
    region TEXT,
    company_size TEXT,
    business_summary TEXT,
    current_systems TEXT,
    key_pain_points TEXT,
    source_confidence REAL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS contacts (
    id TEXT PRIMARY KEY,
    account_id TEXT,
    name TEXT NOT NULL,
    title TEXT,
    department TEXT,
    role_in_opportunity TEXT,
    phone TEXT,
    email TEXT,
    attitude TEXT,
    source_refs TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS opportunities (
    id TEXT PRIMARY KEY,
    account_id TEXT NOT NULL,
    name TEXT NOT NULL,
    stage TEXT,
    stage_status TEXT,
    core_need TEXT,
    budget_signal TEXT,
    budget_amount TEXT,
    expected_timeline TEXT,
    win_probability REAL,
    score INTEGER,
    score_level TEXT,
    risk_level TEXT,
    competitors TEXT,
    pain_points TEXT,
    requirements TEXT,
    missing_information TEXT,
    status TEXT DEFAULT 'active',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(account_id) REFERENCES accounts(id)
);

CREATE TABLE IF NOT EXISTS interactions (
    id TEXT PRIMARY KEY,
    account_id TEXT,
    opportunity_id TEXT,
    interaction_type TEXT,
    channel TEXT,
    title TEXT,
    summary TEXT,
    content TEXT,
    occurred_at TEXT,
    owner TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(account_id) REFERENCES accounts(id),
    FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
);

CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    source_type TEXT,
    source_name TEXT,
    source_ref TEXT,
    content TEXT,
    extracted_fields TEXT,
    confidence REAL,
    requires_human_confirmation INTEGER DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS evidence_files (
    id TEXT PRIMARY KEY,
    evidence_id TEXT NOT NULL,
    original_path TEXT,
    archived_path TEXT,
    relative_path TEXT,
    file_name TEXT,
    display_name TEXT,
    mime_type TEXT,
    size_bytes INTEGER,
    sha256 TEXT,
    is_image INTEGER DEFAULT 0,
    created_at TEXT NOT NULL,
    FOREIGN KEY(evidence_id) REFERENCES evidence(id)
);

CREATE TABLE IF NOT EXISTS opportunity_evidence_map (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    field_name TEXT,
    field_value TEXT,
    status TEXT,
    confidence REAL,
    created_at TEXT NOT NULL,
    FOREIGN KEY(opportunity_id) REFERENCES opportunities(id),
    FOREIGN KEY(evidence_id) REFERENCES evidence(id)
);

CREATE TABLE IF NOT EXISTS risks (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    risk_type TEXT,
    risk_level TEXT,
    description TEXT,
    mitigation TEXT,
    evidence_refs TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
);

CREATE TABLE IF NOT EXISTS next_actions (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    action_title TEXT NOT NULL,
    action_detail TEXT,
    priority TEXT,
    owner TEXT,
    deadline_suggestion TEXT,
    status TEXT DEFAULT 'open',
    reason TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
);

CREATE TABLE IF NOT EXISTS skill_runs (
    id TEXT PRIMARY KEY,
    skill_name TEXT,
    input_summary TEXT,
    output_summary TEXT,
    structured_output TEXT,
    display_output_path TEXT,
    status TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS rendered_views (
    id TEXT PRIMARY KEY,
    object_type TEXT,
    object_id TEXT,
    template_id TEXT,
    html_content TEXT,
    markdown_content TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_opportunities_account ON opportunities(account_id);
CREATE INDEX IF NOT EXISTS idx_opportunities_stage ON opportunities(stage);
CREATE INDEX IF NOT EXISTS idx_opportunities_score ON opportunities(score);
CREATE INDEX IF NOT EXISTS idx_evidence_files_evidence ON evidence_files(evidence_id);
CREATE INDEX IF NOT EXISTS idx_next_actions_opp ON next_actions(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_risks_opp ON risks(opportunity_id);
