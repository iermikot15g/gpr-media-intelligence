import sys
import time
from pathlib import Path
from urllib.robotparser import RobotFileParser
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

# Memastikan modul app dapat ditemukan saat file dijalankan langsung.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from app import collector


BASE_URL = "https://www.memoonline.co.id"
MAX_SITEMAPS = 3
MAX_SITEMAP_URLS = 15
MAX_ARTICLES = 5


def print_section(title):
    print()
    print("=" * 75)
    print(title)
    print("=" * 75)


def load_robots(client, base_url):
    robots_url = urljoin(base_url, "/robots.txt")
    parser = RobotFileParser()
    parser.set_url(robots_url)

    try:
        response = client.get(robots_url)

        print(f"URL robots.txt : {robots_url}")
        print(f"HTTP status    : {response.status_code}")

        if response.status_code == 200:
            parser.parse(response.text.splitlines())
            return parser, True

        parser.parse(["User-agent: *", "Disallow: /"])
        return parser, False

    except httpx.HTTPError as exc:
        print(f"Gagal membaca robots.txt: {exc}")
        parser.parse(["User-agent: *", "Disallow: /"])
        return parser, False

def is_article_candidate_url(url, base_url):
    """
    Menentukan apakah URL layak diuji sebagai artikel.

    Untuk MEMO Online, artikel menggunakan pola /berita/<slug>.
    Untuk media lain, gunakan filter umum collector.
    """
    if not collector.is_same_domain(url, base_url):
        return False

    if collector.is_non_article_url(url):
        return False

    hostname = (urlparse(base_url).hostname or "").removeprefix("www.")
    path = urlparse(url).path.rstrip("/")

    if hostname == "memoonline.co.id":
        return path.startswith("/berita/") and len(path.split("/")) >= 3

    return True

def inspect_sitemaps(client, base_url, robots):
    sitemap_urls = collector.discover_sitemaps(
        client,
        base_url,
        robots,
    )

    print(f"Sitemap ditemukan : {len(sitemap_urls)}")

    queue = list(sitemap_urls)
    visited = set()
    article_urls = []
    rejected_count = 0

    while queue and len(visited) < MAX_SITEMAPS:
        sitemap_url = queue.pop(0)

        if sitemap_url in visited:
            continue

        visited.add(sitemap_url)

        if not robots.can_fetch(
            collector.USER_AGENT,
            sitemap_url,
        ):
            print(f"  Diblokir robots.txt: {sitemap_url}")
            continue

        try:
            response = client.get(sitemap_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "xml")

            # Sitemap index: masukkan alamat sitemap anak.
            for sitemap in soup.find_all("sitemap"):
                loc = sitemap.find("loc")

                if loc and loc.text:
                    child_url = loc.text.strip()

                    if child_url not in visited:
                        queue.append(child_url)

            # Sitemap biasa: prioritaskan URL artikel yang valid.
            for item in soup.find_all("url"):
                loc = item.find("loc")

                if not loc or not loc.text:
                    continue

                article_url = loc.text.strip()

                if not is_article_candidate_url(
                    article_url,
                    base_url,
                ):
                    rejected_count += 1
                    continue

                if not robots.can_fetch(
                    collector.USER_AGENT,
                    article_url,
                ):
                    rejected_count += 1
                    continue

                article_urls.append({
                    "url": article_url,
                    "title": None,
                    "date": None,
                    "date_source": "sitemap_lastmod",
                })

                # Batas diterapkan setelah penyaringan URL.
                if len(article_urls) >= MAX_SITEMAP_URLS:
                    break

            print(
                f"  Sitemap OK: {sitemap_url} "
                f"(HTTP {response.status_code})"
            )

        except httpx.HTTPError as exc:
            print(f"  Sitemap gagal: {sitemap_url} | {exc}")

        if len(article_urls) >= MAX_SITEMAP_URLS:
            break

    print(f"URL sitemap ditolak: {rejected_count}")

    return article_urls, visited

def run_validation(base_url):
    base_url = base_url.rstrip("/")
    hostname = urlparse(base_url).hostname

    print_section("GPR MEDIA INTELLIGENCE - SOURCE VALIDATOR")
    print(f"Domain : {hostname}")
    print(f"URL    : {base_url}")
    print("Mode   : READ ONLY")

    headers = {
        "User-Agent": collector.USER_AGENT,
    }

    with httpx.Client(
        headers=headers,
        timeout=collector.REQUEST_TIMEOUT,
        follow_redirects=True,
    ) as client:

        # --------------------------------------------------
        # 1. Pemeriksaan koneksi homepage
        # --------------------------------------------------
        print_section("1. KONEKSI WEBSITE")

        try:
            homepage = client.get(base_url)
            homepage.raise_for_status()

            print(f"HTTP status : {homepage.status_code}")
            print(f"URL akhir   : {homepage.url}")
            print(f"Ukuran HTML : {len(homepage.text)} karakter")

        except httpx.HTTPError as exc:
            print(f"Website tidak dapat diakses: {exc}")
            return

        # --------------------------------------------------
        # 2. Pemeriksaan robots.txt
        # --------------------------------------------------
        print_section("2. ROBOTS.TXT")

        robots, robots_available = load_robots(
            client,
            base_url,
        )

        homepage_allowed = robots.can_fetch(
            collector.USER_AGENT,
            base_url,
        )

        print(f"Robots tersedia : {robots_available}")
        print(f"Homepage boleh diakses menurut robots: {homepage_allowed}")

        if not robots_available or not homepage_allowed:
            print()
            print(
                "VALIDASI DIHENTIKAN: aturan robots.txt tidak "
                "memungkinkan pemeriksaan lanjutan."
            )
            return

        # --------------------------------------------------
        # 3. Penemuan RSS
        # --------------------------------------------------
        print_section("3. PENEMUAN RSS / ATOM")

        feed_urls = collector.discover_rss_urls(
            client,
            base_url,
        )

        print(f"Alamat feed ditemukan: {len(feed_urls)}")

        for feed_url in feed_urls:
            print(f"  - {feed_url}")

        rss_candidates = collector.collect_rss_urls(
            client,
            feed_urls,
            base_url,
            robots,
        )

        print(f"\nKandidat artikel dari RSS: {len(rss_candidates)}")

        if rss_candidates:
            published_count = sum(
                1
                for item in rss_candidates
                if item.get("date") is not None
            )

            print(
                "RSS dengan tanggal published: "
                f"{published_count}"
            )

        # --------------------------------------------------
        # 4. Pemeriksaan sitemap
        # --------------------------------------------------
        print_section("4. PEMERIKSAAN SITEMAP")

        sitemap_candidates, checked_sitemaps = inspect_sitemaps(
            client,
            base_url,
            robots,
        )

        print(f"\nFile sitemap diperiksa: {len(checked_sitemaps)}")
        print(f"Kandidat URL sitemap : {len(sitemap_candidates)}")

        # --------------------------------------------------
        # 5. Penggabungan dan penyaringan kandidat
        # --------------------------------------------------
        print_section("5. PENYARINGAN URL")

        candidates = {}

        for item in rss_candidates:
            url = item.get("url")

            if url:
                key = collector.normalize_url(url)
                candidates[key] = {
                    **item,
                    "discovery": "RSS",
                }

        for item in sitemap_candidates:
            url = item.get("url")

            if url:
                key = collector.normalize_url(url)

                if key not in candidates:
                    candidates[key] = {
                        **item,
                        "discovery": "Sitemap",
                    }

        valid_candidates = []
        rejected_count = 0
        blocked_count = 0

        for item in candidates.values():
            url = item["url"]

            if not is_article_candidate_url(url, base_url):
                rejected_count += 1
                continue

            if not robots.can_fetch(
                collector.USER_AGENT,
                url,
            ):
                blocked_count += 1
                continue

            valid_candidates.append(item)

        print(f"Total URL unik       : {len(candidates)}")
        print(f"Ditolak sebagai indeks/kategori: {rejected_count}")
        print(f"Diblokir robots.txt  : {blocked_count}")
        print(f"Kandidat lolos filter: {len(valid_candidates)}")

        # Prioritaskan RSS yang memiliki tanggal publikasi.
        valid_candidates.sort(
            key=lambda item: (
                item.get("date") is not None,
                item.get("discovery") == "RSS",
            ),
            reverse=True,
        )

        samples = valid_candidates[:MAX_ARTICLES]

        # --------------------------------------------------
        # 6. Pengujian ekstraksi artikel
        # --------------------------------------------------
        print_section("6. UJI EKSTRAKSI ARTIKEL")

        successful = 0
        failed = 0
        metadata_dates = 0
        qualified_articles = 0
        content_lengths = []

        if not samples:
            print("Tidak ada kandidat yang lolos filter.")

        for index, item in enumerate(samples, start=1):
            url = item["url"]

            print()
            print(f"ARTIKEL {index}")
            print("-" * 75)
            print(f"URL       : {url}")
            print(f"Sumber URL: {item.get('discovery')}")

            rss_date = item.get("date")
            print(f"RSS title : {item.get('title')}")
            print(f"RSS date  : {rss_date}")
            print(f"RSS date source: {item.get('date_source')}")

            try:
                if index > 1:
                    time.sleep(collector.REQUEST_DELAY)

                article = collector.extract_article(
                    client,
                    url,
                    max_attempts=1,
                )

                if not article:
                    failed += 1
                    print("Hasil ekstraksi: GAGAL - konten tidak ditemukan")
                    continue

                title = article.get("title")
                content = article.get("content") or ""
                published_at = article.get("published_at")

                content_length = len(content)
                content_lengths.append(content_length)

                if published_at:
                    metadata_dates += 1

                has_title = bool(title and title.strip())
                has_sufficient_content = content_length >= 500
                has_publication_date = published_at is not None

                if (
                    has_title
                    and has_sufficient_content
                    and has_publication_date
                ):
                    qualified_articles += 1

                successful += 1

                print(f"Judul       : {title}")
                print(f"Tanggal halaman: {published_at}")
                print(f"Panjang isi : {content_length} karakter")
                print(f"Penulis     : {article.get('author')}")
                print(f"Judul valid       : {has_title}")
                print(f"Konten memadai    : {has_sufficient_content}")
                print(f"Tanggal publikasi : {has_publication_date}")
                print(f"Deskripsi   : {article.get('description')}")

                print(
                    "Hasil ekstraksi: "
                    + (
                        "BERHASIL"
                        if content_length >= 500
                        else "PERLU DITINJAU - konten pendek"
                    )
                )

            except Exception as exc:
                failed += 1
                print(f"Hasil ekstraksi: GAGAL - {exc}")

        # --------------------------------------------------
        # 7. Ringkasan dan rekomendasi
        # --------------------------------------------------
        print_section("7. RINGKASAN VALIDASI")

        print(f"Domain                  : {hostname}")
        print(f"RSS ditemukan           : {len(feed_urls)}")
        print(f"Kandidat RSS            : {len(rss_candidates)}")
        print(f"Kandidat sitemap        : {len(sitemap_candidates)}")
        print(f"Kandidat lolos filter   : {len(valid_candidates)}")
        print(f"Artikel diuji           : {len(samples)}")
        print(f"Ekstraksi berhasil      : {successful}")
        print(f"Ekstraksi gagal         : {failed}")
        print(f"Tanggal metadata halaman: {metadata_dates}")
        print(f"Artikel memenuhi kriteria: {qualified_articles}")

        if content_lengths:
            average_length = sum(content_lengths) // len(content_lengths)
            print(f"Rata-rata panjang konten: {average_length} karakter")

        if qualified_articles >= 3 and len(valid_candidates) >= 3:
            recommendation = (
                "LAYAK UNTUK UJI COBA INTEGRASI TERBATAS"
            )
        elif successful >= 1:
            recommendation = (
                "PERLU PEMERIKSAAN LANJUTAN SEBELUM INTEGRASI"
            )
        else:
            recommendation = (
                "BELUM LAYAK DIINTEGRASIKAN"
            )

        print()
        print(f"REKOMENDASI: {recommendation}")
        print()
        print("Catatan: hasil ini merupakan validasi teknis awal,")
        print("bukan persetujuan otomatis untuk mengaktifkan sumber.")


if __name__ == "__main__":
    run_validation(BASE_URL)
