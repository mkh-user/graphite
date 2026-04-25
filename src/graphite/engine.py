"""
Main graph database engine of Graphite
"""
import json
import os
import warnings
from collections import defaultdict
from typing import Any, Dict, List, Union

from typing_extensions import deprecated

from .exceptions import (
	FileSizeError, InvalidJSONError, InvalidPropertiesError, InvalidRelationError,
	NotFoundError, SafeLoadExtensionError, TooNestedJSONError, ValidationError,
)
from .instances import Node, Relation
from .parser import GraphiteParser
from .query import QueryBuilder
from .serialization import GraphiteJSONEncoder, graphite_object_hook
from .types import Field, NodeType, RelationType

SAVE_FILE_VERSION = "1.0"

# pylint: disable=too-many-instance-attributes
class GraphiteEngine:
	"""Main graph database engine"""

	def __init__(self):
		self.node_types: Dict[str, NodeType] = {}
		self.relation_types: Dict[str, RelationType] = {}
		self.nodes: Dict[str, Node] = {}
		self.relations: List[Relation] = []
		self.node_by_type: Dict[str, List[Node]] = defaultdict(list)
		self.relations_by_type: Dict[str, List[Relation]] = defaultdict(list)
		self.relations_by_from: Dict[str, List[Relation]] = defaultdict(list)
		self.relations_by_to: Dict[str, List[Relation]] = defaultdict(list)
		self.parser = GraphiteParser()
		self.query = QueryBuilder(self)

	# =============== SCHEMA DEFINITION ===============

	def define_node(self, definition: str) -> None:
		"""
		Define a node type from DSL

		:param definition: Node definition string in Graphite DSL

		:return: None

		:except GraphiteError: if node definition is not valid
		:except NotFoundError: if parent node definition (from ...) is not found
		"""
		node_name, fields, parent_name = self.parser.parse_node_definition(definition)

		parent = None
		if parent_name:
			if parent_name not in self.node_types:
				raise NotFoundError(
					"Parent node type",
					parent_name,
				)
			parent = self.node_types[parent_name]

		node_type = NodeType(node_name, fields, parent)
		self.node_types[node_name] = node_type

	def define_relation(self, definition: str) -> None:
		"""
		Define a relation type from DSL

		:param definition: Relation definition string in Graphite DSL

		:return: None

		:except ParseError: if relation definition is not valid
		:except RelationTypeDefineError: if relation type have both 'reverse ...' and 'both' flags
		:except NotFoundError: if source or target node types are not found
		"""
		(rel_name, from_type, to_type, fields,
		reverse_name, is_bidirectional) = self.parser.parse_relation_definition(definition)

		# Validate node types exist
		if from_type not in self.node_types:
			raise NotFoundError(
				"Node type",
				from_type,
			)
		if to_type not in self.node_types:
			raise NotFoundError(
				"Node type",
				to_type,
			)

		rel_type = RelationType(
			rel_name, from_type, to_type,
			fields, reverse_name, is_bidirectional
		)
		self.relation_types[rel_name] = rel_type

		# Register reverse relation if specified
		if reverse_name:
			reverse_rel = RelationType(
				reverse_name, to_type, from_type,
				fields, rel_name, is_bidirectional
			)
			self.relation_types[reverse_name] = reverse_rel

	# =============== DATA MANIPULATION ===============

	def create_node(self, node_type: str, node_id: str, *values) -> Node:
		"""
		Create a node instance

		:param node_type: Node type
		:param node_id: Node ID
		:param values: Values for node fields

		:return: Node instance

		:except NotFoundError: if `node_type` not defined
		:except InvalidPropertiesError: if `values` count is not same as node type field count
		:except FieldError: if `values` fail in parse, converting, or validation
		"""
		if node_type not in self.node_types:
			raise NotFoundError(
				"Node type",
				node_type
			)

		node_type_obj = self.node_types[node_type]
		all_fields = node_type_obj.get_all_fields()

		if len(values) != len(all_fields):
			raise InvalidPropertiesError(
				all_fields,
				len(values)
			)

		# Create values dictionary
		node_values = {}
		for current_field, value in zip(all_fields, values):
			node_values[current_field.name] = self.parser.parse_field_value(value, current_field)

		new_node = Node(node_type, node_id, node_values, node_type_obj)
		self.nodes[node_id] = new_node
		self.node_by_type[node_type].append(new_node)
		return new_node

	def create_relation(self, from_id: str, to_id: str, rel_type: str, *values) -> Relation:
		"""
		Create a relation instance

		:param from_id: Source ID
		:param to_id: Target ID
		:param rel_type: Relation type
		:param values: Values for relation fields

		:return: Relation instance

		:except NotFoundError: if `rel_type`, `from_id`, or `to_id` not defined
		:except InvalidRelationError: for invalid node types based on relation type
		:except InvalidPropertiesError: if `values` count is not same as relation type field count
		"""
		if rel_type not in self.relation_types:
			raise NotFoundError(
				"Relation type",
				rel_type,
			)

		rel_type_obj = self.relation_types[rel_type]

		# Check if nodes exist
		if from_id not in self.nodes:
			raise NotFoundError(
				"Node",
				from_id,
			)
		if to_id not in self.nodes:
			raise NotFoundError(
				"Node",
				to_id
			)

		if not (
			self.is_node_from_type(from_id, rel_type_obj.from_type) and
			self.is_node_from_type(to_id, rel_type_obj.to_type)
		):
			raise InvalidRelationError(
				rel_type_obj,
				from_id,
				to_id,
			)

		if len(values) != len(rel_type_obj.fields):
			raise InvalidPropertiesError(
				rel_type_obj.fields,
				len(values)
			)

		# Create values dictionary
		rel_values = {}
		for current_field, value in zip(rel_type_obj.fields, values):
			rel_values[current_field.name] = self.parser.parse_field_value(value, current_field)

		new_relation = Relation(rel_type, from_id, to_id, rel_values, rel_type_obj)
		self.relations.append(new_relation)
		self.relations_by_type[rel_type].append(new_relation)
		self.relations_by_from[from_id].append(new_relation)
		self.relations_by_to[to_id].append(new_relation)

		# If relation is bidirectional, create reverse automatically
		if rel_type_obj.is_bidirectional:
			reverse_rel = Relation(rel_type, to_id, from_id, rel_values, rel_type_obj)
			self.relations.append(reverse_rel)
			self.relations_by_type[rel_type].append(reverse_rel)
			self.relations_by_from[to_id].append(reverse_rel)
			self.relations_by_to[from_id].append(reverse_rel)

		return new_relation

	def is_node_from_type(self, node_id: str, node_type: str) -> bool:
		"""
		Returns True if given node is from given type

		:param node_id: Node ID
		:param node_type: Node type string

		:return: True if given node is from given type otherwise False

		:except NotFoundError: if given `node_id` not defined
		:except NotFoundError: if `node_type` not defined
		"""
		if node_id not in self.nodes:
			raise NotFoundError(
				"Node",
				node_id
			)
		if node_type not in self.node_types:
			raise NotFoundError(
				"Node type",
				node_type
			)
		node_obj = self.nodes[node_id]
		# Fast check for direct inheritance
		if node_obj.type_name == node_type:
			return True
		type_obj = node_obj.type_ref if node_obj.type_ref else self.node_types[node_obj.type_name]
		while type_obj.parent:
			if type_obj.parent.name == node_type:
				return True
			type_obj = type_obj.parent
		return False

	# =============== QUERY METHODS ===============

	def get_node(self, node_id: str) -> Node:
		"""
		Get node by ID

		:param node_id: Node ID

		:return: Node object

		:except NotFoundError: if `node_id` not defined
		"""
		if node_id not in self.nodes:
			raise NotFoundError(
				"Node",
				node_id,
			)
		return self.nodes.get(node_id)

	def get_nodes_of_type(self, node_type: str, with_subtypes: bool = True) -> List[Node]:
		"""
		Get all nodes of a specific type

		:param node_type: Node type string
		:param with_subtypes: If `with_subtypes` is True, adds all subtypes of node type recursively

		:return: List of Node objects

		:except NotFoundError: if `node_type` not defined
		"""
		if node_type not in self.node_types:
			raise NotFoundError(
				"Node type",
				node_type
			)

		nodes: List[Node] = self.node_by_type.get(node_type, [])
		if with_subtypes:
			for ntype in self.node_types.values():
				if ntype.parent and ntype.parent.name == node_type:
					for new_node in self.get_nodes_of_type(ntype.name):
						if new_node not in nodes:
							nodes.append(new_node)
		return nodes

	def get_relations_from(self, node_id: str, rel_type: str = None) -> List[Relation]:
		"""
		Get relations from a node

		:param node_id: Node ID
		:param rel_type: Relation type to filter on, or ``None`` to keep all types

		:return: List of Relations

		:except NotFoundError: if `rel_type` or `node_id` not defined
		"""
		if rel_type and rel_type not in self.relation_types:
			raise NotFoundError(
				"Relation type",
				rel_type
			)
		if node_id not in self.nodes:
			raise NotFoundError(
				"Node",
				node_id
			)

		all_rels = self.relations_by_from.get(node_id, [])
		if rel_type:
			return [r for r in all_rels if r.type_name == rel_type]
		return all_rels

	def get_relations_to(self, node_id: str, rel_type: str = None) -> List[Relation]:
		"""
		Get relations to a node

		:param node_id: Node ID
		:param rel_type: Relation type to filter on, or ``None`` to keep all types

		:return: List of Relations

		:except NotFoundError: if `rel_type` or `node_id` not defined
		"""
		if rel_type and rel_type not in self.relation_types:
			raise NotFoundError(
				"Relation type",
				rel_type
			)
		if node_id not in self.nodes:
			raise NotFoundError(
				"Node",
				node_id
			)

		all_rels = self.relations_by_to.get(node_id, [])
		if rel_type:
			return [r for r in all_rels if r.type_name == rel_type]
		return all_rels

	def undefine_node(self, node_type: str) -> None:
		"""
		Undefine a node type

		:param node_type: Node type string

		:return: None

		:except NotFoundError: if `node_type` not defined
		"""
		if node_type not in self.node_types:
			raise NotFoundError(
				"Node type",
				node_type
			)
		for instance in self.node_by_type[node_type].copy():
			self.remove_node(instance)
		relation_types_to_remove = []
		node_types_to_remove = []
		for relation_type in self.relation_types.values():
			if relation_type.from_type == node_type:
				relation_types_to_remove.append(relation_type.name)
			elif relation_type.to_type == node_type:
				relation_types_to_remove.append(relation_type.name)
		for ntype in self.node_types.values():
			if ntype.parent == self.node_types[node_type]:
				node_types_to_remove.append(ntype.name)
		for processing_rel in relation_types_to_remove:
			if processing_rel in self.relation_types:
				self.undefine_relation(processing_rel)
		for processing_node in node_types_to_remove:
			if processing_node in self.node_types:
				self.undefine_node(processing_node)
		self.node_by_type.pop(node_type, None)
		self.node_types.pop(node_type, None)

	def undefine_relation(self, relation_type: str, _is_reverse: bool = False) -> None:
		"""
		Undefine a relation type

		:param relation_type: Relation type string
		:param _is_reverse: For internal use to remove reverse direction relation type

		:return: None

		:except NotFoundError: if `relation_type` not defined
		"""
		if relation_type not in self.relation_types:
			raise NotFoundError(
				"Relation type",
				relation_type
			)
		for instance in self.relations_by_type[relation_type].copy():
			self.remove_relation(instance)
		if not _is_reverse and self.relation_types[relation_type].reverse_name:
			self.undefine_relation(self.relation_types[relation_type].reverse_name, True)
		self.relation_types.pop(relation_type)
		self.relations_by_type.pop(relation_type, None)

	def remove_node(self, node: Union[Node, str]) -> None:
		"""
		Remove a node and all its relations

		:param node: Node ID string or node object

		:return: None

		:except NotFoundError: if `node` not defined
		"""
		if isinstance(node, str):
			if node not in self.nodes:
				raise NotFoundError(
					"Node",
					node
				)
			node_type = self.nodes[node].type_name
		else:
			if node.id not in self.nodes or self.nodes[node.id] is not node:
				raise NotFoundError(
					"Node",
					node.id
				)
			node_type = node.type_name
			node = node.id
		for from_rel in self.get_relations_from(node).copy():
			self.remove_relation(from_rel)
		for to_rel in self.get_relations_to(node).copy():
			self.remove_relation(to_rel)
		removed = self.nodes.pop(node)
		self.node_by_type[node_type].remove(removed)

	def remove_relation(self, relation: Relation) -> None:
		"""
		Remove a relation

		:param relation: Relation object

		:return: None

		:except NotFoundError: if `relation` not defined
		"""
		if relation not in self.relations:
			raise NotFoundError(
				"Relation",
				str(relation)
			)
		self.relations.remove(relation)
		self.relations_by_type[relation.type_name].remove(relation)
		self.relations_by_from[relation.from_node].remove(relation)
		self.relations_by_to[relation.to_node].remove(relation)

	# ============= BULK LOADING / DSL =============

	def parse(self, data: str) -> None:
		"""
		Parse and load data from Graphite DSL to engine

		:param data: data as Graphite DSL string

		:return: None

		:except ParseError: if parsing fails
		:except NotFoundError: using any undefined object (node type, relation type, node, relation)
		:except ValueError: if a used data type not fount
		"""
		lines = data.strip().split('\n')

		i = 0
		while i < len(lines):
			line = lines[i].strip()
			if not line or line.startswith('#'):
				i += 1
				continue

			if line.startswith('node'):
				# Collect multiline node definition
				node_def = [line]
				i += 1
				while (
						i < len(lines)
						and lines[i].strip()
						and not lines[i].strip().startswith(('node', 'relation'))
				):
					if lines[i].strip().startswith('#'):
						i += 1
						continue
					node_def.append(lines[i])
					i += 1
				self.define_node('\n'.join(node_def))

			elif line.startswith('relation'):
				# Collect multiline relation definition
				rel_def = [line]
				i += 1
				while (
						i < len(lines)
						and lines[i].strip()
						and not lines[i].strip().startswith(('node', 'relation'))
				):
					if lines[i].strip().startswith('#'):
						i += 1
						continue
					rel_def.append(lines[i])
					i += 1
				self.define_relation('\n'.join(rel_def))

			elif '-[' in line and (']->' in line or ']-' in line):
				# Relation instance
				from_id, to_id, rel_type, values, _ = self.parser.parse_relation_instance(line)
				self.create_relation(from_id, to_id, rel_type, *values)
				i += 1

			else:
				# Node instance
				node_type, node_id, values = self.parser.parse_node_instance(line)
				self.create_node(node_type, node_id, *values)
				i += 1

	@deprecated("Use parse() instead")
	def load_dsl(self, dsl: str) -> None:
		"""
		Load Graphite DSL to engine

		:param dsl: DSL string

		:return: None

		:except ParseError: if parsing fails
		:except NotFoundError: using any undefined object (node type, relation type, node, relation)
		:except ValueError: if a used data type not fount
		"""
		self.parse(dsl)

	# =============== PERSISTENCE ===============

	def save(self, file_path: str) -> None:
		"""
		Save database to a single file using JSON

		:param file_path: File path
		"""
		data = self._build_save_payload()
		with open(file_path, 'w', encoding='utf-8') as f:
			# noinspection PyTypeChecker
			json.dump(data, f, cls=GraphiteJSONEncoder, indent=2, ensure_ascii=False)

	def load_safe(
		self, file_path: str, max_size_mb: Union[int, float] = 100, validate_schema: bool = True,
		accept_any_extension: bool = False
	) -> None:
		"""
		Safely load database with security checks

		:param file_path: File to load
		:param max_size_mb: Maximum allowed file size in MB
		:param validate_schema: Whether to validate schema consistency
		:param accept_any_extension: Whether to accept any extension, by default just `.json` is valid

		:return: None

		:except FileSizeError: for files bigger than `max_size_mb`
		:except SafeLoadExtensionError: for files without `.json` extension when extension
		validation enabled
		:except InvalidJSONError: for error at decoding process
		:except TooNestedJSONError: for invalid recursion error
		:except ValidationError: for invalid schema when schema validation enabled
		"""
		# Check file size
		file_size = os.path.getsize(file_path)
		if file_size > max_size_mb * 1024 * 1024:
			raise FileSizeError(
				file_size / 1024 / 1024,
				max_size_mb
			)

		# Check file extension
		if not accept_any_extension and not file_path.lower().endswith('.json'):
			raise SafeLoadExtensionError()

		try:
			with open(file_path, 'r', encoding='utf-8') as f:
				data = json.load(f, object_hook=graphite_object_hook)
		except json.JSONDecodeError as e:
			raise InvalidJSONError() from e
		except RecursionError as e:
			raise TooNestedJSONError() from e

		# Validate structure
		if validate_schema:
			self._validate_loaded_data(data)

		# Load normally
		self._load_from_dict(data)

	# pylint: disable=too-many-branches
	@staticmethod
	def _validate_loaded_data(data: Dict[str, Any]) -> None:
		"""
		Validate loaded data for consistency

		:param data: Dictionary of loaded data

		:return: None

		:except ValidationError: for any fail at validation
		"""
		if not isinstance(data, dict):
			raise ValidationError(
				"Loaded data must be a dictionary",
				"data",
				str(type(data))
			)

		required_keys = ('version', 'node_types', 'relation_types', 'nodes')
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
		if 'relations' in data and not isinstance(data.get('relations'), list):
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
				warnings.warn(f"Unexpected key in data: {key}", UserWarning)

		# Validate nodes reference existing types
		node_type_names = set()
		for node_type in data.get('node_types', []):
			if isinstance(node_type, NodeType):
				node_type_names.add(node_type.name)
			elif isinstance(node_type, dict) and 'name' in node_type:
				node_type_names.add(node_type['name'])

		for check_node in data.get('nodes', []):
			type_name = check_node.type_name if isinstance(check_node, Node) else check_node.get('type_name')
			if type_name not in node_type_names:
				raise NotFoundError(
					"Node type",
					type_name,
				)

	# pylint: disable=too-many-locals
	def _load_from_dict(self, data: Dict[str, Any]) -> None:
		"""
		Internal method to load from dictionary (used by both load and load_safe)

		:param data: Dictionary of loaded data

		:return: None
		"""
		# Clear existing data
		self.clear()

		node_types_data = data.get('node_types', [])
		relation_types_data = data.get('relation_types', [])
		nodes_data = data.get('nodes', [])
		relations_data = data.get('relations', [])

		# Restore node types
		for nt_dict in node_types_data:
			if isinstance(nt_dict, NodeType):
				nt = nt_dict
			else:
				# Convert from dict if needed
				fields: List[Field] = list(map(
					lambda fld: Field(fld["name"], fld["dtype"], fld["default"]),
					nt_dict.get("fields", [])
				))
				nt = NodeType(
					name=nt_dict['name'],
					fields=fields,
					parent=None  # Will be restored later
				)
			self.node_types[nt.name] = nt

		# Restore parent references for node types
		for nt in node_types_data:
			if isinstance(nt, dict):
				parent_name = nt.get('parent')
				name = nt.get('name')
			else:
				parent_name = nt.parent.name if nt.parent else None
				name = nt.name
			if isinstance(parent_name, dict):
				parent_name = parent_name["name"]
			if parent_name and parent_name in self.node_types and name in self.node_types:
				self.node_types[name].parent = self.node_types[parent_name]

		# Restore relation types
		for rt_dict in relation_types_data:
			if isinstance(rt_dict, RelationType):
				rt = rt_dict
			else:
				rt = RelationType(
					name=rt_dict['name'],
					from_type=rt_dict['from_type'],
					to_type=rt_dict['to_type'],
					fields=rt_dict.get('fields', []),
					reverse_name=rt_dict.get('reverse_name'),
					is_bidirectional=rt_dict.get('is_bidirectional', False)
				)
			self.relation_types[rt.name] = rt

		# Restore nodes
		for node_data in nodes_data:
			if isinstance(node_data, Node):
				loading_node = node_data
			else:
				loading_node = Node(
					type_name=node_data['type_name'],
					id=node_data['id'],
					values=node_data['values'],
					type_ref=None
				)

			# Restore type reference
			if loading_node.type_name in self.node_types:
				loading_node.type_ref = self.node_types[loading_node.type_name]

			self.nodes[loading_node.id] = loading_node

		# Restore relations
		for rel_data in relations_data:
			if isinstance(rel_data, Relation):
				rel = rel_data
			else:
				rel = Relation(
					type_name=rel_data['type_name'],
					from_node=rel_data['from_node'],
					to_node=rel_data['to_node'],
					values=rel_data['values'],
					type_ref=None
				)

			# Restore type reference
			if rel.type_name in self.relation_types:
				rel.type_ref = self.relation_types[rel.type_name]

			self.relations.append(rel)

		# Rebuild all indexes
		self._rebuild_all_indexes()

	def _build_save_payload(self) -> Dict[str, Any]:
		"""
		Build a JSON-serializable payload for persistence

		:return: Engine snapshot as JSON dictionary
		"""
		return {
			"version"          : SAVE_FILE_VERSION,
			"node_types"       : list(self.node_types.values()),
			"relation_types"   : list(self.relation_types.values()),
			"nodes"            : list(self.nodes.values()),
			"relations"        : sorted(
				self.relations,
				key=lambda r: (
					r.type_name,
					r.from_node,
					r.to_node,
					sorted((k, str(v)) for k, v in r.values.items())
				)
			),
			"node_by_type"     : dict(self.node_by_type.items()),
			"relations_by_type": dict(self.relations_by_type.items()),
			"relations_by_from": dict(self.relations_by_from.items()),
			"relations_by_to"  : dict(self.relations_by_to.items()),
		}

	def _rebuild_all_indexes(self) -> None:
		"""
		Rebuild nodes and relation indexes

		:return: None
		"""
		self.node_by_type = defaultdict(list)
		for node_instance in self.nodes.values():
			self.node_by_type[node_instance.type_name].append(node_instance)

		self.relations_by_type = defaultdict(list)
		self.relations_by_from = defaultdict(list)
		self.relations_by_to = defaultdict(list)

		for rel in self.relations:
			self.relations_by_type[rel.type_name].append(rel)
			self.relations_by_from[rel.from_node].append(rel)
			self.relations_by_to[rel.to_node].append(rel)

	def load(self, filename: str, safe_mode: bool = True) -> None:
		"""
		Load database from file

		:param filename: File to load (must be JSON)
		:param safe_mode: If True, use safe loading with validation (default: True)

		:return: None
		"""
		if safe_mode:
			self.load_safe(filename)
			return

		# Legacy unsafe loading (for backward compatibility)
		warnings.warn(
			"Unsafe loading mode will be deprecated in next versions. Use safe_mode=True for security. "
			"You can use 'graphite.Migration.convert_pickle_to_json()' to update your database.",
			PendingDeprecationWarning
		)
		self._load_unsafe(filename)

	def _load_unsafe(self, filename: str) -> None:
		"""
		Legacy unsafe loading (kept for compatibility)

		:param filename: File to load

		:return: None
		"""
		with open(filename, 'r', encoding='utf-8') as f:
			data = json.load(f, object_hook=graphite_object_hook)
		self._load_from_dict(data)

	# =============== UTILITY METHODS ===============

	def clear(self) -> None:
		"""
		Clear all data

		:return: None
		"""
		self.node_types.clear()
		self.relation_types.clear()
		self.nodes.clear()
		self.relations.clear()
		self.node_by_type.clear()
		self.relations_by_type.clear()
		self.relations_by_from.clear()
		self.relations_by_to.clear()

	def stats(self) -> Dict[str, Any]:
		"""
		Get database statistics

		:return: Dictionary of statistics containing count of node types, relation types, node,
		and relations
		"""
		return {
			'node_types'    : len(self.node_types),
			'relation_types': len(self.relation_types),
			'nodes'         : len(self.nodes),
			'relations'     : len(self.relations),
		}
