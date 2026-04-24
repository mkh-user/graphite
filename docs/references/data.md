# Graphite data reference

This document provides the API reference for **nodes and relations**, main data classes in Graphite. For field types see
[Field Types section in DSL Reference](/dsl#3-field-types).

You can create a new node with [`engine.create_node()`](/engine#create_nodenode_type-str-node_id-str-values---node) (created node will be returned)
or a relation with [`engine.create_relation()`](/engine#create_relationfrom_id-str-to_id-str-rel_type-str-values---relation) (will be returned), or with DSL.
You can also access to a node with queries (`engine.query` and `query.nodes()`) or direct [engine.get_node()](/engine#get_nodenode_id-str---optionalnode).

# Classes

## `Node`

A node in database.

### `get(field_name: str) -> Any`

Get a field from this node.

### `set(field_name: str, value: Any) -> None`

Set a field in this node.

## `Relation`

A relation between two nodes in database.

### `get(field_name: str) -> Any`

Get a field from this relation.

### `set(field_name: str, value: Any) -> None`

Set a field in this relation.
