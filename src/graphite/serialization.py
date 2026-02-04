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

class GraphiteJSONEncoder(json.JSONEncoder):
	"""Custom JSON encoder for Graphite data structures"""

	def default(self, o: Any) -> Any:  # pylint: disable=too-many-return-statements
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

		# Handle dataclasses
		if is_dataclass(o) and not isinstance(o, type):
			# Convert to dict and add type info
			result = asdict(o)
			result[GRAPHITE_TYPE_FIELD] = type(o).__name__
			return result

		# Handle defaultdict
		if isinstance(o, defaultdict):
			result = dict(o)
			result[GRAPHITE_TYPE_FIELD] = "defaultdict"
			result[DEFAULT_FACTORY_FIELD] = o.default_factory.__name__ if o.default_factory else None
			return result

		# Handle Node and Relation instances (already dataclasses but need special handling)
		if isinstance(o, (Node, Relation)):
			# Convert to dict with minimal information
			return _serialize_instance(o)

		# Handle NodeType and RelationType (dataclasses with parent references)
		if isinstance(o, (NodeType, RelationType)):
			result = asdict(o)
			result[GRAPHITE_TYPE_FIELD] = type(o).__name__
			# Convert parent to name reference to avoid circular references
			if isinstance(o, NodeType) and o.parent:
				result["parent"] = o.parent.name
			# Remove type_ref from serialization
			result.pop("type_ref", None)
			return result

		# Handle Field
		if isinstance(o, Field):
			result = asdict(o)
			result[GRAPHITE_TYPE_FIELD] = "Field"
			# Convert dtype to value
			result["dtype"] = o.dtype.value
			return result

		return super().default(o)


def graphite_object_hook(dct: dict[str, Any]) -> Any:  # pylint: disable=too-many-return-statements
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
			dtype=DataType(dct["dtype"]),
			default=dct.get("default")
		)

	return dct


def _serialize_instance(instance: Node | Relation) -> dict[str, Any]:
	return {
		GRAPHITE_TYPE_FIELD: type(instance).__name__,
		"type_name"        : instance.type_name,
		"id"               : instance.id if hasattr(instance, "id") else None,
		"values"           : instance.values,
		"from_node"        : instance.from_node if hasattr(instance, "from_node") else None,
		"to_node"          : instance.to_node if hasattr(instance, "to_node") else None,
		"type_ref"         : instance.type_ref.name if instance.type_ref else None
	}
