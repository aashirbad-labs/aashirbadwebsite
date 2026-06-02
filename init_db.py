#!/usr/bin/env python
"""
Initialize the database and create necessary directories on first run.
Run this after cloning from GitHub if employees.db doesn't exist.
"""
import sys
import os

# Add the project directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import init_db, DB_PATH

if __name__ == '__main__':
    if not os.path.exists(DB_PATH):
        print(f"📦 Creating database at {DB_PATH}...")
        init_db()
        print("✅ Database initialized successfully!")
    else:
        print(f"✅ Database already exists at {DB_PATH}")
    
    print("\n🎉 Setup complete! Run 'python app.py' to start the application.")
