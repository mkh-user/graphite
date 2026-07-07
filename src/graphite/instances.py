"""Node and relation instance objects"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .exceptions import NotFoundError
from .types import NodeType, RelationType

@dataclass
class Node:
	"""A node in the database. It has a base type, ID, and properties from base type (and it's
	parent type recursively).

	Node class is designed to be instanced by an engine:
	```python
	alice = engine.create_node("Person", "alice", "Alice", 43, "alice@email.com")
	```

	Attributes:
		type_name: Name of base `NodeType`.
		id: The unique identifier of node.
		    !!! Note
		        `id` is designed to be persistent and unique across database, you can set in
		        manually or with `uuid`. Changing ID of a node breaks its references.

		    !!! Tip
		        Nodes are hashable and comparable by ID, so nodes with same ID is equal in `==`
		        operator and will replace each other if added in the same engine.
		values: A dictionary holding field values. Use `set()` and `get()` methods to use it.
		    !!! Tip
		        Values can be accessed with `node["field_name"]` too.
		type_ref: Reference to `NodeType`.
	"""
	type_name: str
	id: str
	values: dict[str, Any]
	type_ref: NodeType | None = None

	def get(self, field_name: str) -> Any:
		"""Returns value of a field in this node.

		Args:
		    field_name: Field name.

		Returns:
		    Value.
		"""
		return self.values.get(field_name)

	def set(self, field_name: str, value: Any) -> None:
		"""Sets a field in this node.

		Args:
		    field_name: Field name.
		    value: Value to set.

		!!! Warning "Subject To Change"
		    Currently type of values can be invalid. This may be fixed in next versions.
		"""
		if field_name not in self.values:
			raise NotFoundError("Field", field_name)
		self.values[field_name] = value

	def __getitem__(self, key: str) -> Any:
		return self.get(key)

	def __repr__(self) -> str:
		return f"Node({self.type_name}:{self.id})"

	def __hash__(self) -> int:
		return hash(self.id)

	def __eq__(self, other: Any) -> bool:
		if isinstance(other, Node):
			return self.id == other.id
		return NotImplemented

@dataclass
class Relation:
	"""A relation between two nodes in the database. Has a base type, source and target node IDs,
	and properties from base type.

	Relation class is designed to be instanced by an engine:
	```python
	friendship = engine.create_relation("alice", "bob", "FRIEND")
	```

	!!! Note
	    Relations are designed to be always unique! Even when you load a database from save of
	    another one. It means you have same relation between same nodes, with same type,
	    and even same values. In short, Graphite is a **multigraph**. They are hashable based on
	    Python's `id()` function.

	    !!! Warning "Subject To Change"
	        Other type of graphs, is planned to be available.

	Attributes:
		type_name: Name of base `RelationType`.
		from_node: Source node's ID.
		to_node: Target node's ID.
		values: A dictionary holding field values. Use `set()` and `get()` methods to use it.
		    !!! Tip
		        Values can be accessed with `node["field_name"]` too.
		type_ref: Reference to `RelationType`.
	"""
	type_name: str
	from_node: str
	to_node: str
	values: dict[str, Any]
	type_ref: RelationType | None = None

	def get(self, field_name: str) -> Any:
		"""Returns value of a field in this relation.

		Args:
		    field_name: Field name.

		Returns:
		    Value.
		"""
		return self.values.get(field_name)

	def set(self, field_name: str, value: Any) -> None:
		"""Sets a field in this relation.

		Args:
		    field_name: Field name.
		    value: Value to set.

		!!! Warning "Subject To Change"
		    Currently type of values can be invalid. This may be fixed in next versions.
		"""
		if field_name not in self.values:
			raise NotFoundError("Field", field_name)
		self.values[field_name] = value

	def __getitem__(self, key: str) -> Any:
		return self.get(key)

	def __repr__(self) -> str:
		return f"Relation({self.type_name}:{self.from_node}->{self.to_node})"

	def __hash__(self) -> int:
		return hash(id(self))

	def __eq__(self, other: object) -> bool:
		if not isinstance(other, Relation):
			return NotImplemented
		return id(self) == id(other)
