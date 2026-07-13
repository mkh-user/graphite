# Graphite Project Mission Document

This page shows an overview of what you can expect from Graphite to do it as well as possible.

## Mission Statement

> **Graphite** is an in-memory graph engine for Python developers who treat graphs as a core part of their project. It provides a structured, schema-enforced graph database that runs entirely inside your Python process — with no separate service to install or manage.

---

## Core Problem It Solves

Python developers working with structured graph data face a trilemma:

| Approach        | Problem                                                                 |
|-----------------|-------------------------------------------------------------------------|
| **Neo4j**       | Heavy, requires separate service, overkill for small-to-medium projects |
| **NetworkX**    | Designed for analysis, not for data management or persistence           |
| **SQL + JOINs** | Slow, complex logic, hard to maintain for graph relationships           |

**Graphite bridges this gap** — providing database-like structure with library-like simplicity.

---

## Target Audience

- Python developers who use graphs as a **primary component** of their project
- Teams building knowledge graphs, network topologies, entity-relationship systems, or graph-based data pipelines
- Projects that are too small for Neo4j but too structured for NetworkX

---

## What Graphite Is NOT

- ❌ A graph database for **billions** or **tens of millions** of nodes
- ❌ A **distributed** or **cloud-native** graph database
- ❌ A **relational database**
- ❌ A **purely analytical** database (like specialized OLAP systems)
- ❌ A **non structured database**
