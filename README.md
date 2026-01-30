# Graphite

A clean, embedded graph database engine for Python.

---

**Graphite** is a lightweight yet flexible **graph database engine** implemented in pure Python.  
It is designed to model graph-like data inside large Python codebases **without introducing the complexity of an external database**.

---

## Features

### 🧩 Embedded by Design
Graphite is not a separate service or infrastructure dependency.  
It lives inside your project, evolves with it, and collaborates naturally with your existing code.

No servers. No ports. No deployment headaches.

---

### 🛠 Ready-made, Customizable Module
Graphite is intentionally simple and hackable.  
You can fork it, modify it, or deeply integrate it into your project without fighting rigid abstractions.

The database adapts to your project — not the other way around.

---

### 🐍 Native Python API
Everything is done through Python APIs.
No query strings.
DSL parsing is just an optional layer.
No context switching.

Your editor already knows how to autocomplete and document your queries.

---

### 🔍 Query? It’s Code.
Queries are built by chaining Python methods on the `QueryResult` object.

- Zero parsing cost
- Full IDE support
- Refactor-safe
- Debuggable

---

### 🔄 Runtime Evolution
Change structures, data, or even engine behavior **at runtime**.
No shutdowns.
No migrations.
No waiting.

---

### 🧱 Structure-Oriented Modeling
Define:
- node types
- relation types
- fields
- base types
- valid forms

Model your domain explicitly and safely.

---

### 🧬 Node Inheritance
Create base node types and extend them with shared properties and advanced relationships.

---

### ✨ Simple, Predictable Syntax
From defining structures to querying data, every step favors clarity and minimal syntax.

---

### 💾 Serializable
Persist the entire database into a single file.

---

## Installation

Install from **PyPI**:

```bash
pip install graphitedb
````

---

## Why Graphite?

Graphite was extracted from a **large production codebase** where Neo4j introduced more complexity than value.

Neo4j is a powerful tool — but in large projects, adding a separate graph database often increases:

* infrastructure complexity
* deployment cost
* maintenance burden
* cognitive load on developers

Graphite exists for cases where this cost is **not justified**.

It provides graph modeling **without adding another system to operate**.

---

## Example Usage

```python
import graphite

def example_complete_dsl_loading():
    engine = graphite.engine()

    complete_dsl = """
    # Define node types
    node Person
        name: string
        age: int

    node User from Person
        id: string
        email: string

    node Object
    node Book from Object
        title: string
        n_pages: int

    node Car from Object
        model: string
        year: int

    # Define relation types
    relation FRIEND both
        Person - Person
        since: date

    relation OWNER reverse OWNED_BY
        Person -> Object
        since: date
        purchased_at: date

    relation AUTHOR reverse AUTHORED_BY
        Person -> Book
        year: int

    # Create nodes
    User, user_1, "Joe Doe", 32, "joe4030", "joe@email.com"
    User, user_2, "Jane Smith", 28, "jane28", "jane@email.com"
    User, user_3, "Bob Wilson", 45, "bob45", "bob@email.com"
    User, user_4, "Alice Brown", 22, "alice22", "alice@email.com"

    Book, book_1, "The Great Gatsby", 180
    Book, book_2, "Python Programming", 450
    Book, book_3, "Graph Databases", 320

    Car, car_1, "Toyota Camry", 2020
    Car, car_2, "Honda Civic", 2018

    # Create relations
    user_1 -[FRIEND, 2020-05-15]- user_2
    user_1 -[FRIEND, 2019-08-22]- user_3
    user_2 -[FRIEND, 2021-01-10]- user_4

    user_1 -[OWNER, 2021-03-01, 2021-02-15]-> car_1
    user_2 -[OWNER, 2019-06-20, 2019-05-10]-> book_1
    user_3 -[OWNER, 2022-11-05, 2022-10-20]-> book_2

    user_1 -[AUTHOR, 2020]-> book_3
    user_2 -[AUTHOR, 2021]-> book_2
    """

    engine.load_dsl(complete_dsl)

    users = engine.query.User.get()
    print([u["name"] for u in users])

    return engine
```

More examples are available in `example.py` in the GitHub repository.
::contentReference[oaicite:0]{index=0}
```
