"""
Serialization utils for Graphite databases
"""
import json
from datetime import date, datetime
from enum import Enum
from dataclasses import is_dataclass, asdict
from collections import defaultdict
from typing import Any

from .types import DataType, NodeType, RelationType, Field
from .instances import Node, Relation

class GraphiteJSONEncoder(json.JSONEncoder):
	"""Custom JSON encoder for Graphite data structures"""

	def default(self, o: Any) -> Any:  # pylint: disable=too-many-return-statements
		# Handle date/datetime objects
		if isinstance(o, (date, datetime)):
			return {
				"__graphite_type__": "datetime",
				"value"            : o.isoformat(),
				"is_date"          : isinstance(o, date)
			}

		# Handle Enum objects
		if isinstance(o, Enum):
			return {
				"__graphite_type__": "enum",
				"enum_class"       : type(o).__name__,
				"value"            : o.value
			}

		# Handle DataType enum specifically
		if isinstance(o, DataType):
			return {
				"__graphite_type__": "datatype",
				"value"            : o.value
			}

		# Handle dataclasses
		if is_dataclass(o) and not isinstance(o, type):
			# Convert to dict and add type info
			result = asdict(o)
			result["__graphite_type__"] = type(o).__name__
			return result

		# Handle defaultdict
		if isinstance(o, defaultdict):
			result = dict(o)
			result["__graphite_type__"] = "defaultdict"
			result["__default_factory"] = o.default_factory.__name__ if o.default_factory else None
			return result

		# Handle Node and Relation instances (already dataclasses but need special handling)
		if isinstance(o, (Node, Relation)):
			# Convert to dict with minimal information
			result = {
				"__graphite_type__": type(o).__name__,
				"type_name"        : o.type_name,
				"id"               : o.id if hasattr(o, 'id') else None,
				"values"           : o.values,
				"from_node"        : o.from_node if hasattr(o, 'from_node') else None,
				"to_node"          : o.to_node if hasattr(o, 'to_node') else None,
				"type_ref"        : o.type_ref.name if o.type_ref else None
			}
			return result

		# Handle NodeType and RelationType (dataclasses with parent references)
		if isinstance(o, (NodeType, RelationType)):
			result = asdict(o)
			result["__graphite_type__"] = type(o).__name__
			# Convert parent to name reference to avoid circular references
			if isinstance(o, NodeType) and o.parent:
				result["parent"] = o.parent.name
			# Remove type_ref from serialization
			result.pop("type_ref", None)
			return result

		# Handle Field
		if isinstance(o, Field):
			result = asdict(o)
			result["__graphite_type__"] = "Field"
			# Convert dtype to value
			result["dtype"] = o.dtype.value
			return result

		return super().default(o)
