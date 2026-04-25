"""
Data, relation, and node type classes for Graphite database
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, List, Optional

class DataType(Enum):
	"""
	Valid data types in graphite. Used in nodes and relations properties.
	"""
	STRING = "string"
	INT = "int"
	DATE = "date"
	FLOAT = "float"
	BOOL = "bool"

@dataclass
class Field:
	"""
	A data field (property) for nodes and relations.
	"""
	name: str
	dtype: DataType
	default: Any = None

@dataclass
class NodeType:
	"""
	A defined node type (with ``node ...`` block in dsl or ``GraphiteEngine.define_node()``).
	Each node type has a name (in snake_case usually), and optional list of fields (properties).
	Supports optional parent node type.
	"""
	name: str
	fields: List[Field] = field(default_factory=list)
	parent: Optional[NodeType] = None

	def get_all_fields(self) -> List[Field]:
		"""Get all fields including inherited ones"""
		fields = self.fields.copy()
		if self.parent:
			fields = self.parent.get_all_fields() + fields
		return fields

	def __hash__(self):
		return hash(self.name)

@dataclass
class RelationType:
	"""
	A defined relation type (with ``relation ...`` block in dsl or
	``GraphiteEngine.define_relation()``). Each relation type has a name (in UPPER_SNAKE_CASE
	usually), and optional list of fields (properties). A relation type can be from one node
	type to another.
	"""
	name: str
	from_type: str
	to_type: str
	fields: List[Field] = field(default_factory=list)
	reverse_name: Optional[str] = None
	is_bidirectional: bool = False

	def __hash__(self):
		return hash(self.name)
