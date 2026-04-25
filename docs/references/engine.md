# Graphite engine reference

This document provides the API reference for `GraphiteEngine` class.

All items described here can be accessed after creating a new instance:

```python
import graphite

engine = graphite.engine()
```

---

# Functions

## `define_node(definition: str) -> None`

Define a node type from DSL string

Only supports one section starting with `node `.

You can use [`graphite.node()`](/module#nodenode_type-str-fields---str) to generate `definition`, see [DSL Reference](/dsl)
for syntax and roles.

### Example

```python
engine.define_node("""
node Person
name: string
age: int
""")
```

## `define_relation(definition: str) -> None`

Define a relation type from DSL string

Only supports one section starting with `relation `.

You can use [`graphite.relation()`](/module#relationname-str-from_type-str-to_type-str-fields---str) to generate `definition`, see [DSL Reference](/dsl)
for syntax and roles.

## `create_node(node_type: str, node_id: str, *values) -> Node`

Create a node instance

`node_type` is type of the node (defined with [`define_node`](#define_nodedefinition-str---none))
`node_id` is unique ID of the node
`values` are `field=value` parameters

`node_type` will be checked for existence (`NotFoundError` otherwise)

`values` count must match with node type fields count (recursively with base node types)

`values` values can be string (automatically parses to value) or direct value
maybe raise `DateParseError` for date-like but invalid values
converts parsed value to field's data type, and raises `FieldError` in any failure

Adds created node to database and returns new node object

## `create_relation(from_id: str, to_id: str, rel_type: str, *values) -> Relation`

Create a relation instance

`from_id` is source node ID
`to_id` is target node ID
`rel_type` is relation type (defined with [`define_relation`](#define_relationdefinition-str---none))
`values` are `field=value` parameters

`NotFoundError` for invalid `rel_type`, `from_id`, or `to_id`
`InvalidPropertiesError` for invalid count of `values` based on relation type's fields

`values` values can be string (automatically parses to value) or direct value
maybe raise `DateParseError` for date-like but invalid values
converts parsed value to field's data type, and raises `FieldError` in any failure

Adds created relation to database and returns new relation object

Creates reverse relation too when relation type is bidirectional (`both`)

## `get_node(node_id: str) -> Optional[Node]`

Get node by ID
`NotFoundError` for invalid IDs

## `get_nodes_of_type(node_type: str, with_subtypes: bool = True) -> List[Node]`

Get all nodes of a specific type

Returns empty array for invalid types
adds all nodes from subtypes when `with_subtypes` is `True`
returns a list of nodes

> **Note:** Using this function is not recommended directly in most cases, use `engine.query.node_type.nodes()` instead
> (for example `engine.query.Person.nodes()`)

## `get_relations_from(node_id: str, rel_type: str = None) -> List[Relation]`

Get relations from a node

Returns empty list for invalid types
when `rel_type` is not `None`, filters relations to given type

## `get_relations_to(node_id: str, rel_type: str = None) -> List[Relation]`

Get relations to a node

Returns empty list for invalid types
when `rel_type` is not `None`, filters relations to given type

## `undefine_node(node_type: str) -> None`

Undefine a node type

`NotFoundError` for invalid type
Removes all instances with `remove_node()`
Removes all relation types (and instances) referenced this node type with `undefine_relation()` (and internal `remove_relation()`s)
Removes all node types (and instances) defined from this node type (with `from` keyword) with `undefine_node()` (and internal `remove_node()`s)

## `undefine_relation(relation_type: str) -> None`

Undefine a relation type

`NotFoundError` fro invalid type
Removes all instances with `remove_relation()`
Removes reverse name created with `reverse` keyword if exists

## `remove_node(node: Union[Node, str]) -> None`

Removes a node instance

Supports both ID (`str`) and object (`Node`) as `node`

Removes all relations connected to this node

## `remove_relation(relation: Relation) -> None`

Removes a relation

`NotFoundError` for invalid relations

## `parse(dsl: str) -> None`

Parses a [Graphite DSL](/dsl) string and load it into database

Accepts node type definition, relation type definition, node instance, and relation in one string separated by empty line

## `load_dsl(dsl: str) -> None`

Loads a [Graphite DSL](/dsl) into database

> **Note:** This function is deprecated and will be removed in next versions, please use `parse()` instead.

## `save(filename: str) -> None`

Save a database to a single file using JSON

> **Note:** File name must end with `.json`

## `load_safe(filename: str, max_size_mb: Union[int, float] = 100, validate_schema: bool = True) -> None`

Safely load database with security checks

Supports maximum size limit and schema validation flag

`FileSizeError` at larger file than limit
`SafeLoadExtensionError` for invalid extension
`InvalidJSONError` for invalid json data
`TooNestedJSONError` for too recursion

## `load(filename: str, safe_mode: bool = True) -> None`

Load database from file

When `safe_mode` is true, use safe loading with schema validation
Otherwise can be used to load legacy JSON content

> **Note:** `pickle` support removed after 0.1, please use `graphite.Migration` class to convert your pickle files to JSON

## `clear() -> None`

Clears all data, including:
* Node types
* Relation types
* Nodes
* Relations
And all indexes used to store these items.

## `stats() -> Dict[str, Any]`

Get database statistics

Keys:
* `node_types`: count of node types
* `relation types`: count of relation types
* `nodes`: count of nodes
* `relationns`: count of relations

## `parse(data: str) -> None`

Parse DSL string into nodes and relations (structure or data)

> **Note:** Please add an empty line after node type or relation type blocks, other blocks (single-line node / relation creating) can be placed without any extra whitespace, just a line break needed.
