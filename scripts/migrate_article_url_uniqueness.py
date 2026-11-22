"""Safely replace the global canonical URL unique index with a per-source index.

Run from the project root:
    python scripts/migrate_article_url_uniqueness.py

Create/verify a database backup before running this migration.
"""

from sqlalchemy import inspect, text

from app.database import engine

OLD_INDEX = "ix_news_articles_canonical_url"
NEW_INDEX = "ix_news_articles_source_canonical_url"


def main():
    inspector = inspect(engine)
    indexes = {item["name"]: item for item in inspector.get_indexes("news_articles")}

    with engine.begin() as connection:
        # Check first: the new composite index cannot be created if legacy rows
        # already contain duplicate canonical URLs within the same source.
        duplicates = connection.execute(text("""
            SELECT source_id, canonical_url, COUNT(*) AS total
            FROM news_articles
            WHERE canonical_url IS NOT NULL
            GROUP BY source_id, canonical_url
            HAVING COUNT(*) > 1
            LIMIT 20
        """)).fetchall()

        if duplicates:
            details = "\n".join(str(tuple(row)) for row in duplicates)
            raise RuntimeError(
                "Migrasi dibatalkan: ditemukan canonical_url ganda pada sumber yang sama.\n"
                + details
            )

        if OLD_INDEX in indexes:
            connection.execute(text(f'DROP INDEX "{OLD_INDEX}"'))

        if NEW_INDEX not in indexes:
            connection.execute(text(
                f'CREATE UNIQUE INDEX "{NEW_INDEX}" '
                'ON news_articles (source_id, canonical_url)'
            ))

    print("Migrasi berhasil.")
    print("Unique index sekarang berlaku untuk kombinasi source_id + canonical_url.")


if __name__ == "__main__":
    main()
