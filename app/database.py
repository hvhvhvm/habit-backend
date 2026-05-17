from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker,declarative_base
import os
from dotenv import load_dotenv
load_dotenv()
print(os.getenv("DATABASE_URL"))
import logging


logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SQLITE_PATH = PROJECT_ROOT / "habits.db"
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DEFAULT_SQLITE_PATH.as_posix()}")

if SQLALCHEMY_DATABASE_URL.startswith("postgres://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgres://", "postgresql+psycopg://", 1)
elif SQLALCHEMY_DATABASE_URL.startswith("postgresql://"):
    SQLALCHEMY_DATABASE_URL = SQLALCHEMY_DATABASE_URL.replace("postgresql://", "postgresql+psycopg://", 1)

# ── Startup diagnostics ──
_is_sqlite = SQLALCHEMY_DATABASE_URL.startswith("sqlite")
_is_production = bool(os.getenv("RENDER") or os.getenv("PORT"))

if _is_sqlite:
    logger.warning("⚠️  DATABASE: Using SQLite at %s", DEFAULT_SQLITE_PATH)
    if _is_production:
        logger.critical(
            "🚨 CRITICAL: SQLite is being used in PRODUCTION! "
            "Data WILL be lost on every restart. "
            "Set the DATABASE_URL environment variable to a PostgreSQL connection string."
        )
    print(f"DATABASE: SQLite - {DEFAULT_SQLITE_PATH}")
else:
    # Mask the connection string for safety (don't log passwords)
    _masked = SQLALCHEMY_DATABASE_URL.split("@")[-1] if "@" in SQLALCHEMY_DATABASE_URL else "configured"
    logger.info("DATABASE: PostgreSQL - %s", _masked)
    print(f"DATABASE: PostgreSQL - {_masked}")

# ── Engine configuration ──
connect_args = {}
engine_kwargs = {}

if _is_sqlite:
    connect_args = {"check_same_thread": False}
else:
    # Supabase / any PostgreSQL pooler: disable prepared statements
    # (PgBouncer in transaction mode doesn't support them)
    connect_args = {"prepare_threshold": 0}
    # Auto-reconnect stale connections (important after Render cold starts)
    engine_kwargs = {"pool_pre_ping": True}

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs,
)
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)
Base = declarative_base()
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

