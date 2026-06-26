import json
import sys
from sqlalchemy.orm import Session
from database import SessionLocal, Base, engine
from models import Task

def seed_database():
    print("Initializing database tables...")
    Base.metadata.create_all(bind=engine)

    db: Session = SessionLocal()
    try:
        # Check if tasks already exist
        existing_count = db.query(Task).count()
        
        # Check for force flag
        force = "--force" in sys.argv
        
        if existing_count > 0 and not force:
            print(f"Database already contains {existing_count} task(s).")
            print("Use 'python seed.py --force' to clear existing tasks and seed again.")
            return

        if force:
            print("Clearing existing tasks...")
            db.query(Task).delete()
            db.commit()

        print("Reading mock data from seed_tasks.json...")
        with open("seed_tasks.json", "r", encoding="utf-8") as f:
            tasks_data = json.load(f)

        print(f"Seeding {len(tasks_data)} tasks into the database...")
        for t_data in tasks_data:
            task = Task(
                title=t_data["title"],
                description=t_data["description"],
                status=t_data["status"]
            )
            db.add(task)
        
        db.commit()
        print("Database seeded successfully!")
    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
