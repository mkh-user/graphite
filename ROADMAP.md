# Graphite Roadmap

**Last Updated:** 2026-07-13

---

## Mission

Provide an **in-memory** graph engine for **Python developers** who treat graphs as **a core part of their project** — with the **simplicity** of working with a Python object, the power of **schema-based** data, and **no need to set up a separate service**.

---

## Guiding Principles

- **Simplicity in use:** All *core* operations are available through a single engine object (`graphite.engine()`). More specialized operations (such as more advanced algorithms) will be accessible via submodules.
- **Reliable performance:** Ideal scalability up to 500,000 nodes with acceptable response times.
- **Python-native:** No external service dependencies, but with potential future extensibility for interaction via optional endpoints in standard distribution.
- **User-centric documentation:** Every feature is demonstrated with concrete examples from the knowledge graph domain or equivalent relevant fields.

---

## Development Focus Areas

- **Documentation & Release** — Improving documentation and preparing for version 1.0 release
- **Storage Backend** — Enhancing storage performance and security
- **Query Engine** — Optimizing the query engine and adding indexes
- **API Extensibility** — Optional capabilities like HTTP layer (for future consideration)
- **Advanced Graph Support** — Support for undirected graphs, custom weights, and beyond
- **Tooling & Integration** — CLI tool, relational database integration, and Jupyter plugin

---

## Progress Tracking

For the complete task list, current status, and progress tracking of version 1.0, please refer to the following Issue:

🔗 **[[Tracker] Graphite 1.0 - #19](https://github.com/mkh-user/graphite/issues/19)**

---

## How to Contribute

New proposals, bug reports, and prioritization discussions are handled through **Issues** and **Discussions** in the GitHub repository.
