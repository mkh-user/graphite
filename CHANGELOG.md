# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [unreleased]

### Added

- Guides and documentation.

## [0.2.2] - 2026-02-12

### Fixed

- Version number not incremented.

## [0.2.1] - 2026-02-12

> [!Note]
> This version isn't available at PyPI because of versioning issues.

### Changed

- Move examples to `examples/` directory.

### Fixed

- Both direction traverse selects both nodes.

## [0.2] - 2026-02-04

### Added

- JSON-based serialization.
- `Migration` class.
- Custom exceptions.
- Unit tests.

### Changed

- Save / load logic for database.
- Split module into multiple files. (Same API)

### Deprecated

- Pickle-based serialization.

### Security

- Validation for saved databases.

## [0.1.3] - 2026-01-30

### Added

- Documentation for examples.
- `pytest` workflow.
- `pylint` workflow.

### Fixed

- Project description mismatch.
- Old README content.

## [0.1.2] - 2026-01-30

### Added

- Automated PyPI releases.
- Error reporting in .where() queries.
- Error reporting for invalid date values.
- `parse()` function for engine.

### Changed

- Change the method of detecting the type of node and relation creation blocks.

## [0.1.1] - 2026-01-29

> [!Note]
> This version was removed from GitHub because of build issues.

### Fixed

- Fix project structure.

## [0.1] - 2026-01-25

> [!Note]
> This version was removed from PyPI and GitHub because of project structure issues.

### Added

- Core implementation.

[unreleased]: https://github.com/mkh-user/graphite/compare/v0.2.2...HEAD
[0.2.2]: https://github.com/mkh-user/graphite/releases/tag/v0.2.2
[0.2.1]: https://github.com/mkh-user/graphite/releases/tag/v0.2.1
[0.2]: https://github.com/mkh-user/graphite/releases/tag/v0.2
[0.1.3]: https://github.com/mkh-user/graphite/releases/tag/v0.1.3
[0.1.2]: https://github.com/mkh-user/graphite/releases/tag/v0.1.2
[0.1.1]: https://github.com/mkh-user/graphite/releases/tag/v0.1.1
<!--Following link will open v0.1.1 because v0.1 was removed.-->
[0.1]: https://github.com/mkh-user/graphite/releases/tag/v0.1.1