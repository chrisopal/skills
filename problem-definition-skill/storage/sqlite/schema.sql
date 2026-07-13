PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS problem_definitions (
  id TEXT PRIMARY KEY,
  account_id TEXT,
  opportunity_id TEXT,
  case_name TEXT NOT NULL,
  surface_problem TEXT,
  surface_status TEXT,
  deep_problem TEXT,
  deep_status TEXT,
  decision_problem TEXT,
  decision_status TEXT,
  business_impacts_json TEXT,
  constraints_json TEXT,
  assumptions_json TEXT,
  missing_information_json TEXT,
  solution_entry_points_json TEXT,
  raw_output_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS success_criteria (
  id TEXT PRIMARY KEY,
  problem_definition_id TEXT NOT NULL,
  dimension TEXT,
  criterion TEXT NOT NULL,
  metric TEXT,
  target_value TEXT,
  status TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(problem_definition_id) REFERENCES problem_definitions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS problem_hypotheses (
  id TEXT PRIMARY KEY,
  problem_definition_id TEXT NOT NULL,
  hypothesis TEXT NOT NULL,
  status TEXT,
  validation_method TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(problem_definition_id) REFERENCES problem_definitions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS clarification_questions (
  id TEXT PRIMARY KEY,
  problem_definition_id TEXT NOT NULL,
  question TEXT NOT NULL,
  purpose TEXT,
  target_role TEXT,
  priority TEXT,
  related_issue TEXT,
  status TEXT DEFAULT 'open',
  created_at TEXT NOT NULL,
  FOREIGN KEY(problem_definition_id) REFERENCES problem_definitions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS problem_evidence_map (
  id TEXT PRIMARY KEY,
  problem_definition_id TEXT NOT NULL,
  field_name TEXT NOT NULL,
  source_id TEXT,
  source_name TEXT,
  excerpt TEXT,
  confidence REAL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(problem_definition_id) REFERENCES problem_definitions(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_problem_opportunity ON problem_definitions(opportunity_id);
CREATE INDEX IF NOT EXISTS idx_problem_account ON problem_definitions(account_id);
CREATE INDEX IF NOT EXISTS idx_question_problem ON clarification_questions(problem_definition_id);
