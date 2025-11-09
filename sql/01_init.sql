-- Database Initialization Script
-- Creates necessary extensions and base tables

-- Enable useful extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Create schema comment
COMMENT ON DATABASE crypto_data IS 'Cryptocurrency market data pipeline database';

-- Create a metadata table to track pipeline runs
CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id SERIAL PRIMARY KEY,
    run_timestamp TIMESTAMP NOT NULL DEFAULT NOW(),
    pipeline_stage VARCHAR(50) NOT NULL,
    status VARCHAR(20) NOT NULL,
    records_processed INTEGER,
    duration_seconds NUMERIC(10, 2),
    error_message TEXT,
    metadata JSONB
);

CREATE INDEX idx_pipeline_runs_timestamp ON pipeline_runs(run_timestamp DESC);
CREATE INDEX idx_pipeline_runs_stage ON pipeline_runs(pipeline_stage);
CREATE INDEX idx_pipeline_runs_status ON pipeline_runs(status);

COMMENT ON TABLE pipeline_runs IS 'Tracks all pipeline execution runs for monitoring and debugging';

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO pipeline_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO pipeline_user;

-- Create a simple function to log pipeline events
CREATE OR REPLACE FUNCTION log_pipeline_run(
    p_stage VARCHAR,
    p_status VARCHAR,
    p_records INTEGER DEFAULT NULL,
    p_duration NUMERIC DEFAULT NULL,
    p_error TEXT DEFAULT NULL,
    p_metadata JSONB DEFAULT NULL
) RETURNS INTEGER AS $$
DECLARE
    v_run_id INTEGER;
BEGIN
    INSERT INTO pipeline_runs (
        pipeline_stage,
        status,
        records_processed,
        duration_seconds,
        error_message,
        metadata
    ) VALUES (
        p_stage,
        p_status,
        p_records,
        p_duration,
        p_error,
        p_metadata
    ) RETURNING run_id INTO v_run_id;
    
    RETURN v_run_id;
END;
$$ LANGUAGE plpgsql;

COMMENT ON FUNCTION log_pipeline_run IS 'Utility function to log pipeline execution events';

-- Create view to see recent pipeline activity
CREATE OR REPLACE VIEW pipeline_activity AS
SELECT 
    run_id,
    run_timestamp,
    pipeline_stage,
    status,
    records_processed,
    duration_seconds,
    error_message
FROM pipeline_runs
ORDER BY run_timestamp DESC
LIMIT 100;

COMMENT ON VIEW pipeline_activity IS 'Recent pipeline execution history';
