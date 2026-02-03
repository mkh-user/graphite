"""
Node and relation instance objects
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional
from .types import NodeType, RelationType

@dataclass
class Node:
	"""
	A node in database. Has a base type, id, and properties from base type (and it's parent
	type recursively).
	"""
	type_name: str
	id: str
	values: Dict[str, Any]
	type_ref: Optional[NodeType] = None

	def get(self, field_name: str) -> Any:
		"""Get a field from this node."""
		return self.values.get(field_name)

	def __getitem__(self, key):
		return self.get(key)

	def __repr__(self):
		return f"Node({self.type_name}:{self.id})"

@dataclass
class Relation:
	"""
	A relation between two nodes in database. Has a base type, source and target node IDs,
	and properties from base type.
	"""
	type_name: str
	from_node: str  # node id
	to_node: str  # node id
	values: Dict[str, Any]
	type_ref: Optional[RelationType] = None

	def get(self, field_name: str) -> Any:
		"""Get a field from this relation."""
		return self.values.get(field_name)

	def __repr__(self):
		return f"Relation({self.type_name}:{self.from_node}->{self.to_node})"
