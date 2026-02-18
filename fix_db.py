#Yong jun , 252176E, group4 
import sqlite3

def add_missing_columns():
    db_path = 'custom_design.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    print(f"Checking database: {db_path}...")
    
    try:
        # Try to add date_of_birth column
        cursor.execute("ALTER TABLE users ADD COLUMN date_of_birth TEXT")
        print("✅ Successfully added 'date_of_birth' column.")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("ℹ️ 'date_of_birth' column already exists.")
        else:
            print(f"❌ Error adding 'date_of_birth': {e}")
            
    try:
        # Try to add phone column if missing
        cursor.execute("ALTER TABLE users ADD COLUMN phone TEXT")
        print("✅ Successfully added 'phone' column.")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("ℹ️ 'phone' column already exists.")

    try:
        # Try to add address column if missing
        cursor.execute("ALTER TABLE users ADD COLUMN address TEXT")
        print("✅ Successfully added 'address' column.")
    except sqlite3.OperationalError as e:
        if "duplicate column" in str(e):
            print("ℹ️ 'address' column already exists.")

    conn.commit()
    conn.close()
    print("Database update complete.")

if __name__ == "__main__":
    add_missing_columns()