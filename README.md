# Graphite

A clean, embedded graph database for Python.

---

**Graphite** is a lightweight yet flexible **graph database** implemented in pure Python. It is designed to model graph-like data inside Python codebases where graph is a core part of project, **without introducing the complexity of an external database**.

It's optimized for graphs with **up to 1M nodes**. Blazing fast as a pure Python database, outperforms NetworkX in both memory and speed, with 90x smaller package size. (Repeatable benchmark is available at `tests/benchmark.py`)

Documentation, with guides about usage or contributing and API reference is available here: <https://mkh-user.github.io/graphite>

📖 **[Full Mission & Scope →](https://mkh-user.github.io/graphite/mission)**

---

## Features

Graphite provides an easy and robust way to use any graph-like data in Python projects, it's designed to provide:

- **🧩 Embedded Database:** Database can live inside your project and in same process, so you can modify data and its structure fast, secure, and without any server-interaction headache.
- **⚙️ Hackable Behavior:** Graphite is designed to provide all common features out-of-the-box, but is completely clean-coded to help you hack it easy and fast to shape it for your special needs.
- **🐍 First-Class Python API:** Graphite uses its DSL as optional utility layer, so you can do anything directly with refactor-safe and intelligent Python API. Use DSL just when you like.
- **🔍 No Query String:** Chain well-documented methods to query on data, no learning, parsing, error vanishing, or guessing. Your Python IDE helps you when you write! Just type `engine.query` and start.
- **🔄 Runtime Evolution:** Customize data structure without shutdown, and deeply control behavior with flexible functions.
- **🧱 Structure-Oriented Modeling:** Define types of nodes and relations with features like inheritance, typed fields, and valid patterns. Model your domain explicitly and safely.
- **🧬 Node Inheritance:** Model real-world data easy and robust. Use subtypes, limited relations, inherited properties, complex validations.
- **✨ Really useful DSL:** Use DSL to create data with more readable and less-duplicated minimal syntax.
- **💾 Serializable:** Persist the entire database into a single JSON file.

---

## Installation

Install from **PyPI**:

```bash
pip install graphitedb
```

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

### Comparation

| Feature                 | Neo4j                               | Graphite                                  | Custom Graph Engine                     |
|-------------------------|-------------------------------------|-------------------------------------------|-----------------------------------------|
| **Bug Safety**          | **🥇Very High:**<br>Mature & tested | **🥈High:**<br>Unit tests, monitored      | **🥉Low-Medium:**<br>You manage testing |
| **Implementation**      | **🥈High:**<br>Setup & Cypher       | **🥇Low:**<br>Embed easily                | **🥉Very High:**<br>Build from scratch  |
| **Flexibility**         | **🥈High:**<br>Complex queries      | **🥉Medium:**<br>Limited but extendable   | **🥇Very High:**<br>Fully customizable  |
| **Performance**         | **🥇High:**<br>Optimized large data | **🥈Medium:**<br>Good for small/medium    | **❓Unknown:**<br>Depends on design      |
| **Scalability**         | **🥇High:**<br>Cluster & sharding   | **🥈Medium:**<br>Single-node & Base types | **❓Unknown:**<br>Possible but hard      |
| **Support / Community** | **🥇Very High:**<br>Large & active  | **🥈Medium:**<br>Docstrings only          | **🥉Low:**<br>Internal only             |
| **Customizability**     | **🥉Low:**<br>Limited to API        | **🥈High:**<br>Open source                | **🥇Very High:**<br>Full control        |
| **Ease of Use**         | **🥈Medium:**<br>Learn Cypher       | **🥇High:**<br>Quick & simple             | **🥉Low:**<br>Needs study & test        |

---

## Example Usage

```python
import graphite
from datetime import date

def basic_example():
    engine = graphite.engine()

    # Use DSL to define types and create data
    engine.parse("""
    # Node types with 'node '
    node Person
        # Indentation is optional
        name: string
        age: int
    """)
    # Define node types with in-editor hints no parsing cost
    engine.define_node("User", ("id", "string"), ("email", "string"), parent="Person")
    # parse() can include multiple blocks
    engine.parse("""
    # You can use node types to control abstractness:
    node Object

    node Book from Object
        title: string
        n_pages: int

    node Car from Object
        model: string
        year: int
    """)
    engine.define_relation(     # Same with parse():
        "FRIEND",               # relation FRIEND both
        "Person",               #     Person - Person
        "Person",               #     since: date
	    ("since", "date"),
        is_bidirectional=True
    )
    # Relation type blocks are same and node types
    engine.parse("""
    relation OWNER reverse OWNED_BY
        Person -> Object
        since: date
        purchased_at: date

    relation AUTHOR reverse AUTHORED_BY
        Person -> Book
        year: int
    """)

    # Add data now
    # Directly create nodes:
    engine.create_node("User", "user_1", "Joe Doe", 32, "joe4030", "joe@email.com")
    # Or with parse():
    engine.parse("""
    User, user_2, "Jane Smith", 28, "jane28", "jane@email.com"
    User, user_3, "Bob Wilson", 45, "bob45", "bob@email.com"
    User, user_4, "Alice Brown", 22, "alice22", "alice@email.com"

    Book, book_1, "The Great Gatsby", 180
    Book, book_2, "Python Programming", 450
    Book, book_3, "Graph Databases", 320

    Car, car_1, "Toyota Camry", 2020
    Car, car_2, "Honda Civic", 2018
    """)
    # And relations:
    # Dates can be parsed automatically:
    engine.create_relation("user_1", "user_2", "FRIEND", "2020-05-15")
    engine.create_relation("user_1", "user_3", "FRIEND", date(2019, 8, 22))
    engine.create_relation("user_2", "book_2", "AUTHOR", 2021)
    # You can pass parse_fields=True to parse all values from string to correct one:
    engine.create_relation("user_1", "book_3", "AUTHOR", "2020", parse_fields=True)
    # Is available in DSL too:
    engine.parse("""
    user_2 -[FRIEND, 2021-01-10]- user_4

    user_1 -[OWNER, 2021-03-01, 2021-02-15]-> car_1
    user_2 -[OWNER, 2019-06-20, 2019-05-10]-> book_1
    user_3 -[OWNER, 2022-11-05, 2022-10-20]-> book_2
    """)

    users = engine.query.User.get()
    print([u["name"] for u in users])

    return engine
```

More examples are available in `examples/` in the GitHub repository.

See <https://mkh-user.github.io/graphite> for the documentation and API reference.

---

_MIT 2026 Mahan Khalili_
