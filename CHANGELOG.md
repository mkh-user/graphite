# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

<!--
## [unreleased]
-->

## [0.4] - 2026-04-29

### Added

- **Query:** Using type-based indexing for relation existent checks
- **Query:** `validate()` to keep result valid
- Benchmark suite
- Add support for removing multiple nodes at single `remove_node()` call with less complexity
- `id()` based indexing for relations
- `remove_nodes()` and `remove_relations()`
- Hash and compare support for nodes and relations
- **Query:** Add sort support for `limit()`, `paginate()`, and `first()`

### Changed

- **Query:** `set()` -> `set_val()`
- Return type of `get_nodes_of_type()`, `get_relations_from()`, `get_relations_to()` to `set`
- **Query:** return type of `get()`, `relations()`, and `ids()` to `set`
- **Query:** return type of `group_by()` to `dict[Any, set[Node]]`
- **Query:** `order_by()` returns sorted list of nodes (because internal query result is a `set`), use in-place sorting
  in `limit()`, `paginate()`, and `first()` instead.

### Fixed

- **Query:** Fixed calling `remove()` query for invalid nodes raises `NotFoundError`
- **Query:** Make all queries atomic
- **Query:** Raise `TypeError` when all values are non-numeric in given field for `min()`, `max()`, `avg()`
- Fixed always `'None'` for wrong-parsed string values
- Fixed replacing all used `node` and `relation` words in node / relation definitions
- Fixed outdated type hints
- Fixed slowness problems:
  - **Query:** `exclude()`: ~0.05 ms (10x faster)
  - **Query:** `intersect()`: ~0.20 ms (6x faster)
  - **Query:** `remove()`: ~0.55 ms (6x faster)
  - **Query:** Batch remove for `remove_relations()` (~6x faster)
  - `remove_node()`, `remove_nodes()`: ~0.55 ms (6x faster)
  - `load()`: ~45.22 ms (2x faster)
  - `save()`: ~251.76 ms (2x faster)
  - Improves for `define_node()`, `define_relation()`, `undefine_node()`, `undefine_relation()`, `create_node()`,
    `create_relation()`, `remove_relation()`
- Remove unused indexing from save file (no version change)

### Deprecated

- `remove_node()` -> `remove_nodes()`
- `remove_relation()` -> `remove_relations()`
- **Query:** `distinct()`: Query results are always unique
- **Query:** using internal `edges` attribute returns a set of relation object IDs (instead of list of relation objects)

### Removed

- Unused `types.Field.default`
- **Query:** `auto_distinct` from `union()`: Query results are always unique
- **Query:** `NotFoundError` for invalid start points (returns `None` instead)

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

[unreleased]: https://github.com/mkh-user/graphite/compare/v0.4...HEAD
[0.4]: https://github.com/mkh-user/graphite/releases/tag/v0.4
[0.3]: https://github.com/mkh-user/graphite/releases/tag/v0.3
[0.2.2]: https://github.com/mkh-user/graphite/releases/tag/v0.2.2
[0.2.1]: https://github.com/mkh-user/graphite/releases/tag/v0.2.1
[0.2]: https://github.com/mkh-user/graphite/releases/tag/v0.2
[0.1.3]: https://github.com/mkh-user/graphite/releases/tag/v0.1.3
[0.1.2]: https://github.com/mkh-user/graphite/releases/tag/v0.1.2
[0.1.1]: https://github.com/mkh-user/graphite/releases/tag/v0.1.1
<!--Following link will open v0.1.1 because v0.1 was removed.-->
[0.1]: https://github.com/mkh-user/graphite/releases/tag/v0.1.1
