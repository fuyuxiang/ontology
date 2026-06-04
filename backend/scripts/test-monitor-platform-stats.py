import sys
from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.api.v1.monitor import get_platform_stats


def main() -> None:
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE assets (id VARCHAR(36) PRIMARY KEY, status VARCHAR(20))"))
        conn.execute(text("CREATE TABLE business_rules (id VARCHAR(36) PRIMARY KEY)"))
        conn.execute(text("CREATE TABLE pipelines (id VARCHAR(36) PRIMARY KEY)"))
        conn.execute(text("INSERT INTO assets (id, status) VALUES ('a1', 'active'), ('a2', 'broken')"))
        conn.execute(text("INSERT INTO business_rules (id) VALUES ('r1'), ('r2')"))
        conn.execute(text("INSERT INTO pipelines (id) VALUES ('p1')"))

    session = sessionmaker(bind=engine)()
    try:
        stats = get_platform_stats(session)
    finally:
        session.close()

    assert stats.total_datasources == 1
    assert stats.total_rules == 2
    assert stats.total_pipelines == 1
    print("monitor platform stats handles legacy rule table")


if __name__ == "__main__":
    main()
