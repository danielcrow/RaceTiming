#!/usr/bin/env python3
"""
Database Migration Script: Add Tag Detection Mode Fields
Adds detection_mode and detection_window_seconds to timing_points table
"""
from sqlalchemy import text
from database import get_session, engine
from models import Base, TagDetectionMode
import sys


def check_columns_exist():
    """Check if the new columns already exist"""
    session = get_session()
    try:
        result = session.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'timing_points' 
            AND column_name IN ('detection_mode', 'detection_window_seconds')
        """))
        existing_columns = [row[0] for row in result]
        return existing_columns
    except Exception as e:
        print(f"Error checking columns: {e}")
        return []
    finally:
        session.close()


def migrate_database():
    """Add detection mode fields to timing_points table"""
    print("=" * 60)
    print("Tag Detection Mode Migration")
    print("=" * 60)
    
    # Check if columns already exist
    existing = check_columns_exist()
    
    if 'detection_mode' in existing and 'detection_window_seconds' in existing:
        print("✓ Migration already applied - columns exist")
        return True
    
    session = get_session()
    
    try:
        print("\n1. Adding detection_mode column...")
        if 'detection_mode' not in existing:
            session.execute(text("""
                ALTER TABLE timing_points
                ADD COLUMN detection_mode VARCHAR(20) DEFAULT 'FIRST_SEEN' NOT NULL
            """))
            print("   ✓ detection_mode column added")
        else:
            print("   ✓ detection_mode column already exists")
        
        print("\n2. Adding detection_window_seconds column...")
        if 'detection_window_seconds' not in existing:
            session.execute(text("""
                ALTER TABLE timing_points 
                ADD COLUMN detection_window_seconds INTEGER DEFAULT 3
            """))
            print("   ✓ detection_window_seconds column added")
        else:
            print("   ✓ detection_window_seconds column already exists")
        
        session.commit()
        
        print("\n3. Verifying migration...")
        result = session.execute(text("""
            SELECT COUNT(*) FROM timing_points
        """))
        count = result.scalar()
        print(f"   ✓ {count} timing points updated with default values")
        
        print("\n" + "=" * 60)
        print("Migration completed successfully!")
        print("=" * 60)
        print("\nDefault values applied:")
        print("  - detection_mode: FIRST_SEEN")
        print("  - detection_window_seconds: 3")
        print("\nYou can now configure detection modes per timing point.")
        print("See TAG_DETECTION_MODES.md for configuration guide.")
        
        return True
        
    except Exception as e:
        session.rollback()
        print(f"\n✗ Migration failed: {e}")
        print("\nPlease check your database connection and try again.")
        return False
        
    finally:
        session.close()


def rollback_migration():
    """Remove detection mode fields (rollback)"""
    print("=" * 60)
    print("Rolling back Tag Detection Mode Migration")
    print("=" * 60)
    
    session = get_session()
    
    try:
        print("\n1. Removing detection_mode column...")
        session.execute(text("""
            ALTER TABLE timing_points 
            DROP COLUMN IF EXISTS detection_mode
        """))
        print("   ✓ detection_mode column removed")
        
        print("\n2. Removing detection_window_seconds column...")
        session.execute(text("""
            ALTER TABLE timing_points 
            DROP COLUMN IF EXISTS detection_window_seconds
        """))
        print("   ✓ detection_window_seconds column removed")
        
        session.commit()
        
        print("\n" + "=" * 60)
        print("Rollback completed successfully!")
        print("=" * 60)
        
        return True
        
    except Exception as e:
        session.rollback()
        print(f"\n✗ Rollback failed: {e}")
        return False
        
    finally:
        session.close()


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        success = rollback_migration()
    else:
        success = migrate_database()
    
    sys.exit(0 if success else 1)

# Made with Bob
