"""
Serialization utils for Graphite databases
"""
import json
from collections import defaultdict
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Callable

from .instances import Node, Relation
from .types import DataType, Field, NodeType, RelationType

GRAPHITE_TYPE_FIELD = "__graphite_type__"
DEFAULT_FACTORY_FIELD = "__default_factory"

def _serialize_node(node: Node) -> dict[str, Any]:
	return {
		GRAPHITE_TYPE_FIELD: "Node",
		"type_name"        : node.type_name,
		"id"               : node.id,
		"values"           : node.values,
	}

def _serialize_relation(relation: Relation) -> dict[str, Any]:
	return {
		GRAPHITE_TYPE_FIELD: "Relation",
		"type_name"        : relation.type_name,
		"from_node"        : relation.from_node,
		"to_node"          : relation.to_node,
		"values"           : relation.values,
	}

def _serialize_node_type(node_type: NodeType) -> dict[str, Any]:
	return {
		GRAPHITE_TYPE_FIELD: "NodeType",
		"name"             : node_type.name,
		"parent"           : node_type.parent.name if node_type.parent else None,
		"fields"           : node_type.fields,
	}

def _serialize_relation_type(relation_type: RelationType) -> dict[str, Any]:
	return {
		GRAPHITE_TYPE_FIELD: "RelationType",
		"name"             : relation_type.name,
		"from_type"        : relation_type.from_type,
		"to_type"          : relation_type.to_type,
		"fields"           : relation_type.fields,
		"reverse_name"     : relation_type.reverse_name,
		"is_bidirectional" : relation_type.is_bidirectional,
	}

class GraphiteJSONEncoder(json.JSONEncoder):
	"""Custom JSON encoder for Graphite data structures"""

	# pylint: disable=too-many-return-statements
	def default(self, o: Any) -> Any:
		# Handle date/datetime objects
		if isinstance(o, (date, datetime)):
			return {
				GRAPHITE_TYPE_FIELD: "datetime",
				"value"            : o.isoformat(),
				"is_date"          : isinstance(o, date)
			}

		# Handle DataType enum specifically (must come before Enum)
		if isinstance(o, DataType):
			return {
				GRAPHITE_TYPE_FIELD: "datatype",
				"value"            : o.value
			}

		# Handle Enum objects
		if isinstance(o, Enum):
			return {
				GRAPHITE_TYPE_FIELD: "enum",
				"enum_class"       : type(o).__name__,
				"value"            : o.value
			}

		# Handle defaultdict
		if isinstance(o, defaultdict):
			result = dict(o)
			result[GRAPHITE_TYPE_FIELD] = "defaultdict"
			result[DEFAULT_FACTORY_FIELD] = o.default_factory.__name__ if o.default_factory else None
			return result

		# Handle Node and Relation instances
		if isinstance(o, Node):
			return _serialize_node(o)
		if isinstance(o, Relation):
			return _serialize_relation(o)

		# Handle NodeType and RelationType
		if isinstance(o, NodeType):
			return _serialize_node_type(o)
		if isinstance(o, RelationType):
			return _serialize_relation_type(o)

		# Handle Field
		if isinstance(o, Field):
			return {
				GRAPHITE_TYPE_FIELD: "Field",
				"name"             : o.name,
				"dtype"            : o.dtype,
			}

		# Handle dataclasses
		if is_dataclass(o) and not isinstance(o, type):
			# Convert to dict and add type info
			result = asdict(o)
			result[GRAPHITE_TYPE_FIELD] = type(o).__name__
			return result

		if isinstance(o, (dict, list)):
			return o

		return super().default(o)

# pylint: disable=too-many-return-statements, too-many-branches
def graphite_object_hook(dct: dict[str, Any]) -> Any:
	"""Decode Graphite-specific objects from JSON."""
	if GRAPHITE_TYPE_FIELD not in dct:
		return dct

	graphite_type = dct.pop(GRAPHITE_TYPE_FIELD)

	if graphite_type == "datetime":
		value = dct["value"]
		if dct.get("is_date"):
			return date.fromisoformat(value)
		return datetime.fromisoformat(value)

	if graphite_type == "enum":
		enum_class = dct["enum_class"]
		value = dct["value"]
		if enum_class == "DataType":
			return DataType(value)
		return dct

	if graphite_type == "datatype":
		return DataType(dct["value"])

	if graphite_type == "defaultdict":
		factory_name = dct.pop(DEFAULT_FACTORY_FIELD, None)
		factory: Callable[[], Any] | None = None
		if factory_name == "list":
			factory = list
		elif factory_name == "dict":
			factory = dict
		result = defaultdict(factory)
		result.update(dct)
		return result

	if graphite_type == "Node":
		return Node(
			type_name=dct["type_name"],
			id=dct["id"],
			values=dct["values"],
			type_ref=None
		)

	if graphite_type == "Relation":
		return Relation(
			type_name=dct["type_name"],
			from_node=dct["from_node"],
			to_node=dct["to_node"],
			values=dct["values"],
			type_ref=None
		)

	if graphite_type == "NodeType":
		return {
			"name": dct["name"],
			"fields": dct.get("fields", []),
			"parent": dct.get("parent")
		}

	if graphite_type == "RelationType":
		return RelationType(
			name=dct["name"],
			from_type=dct["from_type"],
			to_type=dct["to_type"],
			fields=dct.get("fields", []),
			reverse_name=dct.get("reverse_name"),
			is_bidirectional=dct.get("is_bidirectional", False)
		)

	if graphite_type == "Field":
		return Field(
			name=dct["name"],
			dtype=DataType(dct["dtype"])
		)

	return dct
