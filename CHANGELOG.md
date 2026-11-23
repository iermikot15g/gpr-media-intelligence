# Changelog

All notable changes to this project will be documented in this file.

This project follows a simplified version of [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning follows Semantic Versioning principles where practical.

## [Unreleased]

### Planned
- Media monitoring and trend analysis.
- Dashboard analytics and visualization.
- Automated reporting and export.
- AI-assisted media analysis and classification.
- Additional media source integrations.
- Expanded automated tests for application routes and user interface.

## [0.1.0] - 2026-11-23

Initial development snapshot covering Stages 1–4.

### Added

#### Stage 1 — Project Foundation
- Initial FastAPI application structure.
- SQLAlchemy database integration.
- SQLite database for local data storage.
- Core database models for media sources, news articles, and collection runs.
- Initial application templates and dashboard foundation.
- Automated test foundation using Pytest.

#### Stage 2 — Media Source Registration and Validation
- Media source registration through the dashboard.
- Source activation and deactivation controls.
- Source validation before activation.
- HTTP and HTTPS access checks.
- Robots.txt inspection.
- Sitemap and RSS/Atom feed discovery where available.
- Homepage-based article URL discovery as a fallback.
- Article page inspection and metadata extraction.
- Validation reports and validation history.
- Per-source validation configuration storage.
- Automatic validation invalidation when a source's base URL changes.

#### Collector Integration
- Article discovery through supported source mechanisms.
- Homepage fallback for sources without sitemap or RSS feeds.
- Article metadata extraction.
- Publication date extraction from article page metadata, with RSS fallback where applicable.
- Collection date range filtering.
- Source-specific collection selection.
- Collection run history and collection statistics.
- Retry handling for eligible collection failures.
- Source-scoped canonical URL duplicate detection.

#### Stage 3 — News Archive
- News article archive listing.
- Keyword-based article search.
- Media source filtering.
- Publication date filtering.
- Newest-first and oldest-first sorting.
- Pagination and filter preservation.
- Article detail page.
- Link to the original article on the source website.

#### Stage 4 — Collector Security Hardening
- Public URL validation for outbound requests.
- HTTP and HTTPS scheme restrictions.
- Rejection of URLs containing credentials.
- Restriction of outbound ports to 80 and 443.
- DNS resolution checks against non-public IP addresses.
- Redirect validation and manual redirect handling.
- Maximum redirect count enforcement.
- Response size limits.
- Host allowlist enforcement during source validation.
- Security checks integrated into the source validation and collection request flow.

### Changed
- Duplicate detection is scoped to each media source using normalized canonical URLs.
- Article content hashes are stored for analysis and integrity-related use, not as a duplicate rejection condition.
- Collection can target selected active sources instead of always processing every active source.
- Source selection defaults to validated and configured sources.
- Collector discovery and outbound request validation have been separated to support safer request handling and automated tests.

### Fixed
- Homepage discovery excludes known non-article paths and static resources.
- Sources without sitemap or RSS feeds can use homepage discovery as a fallback.
- Publication dates are not inferred from sitemap `lastmod` values.
- URL normalization and source-scoped duplicate checks are applied consistently in the collection flow.
- Test compatibility for simulated HTTP clients and test-domain URLs.

### Testing
- Python compilation check completed successfully.
- Automated test suite: **48 tests passed** on 2026-11-23.

### Notes
- This is an early development snapshot, not a production release.
- The application is currently designed for local use.
- Existing archived articles and database records must be preserved during future upgrades.
- Features listed under `Unreleased` are planned and are not represented as completed functionality.

---

## Changelog Guidelines

When adding a change, use one of the following categories:

- **Added** — new features.
- **Changed** — changes to existing functionality.
- **Deprecated** — features that will be removed in the future.
- **Removed** — removed features.
- **Fixed** — bug fixes.
- **Security** — security-related improvements.

Record meaningful changes under `Unreleased` first. Move them into a numbered release section when a release is formally published.
