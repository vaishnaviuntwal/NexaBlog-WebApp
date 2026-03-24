from app import app, db
import os

def reset_database():
    with app.app_context():
        print("🗑️ Removing old database...")
        
        db_file = 'instance/site.db'
        if os.path.exists(db_file):
            os.remove(db_file)
            print(f"✅ Removed {db_file}")
        
        db_file_root = 'site.db'
        if os.path.exists(db_file_root):
            os.remove(db_file_root)
            print(f"✅ Removed {db_file_root}")
        
        print("🔄 Creating new database with updated schema...")
        db.create_all()
        
        print("✅ Database reset completed successfully!")
        print("🎯 You can now run: python app.py")

if __name__ == '__main__':
    reset_database()