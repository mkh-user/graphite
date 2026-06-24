"""
Serialization utils for Graphite databases
"""
import json
import warnings
from datetime import date, datetime
from typing import Any

from .exceptions import NotFoundError, ValidationError
from .instances import Node, Relation
from .types import DataType, Field, NodeType, RelationType

SAVE_FILE_VERSION = "1.0"
GRAPHITE_TYPE_FIELD = "__graphite_type__"
DEFAULT_FACTORY_FIELD = "__default_factory"

def _serialize_node(node: Node) -> dict[str, Any]:
	return {
		GRAPHITE_TYPE_FIELD: "Node",
		"type_name": node.type_name,
		"id": node.id,
		"values": node.values,
	}

def _serialize_relation(relation: Relation) -> dict[str, Any]:
	return {
		GRAPHITE_TYPE_FIELD: "Relation",
		"type_name": relation.type_name,
		"from_node": relation.from_node,
		"to_node": relation.to_node,
		"values": relation.values,
	}

def _serialize_node_type(node_type: NodeType) -> dict[str, Any]:
	return {
		GRAPHITE_TYPE_FIELD: "NodeType",
		"name": node_type.name,
		"parent": node_type.parent.name if node_type.parent else None,
		"fields": node_type.fields,
	}

def _serialize_relation_type(relation_type: RelationType) -> dict[str, Any]:
	return {
		GRAPHITE_TYPE_FIELD: "RelationType",
		"name": relation_type.name,
		"from_type": relation_type.from_type,
		"to_type": relation_type.to_type,
		"fields": relation_type.fields,
		"reverse_name": relation_type.reverse_name,
		"is_bidirectional": relation_type.is_bidirectional,
	}

class GraphiteJSONEncoder(json.JSONEncoder):
	"""Custom JSON encoder for Graphite data structures"""

	# pylint: disable=too-many-return-statements
	# Reason: Returns reduce complexity of branching, and branches are necessary to handle all
	# supported data types.
	def default(self, o: Any) -> Any:
		# Handle date/datetime objects
		if isinstance(o, (date, datetime)):
			return {
				GRAPHITE_TYPE_FIELD: "date",
				"value": o.isoformat()
			}

		# Handle DataType enum
		if isinstance(o, DataType):
			return {
				GRAPHITE_TYPE_FIELD: "datatype",
				"value": o.value
			}

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
				"name": o.name,
				"dtype": o.dtype,
			}

		if isinstance(o, (dict, list)):
			return o

		return super().default(o)

# pylint: disable=too-many-return-statements
# Reason: As described in GraphiteJSONEncode.default().
def graphite_object_hook(dct: dict[str, Any]) -> Any:
	"""Decode Graphite-specific objects from JSON."""
	if GRAPHITE_TYPE_FIELD not in dct:
		return dct

	graphite_type = dct.pop(GRAPHITE_TYPE_FIELD)

	if graphite_type in ("datetime", "date"):
		return datetime.strptime(dct["value"], "%Y-%m-%d").date()

	if graphite_type == "datatype":
		return DataType(dct["value"])

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
		return NodeType(
			dct["name"],
			dct.get("fields", []),
			dct.get("parent")
		)

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

	raise TypeError(f"Unknown graphite type: {graphite_type}")

def _validate_loaded_data(data: dict[str, Any]) -> None:
	"""
	Validate loaded data for consistency

	:param data: Dictionary of loaded data

	:return: None

	:except ValidationError: for any fail at validation
	"""
	required_keys = ('version', 'node_types', 'relation_types', 'nodes', 'relations')
	for key in required_keys:
		if key not in data:
			raise ValidationError(
				f"Missing required key {key}",
				key,
				"'Missing'"
			)

	if data.get("version") != SAVE_FILE_VERSION:
		raise ValidationError(
			f"Save file version must be {SAVE_FILE_VERSION} not {data.get('version')}",
			"version",
			data.get("version")
		)

	if not isinstance(data.get('node_types'), list):
		raise ValidationError(
			"node_types must be a list",
			"node_types",
			str(type(data.get('node_types')))
		)
	if not isinstance(data.get('relation_types'), list):
		raise ValidationError(
			"relation_types must be a list",
			"relation_types",
			str(type(data.get('relation_types')))
		)
	if not isinstance(data.get('nodes'), list):
		raise ValidationError(
			"nodes must be a list",
			"nodes",
			str(type(data.get('nodes')))
		)
	if not isinstance(data.get('relations'), list):
		raise ValidationError(
			"relations must be a list",
			"relations",
			str(type(data.get('relations')))
		)

	# Check for unexpected keys
	allowed_keys = ('version', 'node_types', 'relation_types', 'nodes', 'relations', 'node_by_type',
	'relations_by_type', 'relations_by_from', 'relations_by_to')
	for key in data.keys():
		if key not in allowed_keys:
			warnings.warn(f"Unexpected key in data: {key}", UserWarning, stacklevel=2)

	# Validate nodes reference existing types
	node_type_names = set()
	for node_type in data.get('node_types', []):
		node_type_names.add(node_type.name)

	for check_node in data.get('nodes', []):
		type_name = check_node.type_name
		if type_name not in node_type_names:
			raise NotFoundError(
				"Node type",
				type_name,
			)

def _load_from_dict(
	data: dict[str, Any]
) -> tuple[dict[str, NodeType], dict[str, RelationType], dict[str, Node], dict[int, Relation]]:
	"""
	Internal method to load from dictionary (used by both load and load_safe)

	:param data: Dictionary of loaded data

	:return: None
	"""
	node_types_data = data.get('node_types', [])
	relation_types_data = data.get('relation_types', [])
	nodes_data = data.get('nodes', [])
	relations_data = data.get('relations', [])

	node_types: dict[str, NodeType] = { }
	relation_types: dict[str, RelationType] = { }
	nodes: dict[str, Node] = { }
	relations: dict[int, Relation] = { }

	# Restore node types
	for nt in node_types_data:
		node_types[nt.name] = nt

	# Restore parent references for node types
	for nt in node_types_data:
		parent_name = nt.parent
		name = nt.name
		if parent_name and parent_name in node_types and name in node_types:
			node_types[name].parent = node_types[parent_name]

	# Restore relation types
	for rt in relation_types_data:
		relation_types[rt.name] = rt

	# Restore nodes
	for node in nodes_data:
		# Restore type reference
		node.type_ref = node_types[node.type_name]
		nodes[node.id] = node

	# Restore relations
	for rel in relations_data:
		# Restore type reference
		rel.type_ref = relation_types[rel.type_name]
		relations[id(rel)] = rel

	return node_types, relation_types, nodes, relations
