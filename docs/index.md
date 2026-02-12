# Graphite Docs

Welcome to Graphite documentation, here is a place for guides, examples, and API references of `graphite` module.

**Graphite** is a lightweight yet flexible **graph database engine** implemented in pure Python.
It is designed to model graph-like data inside large Python codebases **without introducing the complexity of an external database**.

## Features

- **🧩 Embedded by Design:**
  Graphite is not a separate service or infrastructure dependency.
  It lives inside your project, evolves with it, and collaborates naturally with your existing code.
  No servers. No ports. No deployment headaches.
- **🛠 Ready-made, Customizable Module:**
  Graphite is intentionally simple and hackable.
  You can fork it, modify it, or deeply integrate it into your project without fighting rigid abstractions.
  The database adapts to your project — not the other way around.
- **🐍 Native Python API:**
  Everything is done through Python APIs.
  No query strings.
  DSL parsing is just an optional layer.
  No context switching.
  Your editor already knows how to autocomplete and document your queries.
- **🔍 Query? It’s Code:**
  Queries are built by chaining Python functions on the `QueryResult` object.
  Zero parsing cost, Full IDE support, Refactor-safe, and Debuggable.
- **🔄 Runtime Evolution:**
  Change structures, data, or even engine behavior **at runtime**.
  No shutdowns. No migrations. No waiting.
- **🧱 Structure-Oriented Modeling:**
  Define node types, relation types, fields, base types, and valid forms. 
  Model your domain explicitly and safely.
- **🧬 Node Inheritance:**
  Create base node types and extend them with shared properties and advanced relationships.
- **✨ Simple, Predictable Syntax:**
  From defining structures to querying data, every step favors clarity and minimal syntax.
- **💾 Serializable:**
  Persist the entire database into a single file.

## Usage

See [quick start page](/quickstart) for installation guide and a usage example.

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

