"""
Seed database with test data
"""
import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from models import AsyncSessionLocal
from models.models import Professor, Student


async def seed_data():
    """Seed database with test professor and students"""
    async with AsyncSessionLocal() as db:
        try:
            # Create test professor
            professor = Professor(
                name="Dr. Sarah Johnson",
                email="sarah.johnson@university.edu",
                zoom_user_id="sarah.johnson@university.edu",  # Use email as Zoom user ID
                heygen_avatar_id="prof_avatar_001"
            )
            db.add(professor)

            # Create test students
            students = [
                Student(name="Alice Chen", email="alice.chen@student.edu", zoom_user_id="alice.chen@student.edu"),
                Student(name="Bob Martinez", email="bob.martinez@student.edu", zoom_user_id="bob.martinez@student.edu"),
                Student(name="Charlie Kim", email="charlie.kim@student.edu", zoom_user_id="charlie.kim@student.edu"),
                Student(name="Diana Patel", email="diana.patel@student.edu", zoom_user_id="diana.patel@student.edu"),
                Student(name="Ethan Wong", email="ethan.wong@student.edu", zoom_user_id="ethan.wong@student.edu"),
            ]

            for student in students:
                db.add(student)

            await db.commit()

            print("✓ Database seeded successfully!")
            print(f"  - Created 1 professor: {professor.name}")
            print(f"  - Created {len(students)} students")

        except Exception as e:
            print(f"Error seeding database: {e}")
            await db.rollback()


if __name__ == "__main__":
    asyncio.run(seed_data())
