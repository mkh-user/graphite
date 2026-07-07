# DSL Reference

This document defines the formal syntax and behavior of Graphite's Domain-Specific Language (DSL).

The DSL is used to:

- Define node types
- Define relation types
- Create nodes
- Create relations

This DSL is intentionally minimal, strictly typed, and schema-driven. All constructs may be provided in a single
[engine.parse()](../engine/#graphite.GraphiteEngine.parse) call.

## Data Types

Data Types are used in node type and relation type definitions to set what type of data should be used in given field.
All data types must be written in **lowercase**.

### `bool`

`true` or `false` flag, equal to Python's `bool`. `true` and `false` are `True` and `False` respectively in Python.
Parser is case-insensitive.

### `string`

A sequence of chars, equal to Python's `str`. Strings can be defined `"`, `'`, or without any quote wrapper. However,
wrapping is recommended because if your unwrapped string contain comma (`,`), it will be divided into multiple values.
And you can put quotes in strings with using other quote as wrapper.

### `int`

An integer number (without the decimal section), equal to Python's `int`.

### `float`

Floating point number, equal to Python's `float`. Both integer and decimal parts should be written even if `0`.

### `date`

A date, equal to Python's `datetime.date`. Should be written as `yyyy-mm-dd`, `0` prefix is required for both month and
day when value is single-digit.

## Document Structure

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

### Node Types

**Syntax:**

```text
node <TypeName> [from <BaseType>]
    <field_name>: <type>
    <field_name>: <type>
```

**Notes:**

- `<TypeName>` must be unique.
- Field names must be unique within the type.
- Fields are ordered.
- Field order determines value position during node creation.
- It's whitespace-insensitive, just `node`, `<TypeName>`, `from`, and `<BaseType>` should be separated by at least one
  space.
- Node types can be defined without any field.
- Node types may inherit from a base node type using `from` keyword:
    ```text
    node Object
        price: int

    node Book from Object
        author: string
    ```
- Only single base node type is supported for each node type (no `node Employee from ResourceOwner and TeamLead`), it
  should be a tree.
- Inheritance chain can have any length.
- Child types inherit all fields from the base type.
- Field order is:

  1. Base type fields
  2. Child type fields

- Overriding inherited fields is not allowed.

**Recommendations:**

- Use `PascalCase` for node type's name.
- Use `snake_case` for node type's fields.
- Indent fields for a smother visual experience.
- Add a space after field's color (`:`).
- Use power of inheritance to model real data as flexible as you want.

!!! Example
    ```text
    node Person
        name: string
        age: int
    ```

### Relation Types

**Syntax:**

```text
relation <RelationName> [both] [reverse <ReverseName>]
    <SourceType> <arrow> <TargetType>
    <field_name>: <type>
```

Where `<arrow>` is:

- `->` for directed relations
- `-` for undirected relations (used with `both`)

**Notes:**

- `both` declares the relation as undirected.
- A relation type can't be undirected and reverse-named at the same type.
- `<TypeName>` must be unique.
- Field names must be unique within the type.
- Fields are ordered.
- Field order determines value position during node creation.
- It's whitespace-insensitive, just `relation`, `<RelationName>`, `both` or `reverse`, and `<ReverseName>` should be
  separated by at least one space.
- Relation types can be defined without any field.

**Recommendation:**

- Use `SCREAMING_SNAKE_CASE` for relation type's name.
- Use `snake_case` for relation type's fields.
- Indent pattern and fields for a smother visual experience.
- Add a space after field's color (`:`).
- Use `-` instead on `->` in connection pattern of undirected relation types.

!!! Example:
    Directed Relation:
    ```text
    relation WORKS_AT
        Person -> Company
        salary: int
    ```

    Undirected Relation:
    ```text
    relation FRIEND both
        Person - Person
    ```

!!! Danger "Experimental"
    A relation may declare a reverse name:
    
    ```text
    relation PARENT_OF reverse CHILD_OF
        Person -> Person
    ```
    
    This allows creating relations using either name:
    
    ```text
    bob -[PARENT_OF]-> james
    james -[CHILD_OF]-> bob
    ```
    
    !!! Note
        - Reverse names are experimental.
        - Behavior may change in future versions.
        - Production usage is discouraged until stabilized.

### Nodes

**Syntax:**

```text
<TypeName>, <node_id>[, field_value_1, field_value_2, ...]
```

**Notes:**

- `<node_id>` must be unique.
- `<TypeName>` must exist.
- Field values must match the declared field order.
- Inherited fields must be provided first.
- Field count must exactly match the type definition.
- Field values must match declared types.
- Values must be passed in same line.

**Recommendations:**

- Use `snake_case` for node IDs or use `uuid` (`v4`) to generate IDs automatically.

!!! Example
    ```text
    alice, Person, Alice, 30
    ```

    Without Fields:
    ```text
    graphite_games, Company
    ```

### Relations

**Syntax:**

Directed:
```text
<source_id> -[<RelationName>[, field_values...]]-> <target_id>
```

!!! Example
    ```text
    alice -[WORKS_AT, 30000]-> graphite_games
    ```

Undirected:
```text
<source_id> -[<RelationName>[, field_values...]]- <target_id>
```

!!! Example
    ```text
    alice -[FRIEND]- bob
    ```

**Notes:**

- Source node must exist.
- Target node must exist.
- Relation type must exist.
- Source and target types must match the relation definition.
- Field values must match declared field order.
- Field count must match relation type definition.
- Field types must match defined data types.
- No line break is allowed.

### Comments

Single-line comments are supported:

```
# This is a comment
```

Rules:

- Lines starting with `#` are ignored.
- Comments between blocks (node type or relation type definition) are supported.
- Inline comments are not supported yet.

## Parsing and Validation Rules

- Parsing is sequential, not parallel.
- Type definitions must appear before usage.
- Node IDs must be unique.
- Type names must be unique.
- Field names must be unique per type.
- Field count must match schema.
- Type mismatches result in validation errors.
- Invalid source/target combinations are rejected.

!!! Example "Complete Example"
    ```text
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
