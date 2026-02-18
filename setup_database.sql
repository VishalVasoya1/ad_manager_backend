-- Ad Manager Database Setup SQL Script
-- Run this in PostgreSQL as a superuser (e.g., postgres user)
-- You can run this via pgAdmin or psql command line

-- Create the database
CREATE DATABASE ad_manager_db;

-- Connect to the new database (in psql: \c ad_manager_db)

-- Grant privileges to app user
GRANT ALL PRIVILEGES ON DATABASE ad_manager_db TO app_user_db;

-- After running this, start the FastAPI application
-- It will automatically create all tables
