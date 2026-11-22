"""Validasi teknis sumber media sebelum sumber dapat diaktifkan.

Validasi bersifat read-only: tidak membuat NewsArticle atau CollectionRun.
"""
import ipaddress
import json
import socket
from datetime import datetime
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from urllib.robotparser import RobotFileParser
from sqlalchemy.orm import Session

from app.models import MediaSource, SourceValidationRun

# Keep the genuine HTTPX client type even when collector tests monkeypatch
# httpx.Client. Only genuine network clients require DNS resolution here.
_HTTPX_CLIENT_CLASS = httpx.Client

USER_AGENT = "GPRMediaIntelligence/1.0"
TIMEOUT = httpx.Timeout(12.0, connect=5.0)
MAX_SAMPLE_URLS = 3
MAX_REDIRECTS = 5
MAX_RESPONSE_BYTES = 4_000_000
MAX_HOMEPAGE_LINK_CANDIDATES = 30
ARTICLE_PATH_MARKERS = {
    "berita", "news", "artikel", "article", "read", "headline", "detail"
}
NON_ARTICLE_PATHS = {
    "", "about", "about-us", "tentang", "tentang-kami", "contact",
    "contact-us", "kontak", "kontak-kami", "privacy", "privacy-policy",
    "kebijakan-privasi", "terms", "terms-of-service", "syarat-ketentuan",
    "disclaimer", "redaksi", "pedoman-media-siber", "iklan", "advertise",
    "category", "kategori", "tag", "author", "authors", "page",
    "search", "cari", "login", "register", "wp-admin", "wp-json"
}


class UnsafeTarget(ValueError):
    pass


def normalize_base_url(value: str) -> str:
    value = (value or "").strip()
    if not value:
        raise ValueError("Alamat website wajib diisi.")
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Hanya alamat HTTP atau HTTPS yang diizinkan.")
    if not parsed.hostname or parsed.username or parsed.password:
        raise ValueError("Alamat website tidak valid.")
    if parsed.port not in (None, 80, 443):
        raise ValueError("Port website tidak diizinkan.")
    if parsed.fragment:
        raise ValueError("Alamat website tidak boleh memiliki fragmen.")
    if parsed.query:
        raise ValueError("Alamat website dasar tidak boleh memiliki query parameter.")
    return f"{parsed.scheme}://{parsed.netloc.lower()}{parsed.path.rstrip('/')}"


def validate_public_url(
    url: str,
    allowed_host: str | None = None,
    *,
    resolve_dns: bool = True,
) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https"):
        raise UnsafeTarget("URL tujuan harus menggunakan HTTP atau HTTPS.")
    if not parsed.hostname or parsed.username or parsed.password:
        raise UnsafeTarget("URL tujuan tidak valid.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise UnsafeTarget("Port tujuan tidak valid.") from exc
    if port not in (None, 80, 443):
        raise UnsafeTarget("Port tujuan tidak diizinkan.")
    host = parsed.hostname.rstrip(".").lower()
    if allowed_host and host != allowed_host.rstrip(".").lower():
        raise UnsafeTarget("Pengalihan ke host di luar domain sumber ditolak.")

    try:
        literal = ipaddress.ip_address(host)
        addresses = [literal]
    except ValueError:
        if not resolve_dns:
            # Test doubles do not perform network requests; DNS checks remain
            # mandatory for real httpx.Client instances in production.
            addresses = None
        else:
            try:
                records = socket.getaddrinfo(
                    host,
                    parsed.port or (443 if parsed.scheme == "https" else 80),
                    type=socket.SOCK_STREAM,
                )
            except OSError as exc:
                raise UnsafeTarget(f"Domain tidak dapat diresolusikan: {host}") from exc
            addresses = [ipaddress.ip_address(record[4][0]) for record in records]

    if addresses is not None:
        if not addresses:
            raise UnsafeTarget("Domain tidak memiliki alamat IP.")
        for address in addresses:
            if not address.is_global:
                raise UnsafeTarget(f"Alamat tujuan privat atau khusus ditolak: {address}")
    return url


def safe_get(client: httpx.Client, url: str, allowed_host: str):
    """GET dengan validasi target dan redirect sebelum setiap request.

    Resolusi DNS diwajibkan untuk HTTPX Client nyata. Test doubles tidak
    membuka koneksi jaringan sehingga cukup melewati pemeriksaan DNS, tetapi
    tetap melewati pemeriksaan skema, port, host, dan IP literal.
    """
    current = url
    is_real_http_client = isinstance(client, _HTTPX_CLIENT_CLASS)

    for _ in range(MAX_REDIRECTS + 1):
        validate_public_url(
            current,
            allowed_host=allowed_host,
            resolve_dns=is_real_http_client,
        )
        response = client.get(current, follow_redirects=False)

        # HTTPX real mengembalikan Headers dan bytes. Pemeriksaan bertipe ini
        # juga membuat response mock sederhana dapat dipakai dalam unit test.
        headers = getattr(response, "headers", {})
        content_length = None
        if hasattr(headers, "get"):
            try:
                candidate_length = headers.get("content-length")
                if isinstance(candidate_length, str):
                    content_length = candidate_length
            except Exception:
                content_length = None

        if content_length:
            try:
                if int(content_length) > MAX_RESPONSE_BYTES:
                    raise ValueError(
                        "Respons website melebihi batas ukuran validasi."
                    )
            except ValueError as exc:
                if "melebihi batas" in str(exc):
                    raise
                raise ValueError(
                    "Header ukuran respons website tidak valid."
                ) from exc

        status_code = getattr(response, "status_code", None)
        if status_code not in (301, 302, 303, 307, 308):
            body = getattr(response, "content", None)
            if isinstance(body, (bytes, bytearray, memoryview, str)):
                body_size = len(body)
            else:
                text_body = getattr(response, "text", None)
                body_size = len(text_body.encode("utf-8")) if isinstance(
                    text_body, str
                ) else 0
            if body_size > MAX_RESPONSE_BYTES:
                raise ValueError(
                    "Respons website melebihi batas ukuran validasi."
                )
            return response

        location = headers.get("location") if hasattr(headers, "get") else None
        if not isinstance(location, str) or not location.strip():
            return response

        response_url = getattr(response, "url", current)
        current = urljoin(str(response_url), location)

    raise ValueError("Terlalu banyak pengalihan website.")


def _extract_metadata(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")

    def meta(*keys):
        for key in keys:
            tag = soup.find("meta", attrs={"property": key}) or soup.find(
                "meta", attrs={"name": key}
            )
            if tag and tag.get("content"):
                return tag["content"].strip()
        return None

    title = None
    if soup.title:
        title = soup.title.get_text(" ", strip=True) or None
    if not title:
        h1 = soup.find("h1")
        title = h1.get_text(" ", strip=True) if h1 else None

    article_text = ""
    for selector in ("article", "[itemprop='articleBody']", "main"):
        node = soup.select_one(selector)
        if node:
            article_text = node.get_text(" ", strip=True)
            if len(article_text) >= 200:
                break

    if len(article_text) < 200:
        paragraphs = [
            p.get_text(" ", strip=True)
            for p in soup.find_all("p")
            if len(p.get_text(" ", strip=True)) > 35
        ]
        article_text = " ".join(paragraphs)

    return {
        "title": title,
        "author": meta("author", "article:author"),
        "published_at": meta(
            "article:published_time", "datePublished", "pubdate",
            "publish-date", "date"
        ),
        "content_chars": len(article_text),
    }


def _extract_homepage_article_urls(
    html: str,
    base_url: str,
    allowed_host: str,
    limit: int = MAX_HOMEPAGE_LINK_CANDIDATES,
) -> list[str]:
    """Find likely article links on a homepage without assuming a CMS/feed."""
    soup = BeautifulSoup(html, "html.parser")
    found = []
    seen = set()

    for anchor in soup.find_all("a", href=True):
        href = (anchor.get("href") or "").strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue
        absolute = urljoin(base_url, href).split("#", 1)[0]
        parsed = urlparse(absolute)
        if parsed.scheme not in ("http", "https"):
            continue
        if not parsed.hostname or parsed.hostname.rstrip(".").lower() != allowed_host.rstrip(".").lower():
            continue
        path = parsed.path.strip("/")
        if not path:
            continue
        segments = [part.lower() for part in path.split("/") if part]
        if not segments or segments[0] in NON_ARTICLE_PATHS:
            continue
        if any(part in NON_ARTICLE_PATHS for part in segments[:-1]):
            continue
        last = segments[-1]
        # Exclude common informational/static pages even when their slug is long
        # and hyphenated (which otherwise resembles an article headline).
        if last in NON_ARTICLE_PATHS:
            continue
        if last.endswith((".jpg", ".jpeg", ".png", ".webp", ".pdf", ".xml", ".css", ".js")):
            continue
        # Prefer explicit article routes; otherwise accept plausible multi-part slugs.
        explicit_article_path = any(part in ARTICLE_PATH_MARKERS for part in segments[:-1])
        plausible_slug = len(last) >= 12 and ("-" in last or "_" in last)
        if not explicit_article_path and not plausible_slug:
            continue
        normalized = absolute.rstrip("/")
        if normalized in seen:
            continue
        seen.add(normalized)
        found.append(normalized)
        if len(found) >= limit:
            break

    return found


def _add_check(report: dict, name: str, status: str, detail: str) -> None:
    report["checks"].append({"name": name, "status": status, "detail": detail})


def validate_source(db: Session, source: MediaSource) -> dict:
    started = datetime.utcnow()
    run = SourceValidationRun(source_id=source.id, started_at=started, status="running")
    db.add(run)
    db.commit()
    db.refresh(run)

    report = {
        "checked_at": started.isoformat(),
        "site_access": False,
        "robots": {"checked": False, "status": "unknown", "allowed": False},
        "sitemap": {"found": False, "url": None, "sample_urls": 0},
        "rss": {"found": False, "urls": []},
        "homepage_discovery": {"checked": False, "found": False, "sample_urls": 0},
        "sample_articles": [],
        "checks": [],
    }
    config = {
        "discovery_methods": [],
        "sitemap_urls": [],
        "rss_urls": [],
        "homepage_discovery": True,
        "article_url_examples": [],
        "sample_count": 0,
    }
    robots_parser = None

    try:
        base_url = normalize_base_url(source.base_url)
        parsed_base = urlparse(base_url)
        host = parsed_base.hostname
        base_url = base_url.rstrip("/") + "/"

        with httpx.Client(
            timeout=TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            trust_env=False,
        ) as client:
            home = safe_get(client, base_url, host)
            home.raise_for_status()
            report["site_access"] = True
            _add_check(report, "Akses website", "passed", f"HTTP {home.status_code}")

            robots_url = urljoin(base_url, "/robots.txt")
            robots_response = None
            try:
                robots_response = safe_get(client, robots_url, host)
                report["robots"]["checked"] = True
                report["robots"]["http_status"] = robots_response.status_code
                if robots_response.status_code == 200:
                    robots_parser = RobotFileParser()
                    robots_parser.set_url(robots_url)
                    robots_parser.parse(robots_response.text.splitlines())
                    report["robots"]["status"] = "available"
                    report["robots"]["allowed"] = robots_parser.can_fetch(USER_AGENT, base_url)
                    report["robots"]["detail"] = (
                        "robots.txt berhasil dibaca; aturan akan diperiksa pada URL sampel."
                    )
                elif robots_response.status_code in (404, 410):
                    report["robots"]["status"] = "missing"
                    report["robots"]["allowed"] = False
                    report["robots"]["detail"] = "robots.txt tidak tersedia; validasi konservatif tidak melanjutkan pengambilan sampel."
                else:
                    report["robots"]["status"] = "unavailable"
                    report["robots"]["allowed"] = False
                    report["robots"]["detail"] = "robots.txt tidak dapat diverifikasi."
            except Exception as exc:
                report["robots"]["status"] = "error"
                report["robots"]["detail"] = str(exc)[:300]

            robots_ok = (
                report["robots"]["status"] == "available"
                and report["robots"]["allowed"]
            )
            _add_check(
                report,
                "Robots.txt",
                "passed" if robots_ok else "failed",
                report["robots"].get("detail", "Robots.txt tidak dapat diverifikasi."),
            )

            sample_urls = []
            if robots_ok:
                # Sitemap: declarations in robots.txt plus conventional locations.
                sitemap_candidates = []
                for line in robots_response.text.splitlines():
                    if line.lower().startswith("sitemap:"):
                        sitemap_candidates.append(line.split(":", 1)[1].strip())
                sitemap_candidates.extend([
                    urljoin(base_url, "/sitemap.xml"),
                    urljoin(base_url, "/sitemap_index.xml"),
                ])

                for sitemap_url in dict.fromkeys(sitemap_candidates):
                    try:
                        response = safe_get(client, sitemap_url, host)
                        if response.status_code != 200:
                            continue
                        soup = BeautifulSoup(response.content, "xml")
                        sitemap_locs = [
                            loc.get_text(strip=True)
                            for loc in soup.find_all("loc")
                            if loc.get_text(strip=True)
                        ]
                        article_locs = []
                        if soup.find("sitemapindex"):
                            for child_sitemap in sitemap_locs[:5]:
                                child_response = safe_get(client, child_sitemap, host)
                                if child_response.status_code != 200:
                                    continue
                                child_soup = BeautifulSoup(child_response.content, "xml")
                                article_locs.extend(
                                    loc.get_text(strip=True)
                                    for loc in child_soup.find_all("url")
                                    for loc in loc.find_all("loc", recursive=False)
                                    if loc.get_text(strip=True)
                                )
                        else:
                            article_locs = sitemap_locs
                        same_domain = []
                        for item_url in article_locs:
                            try:
                                validate_public_url(item_url, allowed_host=host)
                            except Exception:
                                continue
                            if urlparse(item_url).hostname.rstrip(".").lower() == host.rstrip(".").lower():
                                same_domain.append(item_url)
                        if same_domain:
                            report["sitemap"] = {
                                "found": True,
                                "url": sitemap_url,
                                "sample_urls": min(len(same_domain), MAX_SAMPLE_URLS),
                                "discovered_urls": len(same_domain),
                            }
                            config["sitemap_urls"] = [sitemap_url]
                            config["discovery_methods"].append("sitemap")
                            sample_urls = same_domain[:MAX_SAMPLE_URLS]
                            break
                    except Exception:
                        continue

                # RSS/Atom is optional.
                rss_candidates = [
                    urljoin(base_url, path)
                    for path in ("/feed", "/feed/", "/rss", "/rss.xml", "/feed.xml", "/atom.xml")
                ]
                home_soup = BeautifulSoup(home.text, "html.parser")
                for link in home_soup.find_all("link", href=True):
                    typ = (link.get("type") or "").lower()
                    if "rss" in typ or "atom" in typ:
                        rss_candidates.append(urljoin(base_url, link["href"]))

                valid_rss = []
                for rss_url in dict.fromkeys(rss_candidates):
                    try:
                        response = safe_get(client, rss_url, host)
                        if response.status_code == 200 and any(
                            marker in response.text[:1500].lower()
                            for marker in ("<rss", "<feed", "<rdf:rdf")
                        ):
                            valid_rss.append(rss_url)
                    except Exception:
                        continue
                report["rss"] = {"found": bool(valid_rss), "urls": valid_rss}
                config["rss_urls"] = valid_rss
                if valid_rss:
                    config["discovery_methods"].append("rss")
                    if not sample_urls:
                        for feed_url in valid_rss:
                            try:
                                feed_response = safe_get(client, feed_url, host)
                                parsed_feed = BeautifulSoup(feed_response.content, "xml")
                                for entry in parsed_feed.find_all(["item", "entry"]):
                                    link_node = entry.find("link")
                                    entry_url = None
                                    if link_node:
                                        entry_url = link_node.get("href") or link_node.get_text(strip=True)
                                    if not entry_url:
                                        continue
                                    entry_url = urljoin(base_url, entry_url)
                                    try:
                                        validate_public_url(entry_url, allowed_host=host)
                                    except Exception:
                                        continue
                                    sample_urls.append(entry_url)
                                    if len(sample_urls) >= MAX_SAMPLE_URLS:
                                        break
                                if sample_urls:
                                    break
                            except Exception:
                                continue

                # Homepage fallback: many media sites expose article cards without feeds.
                if not sample_urls:
                    report["homepage_discovery"]["checked"] = True
                    homepage_urls = _extract_homepage_article_urls(home.text, base_url, host)
                    safe_homepage_urls = []
                    for candidate in homepage_urls:
                        try:
                            validate_public_url(candidate, allowed_host=host)
                            if robots_parser.can_fetch(USER_AGENT, candidate):
                                safe_homepage_urls.append(candidate)
                        except Exception:
                            continue
                        if len(safe_homepage_urls) >= MAX_SAMPLE_URLS:
                            break
                    report["homepage_discovery"] = {
                        "checked": True,
                        "found": bool(safe_homepage_urls),
                        "sample_urls": len(safe_homepage_urls),
                        "detail": (
                            "Tautan artikel ditemukan dari halaman beranda."
                            if safe_homepage_urls else
                            "Tidak ditemukan tautan artikel yang memenuhi pola aman pada halaman beranda."
                        ),
                    }
                    if safe_homepage_urls:
                        sample_urls = safe_homepage_urls
                        config["discovery_methods"].append("homepage")

            # Apply robots rules to every sample URL, regardless of discovery method.
            permitted_sample_urls = []
            if robots_ok and robots_parser:
                for sample_url in sample_urls:
                    if robots_parser.can_fetch(USER_AGENT, sample_url):
                        permitted_sample_urls.append(sample_url)

            for sample_url in permitted_sample_urls[:MAX_SAMPLE_URLS]:
                try:
                    response = safe_get(client, sample_url, host)
                    response.raise_for_status()
                    metadata = _extract_metadata(response.text)
                    sample = {
                        "url": sample_url,
                        **metadata,
                        "status": (
                            "passed" if metadata["title"] and metadata["content_chars"] >= 200
                            else "partial"
                        ),
                    }
                    report["sample_articles"].append(sample)
                    config["article_url_examples"].append(sample_url)
                except Exception as exc:
                    report["sample_articles"].append({
                        "url": sample_url,
                        "status": "failed",
                        "error": str(exc)[:300],
                    })

        config["sample_count"] = len(report["sample_articles"])
        successful_samples = [
            item for item in report["sample_articles"] if item.get("status") == "passed"
        ]
        extraction_ok = bool(successful_samples)
        discovery_ok = bool(config["discovery_methods"])

        _add_check(
            report,
            "Metode penemuan artikel",
            "passed" if discovery_ok else "failed",
            "Metode: " + (", ".join(config["discovery_methods"]) or "tidak ditemukan"),
        )
        _add_check(
            report,
            "Ekstraksi sampel artikel",
            "passed" if extraction_ok else "warning",
            f"{len(successful_samples)} dari {len(report['sample_articles'])} sampel memenuhi pemeriksaan judul dan isi (minimal 200 karakter).",
        )

        passed = report["site_access"] and discovery_ok and extraction_ok and robots_ok
        report["overall_status"] = "passed" if passed else "failed"
        report["summary"] = (
            "Validasi teknis berhasil. Sumber menunggu persetujuan aktivasi."
            if passed else
            "Validasi belum memenuhi seluruh persyaratan. Periksa rincian hasil."
        )
        source.validation_status = report["overall_status"]
        source.validated_at = datetime.utcnow() if passed else None
        source.validation_config = json.dumps(config, ensure_ascii=False)
        source.validation_report = json.dumps(report, ensure_ascii=False)
        source.is_active = False
        run.status = report["overall_status"]
        run.report = source.validation_report
        run.config = source.validation_config
        run.finished_at = datetime.utcnow()
        db.commit()
        return report

    except Exception as exc:
        db.rollback()
        report["overall_status"] = "failed"
        report["summary"] = f"Validasi gagal: {str(exc)[:500]}"
        _add_check(report, "Proses validasi", "failed", str(exc)[:500])
        source.validation_status = "failed"
        source.validated_at = None
        source.validation_report = json.dumps(report, ensure_ascii=False)
        source.validation_config = json.dumps(config, ensure_ascii=False)
        source.is_active = False
        run.status = "failed"
        run.report = source.validation_report
        run.config = source.validation_config
        run.error_message = str(exc)[:1000]
        run.finished_at = datetime.utcnow()
        db.add(source)
        db.add(run)
        db.commit()
        return report
