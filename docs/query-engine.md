# Query Engine

This document describes Graphite’s fluent query engine. Queries start from `engine.query` and return a chainable `QueryResult` object.

The entry point is the `QueryBuilder`, which allows starting a query from a node type.

---

## Starting a Query

You can start a query from a node type:

```python
engine.query.Person
engine.query.Company
```

Accessing `engine.query.Person` returns all nodes whose type is `Person`.

To start from all nodes:

```python
engine.query.all()
```

If the node type does not exist, a `NotFoundError` is raised.

---

## Filtering

### `where()`

Filters nodes using either:

* A string condition
* A callable (lambda)

#### String Condition

```python
engine.query.Person.where("age >= 18")
engine.query.Person.where("name == 'Alice'")
```

Supported operators:

* `==` or `=`
* `!=`
* `>`
* `<`
* `>=`
* `<=`

Date fields are parsed using `YYYY-MM-DD` format.

#### Lambda Condition

```python
engine.query.Person.where(lambda n: n.get("age") > 18)
```

If the condition fails to evaluate, a `ConditionError` is raised.

---

### `with_type()`

Filter by exact node type:

```python
engine.query.all().with_type("Person")
```

---

### `with_fields()`

Filter nodes that contain specific fields:

```python
engine.query.all().with_fields("name", "age")
```

---

## Traversal

Traversal moves across relations and returns connected nodes.

### Outgoing

```python
engine.query.Person.outgoing("WORKS_AT")
```

Equivalent to:

```python
engine.query.Person.traverse("WORKS_AT", direction="outgoing")
```

---

### Incoming

```python
engine.query.Company.incoming("WORKS_AT")
```

---

### Both Directions

```python
engine.query.Person.both("FRIEND_OF")
```

If no relation type is provided, all relation types are considered.

Traversal returns a new `QueryResult` containing:

* Connected nodes
* Traversed relations

---

## Result Control

### `limit()`

```python
engine.query.Person.limit(10)
```

---

### `paginate()`

```python
engine.query.Person.paginate(page=2, per_page=10)
```

---

### `distinct()`

Removes duplicate nodes:

```python
engine.query.Person.outgoing("WORKS_AT").distinct()
```

---

### `order_by()`

```python
engine.query.Person.order_by("age")
engine.query.Person.order_by("age", descending=True)
```

---

## Aggregation

### `count()`

```python
engine.query.Person.count()
```

---

### `sum()`

```python
engine.query.Person.sum("salary")
```

Non-numeric values are ignored.

---

### `avg()`

```python
engine.query.Person.avg("age")
```

---

### `min()` / `max()`

```python
engine.query.Person.min("age")
engine.query.Person.max("age")
```

---

### `group_by()`

```python
engine.query.Person.group_by("age")
```

Returns a dictionary mapping field values to lists of nodes.

---

## Combining Queries

### `union()`

```python
q1 = engine.query.Person.where("age > 30")
q2 = engine.query.Person.where("age < 20")

q1.union(q2)
```

May produce duplicates; use `.distinct()` if necessary.

---

### `exclude()`

```python
engine.query.Person.exclude(
    engine.query.Person.where("age < 18")
)
```

---

### `intersect()`

```python
engine.query.Person.where("age > 18").intersect(
    engine.query.Person.where("age < 30")
)
```

!!! tip

    This query is implemented for complex use cases; for simple cases, it is recommended to use `.where()` chains:
    ```python
    engine.query.Person.where("age > 18").where("age < 30")
    ```

---

## Mutations

!!! important

    "Mutation" queries directly apply their effects to the engine. To remove findings from the query (and not actually
    delete nodes and relationships from the engine), you can use `.exclude()` (ramove) and `.intersect()` (select).

### `set()`

Updates field values on all result nodes:

```python
engine.query.Person.where("name == 'Alice'").set(age=30)
```

Changes are applied directly to the engine.

If a field does not exist, a `NotFoundError` is raised.

---

### `remove()`

Removes result nodes:

```python
engine.query.Person.where("age < 0").remove()
```

---

### `remove_relations()`

Removes relations in the current result:

```python
engine.query.Person.outgoing("WORKS_AT").remove_relations()
```

---

## Accessing Results

### Get Nodes

```python
nodes = engine.query.Person.get()
```

---

### First Result

```python
node = engine.query.Person.first()
```

---

### Get IDs

```python
ids = engine.query.Person.ids()
```

---

### Get Relations

```python
relations = engine.query.Person.outgoing("WORKS_AT").relations()
```

---

## Execution Model

* Queries are evaluated eagerly.
* Each chained call returns a new `QueryResult`.
* Nodes and relations are stored in memory.
* Mutating operations (`set`, `remove`) modify engine state directly.

---

## Summary

The Query Engine provides:

* Type-based entry points (`engine.query.Type`)
* Chainable filtering and traversal
* Aggregation and grouping
* Query composition (union, intersect, exclude)
* Direct mutation capabilities

It is designed to provide a concise, expressive interface for graph exploration while preserving type constraints enforced by the engine.
