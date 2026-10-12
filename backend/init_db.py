"""Non-destructive schema/seed initialization used by Windows and manual setups."""
from app.database import Base, SessionLocal, engine
from app.db_compat import ensure_legacy_schema_compat
from app.migrations import run_startup_migrations
from app.main import _seed_system_config
from app.api.v1.auth import seed_admin

if __name__ == "__main__":
    Base.metadata.create_all(engine)
    ensure_legacy_schema_compat(engine)
    run_startup_migrations(engine)
    with SessionLocal() as db:
        seed_admin(db)
        _seed_system_config(db)
    print("Database schema, migrations and initial configuration are ready.")
