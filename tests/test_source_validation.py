import pytest

from app.source_validation import (
    UnsafeTarget,
    _extract_homepage_article_urls,
    _extract_metadata,
    normalize_base_url,
    validate_public_url,
)


def test_normalize_base_url_adds_https_and_removes_trailing_slash():
    assert normalize_base_url("contoh.id/") == "https://contoh.id"


@pytest.mark.parametrize("value", [
    "file:///etc/passwd", "ftp://contoh.id", "https://user:pass@contoh.id",
    "https://contoh.id:8080",
])
def test_normalize_base_url_rejects_unsafe_values(value):
    with pytest.raises(ValueError):
        normalize_base_url(value)


@pytest.mark.parametrize("url", [
    "http://127.0.0.1", "http://10.0.0.1",
    "http://169.254.169.254/latest/meta-data", "http://[::1]/",
])
def test_validate_public_url_rejects_non_public_ip(url):
    with pytest.raises(UnsafeTarget):
        validate_public_url(url)


def test_validate_public_url_rejects_different_host():
    with pytest.raises(UnsafeTarget):
        validate_public_url("https://example.net/article", allowed_host="example.com")


def test_extract_metadata_reads_title_author_date_and_content():
    html = """<html><head><title>Judul Uji</title>
    <meta name="author" content="Redaksi">
    <meta property="article:published_time" content="2026-11-20T10:00:00+07:00">
    </head><body><article><h1>Judul</h1><p>Isi berita ini cukup panjang untuk menjadi contoh
    pengujian ekstraksi metadata dari halaman artikel yang sedang diperiksa.</p></article></body></html>"""
    result = _extract_metadata(html)
    assert result["title"] == "Judul Uji"
    assert result["author"] == "Redaksi"
    assert result["published_at"].startswith("2026-11-20")
    assert result["content_chars"] > 50


def test_homepage_discovery_finds_memo_style_article_links():
    html = """<html><body>
    <a href="/berita/umk-lumajang-2027-naik-654-persen-kadin-lumajang">Berita terbaru</a>
    <a href="/berita/pemerintah-daerah-siap-meningkatkan-pelayanan-publik">Berita lain</a>
    <a href="/tentang-kami">Tentang kami</a>
    <a href="https://example.net/berita/berita-eksternal">Eksternal</a>
    <a href="/category/politik">Kategori</a>
    </body></html>"""
    urls = _extract_homepage_article_urls(
        html, "https://www.memoonline.co.id/", "www.memoonline.co.id"
    )
    assert urls == [
        "https://www.memoonline.co.id/berita/umk-lumajang-2027-naik-654-persen-kadin-lumajang",
        "https://www.memoonline.co.id/berita/pemerintah-daerah-siap-meningkatkan-pelayanan-publik",
    ]


def test_homepage_discovery_deduplicates_links_and_ignores_non_article_links():
    html = """<html><body>
    <a href="/berita/judul-berita-yang-cukup-panjang">Satu</a>
    <a href="/berita/judul-berita-yang-cukup-panjang/">Duplikat</a>
    <a href="/tentang-kami">Tentang</a>
    <a href="/privacy-policy">Privasi</a>
    </body></html>"""
    urls = _extract_homepage_article_urls(
        html, "https://www.memoonline.co.id/", "www.memoonline.co.id"
    )
    assert urls == ["https://www.memoonline.co.id/berita/judul-berita-yang-cukup-panjang"]
