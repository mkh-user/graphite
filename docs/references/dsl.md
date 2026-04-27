# DSL Reference

This document defines the formal syntax and behavior of Graphite’s Domain-Specific Language (DSL).

The DSL is used to:

* Define node types
* Define relation types
* Create nodes
* Create relations

All constructs may be provided in a single `engine.parse()` call.

---

# 1. Document Structure

A DSL document may contain the following elements:

1. Node type definitions
2. Relation type definitions
3. Node instances
4. Relation instances

Definitions must appear before they are used.

Example:

```python
engine.parse("""
node Person
name: string

relation WORKS_AT
Person -> Company
salary: int

alice, Person, Alice
graphite_games, Company

alice -[WORKS_AT, 30000]-> graphite_games
""")
```

---

# 2. Node Type Definition

## Syntax

```
node <TypeName> [from <BaseType>]
<field_name>: <type>
<field_name>: <type>
```

## Rules

* `<TypeName>` must be unique.
* Field names must be unique within the type.
* Fields are ordered.
* Field order determines value position during node creation.

### Minimal Definition

```
node Company
```

Defines a node type with no fields.

### With Fields

```
node Person
name: string
age: int
```

---

## 2.1 Inheritance

Node types may inherit from a single base type:

```
node Object
price: int

node Book from Object
author: string
```

### Inheritance Rules

* Only single inheritance is supported.
* Child types inherit all fields from the base type.
* Field order is:

  1. Base type fields
  2. Child type fields
* Overriding inherited fields is not allowed.

---

# 3. Field Types

Supported scalar types:

* `string`
* `int`
* `float`
* `bool`
* `date`

### Date Format

Date values must follow:

```
YYYY-MM-DD
```

Invalid date formats raise `DateParseError`.

---

# 4. Relation Type Definition

## Syntax

```
relation <RelationName> [both] [reverse <ReverseName>]
<SourceType> <arrow> <TargetType>
<field_name>: <type>
```

Where:

* `<arrow>` is:

  * `->` for directed relations
  * `-` for undirected relations (used with `both`)

---

## 4.1 Directed Relation

```
relation WORKS_AT
Person -> Company
salary: int
```

Defines a directed relation from `Person` to `Company`.

---

## 4.2 Undirected Relation

```
relation FRIEND both
Person - Person
```

Rules:

* `both` declares the relation as undirected.
* The connection pattern must use `-` instead of `->`.

---

## 4.3 Reverse Names (Experimental)

A relation may declare a reverse name:

```
relation PARENT_OF reverse CHILD_OF
Person -> Person
```

This allows creating relations using either name:

```
bob -[PARENT_OF]-> james
james -[CHILD_OF]-> bob
```

### Notes

* Reverse names are experimental.
* Behavior may change in future versions.
* Production usage is discouraged until stabilized.

---

# 5. Node Creation

## Syntax

```
<node_id>, <TypeName>[, field_value_1, field_value_2, ...]
```

## Rules

* `<node_id>` must be unique.
* `<TypeName>` must exist.
* Field values must match the declared field order.
* Inherited fields must be provided first.
* Field count must exactly match the type definition.
* Field values must match declared types.

### Example

```
alice, Person, Alice, 30
```

### Without Fields

```
graphite_games, Company
```

---

# 6. Relation Creation

## 6.1 Directed Relation Instance

### Syntax

```
<source_id> -[<RelationName>[, field_values...]]-> <target_id>
```

### Example

```
alice -[WORKS_AT, 30000]-> graphite_games
```

### Rules

* Source node must exist.
* Target node must exist.
* Relation type must exist.
* Source and target types must match the relation definition.
* Field values must match declared field order.
* Field count must match relation type definition.

---

## 6.2 Undirected Relation Instance

### Syntax

```
<source_id> -[<RelationName>[, field_values...]]- <target_id>
```

Example:

```
alice -[FRIEND]- bob
```

---

# 7. Comments

Single-line comments are supported:

```
# This is a comment
```

Rules:

* Lines starting with `#` are ignored.
* Inline comments are not supported.

---

# 8. Parsing and Validation Rules

* Parsing is sequential.
* Type definitions must appear before usage.
* Node IDs must be unique.
* Type names must be unique.
* Field names must be unique per type.
* Field count must match schema.
* Type mismatches result in validation errors.
* Invalid source/target combinations are rejected.

---

# 9. Error Categories

DSL parsing and validation may raise:

* `ParseError`
* `ValidationError`
* `NotFoundError`
* `InvalidPropertiesError`
* `FieldError`
* `DateParseError`

Exact error types depend on failure category.

---

# 10. Complete Example

```
node Person
name: string
age: int

node Company

relation WORKS_AT
Person -> Company
salary: int

alice, Person, Alice, 30
bob, Person, Bob, 25
graphite_games, Company

alice -[WORKS_AT, 30000]-> graphite_games
bob -[WORKS_AT, 25000]-> graphite_games
```

---

# 11. Execution Model

`engine.parse()` processes input in the following order:

1. Registers type definitions
2. Creates node instances
3. Creates relation instances
4. Performs validation during each step

Parsing is eager. Validation failures abort execution.

---

This DSL is intentionally minimal, strictly typed, and schema-driven.
