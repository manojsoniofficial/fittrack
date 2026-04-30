-- FitTrack Pro — PostgreSQL Initialization
-- Runs automatically when the container starts for the first time

-- Create test database for CI
CREATE DATABASE fittrack_test
    WITH OWNER = fittrack
    ENCODING = 'UTF8'
    LC_COLLATE = 'C'
    LC_CTYPE = 'C'
    TEMPLATE = template0;

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE fittrack_dev TO fittrack;
GRANT ALL PRIVILEGES ON DATABASE fittrack_test TO fittrack;

-- Enable pg_trgm for fuzzy search (optional)
\c fittrack_dev
CREATE EXTENSION IF NOT EXISTS pg_trgm;

\c fittrack_test
CREATE EXTENSION IF NOT EXISTS pg_trgm;
