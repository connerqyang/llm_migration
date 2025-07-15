-- LLM Migration Tool Database Schema
-- PostgreSQL Database Schema for tracking migration attempts and analytics

-- Enable UUID extension for primary keys
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Components table - catalog of supported TUX components
CREATE TABLE components (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL UNIQUE,
    description TEXT,
    old_import_path VARCHAR(255),
    new_import_path VARCHAR(255),
    migration_guide_path VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Migrations table - core migration attempts
CREATE TABLE migrations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    component_id UUID NOT NULL REFERENCES components(id),
    component_name VARCHAR(100) NOT NULL,
    file_path TEXT NOT NULL,
    subrepo_path TEXT,
    repo_path TEXT,
    full_file_path TEXT NOT NULL,
    
    -- Migration settings
    max_retries INTEGER DEFAULT 3,
    selected_steps TEXT[], -- Array of validation steps like ['fix-eslint', 'fix-build']
    
    -- Status and timing
    status VARCHAR(50) NOT NULL DEFAULT 'pending', -- pending, running, completed, failed
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    
    -- Git information
    branch_name VARCHAR(255),
    commit_hash VARCHAR(40),
    base_branch VARCHAR(100) DEFAULT 'master',
    
    -- Code snapshots
    original_code TEXT,
    final_code TEXT,
    
    -- Results
    overall_success BOOLEAN,
    validation_passed BOOLEAN,
    migration_notes TEXT,
    error_summary TEXT,
    
    -- Metadata
    created_by VARCHAR(100), -- User identifier
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Validation steps table - individual validation stage results
CREATE TABLE validation_steps (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    migration_id UUID NOT NULL REFERENCES migrations(id) ON DELETE CASCADE,
    
    -- Step identification
    step_type VARCHAR(50) NOT NULL, -- eslint, typescript, build
    step_name VARCHAR(100) NOT NULL,
    retry_attempt INTEGER NOT NULL DEFAULT 1,
    step_order INTEGER NOT NULL,
    
    -- Execution details
    status VARCHAR(50) NOT NULL, -- pending, in_progress, completed, failed
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    duration_seconds INTEGER,
    
    -- Results and metrics
    success BOOLEAN,
    total_checks INTEGER DEFAULT 0,
    passed_checks INTEGER DEFAULT 0,
    failed_checks INTEGER DEFAULT 0,
    skipped_checks INTEGER DEFAULT 0,
    success_rate DECIMAL(5,2), -- Percentage
    
    -- Code at this step
    input_code TEXT,
    output_code TEXT,
    code_changes_made BOOLEAN DEFAULT false,
    
    -- Error tracking
    error_count INTEGER DEFAULT 0,
    errors_before JSONB, -- Array of error objects before fixes
    errors_after JSONB, -- Array of error objects after fixes
    errors_resolved INTEGER DEFAULT 0,
    errors_introduced INTEGER DEFAULT 0,
    
    -- LLM interaction
    llm_used BOOLEAN DEFAULT false,
    llm_prompt TEXT,
    llm_response TEXT,
    llm_fix_successful BOOLEAN,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Error logs table - detailed error tracking
CREATE TABLE error_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    migration_id UUID NOT NULL REFERENCES migrations(id) ON DELETE CASCADE,
    validation_step_id UUID REFERENCES validation_steps(id) ON DELETE CASCADE,
    
    -- Error details
    error_type VARCHAR(100) NOT NULL, -- eslint, typescript, build, system
    error_code VARCHAR(100), -- Specific error code if available
    error_message TEXT NOT NULL,
    error_severity INTEGER DEFAULT 2, -- 1=warning, 2=error, 3=fatal
    
    -- Location information
    file_path TEXT,
    line_number INTEGER,
    column_number INTEGER,
    
    -- Context
    surrounding_code TEXT,
    suggested_fix TEXT,
    was_fixed BOOLEAN DEFAULT false,
    fix_attempt_count INTEGER DEFAULT 0,
    
    -- Timing
    first_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP WITH TIME ZONE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Migration metrics table - aggregated statistics for performance tracking
CREATE TABLE migration_metrics (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    
    -- Time period
    date_period DATE NOT NULL, -- Daily aggregation
    component_name VARCHAR(100),
    
    -- Counts
    total_attempts INTEGER DEFAULT 0,
    successful_attempts INTEGER DEFAULT 0,
    failed_attempts INTEGER DEFAULT 0,
    
    -- Success rates
    overall_success_rate DECIMAL(5,2),
    validation_success_rate DECIMAL(5,2),
    
    -- Performance metrics
    avg_duration_seconds DECIMAL(8,2),
    avg_retry_count DECIMAL(4,2),
    
    -- Error statistics
    total_errors INTEGER DEFAULT 0,
    eslint_errors INTEGER DEFAULT 0,
    typescript_errors INTEGER DEFAULT 0,
    build_errors INTEGER DEFAULT 0,
    
    -- LLM usage
    llm_fixes_attempted INTEGER DEFAULT 0,
    llm_fixes_successful INTEGER DEFAULT 0,
    llm_success_rate DECIMAL(5,2),
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- Ensure unique daily metrics per component
    UNIQUE(date_period, component_name)
);

-- Indexes for performance
CREATE INDEX idx_migrations_component_name ON migrations(component_name);
CREATE INDEX idx_migrations_status ON migrations(status);
CREATE INDEX idx_migrations_created_at ON migrations(created_at);
CREATE INDEX idx_migrations_file_path ON migrations(file_path);

CREATE INDEX idx_validation_steps_migration_id ON validation_steps(migration_id);
CREATE INDEX idx_validation_steps_step_type ON validation_steps(step_type);
CREATE INDEX idx_validation_steps_status ON validation_steps(status);

CREATE INDEX idx_error_logs_migration_id ON error_logs(migration_id);
CREATE INDEX idx_error_logs_error_type ON error_logs(error_type);
CREATE INDEX idx_error_logs_created_at ON error_logs(created_at);

CREATE INDEX idx_migration_metrics_date_period ON migration_metrics(date_period);
CREATE INDEX idx_migration_metrics_component_name ON migration_metrics(component_name);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Add updated_at triggers to all tables
CREATE TRIGGER update_components_updated_at BEFORE UPDATE ON components FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_migrations_updated_at BEFORE UPDATE ON migrations FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_validation_steps_updated_at BEFORE UPDATE ON validation_steps FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_error_logs_updated_at BEFORE UPDATE ON error_logs FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_migration_metrics_updated_at BEFORE UPDATE ON migration_metrics FOR EACH ROW EXECUTE FUNCTION update_migration_metrics_updated_at_column();

-- Insert initial supported components
INSERT INTO components (name, old_import_path, new_import_path, description) VALUES
('TUXButton', '@byted-tiktok/tux-components', '@byted-tiktok/tux-web', 'Button component migration from old TUX to new TUX'),
('TUXIcon', '@byted-tiktok/tux-components', '@byted-tiktok/tux-web', 'Icon component migration from old TUX to new TUX');

-- Create a view for easy analytics queries
CREATE VIEW migration_analytics AS
SELECT 
    m.component_name,
    COUNT(*) as total_migrations,
    COUNT(*) FILTER (WHERE m.overall_success = true) as successful_migrations,
    COUNT(*) FILTER (WHERE m.overall_success = false) as failed_migrations,
    ROUND(
        (COUNT(*) FILTER (WHERE m.overall_success = true)::DECIMAL / COUNT(*)) * 100, 
        2
    ) as success_rate,
    AVG(m.duration_seconds) as avg_duration_seconds,
    AVG(
        (SELECT COUNT(*) FROM validation_steps vs WHERE vs.migration_id = m.id)
    ) as avg_validation_steps,
    COUNT(DISTINCT m.file_path) as unique_files_migrated,
    MAX(m.created_at) as last_migration_date
FROM migrations m
GROUP BY m.component_name;