
import hashlib
import json
import logging
import re
import time

from datetime import datetime, date, time as datetime_time, timedelta, timezone
from urllib.parse import (
    urljoin,
    urlparse,
    urlunparse,
    parse_qsl,
    urlencode,
)
from urllib.robotparser import RobotFileParser

import feedparser
import httpx
import trafilatura

from dateutil import parser as date_parser
from sqlalchemy import or_

from app.database import SessionLocal
from app.models import MediaSource, NewsArticle, CollectionRun
from app.source_validation import (
    _extract_homepage_article_urls,
    safe_get as validation_safe_get,
    validate_public_url,
)

from bs4 import BeautifulSoup


logger = logging.getLogger(__name__)

USER_AGENT = "GPRMediaIntelligence/1.0"
REQUEST_TIMEOUT = 20
REQUEST_DELAY = 1
MAX_ARTICLES_PER_SOURCE = 5
MAX_CANDIDATES_PER_SOURCE = 50


def normalize_url(url):
    """Membersihkan URL untuk mengurangi duplikasi."""

    parsed = urlparse(url)

    ignored_params = {
        "utm_source",
        "utm_medium",
        "utm_campaign",
        "utm_term",
        "utm_content",
        "fbclid",
        "gclid",
    }

    query = [
        (key, value)
        for key, value in parse_qsl(parsed.query)
        if key.lower() not in ignored_params
    ]

    return urlunparse((
        parsed.scheme.lower(),
        parsed.netloc.lower(),
        parsed.path.rstrip("/") or "/",
        "",
        urlencode(query),
        "",
    ))


def parse_date(value):
    """Mengubah tanggal dari website menjadi datetime UTC tanpa timezone."""

    if not value:
        return None

    try:
        result = date_parser.parse(str(value))

        if result.tzinfo:
            result = result.astimezone(timezone.utc).replace(tzinfo=None)

        return result

    except (ValueError, TypeError, OverflowError):
        return None


def is_same_domain(url, base_url):
    return urlparse(url).netloc.lower() == urlparse(base_url).netloc.lower()



def is_non_article_url(url):
    """
    Memeriksa URL yang kemungkinan merupakan halaman indeks,
    kategori, atau pencarian, bukan halaman artikel berita.
    """
    parsed = urlparse(url)
    path = parsed.path.lower().rstrip("/")

    if path == "":
        return True

    excluded_prefixes = (
        "/tag/",
        "/category/",
        "/author/",
        "/page/",
        "/search/",
    )

    if any(path.startswith(prefix) for prefix in excluded_prefixes):
        return True

    # Halaman indeks berita Ketikan.
    if path == "/berita":
        return True

    # Halaman kategori dan subkategori KanalNews.
    if path == "/regional" or path.startswith("/regional/"):
        return True

    # Halaman kategori umum KanalNews.
    if path == "/uncategorized":
        return True

    # Halaman kategori KanalNews yang menggunakan slug
    # langsung pada root domain.
    hostname = (parsed.hostname or "").lower()

    # MEMO Online: hanya URL artikel /berita/<slug>.
    if hostname.removeprefix("www.") == "memoonline.co.id":
        if not path.startswith("/berita/"):
            return True

        if len(path.split("/")) < 3:
            return True

    if hostname.removeprefix("www.") == "kanalnews.id":
        kanalnews_categories = {
            "/peristiwa",
            "/kesehatan",
            "/politik",
            "/opini",
            "/tni-polri",
        }

        if path in kanalnews_categories:
            return True

    # URL pencarian.
    if parsed.query and (
        "s=" in parsed.query.lower()
        or "search=" in parsed.query.lower()
    ):
        return True

    return False


def get_robots_parser(client, base_url):
    """Membaca robots.txt melalui pemeriksaan URL dan redirect yang aman."""

    robots_url = urljoin(base_url, "/robots.txt")
    parser = RobotFileParser()
    parser.set_url(robots_url)

    try:
        host = urlparse(base_url).hostname
        response = validation_safe_get(client, robots_url, host)
        if response.status_code == 200:
            parser.parse(response.text.splitlines())
        else:
            # Jika robots.txt tidak tersedia, jangan menganggap
            # seluruh halaman otomatis boleh diakses.
            parser.parse(["User-agent: *", "Disallow: /"])

    except (httpx.HTTPError, ValueError):
        parser.parse(["User-agent: *", "Disallow: /"])

    return parser


def discover_sitemaps(client, base_url, robots):
    """Mencari alamat sitemap melalui robots.txt dan lokasi standar."""

    candidates = []

    for line in robots.site_maps() or []:
        candidates.append(line)

    candidates.extend([
        urljoin(base_url, "/sitemap.xml"),
        urljoin(base_url, "/sitemap_index.xml"),
    ])

    return list(dict.fromkeys(candidates))


def collect_sitemap_urls(
    client,
    sitemap_url,
    base_url,
    robots,
    depth=0,
    max_urls=None,
):
    """Membaca sitemap/index dengan validasi host, DNS publik, dan redirect."""

    if depth > 2:
        return []

    if max_urls is not None and max_urls <= 0:
        return []

    if not robots.can_fetch(USER_AGENT, sitemap_url):
        return []

    try:
        host = urlparse(base_url).hostname
        response = validation_safe_get(client, sitemap_url, host)
        response.raise_for_status()
    except (httpx.HTTPError, ValueError):
        return []

    soup = BeautifulSoup(response.content, "xml")
    results = []

    # Sitemap index.
    for sitemap in soup.find_all("sitemap"):
        loc = sitemap.find("loc")

        if not loc or not loc.text:
            continue

        remaining = (
            None
            if max_urls is None
            else max_urls - len(results)
        )

        if remaining is not None and remaining <= 0:
            break

        results.extend(
            collect_sitemap_urls(
                client,
                loc.text.strip(),
                base_url,
                robots,
                depth + 1,
                max_urls=remaining,
            )
        )

    # Sitemap biasa.
    for item in soup.find_all("url"):
        loc = item.find("loc")

        if not loc or not loc.text:
            continue

        article_url = loc.text.strip()

        if not is_same_domain(article_url, base_url):
            continue

        # Buang URL non-artikel sejak pembacaan sitemap.
        if is_non_article_url(article_url):
            continue

        lastmod = item.find("lastmod")

        results.append({
            "url": article_url,
            "title": None,
            "date": parse_date(lastmod.text) if lastmod else None,
            "date_source": "sitemap_lastmod",
        })

        if (
            max_urls is not None
            and len(results) >= max_urls
        ):
            break

    return results

def discover_rss_urls(client, base_url):
    """Mencari RSS melalui permintaan homepage yang tervalidasi."""

    candidates = [
        urljoin(base_url, "/feed"),
        urljoin(base_url, "/feed/"),
        urljoin(base_url, "/rss"),
        urljoin(base_url, "/rss.xml"),
        urljoin(base_url, "/feed.xml"),
        urljoin(base_url, "/atom.xml"),
    ]

    try:
        host = urlparse(base_url).hostname
        response = validation_safe_get(client, base_url, host)
        response.raise_for_status()

        from bs4 import BeautifulSoup

        soup = BeautifulSoup(response.text, "html.parser")

        for link in soup.find_all("link", href=True):
            feed_type = link.get("type", "").lower()

            if "rss" in feed_type or "atom" in feed_type:
                candidates.append(
                    urljoin(base_url, link["href"])
                )

    except (httpx.HTTPError, ValueError):
        pass

    return list(dict.fromkeys(candidates))


def collect_rss_urls(client, feed_urls, base_url, robots):
    """Mengambil RSS/Atom setelah validasi URL dan redirect."""

    results = []

    for feed_url in feed_urls:
        if not robots.can_fetch(USER_AGENT, feed_url):
            continue

        try:
            host = urlparse(base_url).hostname
            response = validation_safe_get(client, feed_url, host)
            response.raise_for_status()

            feed = feedparser.parse(response.content)

            if not feed.entries:
                continue

            for entry in feed.entries:
                article_url = entry.get("link")

                if not article_url:
                    continue

                article_url = urljoin(base_url, article_url)

                if not is_same_domain(article_url, base_url):
                    continue

                published = entry.get("published")
                updated = entry.get("updated")

                results.append({
                    "url": article_url,
                    "title": entry.get("title"),
                    "date": parse_date(published),
                    "updated_date": parse_date(updated),
                    "date_source": (
                        "rss_published"
                        if published
                        else "rss_updated"
                        if updated
                        else None
                    ),
                })

        except Exception as exc:
            logger.warning("RSS gagal %s: %s", feed_url, exc)

    return results

def collect_homepage_urls(client, base_url, robots, max_urls=MAX_CANDIDATES_PER_SOURCE):
    """Discover article links from the source homepage as a fallback.

    The same URL-pattern recognizer and SSRF/redirect checks used during
    source validation are reused here. Only same-host, public HTTP(S) URLs
    permitted by robots.txt are returned.
    """
    parsed = urlparse(base_url)
    host = parsed.hostname
    if not host:
        return []

    try:
        response = validation_safe_get(client, base_url, host)
        response.raise_for_status()
    except Exception as exc:
        logger.warning("Homepage discovery gagal %s: %s", base_url, exc)
        return []

    discovered = _extract_homepage_article_urls(
        response.text,
        base_url,
        host,
        limit=max_urls,
    )

    results = []
    for article_url in discovered:
        try:
            validate_public_url(article_url, allowed_host=host)
            if not robots.can_fetch(USER_AGENT, article_url):
                continue
            if is_non_article_url(article_url):
                continue
            results.append({
                "url": article_url,
                "title": None,
                "date": None,
                "date_source": "homepage",
            })
        except Exception as exc:
            logger.info("URL homepage dilewati %s: %s", article_url, exc)

        if len(results) >= max_urls:
            break

    return results


def _source_validation_config(source):
    """Read persisted validation config without trusting malformed JSON."""
    raw = getattr(source, "validation_config", None)
    if not raw:
        return {}
    try:
        value = json.loads(raw) if isinstance(raw, str) else raw
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError, json.JSONDecodeError):
        return {}


def extract_published_date(html):
    """Mengambil tanggal publikasi eksplisit dari metadata halaman."""

    soup = BeautifulSoup(html, "html.parser")

    # Metadata HTML yang secara eksplisit menunjukkan publikasi.
    publication_keys = {
        "article:published_time",
        "og:published_time",
        "datepublished",
        "publishdate",
        "pubdate",
    }

    for tag in soup.find_all("meta"):
        key = (
            tag.get("property")
            or tag.get("name")
            or tag.get("itemprop")
            or ""
        ).strip().lower()

        if key in publication_keys:
            value = tag.get("content")

            if value:
                parsed = parse_date(value)
                if parsed:
                    return parsed

    # Elemen HTML dengan itemprop datePublished.
    for tag in soup.find_all(attrs={"itemprop": "datePublished"}):
        value = tag.get("content") or tag.get("datetime") or tag.get_text(
            strip=True
        )

        if value:
            parsed = parse_date(value)
            if parsed:
                return parsed

    # Metadata JSON-LD dengan properti datePublished.
    def find_date_published(data):
        if isinstance(data, dict):
            value = data.get("datePublished")

            if value:
                parsed = parse_date(value)
                if parsed:
                    return parsed

            for child in data.values():
                result = find_date_published(child)
                if result:
                    return result

        elif isinstance(data, list):
            for child in data:
                result = find_date_published(child)
                if result:
                    return result

        return None

    for script in soup.find_all(
        "script",
        attrs={"type": "application/ld+json"},
    ):
        try:
            data = json.loads(script.string or script.get_text())
            result = find_date_published(data)

            if result:
                return result

        except (json.JSONDecodeError, TypeError):
            continue

    return None


def extract_article(client, url, max_attempts=3):
    """Mengambil dan mengekstrak konten artikel dengan retry terbatas."""

    for attempt in range(1, max_attempts + 1):
        try:
            host = urlparse(url).hostname
            response = validation_safe_get(client, url, host)
            response.raise_for_status()
            downloaded = response.text
            break

        except (httpx.TransportError, httpx.TimeoutException) as exc:
            if attempt >= max_attempts:
                logger.warning(
                    "GAGAL mengambil artikel setelah %s percobaan: %s | %s",
                    max_attempts,
                    url,
                    exc,
                )
                raise

            delay = 2 ** attempt

            logger.warning(
                "Koneksi gagal, mencoba ulang %s/%s dalam %s detik: %s | %s",
                attempt,
                max_attempts - 1,
                delay,
                url,
                exc,
            )

            time.sleep(delay)

    content = trafilatura.extract(
        downloaded,
        include_comments=False,
        include_tables=True,
        favor_precision=True,
    )

    metadata = trafilatura.extract_metadata(downloaded)

    if not content:
        return None

    return {
        "title": metadata.title if metadata else None,
        "content": content,
        "author": metadata.author if metadata else None,
        "published_at": extract_published_date(downloaded),
        "description": metadata.description if metadata else None,
    }



def collect_articles(date_from, date_to, source_ids=None):
    """
    Mengumpulkan artikel dari sumber aktif yang dipilih.

    source_ids=None mempertahankan kompatibilitas pemanggilan lama.
    Jika source_ids diberikan, hanya ID tersebut yang diproses.

    Ketentuan:
    - Maksimal 5 artikel tersimpan per sumber.
    - Maksimal 50 kandidat diperiksa per sumber.
    - RSS published menjadi petunjuk tanggal publikasi cadangan.
    - Sitemap lastmod dan RSS updated hanya untuk pengurutan.
    - Homepage discovery menjadi fallback jika diaktifkan oleh hasil validasi.
    - Retry dilakukan setelah seluruh sumber selesai diproses.
    """

    db = SessionLocal()
    run = None
    run_persisted = False

    result = {
        "run_id": None,
        "status": "failed",
        "sources_checked": 0,
        "articles_found": 0,
        "articles_saved": 0,
        "duplicates_skipped": 0,
        "articles_failed": 0,
        "failure_details": [],
        "error_message": None,
    }

    saved_by_source = {}
    retry_queue = []
    failure_details = []

    def record_failure(source_name, article_url, stage, reason):
        """Mencatat kegagalan artikel tanpa mengubah skema database."""

        run.articles_failed += 1

        failure_details.append({
            "source": source_name or "Sumber tidak diketahui",
            "url": article_url or "-",
            "stage": stage,
            "reason": str(reason)[:1000],
        })

    try:
        # --------------------------------------------------
        # 1. Membuat catatan proses koleksi
        # --------------------------------------------------

        run = CollectionRun(
            date_from=datetime.combine(
                date_from,
                datetime_time.min,
            ),
            date_to=datetime.combine(
                date_to,
                datetime_time.max,
            ),
            status="running",
        )

        db.add(run)
        db.commit()
        run_persisted = True
        db.refresh(run)

        source_query = db.query(MediaSource).filter(
            MediaSource.is_active.is_(True)
        )
        if source_ids is not None:
            normalized_source_ids = list(dict.fromkeys(int(item) for item in source_ids))
            if not normalized_source_ids:
                sources = []
            else:
                sources = source_query.filter(
                    MediaSource.id.in_(normalized_source_ids)
                ).all()
        else:
            sources = source_query.all()

        run.sources_checked = len(sources)

        saved_by_source = {
            source.id: 0
            for source in sources
        }

        # --------------------------------------------------
        # 2. Pemrosesan sumber utama
        # --------------------------------------------------

        with httpx.Client(
            timeout=REQUEST_TIMEOUT,
            follow_redirects=False,
            trust_env=False,
            headers={"User-Agent": USER_AGENT},
        ) as client:

            for source in sources:
                base_url = source.base_url.rstrip("/") + "/"

                try:
                    # Membaca robots.txt.
                    robots = get_robots_parser(
                        client,
                        base_url,
                    )

                    # --------------------------------------
                    # 2A. Mengumpulkan kandidat sitemap
                    # --------------------------------------

                    sitemap_urls = discover_sitemaps(
                        client,
                        base_url,
                        robots,
                    )

                    candidates = []

                    hostname = (
                        urlparse(source.base_url).hostname or ""
                    ).removeprefix("www.")

                    # Batas khusus MEMO Online.
                    sitemap_candidate_limit = (
                        MAX_CANDIDATES_PER_SOURCE
                        if hostname == "memoonline.co.id"
                        else None
                    )

                    for sitemap_url in sitemap_urls:

                        remaining = (
                            None
                            if sitemap_candidate_limit is None
                            else sitemap_candidate_limit - len(candidates)
                        )

                        if remaining is not None and remaining <= 0:
                            break

                        candidates.extend(
                            collect_sitemap_urls(
                                client,
                                sitemap_url,
                                base_url,
                                robots,
                                max_urls=remaining,
                            )
                        )

                    # --------------------------------------
                    # 2B. Mengumpulkan kandidat RSS
                    # --------------------------------------

                    if hostname != "memoonline.co.id":
                        rss_urls = discover_rss_urls(
                            client,
                            base_url,
                        )

                        candidates.extend(
                            collect_rss_urls(
                                client,
                                rss_urls,
                                base_url,
                                robots,
                            )
                        )

                    # --------------------------------------
                    # 2C. Homepage discovery sebagai fallback
                    # --------------------------------------
                    # Hanya jalankan bila hasil validasi sumber menyatakan
                    # homepage discovery didukung dan sitemap/RSS tidak
                    # menghasilkan kandidat. Ini penting untuk MEMO Online.
                    validation_config = _source_validation_config(source)
                    homepage_enabled = bool(
                        validation_config.get("homepage_discovery")
                        or "homepage" in validation_config.get("discovery_methods", [])
                    )
                    if not candidates and homepage_enabled:
                        homepage_candidates = collect_homepage_urls(
                            client,
                            base_url,
                            robots,
                            max_urls=MAX_CANDIDATES_PER_SOURCE,
                        )
                        candidates.extend(homepage_candidates)

                    # --------------------------------------
                    # 2D. Menggabungkan kandidat berdasarkan URL
                    # --------------------------------------

                    unique_candidates = {}

                    for item in candidates:
                        normalized = normalize_url(item["url"])

                        if normalized not in unique_candidates:
                            unique_candidates[normalized] = item
                            continue

                        existing_item = unique_candidates[normalized]

                        # RSS published diprioritaskan jika
                        # tanggalnya berhasil diparsing.
                        if (
                            item.get("date_source") == "rss_published"
                            and item.get("date") is not None
                        ):
                            existing_item["date"] = item["date"]
                            existing_item["date_source"] = "rss_published"

                        # Sitemap lastmod menjadi petunjuk
                        # pengurutan jika belum ada tanggal.
                        elif (
                            existing_item.get("date") is None
                            and item.get("date_source") == "sitemap_lastmod"
                            and item.get("date") is not None
                        ):
                            existing_item["date"] = item["date"]
                            existing_item["date_source"] = "sitemap_lastmod"

                        # Simpan tanggal pembaruan RSS secara terpisah.
                        if item.get("updated_date"):
                            existing_item["updated_date"] = (
                                item["updated_date"]
                            )

                        # Pertahankan judul jika belum tersedia.
                        if (
                            not existing_item.get("title")
                            and item.get("title")
                        ):
                            existing_item["title"] = item["title"]

                    candidates = list(unique_candidates.values())

                    run.articles_found += len(candidates)

                    # --------------------------------------
                    # 2E. Memeriksa URL yang valid
                    # --------------------------------------

                    valid_candidates = []
                    allowed_host = urlparse(base_url).hostname
                    for item in candidates:
                        candidate_url = item.get("url")
                        if not candidate_url or is_non_article_url(candidate_url):
                            continue
                        try:
                            validate_public_url(
                                candidate_url,
                                allowed_host=allowed_host,
                            )
                        except Exception as exc:
                            logger.info(
                                "Kandidat URL ditolak sebelum diproses: %s | %s",
                                candidate_url,
                                exc,
                            )
                            continue
                        if robots.can_fetch(USER_AGENT, candidate_url):
                            valid_candidates.append(item)

                    # --------------------------------------
                    # 2F. Mengelompokkan kandidat
                    # --------------------------------------

                    rss_published_candidates = [
                        item
                        for item in valid_candidates
                        if (
                            item.get("date") is not None
                            and item.get("date_source") == "rss_published"
                        )
                    ]

                    sitemap_candidates = [
                        item
                        for item in valid_candidates
                        if item.get("date_source") == "sitemap_lastmod"
                    ]

                    other_candidates = [
                        item
                        for item in valid_candidates
                        if item.get("date_source") not in (
                            "rss_published",
                            "sitemap_lastmod",
                        )
                    ]

                    # RSS published: tanggal publikasi kandidat.
                    rss_published_candidates.sort(
                        key=lambda item: item["date"],
                        reverse=True,
                    )

                    # Sitemap: hanya petunjuk urutan pemeriksaan.
                    sitemap_candidates.sort(
                        key=lambda item: item.get("date") or datetime.min,
                        reverse=True,
                    )

                    # Kandidat lainnya: gunakan RSS updated
                    # sebagai petunjuk urutan jika tersedia.
                    other_candidates.sort(
                        key=lambda item: (
                            item.get("updated_date")
                            or item.get("date")
                            or datetime.min
                        ),
                        reverse=True,
                    )

                    ordered_candidates = (
                        rss_published_candidates
                        + sitemap_candidates
                        + other_candidates
                    )

                    # --------------------------------------
                    # 2G. Menghapus kandidat yang sudah tersimpan
                    # --------------------------------------

                    candidates_to_process = []
                    seen_candidate_urls = set()

                    for item in ordered_candidates:
                        canonical_url = normalize_url(item["url"])

                        if canonical_url in seen_candidate_urls:
                            continue

                        seen_candidate_urls.add(canonical_url)

                        existing = db.query(NewsArticle).filter(
                            NewsArticle.source_id == source.id,
                            NewsArticle.canonical_url == canonical_url,
                        ).first()

                        if existing:
                            run.duplicates_skipped += 1
                            continue

                        candidates_to_process.append(item)

                        if (
                            len(candidates_to_process)
                            >= MAX_CANDIDATES_PER_SOURCE
                        ):
                            break

                    logger.warning(
                        "SELEKSI sumber=%s | valid=%s | "
                        "rss_published=%s | sitemap=%s | homepage=%s | "
                        "lainnya=%s | diperiksa=%s",
                        source.name,
                        len(valid_candidates),
                        len(rss_published_candidates),
                        len(sitemap_candidates),
                        sum(1 for item in valid_candidates if item.get("date_source") == "homepage"),
                        len(other_candidates),
                        len(candidates_to_process),
                    )

                    # --------------------------------------
                    # 2H. Memproses kandidat artikel
                    # --------------------------------------

                    for item in candidates_to_process:

                        if (
                            saved_by_source[source.id]
                            >= MAX_ARTICLES_PER_SOURCE
                        ):
                            break

                        article_url = item["url"]
                        canonical_url = normalize_url(article_url)

                        try:
                            time.sleep(REQUEST_DELAY)

                            article = extract_article(
                                client,
                                article_url,
                            )

                            if not article:
                                record_failure(
                                    source.name,
                                    article_url,
                                    "Ekstraksi artikel",
                                    "Konten artikel tidak berhasil diekstrak.",
                                )
                                continue

                            # Metadata halaman menjadi prioritas.
                            published_at = article.get("published_at")

                            # RSS published hanya sebagai cadangan.
                            if (
                                not published_at
                                and item.get("date_source") == "rss_published"
                            ):
                                published_at = item.get("date")

                            logger.warning(
                                "DIAGNOSTIK TANGGAL | sumber=%s | "
                                "url=%s | tanggal_kandidat=%s | "
                                "date_source=%s | tanggal_ekstraksi=%s | "
                                "tanggal_final=%s",
                                source.name,
                                article_url,
                                item.get("date"),
                                item.get("date_source"),
                                article.get("published_at"),
                                published_at,
                            )

                            if not published_at:
                                record_failure(
                                    source.name,
                                    article_url,
                                    "Validasi tanggal",
                                    "Tanggal publikasi tidak ditemukan pada halaman maupun RSS.",
                                )

                                logger.warning(
                                    "Artikel dilewati: tanggal publikasi "
                                    "tidak ditemukan | %s",
                                    article_url,
                                )
                                continue

                            if not (
                                run.date_from
                                <= published_at
                                <= run.date_to
                            ):
                                logger.warning(
                                    "Artikel dilewati: tanggal publikasi "
                                    "di luar rentang | tanggal=%s | "
                                    "rentang=%s sampai %s | url=%s",
                                    published_at,
                                    run.date_from,
                                    run.date_to,
                                    article_url,
                                )
                                continue

                            title = (
                                article.get("title")
                                or item.get("title")
                            )

                            if not title:
                                record_failure(
                                    source.name,
                                    article_url,
                                    "Validasi judul",
                                    "Judul artikel tidak ditemukan.",
                                )
                                continue

                            content = article.get("content")

                            if not content or not content.strip():
                                record_failure(
                                    source.name,
                                    article_url,
                                    "Validasi konten",
                                    "Isi artikel kosong atau tidak berhasil diekstrak.",
                                )
                                continue

                            content = content.strip()

                            content_hash = hashlib.sha256(
                                content.encode("utf-8")
                            ).hexdigest()

                            new_article = NewsArticle(
                                source_id=source.id,
                                url=article_url,
                                canonical_url=canonical_url,
                                title=title.strip(),
                                content=content,
                                summary=article.get("description"),
                                author=article.get("author"),
                                published_at=published_at,
                                content_hash=content_hash,
                                status="collected",
                                extra_metadata=json.dumps({
                                    "collector": "GPR Media Intelligence",
                                    "version": "1.0",
                                }),
                            )

                            db.add(new_article)
                            db.commit()

                            run.articles_saved += 1
                            saved_by_source[source.id] += 1

                        except (
                            httpx.TransportError,
                            httpx.TimeoutException,
                        ) as exc:
                            db.rollback()

                            retry_queue.append({
                                "source_id": source.id,
                                "article_url": article_url,
                                "canonical_url": canonical_url,
                                "item": item,
                            })

                            logger.warning(
                                "Artikel masuk antrean retry tertunda: "
                                "%s | %s",
                                article_url,
                                exc,
                            )

                        except Exception as exc:
                            db.rollback()

                            record_failure(
                                source.name,
                                article_url,
                                "Pemrosesan artikel",
                                exc,
                            )

                            logger.exception(
                                "Gagal memproses artikel %s: %s",
                                article_url,
                                exc,
                            )

                except Exception as exc:
                    db.rollback()

                    record_failure(
                        source.name,
                        source.base_url,
                        "Pemrosesan sumber",
                        exc,
                    )

                    logger.exception(
                        "Gagal memproses sumber %s: %s",
                        source.name,
                        exc,
                    )

        # --------------------------------------------------
        # 3. Retry setelah seluruh sumber selesai diproses
        # --------------------------------------------------

        if retry_queue:
            logger.warning(
                "Memulai retry tertunda untuk %s artikel",
                len(retry_queue),
            )

            time.sleep(10)

            # Client khusus retry. Tidak menggunakan client utama
            # karena client utama sudah ditutup.
            with httpx.Client(
                timeout=REQUEST_TIMEOUT,
                follow_redirects=False,
                trust_env=False,
                headers={"User-Agent": USER_AGENT},
            ) as retry_client:

                for retry_item in retry_queue:
                    source = None

                    article_url = retry_item["article_url"]
                    canonical_url = retry_item["canonical_url"]
                    item = retry_item["item"]

                    try:
                        source = db.query(MediaSource).filter(
                            MediaSource.id == retry_item["source_id"]
                        ).first()

                        if not source:
                            record_failure(
                                f"ID sumber {retry_item['source_id']}",
                                article_url,
                                "Retry",
                                "Data sumber media tidak ditemukan.",
                            )
                            continue

                        # Pastikan kuota sumber belum terpenuhi.
                        if (
                            saved_by_source.get(source.id, 0)
                            >= MAX_ARTICLES_PER_SOURCE
                        ):
                            logger.info(
                                "Retry dilewati: kuota artikel "
                                "sudah terpenuhi | %s",
                                source.name,
                            )
                            continue

                        # Periksa robots.txt menggunakan retry_client.
                        robots = get_robots_parser(
                            retry_client,
                            source.base_url.rstrip("/") + "/",
                        )

                        if not robots.can_fetch(
                            USER_AGENT,
                            article_url,
                        ):
                            record_failure(
                                source.name,
                                article_url,
                                "Validasi robots.txt saat retry",
                                "Pengambilan artikel tidak diizinkan oleh robots.txt.",
                            )

                            logger.warning(
                                "Retry dilewati karena robots.txt: %s",
                                article_url,
                            )
                            continue

                        # Periksa kembali URL sebelum mengambil artikel.
                        existing = db.query(NewsArticle).filter(
                            NewsArticle.source_id == source.id,
                            NewsArticle.canonical_url == canonical_url,
                        ).first()

                        if existing:
                            run.duplicates_skipped += 1
                            continue

                        time.sleep(REQUEST_DELAY)

                        article = extract_article(
                            retry_client,
                            article_url,
                            max_attempts=1,
                        )

                        if not article:
                            record_failure(
                                source.name,
                                article_url,
                                "Ekstraksi artikel",
                                "Konten artikel tidak berhasil diekstrak.",
                            )
                            continue

                        published_at = article.get("published_at")

                        if (
                            not published_at
                            and item.get("date_source") == "rss_published"
                        ):
                            published_at = item.get("date")

                        logger.warning(
                            "DIAGNOSTIK TANGGAL RETRY | sumber=%s | "
                            "url=%s | tanggal_kandidat=%s | "
                            "date_source=%s | tanggal_ekstraksi=%s | "
                            "tanggal_final=%s",
                            source.name,
                            article_url,
                            item.get("date"),
                            item.get("date_source"),
                            article.get("published_at"),
                            published_at,
                        )

                        if not published_at:
                            record_failure(
                                source.name,
                                article_url,
                                "Validasi tanggal",
                                "Tanggal publikasi tidak ditemukan pada halaman maupun RSS.",
                            )

                            logger.warning(
                                "Artikel dilewati: tanggal publikasi "
                                "tidak ditemukan | %s",
                                article_url,
                            )
                            continue

                        if not (
                            run.date_from
                            <= published_at
                            <= run.date_to
                        ):
                            logger.warning(
                                "Retry dilewati: tanggal di luar rentang | "
                                "%s",
                                article_url,
                            )
                            continue

                        title = (
                            article.get("title")
                            or item.get("title")
                        )

                        if not title:
                            record_failure(
                                source.name,
                                article_url,
                                "Validasi judul",
                                "Judul artikel tidak ditemukan.",
                            )
                            continue

                        content = article.get("content")

                        if not content or not content.strip():
                            record_failure(
                                source.name,
                                article_url,
                                "Validasi konten",
                                "Isi artikel kosong atau tidak berhasil diekstrak.",
                            )
                            continue

                        content = content.strip()

                        content_hash = hashlib.sha256(
                            content.encode("utf-8")
                        ).hexdigest()

                        new_article = NewsArticle(
                            source_id=source.id,
                            url=article_url,
                            canonical_url=canonical_url,
                            title=title.strip(),
                            content=content,
                            summary=article.get("description"),
                            author=article.get("author"),
                            published_at=published_at,
                            content_hash=content_hash,
                            status="collected",
                            extra_metadata=json.dumps({
                                "collector": "GPR Media Intelligence",
                                "version": "1.0",
                            }),
                        )

                        db.add(new_article)
                        db.commit()

                        run.articles_saved += 1
                        saved_by_source[source.id] += 1

                        logger.warning(
                            "Retry berhasil menyimpan artikel: %s",
                            article_url,
                        )

                    except Exception as exc:
                        db.rollback()

                        record_failure(
                            source.name if source else f"ID sumber {retry_item['source_id']}",
                            article_url,
                            "Pemrosesan retry",
                            exc,
                        )

                        logger.exception(
                            "Retry tertunda gagal untuk %s: %s",
                            article_url,
                            exc,
                        )

        # --------------------------------------------------
        # 4. Menyelesaikan proses
        # --------------------------------------------------

        run.status = "completed"

    except Exception as exc:
        db.rollback()

        if run is not None and run_persisted:
            run.status = "failed"
            run.error_message = str(exc)

        else:
            result["error_message"] = (
                f"Gagal membuat CollectionRun: {exc}"
            )
            run = None

        logger.exception("Proses pengumpulan gagal")

    # ------------------------------------------------------
    # 5. Menyimpan hasil akhir dan menutup database
    # ------------------------------------------------------

    finally:
        try:
            if run is not None:
                run.finished_at = datetime.now(timezone.utc)

                result = {
                    "run_id": run.id,
                    "status": run.status,
                    "sources_checked": run.sources_checked,
                    "articles_found": run.articles_found,
                    "articles_saved": run.articles_saved,
                    "duplicates_skipped": run.duplicates_skipped,
                    "articles_failed": run.articles_failed,
                    "failure_details": failure_details,
                    "error_message": run.error_message,
                }

                try:
                    db.commit()

                except Exception as exc:
                    db.rollback()

                    result["status"] = "failed"
                    result["error_message"] = (
                        "Gagal menyimpan hasil akhir CollectionRun: "
                        f"{exc}"
                    )

                    logger.exception(
                        "Gagal menyimpan hasil akhir CollectionRun"
                    )

        finally:
            db.close()

    return result
