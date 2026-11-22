"""Idempotent additive migration for source validation workflow."""
from sqlalchemy import inspect, text
from app.database import engine
from app.models import Base


def migrate():
    Base.metadata.create_all(bind=engine)
    inspector = inspect(engine)
    columns = {item["name"] for item in inspector.get_columns("media_sources")}
    additions = {
        "validation_status": "VARCHAR(30) NOT NULL DEFAULT 'not_tested'",
        "validated_at": "DATETIME",
        "validation_config": "TEXT",
        "validation_report": "TEXT",
    }
    with engine.begin() as connection:
        for name, definition in additions.items():
            if name not in columns:
                connection.execute(text(
                    f"ALTER TABLE media_sources ADD COLUMN {name} {definition}"
                ))
    Base.metadata.create_all(bind=engine)
    print("Migrasi validasi sumber media berhasil.")


if __name__ == "__main__":
    migrate()
