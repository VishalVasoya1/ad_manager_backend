"""
Database setup script - creates the database and runs migrations for new columns.
Run this with PostgreSQL superuser credentials.
"""

import asyncio
import asyncpg
from app.config.settings import settings


async def create_database():
    """Create the database if it doesn't exist using postgres superuser."""
    print("\n⚠️  You need PostgreSQL superuser credentials to create the database.")
    print("Please enter your PostgreSQL superuser credentials:")
    postgres_user = input("PostgreSQL username (default: postgres): ").strip() or "postgres"
    postgres_password = input("PostgreSQL password: ").strip()
    
    # Connect to the default 'postgres' database to create our database
    conn = await asyncpg.connect(
        user=postgres_user,
        password=postgres_password,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database='postgres'
    )
    
    try:
        # Check if database exists
        exists = await conn.fetchval(
            "SELECT 1 FROM pg_database WHERE datname = $1",
            settings.DB_NAME
        )
        
        if not exists:
            # Create database
            await conn.execute(f'CREATE DATABASE {settings.DB_NAME}')
            print(f"✅ Database '{settings.DB_NAME}' created successfully!")
            
            # Grant privileges to app user
            await conn.execute(f'GRANT ALL PRIVILEGES ON DATABASE {settings.DB_NAME} TO {settings.DB_USER}')
            print(f"✅ Granted privileges to '{settings.DB_USER}'")
        else:
            print(f"ℹ️  Database '{settings.DB_NAME}' already exists.")
    finally:
        await conn.close()


async def add_user_tracking_columns():
    """Add created_by and updated_by columns to app_user table if they don't exist."""
    conn = await asyncpg.connect(
        user=settings.DB_USER,
        password=settings.DB_PASSWORD,
        host=settings.DB_HOST,
        port=settings.DB_PORT,
        database=settings.DB_NAME
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
        print("2. Check your .env file has correct credentials:")
        print(f"   DB_USER={settings.DB_USER}")
        print(f"   DB_HOST={settings.DB_HOST}")
        print(f"   DB_PORT={settings.DB_PORT}")
        print(f"   DB_NAME={settings.DB_NAME}")
        print("3. Make sure the postgres superuser password is correct")


if __name__ == "__main__":
    asyncio.run(main())
