# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-10-31

First standalone release. Extracted from the `add_config_parameters` plugin of [pytest-plugins](https://github.com/aviz92/pytest-plugins), which never worked there.

### Added
- Each test class gets its own deep copy of the config, so a test that mutates it can't affect other classes.
- Clear usage errors at startup for a missing file, a directory, an unreadable file, or invalid / non-UTF-8 JSON.

### Changed
- The file is read once at startup instead of once per test class.
- Without `--config-path` nothing is registered, so no fixture runs.
- No runtime dependency other than pytest.

### Fixed
- `--config-path` takes a path (it was a value-less switch).
- The config is actually injected (the fixture checked an attribute pytest's config object doesn't have, so it never ran).

---
