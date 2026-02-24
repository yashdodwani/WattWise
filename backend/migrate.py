#!/usr/bin/env python
"""Database migration script to add authentication columns to users table"""

from sqlalchemy import text
from db.session import engine

def migrate_users_table():
    """Add auth columns to existing users table"""

    with engine.connect() as connection:
        # Check if columns already exist
        result = connection.execute(
            text("""
                SELECT column_name FROM information_schema.columns 
                WHERE table_name = 'users' AND column_name = 'username'
            """)
        )

        if result.fetchone():
            print("✅ Authentication columns already exist!")
            return

        print("🔄 Adding authentication columns to users table...")

        try:
            # Add username column
            connection.execute(text("""
                ALTER TABLE users ADD COLUMN username VARCHAR UNIQUE
            """))
            print("✅ Added username column")

            # Add password_hash column
            connection.execute(text("""
                ALTER TABLE users ADD COLUMN password_hash VARCHAR
            """))
            print("✅ Added password_hash column")

            # Add phone_number column
            connection.execute(text("""
                ALTER TABLE users ADD COLUMN phone_number VARCHAR UNIQUE NOT NULL DEFAULT 'unknown'
            """))
            print("✅ Added phone_number column")

            # Add consumer_number column
            connection.execute(text("""
                ALTER TABLE users ADD COLUMN consumer_number VARCHAR UNIQUE NOT NULL DEFAULT 'unknown'
            """))
            print("✅ Added consumer_number column")

            # Add is_active column
            connection.execute(text("""
                ALTER TABLE users ADD COLUMN is_active BOOLEAN DEFAULT TRUE
            """))
            print("✅ Added is_active column")

            # Add created_at column
            connection.execute(text("""
                ALTER TABLE users ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            """))
            print("✅ Added created_at column")

            connection.commit()
            print("\n✅ Migration completed successfully!")

        except Exception as e:
            connection.rollback()
            print(f"❌ Migration failed: {e}")
            raise


def create_otp_table():
    """Create OTP records table if it doesn't exist"""

    with engine.connect() as connection:
        try:
            connection.execute(text("""
                CREATE TABLE IF NOT EXISTS otp_records (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL REFERENCES users(id),
                    otp_code VARCHAR NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    expires_at TIMESTAMP NOT NULL,
                    is_used BOOLEAN DEFAULT FALSE
                )
            """))
            connection.commit()
            print("✅ OTP records table created/verified")
        except Exception as e:
            print(f"⚠️  OTP table creation warning: {e}")


if __name__ == "__main__":
    print("=" * 60)
    print("🔄 WattWise Database Migration Script")
    print("=" * 60)
    print()

    try:
        migrate_users_table()
        print()
        create_otp_table()
        print()
        print("=" * 60)
        print("✅ DATABASE MIGRATION COMPLETE")
        print("=" * 60)
        print("\nYou can now start the server:")
        print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")

    except Exception as e:
        print()
        print("=" * 60)
        print(f"❌ MIGRATION FAILED: {e}")
        print("=" * 60)
        exit(1)

