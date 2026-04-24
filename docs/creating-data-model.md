# Creating Your Data Model

This document explains how to model data using Graphite’s graph model.

> **Note**
> This document does not cover all Graphite features or general database design principles.

---

## Engine Setup

> **Note**
> See the [Quickstart](/quickstart) guide for a complete setup walkthrough.

First, install Graphite:

```bash
pip install graphitedb
```

Then import it and create an engine instance:

```python
import graphite

engine = graphite.engine()
```

The engine is responsible for parsing DSL definitions, storing data, and executing graph operations.

---

## Defining Node Types

Before inserting data, define the structure of your domain. Start by identifying the core object types in your system.

In this example, we model employment relationships. The primary entities are `Person` and `Company`.

```python
node_types = """
node Person
name: string

node Company
"""

engine.parse(node_types)
```

This defines:

* A `Person` node type with a `name` field of type `string`.
* A `Company` node type without fields.

> **Note**
> You can define node types, relation types, nodes, and relations in a single `.parse()` call if needed.

---

### Node Type Inheritance

Graphite supports inheritance using the `from` keyword. This allows you to share fields across related types.

```python
node_types = """
node Object
price: int

node Chair from Object
height: float

node Book from Object
author: string
"""
```

In this example:

* `Object` defines a shared `price` field.
* `Chair` inherits `price` and adds `height`.
* `Book` inherits `price` and adds `author`.

Child node types include all fields from their base types.

---

## Defining Relation Types

Relations define how nodes connect and what data is associated with those connections.

For modeling jobs, a `WORKS_AT` relation is appropriate:

```python
relation_types = """
relation WORKS_AT
Person -> Company
salary: int
"""

engine.parse(relation_types)
```

This defines:

* A relation type named `WORKS_AT`
* Source node type: `Person`
* Target node type: `Company`
* A `salary` field of type `int`

The engine enforces the source and target type constraints.

---

## Creating Nodes

After defining types, you can create nodes using either DSL or direct engine methods.

### Using DSL

```python
engine.parse("graphite_games, Company")

engine.parse("""
database_home, Company

joe, Person, Joe
admin, Person, John
""")
```

### Using Engine API

```python
engine.create_node("alice", "Person", "Alice")
```

Each node:

* Has a unique ID
* Has a base type
* Stores field values in the order defined by its type hierarchy

---

## Creating Relations

Relations connect nodes according to relation type definitions.

### Using DSL

```python
engine.parse("""
alice -[WORKS_AT, 30000]-> graphite_games
alice -[WORKS_AT, 1000]-> database_home
""")
```

The DSL pattern is:

```
source -[RELATION_TYPE, field_values]-> target
```

### Using Engine API

```python
engine.create_relation("joe", "graphite_games", "WORKS_AT", 30000)
```

> **Note**
> Undirected relations can be defined using:
>
> ```
> source -[RELATION_TYPE, field_values]- target
> ```

---

## Next Steps

Once your data model and data are defined, you can query the graph, traverse relationships, and perform analysis using Graphite’s APIs. These operations are covered in the next documents.
