# Graphite Docs

Welcome to Graphite documentation, here is a place for guides, examples, and API references of `graphite` module.

**Graphite** is a lightweight yet flexible **graph database engine** implemented in pure Python.
It is designed to model graph-like data inside large Python codebases **without introducing the complexity of an external database**.

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

## Usage

See [quick start page](quickstart) for installation guide and a usage example.

## Why Graphite?

Graphite was extracted from an **application project codebase** where a big-scale separate database (such as Neo4j, Memgraph, etc.) introduced more complexity than value.

Big-scale databases are powerful tools — but when you want to use graph databases in various devices or small / medium projects, adding a separate graph database often increases:

* Infrastructure complexity
* Deployment cost
* Maintenance burden
* Cognitive load on developers
* Security risks
* Server loads
* Limitation to special hardware

Graphite exists for cases where this cost is **not justified**.

It provides graph modeling **without adding another system to operate**.

### Comparation

This is a comparation between Graphite and similar tools, to know what you gain with using Graphite instead. Anyway, there are many more parameters to consider while selecting your database.

??? Note "Why we mention "Pure Python" as a benefit?"
    Compatibility issues are worse things when you want to ship for variable devices, so we have an important metric to validate Graphite: "Wherever you can run your Python code you can use Graphite seamlessly."

    This helps developers to use Graphite as a real embeddable database. You or your user can use modeled graph data with Graphite without installing any additional dependency (even a native C++ core) or connecting to a remote database.

| Database         | Smaller than Graphite (bundle and memory usage) | Faster than Graphite |         Pure Python          |
|------------------|:-----------------------------------------------:|:--------------------:|:----------------------------:|
| **NetworkX**     |                        ❌                        |          ❌           |       ✅ (Dependencies)       |
| **Silk-Graph**   |                        ❌                        |          ✅           |              ❌               |
| **Neo4j**        |                        ❌                        |  ✅ (In large scale)  |              ❌               |
| **Memgraph**     |                        ❌                        |          ✅           |              ❌               |
| **TerminusDB**   |                        ❌                        |          ❌           |   ✅ (Designed for server)    |
| **ArangoDB**     |                        ❌                        |          ✅           |              ❌               |
| **Kuzu**         |                        ❌                        |          ✅           |              ❌               |
| **SparrowDB**    |                        ❌                        |          ✅           |              ❌               |
| **NeuG**         |                        ❌                        |          ✅           | ❌ (Windows is not supported) |
| **FalkorDBLite** |                        ❌                        |          ✅           |              ❌               |
| **OverGraph**    |                        ❌                        |          ✅           |              ❌               |

As above, Graphite aims to be very lightweight and suitable to run anywhere, and fast as a pure Python database. Also, next table shows how you can use Graphite instead of a big-scale or custom database as a ready-to-use or starting point for your graph-like data:

| Feature                 | Big Databases                           | Graphite                                                    | Custom Graph Engine                     |
|-------------------------|-----------------------------------------|-------------------------------------------------------------|-----------------------------------------|
| **Bug Safety**          | **🥇Very High:**<br>Mature & tested     | **🥈High:**<br>100% Tested with unit tests                  | **🥉Low-Medium:**<br>You manage testing |
| **Implementation**      | **🥈High:**<br>Setup & Deploy           | **🥇Low:**<br>Embed easily                                  | **🥉Very High:**<br>Build from scratch  |
| **Flexibility**         | **🥉Medium:**<br>Complex queries        | **🥈High:**<br>Pure-Python and customizable                 | **🥇Very High:**<br>Fully customizable  |
| **Performance**         | **🥇High:**<br>Optimized for large data | **🥈Medium:**<br>Good for small/medium                      | **❓Unknown:**<br>Depends on design      |
| **Scalability**         | **🥇High:**<br>Cluster & sharding       | **🥈Medium:**<br>Scalable at data structure instead of size | **❓Unknown:**<br>Possible but hard      |
| **Support / Community** | **🥇Very High:**<br>Large & active      | **🥈Medium:**<br>Documentation, GitHub Discussions          | **🥉Low:**<br>Internal only             |
| **Customizability**     | **🥉Low:**<br>Limited to API            | **🥈High:**<br>Open source                                  | **🥇Very High:**<br>Full control        |
| **Ease of Use**         | **🥈Medium:**<br>Learn Cypher           | **🥇Very High:**<br>Quick & simple                          | **🥉Low:**<br>Needs study & test        |
