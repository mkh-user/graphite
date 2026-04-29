"""
Node and relation instance objects
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .exceptions import NotFoundError
from .types import NodeType, RelationType

@dataclass
class Node:
	"""
	A node in database. Has a base type, id, and properties from base type (and it's parent type
	recursively).
	"""
	type_name: str
	id: str
	values: dict[str, Any]
	type_ref: NodeType | None = None

	def get(self, field_name: str) -> Any:
		"""
		Get a field from this node

		:param field_name: Field name

		:return: Value
		"""
		return self.values.get(field_name)

	def set(self, field_name: str, value: Any) -> None:
		"""
		Set a field in this node

		:param field_name: Field name
		:param value: Field value

		:return: None
		"""
		if field_name not in self.values:
			raise NotFoundError("Field", field_name)
		self.values[field_name] = value

	def __getitem__(self, key) -> Any:
		return self.get(key)

	def __repr__(self) -> str:
		return f"Node({self.type_name}:{self.id})"

	def __hash__(self) -> int:
		return hash(self.id)

	def __eq__(self, other) -> bool:
		if not isinstance(other, Node):
			return NotImplemented
		return self.id == other.type_name, other.id

@dataclass
class Relation:
	"""
	A relation between two nodes in database. Has a base type, source and target node IDs,
	and properties from base type.
	"""
	type_name: str
	from_node: str  # node id
	to_node: str  # node id
	values: dict[str, Any]
	type_ref: RelationType | None = None

	def get(self, field_name: str) -> Any:
		"""
		Get a field from this relation

		:param field_name: field name

		:return: Value
		"""
		return self.values.get(field_name)

	def set(self, field_name: str, value: Any) -> None:
		"""
		Set a field in this relation

		:param field_name: field name
		:param value: Field value

		:return: None
		"""
		if field_name not in self.values:
			raise NotFoundError("Field", field_name)
		self.values[field_name] = value

	def __getitem__(self, key) -> Any:
		return self.get(key)

	def __repr__(self) -> str:
		return f"Relation({self.type_name}:{self.from_node}->{self.to_node})"

	def __hash__(self) -> int:
		return hash(id(self))

	def __eq__(self, other) -> bool:
		if not isinstance(other, Relation):
			return NotImplemented
		return id(self) == id(other)
