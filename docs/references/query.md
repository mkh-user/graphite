# Query reference

This document provides the API reference for query engine of graphite module.

All items in this list can be accessed with `engine.query.all()` and `engine.query.<node_type>`

# Functions

## `set(**values) -> QeuryResult`

Change result nodes' value

This query mutates nodes inplace and changes will be applied to engine directly
This query raises ``NotFoundError`` for nodes without compatible fields, use
``.with_fields()`` to ensure all fields are valid.

## `remove() -> QueryResult`

Remove current result nodes

## `remove_relations() -> QueryResult`

Remove current result relations

## `where(condition: Union[str, Callable]) -> QueryResult`

Filter nodes based on given condition

`ConditionError` at any error
String conditions can be like: `age > 18`

## `with_type(node_type: str) -> QueryResult`

Filter nodes based on type

## `with_fields(*fiels: str) -> QueryResult`

Filter nodes with given fields

## `traverse(relation_type: Optional[str] = None, direction: str = 'outgoing') -> QueryResult`

Traverse relations from current nodes
Returns a new query result with connected nodes and traversed relations
Removes duplicate nodes in result

Traverse in all relation types when `relation_type` is `None`

> **Note:**  
> Please use `outgoing()`, `incoming()`, `both()` for safer API instead of this function.

## `outgoing(relation_type: Optional[str] = None) -> QueryResult`

Traverse outgoing relations

> **Note:** This is a wrapper function for `traverse()`.

## `incoming(relation_type: Optional[str] = None) -> QueryResult`

Traverse incoming relations

> **Note:** This is a wrapper function for `traverse()`.

## `both(relation_type: Optional[str] = None) -> QueryResult`

Traverse both incoming and outgoing relations

## `limit(n: int) -> QueryResult`

Limit number of nodes in result (not relations)

## `paginate(page: int, per_page: int) -> QueryResult`

Returns specified page of nodes (and all relation)
Returns empty result for negative (or 0) `per_page`
Page index start from 0

## `union(query: QueryResult) -> QueryResult`

Merge query result
This query can produce duplicates, use `.distinct()` to remove duplicates

## `exclude(query: QueryResult) -> QueryResult`

Remove result of given query from current query result (nodes and relations)

## `intersect(query: QueryResult) -> QueryResult`

Just keeps shared nodes and relations between current and given queries

## `distinct() -> QueryResult`

Get distinct nodes (removes duplicates)

## `order_by(by_field: str, descending: bool = False) -> QueryResult`

Order nodes by field

## `sum(field: str) -> float`

Sum of a field values in nodes

> **Note:** This query skips non-numeric values.
