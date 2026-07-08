-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    status TEXT NOT NULL,
    principal_investigator TEXT NOT NULL,
    organisation TEXT NOT NULL
);

-- Datasets table
CREATE TABLE IF NOT EXISTS datasets (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT NOT NULL,
    records INT NOT NULL,
    restricted BOOLEAN NOT NULL,
    fields JSONB NOT NULL
);

-- Project x Dataset link table
CREATE TABLE IF NOT EXISTS project_x_datasets (
    project_id TEXT REFERENCES projects(id),
    dataset_id TEXT REFERENCES datasets(id),
    PRIMARY KEY (project_id, dataset_id)
);

-- Researchers table
CREATE TABLE IF NOT EXISTS researchers (
    username TEXT PRIMARY KEY,
    display_name TEXT NOT NULL,
    role TEXT NOT NULL
);

-- Researcher x Project link table ('*' project_id = all projects, admin)
CREATE TABLE IF NOT EXISTS researcher_x_projects (
    username TEXT REFERENCES researchers(username),
    project_id TEXT NOT NULL,
    PRIMARY KEY (username, project_id)
);

-- Audit trail table (requirement 5: request id, tools, timings, errors)
CREATE TABLE IF NOT EXISTS audit_log (
    trace_id TEXT PRIMARY KEY,
    question TEXT NOT NULL,
    tools_invoked JSONB NOT NULL DEFAULT '[]',
    sources JSONB NOT NULL DEFAULT '[]',
    governance JSONB NOT NULL DEFAULT '[]',
    duration_ms INT,
    error TEXT,
    researcher TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Read-only role used by data_api for all read/analytical queries
DO $$ BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'ra_readonly') THEN
        CREATE ROLE ra_readonly LOGIN PASSWORD 'ra_readonly';
    END IF;
END $$;
GRANT CONNECT ON DATABASE research TO ra_readonly;
GRANT USAGE ON SCHEMA public TO ra_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO ra_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO ra_readonly;
