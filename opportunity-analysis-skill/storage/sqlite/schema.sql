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
    responsibility_scope TEXT,
    decision_role TEXT,
    is_requirement_owner INTEGER DEFAULT 0,
    confirmation_status TEXT,
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
    stage_id TEXT,
    stage_reason TEXT,
    stage_confidence TEXT,
    stage_signal_hits TEXT,
    opportunity_confirmed INTEGER,
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

CREATE TABLE IF NOT EXISTS decision_chain (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    contact_id TEXT,
    person_name TEXT,
    title TEXT,
    decision_role TEXT NOT NULL,
    chain_level TEXT,
    responsibility_scope TEXT,
    influence_level TEXT,
    status TEXT,
    evidence_refs TEXT,
    next_step TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(opportunity_id) REFERENCES opportunities(id),
    FOREIGN KEY(contact_id) REFERENCES contacts(id)
);

CREATE TABLE IF NOT EXISTS commercial_assessments (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    win_likelihood_score INTEGER,
    deal_attractiveness_score INTEGER,
    delivery_confidence_score INTEGER,
    overall_opportunity_score INTEGER,
    win_probability REAL,
    confidence_level TEXT,
    assessment_confidence_score INTEGER,
    unanswered_critical_count INTEGER,
    created_at TEXT NOT NULL,
    FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
);

CREATE TABLE IF NOT EXISTS assessment_dimensions (
    id TEXT PRIMARY KEY,
    assessment_id TEXT NOT NULL,
    opportunity_id TEXT NOT NULL,
    dimension_id TEXT NOT NULL,
    category TEXT,
    label TEXT,
    priority TEXT,
    critical INTEGER DEFAULT 0,
    rating TEXT,
    score INTEGER,
    weight REAL,
    evidence_status TEXT,
    rationale TEXT,
    question TEXT,
    answer TEXT,
    evidence_refs TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(assessment_id) REFERENCES commercial_assessments(id),
    FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
);

CREATE TABLE IF NOT EXISTS sales_confirmation_questions (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    assessment_id TEXT NOT NULL,
    dimension_id TEXT NOT NULL,
    category TEXT,
    label TEXT,
    question TEXT NOT NULL,
    priority TEXT,
    status TEXT,
    current_rating TEXT,
    impact TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(opportunity_id) REFERENCES opportunities(id),
    FOREIGN KEY(assessment_id) REFERENCES commercial_assessments(id)
);

CREATE TABLE IF NOT EXISTS sales_confirmation_answers (
    id TEXT PRIMARY KEY,
    opportunity_id TEXT NOT NULL,
    assessment_id TEXT,
    question_id TEXT,
    dimension_id TEXT,
    answer_text TEXT,
    rating TEXT,
    source TEXT,
    answered_by TEXT,
    answered_at TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY(opportunity_id) REFERENCES opportunities(id)
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
CREATE INDEX IF NOT EXISTS idx_decision_chain_opp ON decision_chain(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_commercial_assessments_opp ON commercial_assessments(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_assessment_dimensions_opp ON assessment_dimensions(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_sales_questions_opp ON sales_confirmation_questions(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_sales_answers_opp ON sales_confirmation_answers(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_next_actions_opp ON next_actions(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_risks_opp ON risks(opportunity_id);
