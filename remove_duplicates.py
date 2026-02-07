import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

try:
    # Try to get from .env first, then use defaults from config.py
    db_host = os.getenv("DB_HOST", "localhost")
    db_name = os.getenv("DB_NAME", "mydb")
    db_user = os.getenv("DB_USER", "admin")
    db_password = os.getenv("DB_PASSWORD", "admin")
    db_port = os.getenv("DB_PORT", "5432")
    
    print(f"Connecting to database: {db_user}@{db_host}:{db_port}/{db_name}")
    
    conn = psycopg2.connect(
        host=db_host,
        database=db_name,
        user=db_user,
        password=db_password,
        port=db_port
    )

    cursor = conn.cursor()
    
    print("=" * 60)
    print("REMOVING DUPLICATE RECORDS FROM DATABASE")
    print("=" * 60)
    
    # Count total records before cleanup
    cursor.execute("SELECT COUNT(*) FROM telegram")
    total_before = cursor.fetchone()[0]
    print(f"\n📊 Total records before cleanup: {total_before}")
    
    # Delete duplicates, keeping only the oldest record for each unique message+time+city
    delete_duplicates_query = """
    DELETE FROM telegram
    WHERE id NOT IN (
        SELECT MIN(id)
        FROM telegram
        GROUP BY message, time, matched_city
    );
    """
    
    cursor.execute(delete_duplicates_query)
    deleted_count = cursor.rowcount
    conn.commit()
    
    # Count records after cleanup
    cursor.execute("SELECT COUNT(*) FROM telegram")
    total_after = cursor.fetchone()[0]
    
    print(f"🗑️  Deleted {deleted_count} duplicate records")
    print(f"✅ Total records after cleanup: {total_after}")
    print(f"\n🎉 Database cleaned successfully!")
    
    cursor.close()
    conn.close()
    
    print("\n📝 Next steps:")
    print("1. Refresh your browser")
    print("2. The duplicate markers should be gone")
    
except Exception as e:
    print(f"❌ Database error: {e}")
