from unittest.mock import MagicMock, patch

from app import collector


def test_source_validation_config_parses_json():
    source = MagicMock()
    source.validation_config = '{"homepage_discovery": true, "discovery_methods": ["homepage"]}'

    config = collector._source_validation_config(source)

    assert config["homepage_discovery"] is True
    assert config["discovery_methods"] == ["homepage"]


def test_source_validation_config_handles_invalid_json():
    source = MagicMock()
    source.validation_config = "bukan-json"

    assert collector._source_validation_config(source) == {}


def test_homepage_discovery_returns_only_allowed_article_urls():
    client = MagicMock()
    response = MagicMock()
    response.text = "<html>homepage</html>"
    response.raise_for_status.return_value = None
    robots = MagicMock()
    robots.can_fetch.side_effect = lambda agent, url: "/artikel-dilarang" not in url

    discovered = [
        "https://www.memoonline.co.id/berita/artikel-satu",
        "https://www.memoonline.co.id/berita/artikel-dilarang",
    ]

    with patch.object(collector, "validation_safe_get", return_value=response):
        with patch.object(
            collector,
            "_extract_homepage_article_urls",
            return_value=discovered,
        ):
            with patch.object(collector, "validate_public_url") as validate:
                result = collector.collect_homepage_urls(
                    client,
                    "https://www.memoonline.co.id/",
                    robots,
                    max_urls=10,
                )

    assert [item["url"] for item in result] == [discovered[0]]
    assert result[0]["date_source"] == "homepage"
    assert validate.call_count == 2


def test_homepage_discovery_fails_closed_when_homepage_request_fails():
    robots = MagicMock()

    with patch.object(
        collector,
        "validation_safe_get",
        side_effect=RuntimeError("domain tidak aman"),
    ):
        result = collector.collect_homepage_urls(
            MagicMock(),
            "https://www.memoonline.co.id/",
            robots,
        )

    assert result == []
    robots.can_fetch.assert_not_called()
