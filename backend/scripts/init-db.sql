-- Initial Database Setup Script
-- This script runs automatically when PostgreSQL container is first created

-- Set timezone to UTC
SET timezone = 'UTC';

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Grant privileges
GRANT ALL PRIVILEGES ON DATABASE smart_campus TO campus_admin;

-- Done
SELECT 'Database initialization completed' AS status;
