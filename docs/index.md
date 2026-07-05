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
