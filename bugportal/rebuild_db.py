# bugportal/rebuild_db.py
import os
from app.db import init_db, DB_PATH
from app.repositories import import_data_if_empty

if __name__ == "__main__":
    if os.path.exists(DB_PATH):
        print(f"Deleting old database: {DB_PATH}")
        os.remove(DB_PATH)
    
    print("Initializing database...")
    init_db()
    
    print("Importing data...")
    import_data_if_empty()
    
    print("Done! Database rebuilt successfully.")