# Security Policy

## 1. Purpose

This document describes the security principles, implemented safeguards, and security-related development requirements for GPR Media Intelligence.

The application retrieves content from external media websites. Therefore, outbound HTTP requests, URL validation, redirects, response handling, and source configuration must be treated as security-sensitive operations.

The current implementation is primarily intended for local use and development.

It must not be assumed to be production-hardened or safe for unrestricted public deployment.

## 2. Security Objectives

The security objectives are to:

- Reduce the risk of Server-Side Request Forgery (SSRF).
- Restrict outbound requests to valid public web destinations.
- Prevent unsafe redirect handling.
- Limit response sizes and resource consumption.
- Avoid exposing credentials and secrets.
- Preserve the integrity of archived data.
- Keep validation and collection operations within defined boundaries.
- Ensure that security controls remain testable.

## 3. Implemented URL Validation Controls

The source validation module applies restrictions before making outbound requests.

### 3.1 Allowed Schemes

Only the following URL schemes are accepted:

- `http`
- `https`

Other schemes must be rejected.

### 3.2 URL Credentials

URLs containing embedded username or password credentials must be rejected.

Example of a disallowed URL:

```text
https://username:password@example.com/
```

### 3.3 Allowed Ports

Outbound URLs are restricted to:

- Port 80
- Port 443

Other ports must be rejected.

### 3.4 DNS and IP Address Validation

The validation flow resolves hostnames and rejects destinations that resolve to non-public IP addresses.

This helps reduce the risk of requests targeting:
- Localhost.
- Private network addresses.
- Link-local addresses.
- Other non-public IP ranges.

DNS validation is applied during real outbound request handling.

**Important limitation:** DNS validation immediately before an HTTP request does not by itself guarantee that the HTTP transport connects to the exact IP address that was validated. DNS rebinding and time-of-check/time-of-use risks require additional transport-level protections.

Future hardening should consider binding validated DNS results to the actual connection process.

### 3.5 Redirect Validation

Automatic redirect following is disabled in the secured request flow.

Redirects are handled manually so that each redirect target can be validated before another outbound request is made.

The current implementation:
- Supports standard HTTP redirect status codes.
- Validates redirect targets.
- Applies host allowlist restrictions.
- Enforces a maximum of five redirects.

Redirect validation must not be bypassed by introducing another HTTP request path.

### 3.6 Response Size Limits

Responses are subject to a maximum size of 4 MB.

The implementation checks available response size information and the response body to reduce the risk of excessive memory consumption.

Future improvements should also consider streaming response limits and decompressed response sizes.

## 4. Source Validation and Collection Security

Media source validation and article collection must follow the same outbound request safety principles.

The application should:
- Validate candidate URLs before fetching them.
- Validate redirect destinations.
- Respect robots.txt where applicable.
- Avoid requesting unrelated resources.
- Exclude known static and non-article paths during discovery.
- Apply bounded retries.
- Avoid unbounded collection operations.
- Keep source-specific configuration under application control.

Source validation samples are read-only and must not be inserted into the article archive.

## 5. Host Allowlist

Source validation uses host restrictions to prevent requests from being redirected to unrelated destinations.

The validated source host context must be preserved when following redirects.

Any future changes to hostname matching must consider:
- Subdomain handling.
- Canonical hostname normalization.
- Internationalized domain names.
- Redirect targets.
- DNS resolution results.

Do not replace hostname validation with a loose substring comparison.

## 6. Input Validation

All user-controlled values that influence application behavior must be validated.

Examples include:
- Media source names.
- Base URLs.
- Source IDs.
- Collection date ranges.
- Search and filtering parameters.
- Source validation configuration.

Database operations should use SQLAlchemy or other parameterized query mechanisms.

Do not construct SQL statements by concatenating untrusted input.

## 7. Secrets and Configuration

Sensitive information must not be committed to the repository.

Examples include:
- API keys.
- Authentication tokens.
- Passwords.
- Database credentials.
- Private keys.
- Environment-specific secrets.

Development configuration should use environment variables or local configuration files excluded by `.gitignore`.

The repository must not contain:
- `.env` files with real secrets.
- Private database files.
- Local logs containing sensitive information.
- Unnecessary backups.
- Private keys or credentials.

## 8. Database and Archive Integrity

The database stores collected articles and source history.

Security-related development must preserve existing archive data.

Requirements:
- Do not delete the database during normal upgrades.
- Back up the database before schema changes.
- Use controlled migrations for schema modifications.
- Preserve the composite source-scoped duplicate constraint.
- Do not introduce global URL uniqueness.
- Do not use `content_hash` as a duplicate rejection condition.
- Avoid destructive database operations unless explicitly authorized and necessary.

## 9. Error Handling and Logging

Application errors should provide enough information for debugging without unnecessarily exposing sensitive details.

Do not log:
- Passwords.
- API keys.
- Authentication tokens.
- Private credentials.
- Sensitive environment variables.

External website errors should be handled without allowing a single failed source to crash unrelated collection operations.

Collection and validation failures should be recorded in their respective history records where supported.

## 10. Testing Security Controls

Security-related changes must include appropriate tests.

Important test areas include:

- Rejection of unsupported URL schemes.
- Rejection of URLs containing credentials.
- Rejection of unsupported ports.
- Rejection of private and non-public IP destinations.
- DNS resolution validation.
- Redirect target validation.
- Maximum redirect enforcement.
- Host allowlist enforcement.
- Response size limits.
- Candidate URL validation.
- Safe handling of malformed URLs.
- Regression tests for existing collection behavior.

Tests should use controlled mock HTTP clients and test domains where appropriate.

A passing test suite does not replace security review or testing against realistic network conditions.

## 11. Known Limitations and Future Hardening

The current safeguards reduce several common risks but do not establish complete production security.

Further work should consider:

- Transport-level DNS pinning or equivalent protections against DNS rebinding.
- Streaming response limits and decompression safeguards.
- Connection and read timeouts.
- Rate limiting and per-source request budgets.
- Background job isolation.
- Authentication and authorization.
- CSRF protection where applicable to browser-based state-changing operations.
- Secure session and cookie configuration if authentication is introduced.
- Dependency vulnerability scanning.
- Centralized security logging and monitoring.
- Production deployment hardening.
- Regular security reviews and penetration testing.

These are future hardening areas and must not be represented as already implemented unless verified in the application.

## 12. Reporting a Security Vulnerability

Please do not publish details of an exploitable vulnerability in a public issue before the project maintainer has had an opportunity to assess it.

When reporting a vulnerability, include:
- A short description of the issue.
- Affected application module or feature.
- Steps to reproduce.
- Expected behavior.
- Actual behavior.
- Potential impact.
- Suggested mitigation, if known.

Avoid including real credentials, private data, or sensitive archive contents in a report.

The project maintainer should review the report and coordinate an appropriate fix before public disclosure.

## 13. Security Development Principles

All contributors should follow these principles:

1. Validate external destinations before making outbound requests.
2. Never bypass redirect validation.
3. Keep network operations bounded.
4. Do not expose secrets.
5. Preserve archived data.
6. Test security-sensitive changes.
7. Document known limitations honestly.
8. Prefer explicit allowlists and validation over permissive assumptions.

Security is a continuous development responsibility, not a one-time implementation stage.
