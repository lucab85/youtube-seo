"""Database setup utility."""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.models import init_db
from src.utils.logger import setup_logger, get_logger

setup_logger()
logger = get_logger('db_setup')


def main():
    """Initialize database tables."""
    try:
        logger.info("Initializing database...")
        init_db()
        logger.info("Database initialized successfully!")
        print("\n✅ Database setup complete!")
        print("You can now run: python main.py --url <youtube_url>")
        return 0
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        print(f"\n❌ Database setup failed: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
