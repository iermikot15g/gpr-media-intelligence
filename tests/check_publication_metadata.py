
import logging
import time

import httpx

from app.collector import (
    USER_AGENT,
    REQUEST_TIMEOUT,
    REQUEST_DELAY,
    SessionLocal,
    MediaSource,
    get_robots_parser,
    discover_sitemaps,
    collect_sitemap_urls,
    extract_article,
    is_non_article_url,
)


logging.basicConfig(
    level=logging.WARNING,
    format="%(levelname)s: %(message)s",
)

MAX_ARTICLES_PER_SOURCE = 3


def main():
    db = SessionLocal()

    try:
        sources = (
            db.query(MediaSource)
            .filter(MediaSource.is_active.is_(True))
            .order_by(MediaSource.id)
            .all()
        )

        print("\nPEMERIKSAAN METADATA TANGGAL PUBLIKASI")
        print("=" * 75)

        if not sources:
            print("Tidak ada sumber media yang aktif.")
            return

        totals = {
            "tested": 0,
            "found": 0,
            "missing": 0,
            "failed": 0,
            "blocked": 0,
        }

        with httpx.Client(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=True,
            headers={"User-Agent": USER_AGENT},
        ) as client:

            for source in sources:
                base_url = source.base_url.rstrip("/") + "/"

                stats = {
                    "found": 0,
                    "missing": 0,
                    "failed": 0,
                    "blocked": 0,
                }

                print(f"\nSUMBER: {source.name}")
                print(f"URL   : {source.base_url}")

                try:
                    robots = get_robots_parser(
                        client,
                        base_url,
                    )

                    sitemap_urls = discover_sitemaps(
                        client,
                        base_url,
                        robots,
                    )

                    candidates = []

                    for sitemap_url in sitemap_urls:
                        candidates.extend(
                            collect_sitemap_urls(
                                client,
                                sitemap_url,
                                base_url,
                                robots,
                            )
                        )

                    # Hilangkan URL duplikat dan halaman non-artikel.
                    unique_urls = list(dict.fromkeys(
                        item["url"]
                        for item in candidates
                        if (
                            not is_non_article_url(item["url"])
                            and robots.can_fetch(
                                USER_AGENT,
                                item["url"],
                            )
                        )
                    ))

                    print(
                        f"Kandidat sitemap yang diizinkan: "
                        f"{len(unique_urls)}"
                    )

                    if not unique_urls:
                        print(
                            "Tidak ada kandidat yang dapat diuji. "
                            "Periksa sitemap dan robots.txt."
                        )
                        continue

                    tested = 0

                    for article_url in unique_urls:
                        if tested >= MAX_ARTICLES_PER_SOURCE:
                            break

                        if not robots.can_fetch(
                            USER_AGENT,
                            article_url,
                        ):
                            stats["blocked"] += 1
                            continue

                        time.sleep(REQUEST_DELAY)

                        try:
                            article = extract_article(
                                client,
                                article_url,
                            )

                            tested += 1

                            if not article:
                                stats["failed"] += 1
                                print(
                                    f"GAGAL EKSTRAKSI: {article_url}"
                                )
                                continue

                            published_at = article.get("published_at")

                            if published_at:
                                stats["found"] += 1
                                status = "TERBACA"
                            else:
                                stats["missing"] += 1
                                status = "TIDAK DITEMUKAN"

                            print(f"\n{status}")
                            print(
                                f"Judul  : {article.get('title')}"
                            )
                            print(
                                f"Tanggal: {published_at}"
                            )
                            print(f"URL    : {article_url}")

                        except Exception as exc:
                            tested += 1
                            stats["failed"] += 1
                            print(f"GAGAL: {article_url}")
                            print(f"Alasan: {exc}")

                    totals["tested"] += tested

                except Exception as exc:
                    print(f"GAGAL MEMERIKSA SUMBER: {exc}")
                    stats["failed"] += 1

                for key in stats:
                    totals[key] += stats[key]

                print("\nRingkasan sumber:")
                print(f"Metadata terbaca : {stats['found']}")
                print(f"Tanggal kosong   : {stats['missing']}")
                print(f"Gagal             : {stats['failed']}")
                print(f"Diblokir robots   : {stats['blocked']}")

        print("\n" + "=" * 75)
        print("RINGKASAN SELURUH SUMBER")
        print("=" * 75)
        print(f"Artikel diuji     : {totals['tested']}")
        print(f"Metadata terbaca  : {totals['found']}")
        print(f"Tanggal kosong    : {totals['missing']}")
        print(f"Gagal             : {totals['failed']}")
        print(f"Diblokir robots   : {totals['blocked']}")

        print("\nPemeriksaan selesai. Tidak ada artikel yang disimpan.")

    finally:
        db.close()


if __name__ == "__main__":
    main()
