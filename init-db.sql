-- Initialize HackRX database schema
-- This file is automatically executed when PostgreSQL container starts

-- Create document cache table
CREATE TABLE IF NOT EXISTS document_cache (
    id SERIAL PRIMARY KEY,
    document_hash VARCHAR(64) UNIQUE NOT NULL,
    document_url TEXT NOT NULL,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    chunk_count INTEGER,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create query cache table
CREATE TABLE IF NOT EXISTS query_cache (
    id SERIAL PRIMARY KEY,
    query_hash VARCHAR(64) UNIQUE NOT NULL,
    document_hash VARCHAR(64) NOT NULL,
    query TEXT NOT NULL,
    answer TEXT,
    sources JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (document_hash) REFERENCES document_cache(document_hash) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_document_cache_hash ON document_cache(document_hash);
CREATE INDEX IF NOT EXISTS idx_document_cache_processed_at ON document_cache(processed_at);
CREATE INDEX IF NOT EXISTS idx_query_cache_hash ON query_cache(query_hash);
CREATE INDEX IF NOT EXISTS idx_query_cache_document_hash ON query_cache(document_hash);
CREATE INDEX IF NOT EXISTS idx_query_cache_created_at ON query_cache(created_at);

-- Create function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create triggers to automatically update updated_at
CREATE TRIGGER update_document_cache_updated_at 
    BEFORE UPDATE ON document_cache 
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

CREATE TRIGGER update_query_cache_updated_at 
    BEFORE UPDATE ON query_cache 
    FOR EACH ROW EXECUTE PROCEDURE update_updated_at_column();

-- Insert initial data or configuration if needed
-- (You can add sample data here if required)

-- Grant permissions (optional, for development)
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO hackrx_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO hackrx_user;
