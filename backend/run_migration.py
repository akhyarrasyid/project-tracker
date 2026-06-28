import sys

from alembic import command
from alembic.config import Config

print("Starting migration...", flush=True)

print("DATABASE_URL loaded, running upgrade...", flush=True)


def main() -> None:
    cfg = Config("alembic.ini")
    command.upgrade(cfg, "head")
    print("Migration completed successfully.", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"Migration failed: {exc}", file=sys.stderr, flush=True)
        raise
