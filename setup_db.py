"""
Database setup script - creates the database and runs migrations for new columns.
Run this with PostgreSQL superuser credentials.
"""

import asyncio
import asyncpg
from app.config.setting import settings


async def create_database():
    """Create the database if it doesn't exist using postgres superuser."""
    print("\n⚠️  You need PostgreSQL superuser credentials to create the database.")
    print("Please enter your PostgreSQL superuser credentials:")
    postgres_user = input("PostgreSQL username (default: postgres): ").strip() or "postgres"
    postgres_password = input("PostgreSQL password: ").strip()
    
    db_user, _, db_host, db_port, db_name = settings.DB_PARSED

    # Connect to the default 'postgres' database to create our database
    conn = await asyncpg.connect(
        user=postgres_user,
        password=postgres_password,
        host=db_host,
        port=db_port,
        database='postgres'
    )
    
    try:
        # Check if database exists
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            db_name
        )
        
        if not exists:
            # Create database
            await conn.execute(f'CREATE DATABASE {db_name}')
            print(f"✅ Database '{db_name}' created successfully!")
            
            # Grant privileges to app user
            await conn.execute(f'GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user}')
            print(f"✅ Granted privileges to '{db_user}'")
        else:
            print(f"ℹ️  Database '{db_name}' already exists.")
    finally:
        await conn.close()


async def add_user_tracking_columns():
    """Add created_by and updated_by columns to app_user table if they don't exist."""
    db_user, db_password, db_host, db_port, db_name = settings.DB_PARSED

    conn = await asyncpg.connect(
        user=db_user,
        password=db_password,
        host=db_host,
        port=db_port,
        database=db_name
    )
    
    try:
        # Check if created_by column exists
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.columns 
                WHERE table_name = 'app_user' 
                AND column_name = 'created_by'
            )
        """)
        
        if not column_exists:
            print("\nAdding created_by and updated_by columns to app_user table...")
            
            await conn.execute("""
                ALTER TABLE app_user 
                ADD COLUMN created_by UUID REFERENCES app_user(id),
                ADD COLUMN updated_by UUID REFERENCES app_user(id)
            """)
            
            print("✅ Columns added successfully!")
        else:
            print("\nℹ️  User tracking columns already exist.")
    
    except asyncpg.exceptions.UndefinedTableError:
        print("\nℹ️  Table 'app_user' doesn't exist yet. Will be created on first startup.")
    except Exception as e:
        print(f"\n⚠️  Migration note: {e}")
    finally:
        await conn.close()


async def main():
    """Run all setup steps."""
    print("=" * 60)
    print("Ad Manager Database Setup")
    print("=" * 60)
    
    try:
        await create_database()
        await add_user_tracking_columns()
        print("\n✅ Setup complete! You can now start the application with:")
        print("   uvicorn main:app --reload")
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check your .env file has a valid DB_URL")
        print(f"   DB_URL={settings.DB_URL}")
        print("3. Make sure the postgres superuser password is correct")


if __name__ == "__main__":
    asyncio.run(main())
