# Graphite Module-Level Reference

This document provides the API reference for objects available directly from the `graphite` module.

All items described here can be accessed after importing the module:

```python
import graphite
```

---

# Functions

## `node(node_type: str, **fields) -> str`

Generates a DSL string for a node type definition.

This function does **not** register the type in the engine.
It only returns a formatted DSL string that can be passed to `engine.parse()`.

### Parameters

* `node_type`: Name of the node type.
* `**fields`: Field definitions in the form `field_name="type"`.

### Returns

* A formatted DSL string representing the node definition.

### Example

```python
definition = graphite.node("Person", name="string", age="int")

print(definition)
```

Result:

```
node Person
name: string
age: int
```

---

## `relation(name: str, from_type: str, to_type: str, **fields) -> str`

Generates a DSL string for a relation type definition.

This function only produces a DSL string.
It does not validate or register the relation until passed to `engine.parse()`.

### Parameters

* `name`: Relation name.
* `from_type`: Source node type.
* `to_type`: Target node type.
* `**fields`: Field definitions in the form `field_name="type"`.

### Returns

* A formatted DSL string representing the relation definition.

### Example

```python
definition = graphite.relation(
    "WORKS_AT",
    "Person",
    "Company",
    salary="int"
)

print(definition)
```

Result:

```
relation WORKS_AT
Person -> Company
salary: int
```

### Limitations

* Does not support undirected (`both`) relations.
* Does not support reverse relation names.
* Advanced DSL features must be written manually.

---

## `engine() -> GraphiteEngine`

Creates and returns a new [`GraphiteEngine`](/engine) instance.

Each engine instance maintains its own:

* Node types
* Relation types
* Nodes
* Relations

### Example

```python
engine = graphite.engine()
```

---

# Classes

## `SecurityWarning` *(Warning)*

A marker warning class used for security-related concerns within Graphite.

It subclasses Python’s `Warning` type and may be raised or emitted when unsafe or potentially dangerous operations are detected.

---

# Usage Pattern

A typical workflow using module-level helpers:

```python
import graphite

engine = graphite.engine()

engine.parse(
    graphite.node("Person", name="string", age="int")
)

engine.parse(
    graphite.relation("WORKS_AT", "Person", "Company", salary="int")
)
```

You may use `engine()` only.
All definitions can also be written directly in DSL format.
