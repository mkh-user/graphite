# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [unreleased]

### Added

- **Query:** Using type-based indexing for relation existent checks

### Fixed

- **Query:** Fixed calling `remove()` query for invalid nodes raises `NotFoundError`
- **Query:** Make all queries atomic
- **Query:** Raise `TypeError` when all values are non-numeric in given field for `min()`, `max()`, `avg()`

### Removed

- Unused `types.Field.default`

## [0.3] - 2026-04-25

### Added

- Guides and documentation
- Complete in-code documentation
- **Engine API:** `undefine_node()`, `undefine_relation()`, `remove_node()`, `remove_relation()`, `is_node_from_type()`
- `set()` function for `Node` and `Relation`
- **Query:** `set()`, `remove()`, `remove_relations()`, `with_type()`, `with_field()`, `paginate()`, `union()`, `exclude()`, `intersect()`, `sum()`, `avg()`, `min()`, `max()`, `group_by()`, `relations()`
- **Query:** Starting query from all nodes with `engine.query.all()`
- **Query:** Traverse in all relation types
- Validate save file version before load
- Validate source and target node types
- Enhanced error handling, warnings, error messages, and checks
- Add `accept_any_extension` to `load_safe()` to disable file extension check
- Additional type hints
- **Query:** `include_parent_types` for `whit_type()` to check parent types too
- **Query:** `auto_distinct` for `union()` to make result nodes distinct automatically
- **Query:** Add all relation to query when starting point is `.all()`

### Changed

- **Query:** Keep all relations after `limit()` query
- Return of `Migration.convert_pickle_to_json()` from `bool` to `None`, Standard error handling used
- `SchemaError` -> `ParseError`

### Deprecated

- `load_dsl()` -> `parse()`

### Fixed

- Fixed order while saving database for relations
- Fixed support for comments in properties section
- Fixed weak line type detection in DSL
- Relation types can't be bidirectional and reverse named at the same time anymore
- `parser.parse_relation_instance()` return signature
- Fixed editor confusion at query chain
- Fixed `TypeError` instead of `ConditionError` at query condition evaluation
- Fixed wrong example in `QueryBuilder` docstrings
- Fixed silent `None` or `[]` for invalid `get_node()`, `get_relations_from()`, `get_relations_to()` calls
- Fixed wrong error handling for `Migration` class

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

[unreleased]: https://github.com/mkh-user/graphite/compare/v0.3...HEAD
[0.3]: https://github.com/mkh-user/graphite/releases/tag/v0.3
[0.2.2]: https://github.com/mkh-user/graphite/releases/tag/v0.2.2
[0.2.1]: https://github.com/mkh-user/graphite/releases/tag/v0.2.1
[0.2]: https://github.com/mkh-user/graphite/releases/tag/v0.2
[0.1.3]: https://github.com/mkh-user/graphite/releases/tag/v0.1.3
[0.1.2]: https://github.com/mkh-user/graphite/releases/tag/v0.1.2
[0.1.1]: https://github.com/mkh-user/graphite/releases/tag/v0.1.1
<!--Following link will open v0.1.1 because v0.1 was removed.-->
[0.1]: https://github.com/mkh-user/graphite/releases/tag/v0.1.1
