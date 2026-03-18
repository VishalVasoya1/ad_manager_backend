"""
Combined migration script for bulk operations feature.
Runs all required migrations:
1. Add type_value column to ad_field table
2. Update user_activity constraint to allow bulk operations
"""

import asyncio
import asyncpg
from app.config.setting import settings


async def run_all_migrations():
    """Run all migrations for bulk operations feature."""
    db_user, db_password, db_host, db_port, db_name = settings.DB_PARSED

    print("\n" + "=" * 70)
    print("Running All Migrations for Bulk Operations Feature")
    print("=" * 70)

    try:
        conn = await asyncpg.connect(
            user=db_user,
            password=db_password,
            host=db_host,
            port=db_port,
            database=db_name
        )
        
        print(f"\n✅ Connected to database '{db_name}'")
        
        # Migration 1: Add type_value column to ad_field
        print("\n" + "-" * 70)
        print("Migration 1: Add type_value column to ad_field table")
        print("-" * 70)
        
        column_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.columns 
                WHERE table_name = 'ad_field' 
                AND column_name = 'type_value'
            )
        """)
        
        if column_exists:
            print("ℹ️  Column 'type_value' already exists in ad_field table.")
        else:
            print("📝 Adding 'type_value' column to ad_field table...")
            await conn.execute("""
                ALTER TABLE ad_field
                ADD COLUMN type_value TEXT NULL
            """)
            print("✅ Column 'type_value' added successfully!")
        
        # Migration 2: Update user_activity constraint
        print("\n" + "-" * 70)
        print("Migration 2: Update user_activity action constraint")
        print("-" * 70)
        
        constraint_exists = await conn.fetchval("""
            SELECT EXISTS (
                SELECT 1 
                FROM information_schema.table_constraints 
                WHERE table_name = 'user_activity' 
                AND constraint_name = 'ck_user_activity_action'
            )
        """)
        
        if not constraint_exists:
            print("ℹ️  Constraint doesn't exist. Creating new constraint...")
            await conn.execute("""
                ALTER TABLE user_activity
                ADD CONSTRAINT ck_user_activity_action
                CHECK (action IN ('create','update','delete','view','login','logout','bulk_create','bulk_update','bulk_delete'))
            """)
            print("✅ Constraint created successfully!")
        else:
            print("📝 Updating constraint to include bulk operations...")
            
            # Drop the old constraint
            await conn.execute("""
                ALTER TABLE user_activity
                DROP CONSTRAINT ck_user_activity_action
            """)
            print("   ✓ Old constraint dropped")
            
            # Create the new constraint
            await conn.execute("""
                ALTER TABLE user_activity
                ADD CONSTRAINT ck_user_activity_action
                CHECK (action IN ('create','update','delete','view','login','logout','bulk_create','bulk_update','bulk_delete'))
            """)
            print("   ✓ New constraint created")
            print("✅ Constraint updated successfully!")
        
        await conn.close()
        
        print("\n" + "=" * 70)
        print("✅ All migrations completed successfully!")
        print("=" * 70)
        print("\nNew features available:")
        print("  ✓ type_value column in ad_field table")
        print("  ✓ Bulk create ad_fields: POST /admin/ads/v1/adfield/bulk")
        print("  ✓ Bulk update ad_fields: PUT /admin/ads/v1/adfield/bulk")
        print("  ✓ Bulk delete ad_fields: DELETE /admin/ads/v1/adfield/bulk")
        print("\nRestart your application:")
        print("  uvicorn main:app --reload")
        
    except asyncpg.exceptions.UndefinedTableError as e:
        print(f"\n❌ Error: Required table doesn't exist: {e}")
        print("Please start your application first to create all tables:")
        print("   uvicorn main:app --reload")
    except Exception as e:
        print(f"\n❌ Migration failed: {e}")
        print("\nTroubleshooting:")
        print("1. Make sure PostgreSQL is running")
        print("2. Make sure the database exists")
        print("3. Check your .env file has a valid DB_URL")
        print(f"   Current DB_URL: {settings.DB_URL}")
        raise


if __name__ == "__main__":
    asyncio.run(run_all_migrations())
