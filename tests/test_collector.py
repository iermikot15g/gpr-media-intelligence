
from datetime import date, datetime, timezone
from unittest.mock import MagicMock, patch

from app import collector

def test_parse_date_converts_timezone_to_utc():
    result = collector.parse_date("2026-11-19T10:00:00+07:00")

    assert result == datetime(2026, 11, 19, 3, 0)


def test_parse_date_preserves_naive_datetime():
    result = collector.parse_date("2026-11-19T10:00:00")

    assert result == datetime(2026, 11, 19, 10, 0)


def test_parse_date_returns_none_for_invalid_value():
    result = collector.parse_date("tanggal tidak valid")

    assert result is None

def test_kanalnews_category_urls_are_excluded():
    category_urls = [
        "https://www.kanalnews.id/peristiwa/",
        "https://www.kanalnews.id/kesehatan/",
        "https://www.kanalnews.id/politik/",
        "https://www.kanalnews.id/opini/",
        "https://www.kanalnews.id/tni-polri/",
    ]

    for url in category_urls:
        assert collector.is_non_article_url(url) is True


def test_kanalnews_article_url_is_not_excluded():
    article_url = (
        "https://www.kanalnews.id/"
        "diduga-ada-intimidasi-video-cekcok-perawat-rs-bhc-sumenep-dihapus-pemilik-akun-minta-takedown-berita/"
    )

    assert collector.is_non_article_url(article_url) is False

def test_memo_category_urls_are_excluded():
    category_urls = [
        "https://www.memoonline.co.id/kategori/",
        "https://www.memoonline.co.id/kategori/pemerintahan/",
        "https://www.memoonline.co.id/kategori/hukum-kriminal/",
        "https://www.memoonline.co.id/kategori/sosial/",
        "https://www.memoonline.co.id/kategori/peristiwa-daerah/",
    ]

    for url in category_urls:
        assert collector.is_non_article_url(url) is True


def test_memo_article_url_is_not_excluded():
    article_url = (
        "https://www.memoonline.co.id/berita/"
        "umk-lumajang-2027-naik-654-persen"
    )

    assert collector.is_non_article_url(article_url) is False


def test_memo_category_path_on_other_domain_is_not_excluded():
    url = "https://media-lain.test/kategori/pemerintahan/"

    assert collector.is_non_article_url(url) is False

def test_category_path_on_other_domain_is_not_excluded():
    url = "https://media-lain.test/peristiwa/"

    assert collector.is_non_article_url(url) is False

def test_extract_published_date_from_article_meta():
    html = """
    <html>
        <head>
            <meta property="article:published_time"
                  content="2026-11-19T10:00:00+07:00">
            <meta property="article:modified_time"
                  content="2026-11-20T10:00:00+07:00">
        </head>
    </html>
    """

    result = collector.extract_published_date(html)

    assert result == datetime(2026, 11, 19, 3, 0)


def test_extract_published_date_from_json_ld():
    html = """
    <html>
        <head>
            <script type="application/ld+json">
            {
                "@type": "NewsArticle",
                "datePublished": "2026-11-19T10:00:00+07:00",
                "dateModified": "2026-11-20T10:00:00+07:00"
            }
            </script>
        </head>
    </html>
    """

    result = collector.extract_published_date(html)

    assert result == datetime(2026, 11, 19, 3, 0)

def test_extract_published_date_does_not_use_modified_date():
    html = """
    <html>
        <head>
            <meta property="article:modified_time"
                  content="2026-11-20T10:00:00+07:00">
        </head>
    </html>
    """

    result = collector.extract_published_date(html)

    assert result is None

def make_mock_run():
    run = MagicMock()
    run.id = 123
    run.status = "running"
    run.sources_checked = 0
    run.articles_found = 0
    run.articles_saved = 0
    run.duplicates_skipped = 0
    run.articles_failed = 0
    run.error_message = None
    return run


@patch("app.collector.SessionLocal")
def test_collection_without_active_sources(mock_session_local):
    db = MagicMock()
    run = make_mock_run()

    mock_session_local.return_value = db
    db.query.return_value.filter.return_value.all.return_value = []

    with patch.object(collector, "CollectionRun", return_value=run):
        result = collector.collect_articles(
            date(2026, 11, 18),
            date(2026, 11, 19),
        )

    assert result["status"] == "completed"
    assert result["run_id"] == 123
    assert result["sources_checked"] == 0
    assert result["articles_saved"] == 0

    db.close.assert_called_once()


@patch("app.collector.SessionLocal")
def test_collection_run_creation_failure(mock_session_local):
    db = MagicMock()
    mock_session_local.return_value = db

    db.commit.side_effect = RuntimeError("Simulasi database gagal")

    result = collector.collect_articles(
        date(2026, 11, 18),
        date(2026, 11, 19),
    )

    assert result["status"] == "failed"
    assert result["run_id"] is None
    assert "Gagal membuat CollectionRun" in result["error_message"]

    db.rollback.assert_called_once()
    db.close.assert_called_once()


@patch("app.collector.SessionLocal")
def test_collection_final_commit_failure(mock_session_local):
    db = MagicMock()
    run = make_mock_run()

    mock_session_local.return_value = db
    db.query.return_value.filter.return_value.all.return_value = []

    # Commit pertama berhasil, commit akhir gagal.
    db.commit.side_effect = [None, RuntimeError("Commit akhir gagal")]

    with patch.object(collector, "CollectionRun", return_value=run):
        result = collector.collect_articles(
            date(2026, 11, 18),
            date(2026, 11, 19),
        )

    assert result["status"] == "failed"
    assert result["run_id"] == 123
    assert "Commit akhir gagal" in result["error_message"]

    db.rollback.assert_called_once()
    db.close.assert_called_once()

import httpx


def test_extract_article_succeeds_after_retry():
    mock_client = MagicMock()

    mock_response = MagicMock()
    mock_response.text = "<html><body>Artikel berhasil</body></html>"
    mock_response.raise_for_status.return_value = None

    mock_client.get.side_effect = [
        httpx.ConnectError("Koneksi terputus"),
        mock_response,
    ]

    with patch.object(collector.time, "sleep") as mock_sleep:
        with patch.object(
            collector.trafilatura,
            "extract",
            return_value="Isi artikel yang berhasil",
        ):
            with patch.object(
                collector.trafilatura,
                "extract_metadata",
                return_value=None,
            ):
                result = collector.extract_article(mock_client, "https://contoh.test/artikel")

    assert result is not None
    assert result["content"] == "Isi artikel yang berhasil"
    assert mock_client.get.call_count == 2
    mock_sleep.assert_called_once_with(2)


def test_extract_article_fails_after_max_attempts():
    mock_client = MagicMock()
    mock_client.get.side_effect = httpx.ConnectError("Koneksi terputus")

    with patch.object(collector.time, "sleep") as mock_sleep:
        try:
            collector.extract_article(
                mock_client,
                "https://contoh.test/artikel",
                max_attempts=3,
            )
            assert False, "Seharusnya terjadi kegagalan koneksi"
        except httpx.TransportError:
            pass

    assert mock_client.get.call_count == 3
    assert mock_sleep.call_count == 2


def test_extract_article_single_attempt():
    mock_client = MagicMock()
    mock_client.get.side_effect = httpx.ConnectError("Koneksi terputus")

    with patch.object(collector.time, "sleep") as mock_sleep:
        try:
            collector.extract_article(
                mock_client,
                "https://contoh.test/artikel",
                max_attempts=1,
            )
            assert False, "Seharusnya terjadi kegagalan koneksi"
        except httpx.TransportError:
            pass

    assert mock_client.get.call_count == 1
    mock_sleep.assert_not_called()

def _run_collection_retry_test(
    extract_side_effect,
    article_query_results,
    candidate_date=None,
    candidate_date_source=None,
    article_published_at="default",
    sitemap_candidates=None,
    rss_candidates=None,
    source_name="Media Uji",
    source_base_url="https://media-uji.test",
    return_sitemap_mock=False,
    return_rss_mocks=False,
):
    from contextlib import ExitStack
    from datetime import datetime, time as datetime_time

    source = MagicMock()
    source.id = 7
    source.name = source_name
    source.base_url = source_base_url

    run = MagicMock()
    run.id = 123
    run.status = "running"
    run.date_from = datetime.combine(
        date(2026, 11, 19), datetime_time.min
    )
    run.date_to = datetime.combine(
        date(2026, 11, 19), datetime_time.max
    )

    run.sources_checked = 0
    run.articles_found = 0
    run.articles_saved = 0
    run.duplicates_skipped = 0
    run.articles_failed = 0
    run.error_message = None

    db = MagicMock()

    source_query = MagicMock()
    source_query.filter.return_value = source_query
    source_query.all.return_value = [source]
    source_query.first.return_value = source

    article_query = MagicMock()
    article_query.filter.return_value = article_query
    article_query.first.side_effect = article_query_results

    def query_side_effect(model):
        if model is collector.MediaSource:
            return source_query
        return article_query

    db.query.side_effect = query_side_effect

    # Client utama dan retry harus merupakan dua objek berbeda.
    main_client = MagicMock()
    main_context = MagicMock()
    main_context.__enter__.return_value = main_client

    retry_client = MagicMock()
    retry_context = MagicMock()
    retry_context.__enter__.return_value = retry_client

    robots = MagicMock()
    robots.can_fetch.return_value = True

    candidate = {
        "url": "https://media-uji.test/artikel/contoh",
        "title": "Judul Kandidat",
        "date": candidate_date,
        "date_source": candidate_date_source,
    }

    if rss_candidates is None:
        rss_candidates = [candidate]

    if sitemap_candidates is None:
        sitemap_candidates = []

    if article_published_at == "default":
        article_published_at = datetime(2026, 11, 19, 10, 0)

    article = {
        "title": "Judul Artikel Uji",
        "published_at": article_published_at,
        "content": "Isi artikel untuk pengujian retry.",
        "description": "Ringkasan artikel uji.",
        "author": "Redaksi",
    }

    sitemap_urls = (
        ["https://media-uji.test/sitemap.xml"]
        if sitemap_candidates or return_sitemap_mock
        else []
    )

    with ExitStack() as stack:
        stack.enter_context(
            patch("app.collector.SessionLocal", return_value=db)
        )
        stack.enter_context(
            patch("app.collector.CollectionRun", return_value=run)
        )
        stack.enter_context(
            patch(
                "app.collector.httpx.Client",
                side_effect=[main_context, retry_context],
            )
        )
        stack.enter_context(
            patch("app.collector.get_robots_parser", return_value=robots)
        )
        stack.enter_context(
            patch(
                "app.collector.discover_sitemaps",
                return_value=sitemap_urls,
            )
        )
        discover_rss_mock = stack.enter_context(
            patch(
                "app.collector.discover_rss_urls",
                return_value=[],
            )
        )
        sitemap_mock = stack.enter_context(
            patch(
                "app.collector.collect_sitemap_urls",
                return_value=sitemap_candidates,
            )
        )
        collect_rss_mock = stack.enter_context(
            patch(
                "app.collector.collect_rss_urls",
                return_value=rss_candidates,
            )
        )
        stack.enter_context(
            patch("app.collector.is_non_article_url", return_value=False)
        )
        stack.enter_context(
            patch("app.collector.time.sleep")
        )

        extract_mock = stack.enter_context(
            patch(
                "app.collector.extract_article",
                side_effect=extract_side_effect,
            )
        )

        result = collector.collect_articles(
            date(2026, 11, 19),
            date(2026, 11, 19),
        )

    if return_rss_mocks:
        return (
            result,
            db,
            extract_mock,
            discover_rss_mock,
            collect_rss_mock,
        )

    if return_sitemap_mock:
        return result, db, extract_mock, sitemap_mock

    return result, db, extract_mock


def test_memo_online_skips_rss_discovery():
    (
        result,
        db,
        extract_mock,
        discover_rss_mock,
        collect_rss_mock,
    ) = _run_collection_retry_test(
        extract_side_effect=[],
        article_query_results=[],
        sitemap_candidates=[],
        rss_candidates=[],
        source_name="MEMO Online",
        source_base_url="https://www.memoonline.co.id",
        return_rss_mocks=True,
    )

    assert result["status"] == "completed"
    discover_rss_mock.assert_not_called()
    collect_rss_mock.assert_not_called()

def test_other_sources_still_use_rss_discovery():
    (
        result,
        db,
        extract_mock,
        discover_rss_mock,
        collect_rss_mock,
    ) = _run_collection_retry_test(
        extract_side_effect=[],
        article_query_results=[],
        sitemap_candidates=[],
        rss_candidates=[],
        source_name="Media Uji",
        source_base_url="https://media-uji.test",
        return_rss_mocks=True,
    )

    assert result["status"] == "completed"
    discover_rss_mock.assert_called_once()
    collect_rss_mock.assert_called_once()

def test_retry_queue_saves_article_successfully():
    result, db, extract_mock = _run_collection_retry_test(
        extract_side_effect=[
            httpx.ConnectError("Koneksi awal gagal"),
            {
                "title": "Judul Artikel Uji",
                "published_at": __import__("datetime").datetime(
                    2026, 11, 19, 10, 0
                ),
                "content": "Isi artikel untuk pengujian retry.",
                "description": "Ringkasan artikel uji.",
                "author": "Redaksi",
            },
        ],
        article_query_results=[None, None],
    )

    assert result["status"] == "completed"
    assert result["articles_saved"] == 1
    assert result["articles_failed"] == 0
    assert db.add.call_count == 2
    assert extract_mock.call_count == 2
    assert extract_mock.call_args_list[1].kwargs["max_attempts"] == 1


def test_retry_queue_counts_failed_retry():
    result, db, extract_mock = _run_collection_retry_test(
        extract_side_effect=[
            httpx.ConnectError("Koneksi awal gagal"),
            httpx.ConnectError("Retry tetap gagal"),
        ],
        article_query_results=[None, None],
    )

    assert result["status"] == "completed"
    assert result["articles_saved"] == 0
    assert result["articles_failed"] == 1
    assert db.add.call_count == 1
    assert extract_mock.call_count == 2


def test_retry_queue_skips_existing_canonical_url():
    existing_article = MagicMock()

    result, db, extract_mock = _run_collection_retry_test(
        extract_side_effect=[
            httpx.ConnectError("Koneksi awal gagal"),
        ],
        article_query_results=[None, existing_article],
    )

    assert result["status"] == "completed"
    assert result["articles_saved"] == 0
    assert result["duplicates_skipped"] == 1
    assert db.add.call_count == 1
    assert extract_mock.call_count == 1


def test_retry_queue_accepts_same_content_with_different_url():
    result, db, extract_mock = _run_collection_retry_test(
        extract_side_effect=[
            httpx.ConnectError("Koneksi awal gagal"),
            {
                "title": "Judul Artikel Uji",
                "published_at": datetime(2026, 11, 19, 10, 0),
                "content": "Isi artikel untuk pengujian retry.",
                "description": "Ringkasan artikel uji.",
                "author": "Redaksi",
            },
        ],
        article_query_results=[None, None],
    )

    assert result["status"] == "completed"
    assert result["articles_saved"] == 1
    assert result["duplicates_skipped"] == 0
    assert db.add.call_count == 2
    assert extract_mock.call_count == 2


def test_rss_published_takes_priority_over_sitemap_lastmod():
    sitemap_candidate = {
        "url": "https://media-uji.test/artikel/contoh",
        "title": "Judul dari Sitemap",
        "date": datetime(2026, 11, 18, 10, 0),
        "date_source": "sitemap_lastmod",
    }

    rss_candidate = {
        "url": "https://media-uji.test/artikel/contoh",
        "title": "Judul dari RSS",
        "date": datetime(2026, 11, 19, 10, 0),
        "date_source": "rss_published",
    }

    result, db, extract_mock = _run_collection_retry_test(
        extract_side_effect=[
            {
                "title": "Judul Artikel Uji",
                "published_at": None,
                "content": "Konten artikel RSS.",
                "description": "Ringkasan",
                "author": "Redaksi",
            }
        ],
        article_query_results=[None, None],
        sitemap_candidates=[sitemap_candidate],
        rss_candidates=[rss_candidate],
    )

    assert result["status"] == "completed"
    assert result["articles_found"] == 1
    assert result["articles_saved"] == 1
    assert result["articles_failed"] == 0
    assert db.add.call_count == 2


def test_page_publication_date_takes_priority_over_rss_date():
    result, db, extract_mock = _run_collection_retry_test(
        extract_side_effect=[
            {
                "title": "Judul Artikel Uji",
                "published_at": datetime(2026, 11, 18, 10, 0),
                "content": "Konten artikel dengan tanggal lama.",
                "description": "Ringkasan",
                "author": "Redaksi",
            }
        ],
        article_query_results=[None],
        candidate_date=datetime(2026, 11, 19, 10, 0),
        candidate_date_source="rss_published",
    )

    assert result["status"] == "completed"
    assert result["articles_saved"] == 0
    assert result["articles_failed"] == 0
    assert db.add.call_count == 1


def test_sitemap_lastmod_is_not_used_as_publication_date():
    sitemap_candidate = {
        "url": "https://media-uji.test/artikel/contoh",
        "title": "Judul dari Sitemap",
        "date": datetime(2026, 11, 19, 10, 0),
        "date_source": "sitemap_lastmod",
    }

    result, db, extract_mock = _run_collection_retry_test(
        extract_side_effect=[
            {
                "title": "Judul Artikel Uji",
                "published_at": None,
                "content": "Konten tanpa tanggal publikasi.",
                "description": "Ringkasan",
                "author": "Redaksi",
            }
        ],
        article_query_results=[None],
        sitemap_candidates=[sitemap_candidate],
        rss_candidates=[],
    )

    assert result["status"] == "completed"
    assert result["articles_saved"] == 0
    assert result["articles_failed"] == 1
    assert db.add.call_count == 1


def test_retry_uses_separate_http_client():
    result, db, extract_mock = _run_collection_retry_test(
        extract_side_effect=[
            httpx.ConnectError("Koneksi awal gagal"),
            {
                "title": "Judul Artikel Uji",
                "published_at": datetime(2026, 11, 19, 10, 0),
                "content": "Isi artikel untuk pengujian retry.",
                "description": "Ringkasan",
                "author": "Redaksi",
            },
        ],
        article_query_results=[None, None, None],
    )

    assert result["status"] == "completed"
    assert result["articles_saved"] == 1
    assert extract_mock.call_count == 2

    main_client = extract_mock.call_args_list[0].args[0]
    retry_client = extract_mock.call_args_list[1].args[0]

    assert main_client is not retry_client

def test_collection_respects_max_articles_per_source():
    candidates = [
        {
            "url": f"https://media-uji.test/artikel/{i}",
            "title": f"Judul Kandidat {i}",
            "date": datetime(2026, 11, 19, 10, 0),
            "date_source": "rss_published",
        }
        for i in range(7)
    ]

    articles = [
        {
            "title": f"Judul Artikel {i}",
            "published_at": datetime(2026, 11, 19, 10, 0),
            "content": f"Konten unik artikel nomor {i}.",
            "description": "Ringkasan",
            "author": "Redaksi",
        }
        for i in range(7)
    ]

    result, db, extract_mock = _run_collection_retry_test(
        extract_side_effect=articles,
        article_query_results=[None] * 14,
        rss_candidates=candidates,
    )

    assert result["status"] == "completed"
    assert result["articles_found"] == 7
    assert result["articles_saved"] == 5
    assert result["articles_failed"] == 0
    assert extract_mock.call_count == 5

    # Satu pemanggilan untuk CollectionRun dan lima artikel.
    assert db.add.call_count == 6


def test_memo_sitemap_candidate_limit_is_50():
    result, db, extract_mock, sitemap_mock = (
        _run_collection_retry_test(
            extract_side_effect=[],
            article_query_results=[],
            sitemap_candidates=[],
            rss_candidates=[],
            source_name="MEMO Online",
            source_base_url="https://www.memoonline.co.id",
            return_sitemap_mock=True,
        )
    )

    assert result["status"] == "completed"
    sitemap_mock.assert_called_once()

    assert (
        sitemap_mock.call_args.kwargs["max_urls"]
        == collector.MAX_CANDIDATES_PER_SOURCE
        == 50
    )

def test_other_source_sitemap_has_no_special_candidate_limit():
    result, db, extract_mock, sitemap_mock = (
        _run_collection_retry_test(
            extract_side_effect=[],
            article_query_results=[],
            sitemap_candidates=[],
            rss_candidates=[],
            source_name="Media Uji",
            source_base_url="https://media-uji.test",
            return_sitemap_mock=True,
        )
    )

    assert result["status"] == "completed"
    sitemap_mock.assert_called_once()

    assert sitemap_mock.call_args.kwargs["max_urls"] is None
