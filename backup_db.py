import shutil
import os
from datetime import datetime

# Configuration
DB_PATH = "Data/history.db"
BACKUP_DIR = "backups"
MAX_BACKUPS = 5

def backup_database():
    """
    Creates a backup of the SQLite database.
    Retains only the last MAX_BACKUPS files.
    """
    if not os.path.exists(DB_PATH):
        print(f"Database not found at {DB_PATH}")
        return

    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR)
        print(f"Created backup directory: {BACKUP_DIR}")

    # Create backup with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"history_{timestamp}.db"
    backup_path = os.path.join(BACKUP_DIR, backup_filename)

    try:
        shutil.copy2(DB_PATH, backup_path)
        print(f"✅ Backup created successfully: {backup_path}")
        
        # Cleanup old backups
        manage_retention()
        
    except Exception as e:
        print(f"❌ Backup failed: {e}")

def manage_retention():
    """Removes oldest backups if count exceeds MAX_BACKUPS"""
    try:
        backups = sorted(
            [os.path.join(BACKUP_DIR, f) for f in os.listdir(BACKUP_DIR) if f.endswith('.db')],
            key=os.path.getmtime
        )
        
        while len(backups) > MAX_BACKUPS:
            oldest = backups.pop(0)
            os.remove(oldest)
            print(f"🗑️ Removed old backup: {oldest}")
            
    except Exception as e:
        print(f"⚠️ Error managing retention: {e}")

if __name__ == "__main__":
    print(f"Starting backup process for {DB_PATH}...")
    backup_database()
