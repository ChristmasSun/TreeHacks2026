"""
Database initialization script
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import models
sys.path.append(str(Path(__file__).parent.parent))

from models import init_db, drop_db


async def main():
    """Initialize the database"""
    print("Initializing database...")
    await init_db()
    print("✓ Database initialized successfully!")
    print("Tables created:")
    print("  - professors")
    print("  - students")
    print("  - sessions")
    print("  - breakout_rooms")
    print("  - transcripts")
    print("  - student_progress")
    print("  - context_documents")
    print("  - session_analytics")


async def reset():
    """Drop and recreate all tables"""
    print("WARNING: This will delete all data!")
    response = input("Are you sure? (yes/no): ")
    if response.lower() == "yes":
        print("Dropping tables...")
        await drop_db()
        print("Creating tables...")
        await init_db()
        print("✓ Database reset successfully!")
    else:
        print("Operation cancelled.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--reset":
        asyncio.run(reset())
    else:
        asyncio.run(main())
