# Graphite Project Roadmap

**Last Updated:** 2026-07-01

---

## Project Mission

To provide an **in-memory** graph engine for **Python developers** who treat graphs as **a core part of their project** — with the **simplicity** of working with a Python object, the power of **schema-based** data, and **no need to set up a separate service**.

---

## Guiding Principles

- **Simplicity in use:** All *core* operations are available through a single engine object (`graphite.engine()`). More specialized operations (such as more advanced algorithms) will be accessible via submodules.
- **Reliable performance:** Ideal scalability up to 500,000 nodes with acceptable response times.
- **Python-native:** No external service dependencies, but with potential future extensibility for interaction via optional endpoints in standard distribution.
- **User-centric documentation:** Every feature is demonstrated with concrete examples from the knowledge graph domain or equivalent relevant fields.

---

## Development Checklist

### General

- [x] Improve error handling
- [ ] Add support for undirected graphs (while preserving the current directed relationship model via the `both` flag)
- [ ] (idea stage) Investigate and potentially add support for Temporal Graphs based on user demand
- [ ] Allow users to define **custom weight calculation functions** (instead of static field-based weights)
- [ ] Errors refactor
- [ ] Use caching when possible
  - [x] Cache node type fields
- [x] Be scalable to 1M nodes, 1M relations, with <2.5 GB memory usage - [done with 1.4 GB memory usage!](https://github.com/mkh-user/graphite/actions/runs/29027133185) 
- [ ] Algorithms
  - [x] BFS
  - [x] Distance-based shortest path
  - [ ] Weight-based shortest path

### Schema & Data Manipulation

- [x] Improve block-detection logic
- [x] Support in-block comments
- [x] Support inline comments
- [x] Replace `load_dsl()` with `parse()`
- [x] Support removing definitions
- [x] Validate node types in relation creation
- [x] Batched removes
- [x] Support single quotes in DSL
- [ ] Validate value types in all cases
  - [ ] Add `any` field type
- [ ] Make skipping DSL easier
- [ ] Add SQL-like features and more to fields (default, validation, etc.)
- [ ] Add `time` field type
- [ ] Complete data types support

### Documentation

- [ ] Documentation
  - [x] Basic proof
  - [ ] Basic proof rewrite
  - [ ] Automated API reference in documentation
    - [ ] Refactor docstrings
  - [ ] Stable (complete proof)
    - [ ] At least 3 complete examples from the knowledge graph domain (or equivalent fields)
- [ ] Examples
  - [ ] Improve examples
- [ ] Create a sample repository containing a simple knowledge graph (e.g., movies, scientific papers, or real-world data)
- [ ] Finalize the feature list for the first official release (version 1.0)

### Persistence

- [x] Improve Security: Replace Pickle with JSON
- [x] Migration utils
- [x] Schema validation
- [x] Stabilize save file order
- [x] Spec version check
- [ ] Redesign save/load API
- [ ] Improve Performance: Replace JSON format with a secure binary format
- [ ] Ensure backward compatibility for loading legacy JSON files
- [ ] Remove deprecated Pickle migration utilities
- [ ] Remove unsafe load support
- [ ] Add optional compression to reduce storage file size

### Query Engine

- [x] Add aggregation queries
- [x] `query.all()`
- [x] Untyped traverse
- [x] Distinct results always
- [x] Atomicity
- [ ] Improve IDE support
- [ ] Add basic indexes on frequently used property fields for faster node/edge lookups (by user)
- [ ] Redesign the query engine to optimize execution order (replace current step-by-step execution without planning)
- [ ] (idea stage) Full-featured Query Optimizer (like those in large databases)
- [ ] Document query performance with approximate timings for various scenarios (up to 500,000 nodes)

### Maintenance

- [x] Pytest, Pylint, Type check CI
- [x] 100% Test coverage
- [x] Complete types
- [x] Multiple files splitting
- [ ] Review developer docs and guides

### API Extensibility & Interoperability

- [ ] (idea stage) Create a lightweight HTTP layer as an endpoint to interact with the graph from outside Python (services, other languages)
  - [ ] Support running the engine in `Server Mode` to handle concurrent requests
    - [ ] Support transactions
  - [ ] Document endpoint usage with `curl` examples or simple request samples
  - [ ] Move this subsections to an issue

### Tooling & Integration

- [ ] (idea stage) Build a simple CLI for statistical reporting on the graph (with potential for additional capabilities later)
- [ ] Provide integration with relational databases for initial data ingestion (seamless import)
- [ ] (idea stage) Create a sample plugin for graph visualization in Jupyter Notebook

---

## How to Contribute & Prioritize

Reviewing and implementing items on this checklist, as well as proposing new ones, will be handled through **Discussions** and **Issues** in the GitHub repository. Please search click on links after each item to see related issue / discussion.
