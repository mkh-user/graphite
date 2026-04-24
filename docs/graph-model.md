# Graph Model

This document describes the core graph model used in Graphite and its main components.

## Overview

Graphite uses an object-oriented graph model designed to integrate naturally with Python applications. The workflow is structured and type-driven:

1. Define **node types** and **relation types**.
2. Create **nodes** based on node types.
3. Create **relations** between nodes based on relation types.
4. Update and query the graph for traversal, path finding, and analysis.

The model enforces structure at the type level while allowing flexible graph operations at runtime.

---

## Node Types

A **Node Type** defines the schema for a group of nodes. It specifies:

* A set of fields (attributes).
* The type identity of the node.

Node types are also used in relation definitions to restrict valid source and target nodes.

**Example**

You may define:

* `Person`
* `Company`

Each node created from these types must conform to their respective field definitions.

---

## Relation Types

A **Relation Type** defines the structure and constraints of a relation (edge). It specifies:

* A set of fields for the relation.
* A connection pattern:

  * Source node type
  * Target node type

This ensures that only compatible node types can be connected.

**Example**

A relation type:

* `WORKS_AT`

  * Source: `Person`
  * Target: `Company`

This guarantees that `WORKS_AT` relations can only connect a `Person` node to a `Company` node.

---

## Nodes

A **Node** is an instance of a node type. Each node has:

* A unique identifier (ID)
* A base node type
* A set of field values defined by its type

**Example**

* `alice` (type: `Person`)
* `graphite_films` (type: `Company`)

Nodes store data and serve as vertices in the graph structure.

---

## Relations

A **Relation** is an instance of a relation type and represents a directed connection between two nodes.

Each relation:

* Has a relation type
* Connects a source node to a target node
* May contain additional field values

Relations are the core of graph modeling, enabling traversal, dependency tracking, and structural analysis.

---

This type-driven design provides structural safety while maintaining the flexibility expected from a graph database.
