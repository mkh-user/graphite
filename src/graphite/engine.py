"""
Main graph database engine of Graphite
"""
import json
import os
import warnings
from collections import defaultdict
from typing import Any

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

# pylint: disable=too-many-instance-attributes, too-many-public-methods
class GraphiteEngine:
	"""Main graph database engine"""

	def __init__(self):
		self.node_types: dict[str, NodeType] = {}
		self.relation_types: dict[str, RelationType] = {}
		self.nodes: dict[str, Node] = {}
		self.relations: dict[int, Relation] = {}
		self.node_by_type: dict[str, set[Node]] = defaultdict(set)
		self.relations_by_type: dict[str, set[int]] = defaultdict(set)
		self.relations_by_from: dict[str, set[int]] = defaultdict(set)
		self.relations_by_to: dict[str, set[int]] = defaultdict(set)
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
		self.node_by_type[node_type].add(new_node)
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
		relation_id = id(new_relation)
		self.relations[relation_id] = new_relation
		self.relations_by_type[rel_type].add(relation_id)
		self.relations_by_from[from_id].add(relation_id)
		self.relations_by_to[to_id].add(relation_id)

		# If relation is bidirectional, create reverse automatically
		if rel_type_obj.is_bidirectional:
			reverse_rel = Relation(rel_type, to_id, from_id, rel_values, rel_type_obj)
			reverse_id = id(reverse_rel)
			self.relations[reverse_id] = reverse_rel
			self.relations_by_type[rel_type].add(reverse_id)
			self.relations_by_from[to_id].add(reverse_id)
			self.relations_by_to[from_id].add(reverse_id)

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

	def get_nodes_of_type(self, node_type: str, with_subtypes: bool = True) -> set[Node]:
		"""
		Get all nodes of a specific type

		:param node_type: Node type string
		:param with_subtypes: If `with_subtypes` is True, adds all subtypes of node type recursively

		:return: Set of Node objects

		:except NotFoundError: if `node_type` not defined
		"""
		if node_type not in self.node_types:
			raise NotFoundError(
				"Node type",
				node_type
			)

		nodes = self.node_by_type[node_type]
		if with_subtypes:
			for ntype in self.node_types.values():
				if ntype.parent and ntype.parent.name == node_type:
					nodes.update(self.get_nodes_of_type(ntype.name, True))
		return nodes

	def get_relations_from(self, node_id: str, rel_type: str = None) -> set[Relation]:
		"""
		Get relations from a node

		:param node_id: Node ID
		:param rel_type: Relation type to filter on, or ``None`` to keep all types

		:return: Set of Relations

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

		result_ids = self.relations_by_from[node_id]
		if rel_type:
			result_ids = [r for r in result_ids if r in self.relations_by_type[rel_type]]
		return {self.relations[rel_id] for rel_id in result_ids}

	def get_relations_to(self, node_id: str, rel_type: str = None) -> set[Relation]:
		"""
		Get relations to a node

		:param node_id: Node ID
		:param rel_type: Relation type to filter on, or ``None`` to keep all types

		:return: Set of Relations

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

		result_ids = self.relations_by_to[node_id]
		if rel_type:
			result_ids = [r for r in result_ids if r in self.relations_by_type[rel_type]]
		return {self.relations[rel_id] for rel_id in result_ids}

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
		for ntype in self.node_types.values():
			if ntype.parent and ntype.parent.name == node_type:
				self.undefine_node(ntype.name)
		for rtype in self.relation_types.values():
			if node_type in (rtype.from_type, rtype.to_type):
				self.undefine_relation(rtype.name)
		self.remove_nodes(self.node_by_type[node_type])
		del self.node_types[node_type]
		self.node_by_type.pop(node_type)

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
		if not _is_reverse and self.relation_types[relation_type].reverse_name:
			self.undefine_relation(self.relation_types[relation_type].reverse_name, True)
		self.remove_relations({self.relations[r] for r in self.relations_by_type[relation_type]})
		del self.relation_types[relation_type]
		self.relations_by_type.pop(relation_type)

	def remove_nodes(
		self,
		nodes: Node | str | set[Node | str] | list[Node | str]
	) -> None:
		"""
		Remove given nodes and all their relations

		**Note:** When removing multiple nodes, this method is significantly faster than
        calling it repeatedly because indexes are rebuilt only once.

		:param nodes: Set, list, or one of node ID strings or node objects

		:return: None

		:except NotFoundError: if any node is not found
		"""
		if isinstance(nodes, list):
			nodes = set(nodes)
		elif isinstance(nodes, (str, Node)):
			nodes = {nodes}

		for node in nodes:
			if isinstance(node, Node):
				nodes.remove(node)
				nodes.add(node.id)
				node = node.id
			if node not in self.nodes:
				raise NotFoundError("Node", node)

		relations_to_remove: set[int] = set()

		for node in nodes:
			for rel in self.relations_by_from[node]:
				relations_to_remove.add(rel)
			for rel in self.relations_by_to[node]:
				relations_to_remove.add(rel)

			n = self.nodes.pop(node)
			self.node_by_type[n.type_name].discard(n)

		self.remove_relations({self.relations[rel] for rel in relations_to_remove})

	def remove_relations(self, relations: Relation | set[Relation] | list[Relation]) -> None:
		"""
		Removes given relations

		:param relations: Set, list, or one of relation objects

		:return: None

		:except NotFoundError: if any relation is not found
		"""
		if isinstance(relations, list):
			relations = set(relations)
		elif isinstance(relations, Relation):
			relations = {relations}

		for rel in relations:
			if id(rel) not in self.relations:
				raise NotFoundError("Relation", str(rel))

		for rel in relations:
			rel_id = id(rel)
			del self.relations[rel_id]
			self.relations_by_type[rel.type_name].discard(rel)
			self.relations_by_from[rel.from_node].discard(rel)
			self.relations_by_to[rel.to_node].discard(rel)

	@deprecated("Use remove_nodes() instead")
	def remove_node(self, node: Node | str | list[Node | str]) -> None:
		"""
		Remove given nodes and all their relations

		**Note:** When removing multiple nodes, this method is significantly faster than
        calling it repeatedly because indexes are rebuilt only once.

		:param node: List of node ID strings or node objects

		:return: None

		:except NotFoundError: if any node is not found
		"""
		return self.remove_nodes(node)

	@deprecated("Use remove_relations() instead")
	def remove_relation(self, relation: Relation | set[Relation] | list[Relation]) -> None:
		"""
		Removes given relations

		:param relation: Set, list, or one of relation objects

		:return: None

		:except NotFoundError: if any relation is not found
		"""
		return self.remove_relations(relation)

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

			if line.startswith('node '):
				# Collect multiline node definition
				node_def = [line]
				i += 1
				while (
						i < len(lines)
						and lines[i].strip()
						and not lines[i].strip().startswith(('node ', 'relation '))
				):
					if lines[i].strip().startswith('#'):
						i += 1
						continue
					node_def.append(lines[i])
					i += 1
				self.define_node('\n'.join(node_def))

			elif line.startswith('relation '):
				# Collect multiline relation definition
				rel_def = [line]
				i += 1
				while (
						i < len(lines)
						and lines[i].strip()
						and not lines[i].strip().startswith(('node ', 'relation '))
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
		self, file_path: str, max_size_mb: int | float = 100, validate_schema: bool = True,
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
	def _validate_loaded_data(data: dict[str, Any]) -> None:
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
	def _load_from_dict(self, data: dict[str, Any]) -> None:
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
				fields: list[Field] = list(map(
					lambda fld: Field(fld["name"], fld["dtype"]),
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

			self.relations[id(rel)] = rel

		# Rebuild all indexes
		self._rebuild_all_indexes()

	def _build_save_payload(self) -> dict[str, Any]:
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
				self.relations.values(),
				key=lambda r: (
					r.type_name,
					r.from_node,
					r.to_node,
					sorted((k, str(v)) for k, v in r.values.items())
				)
			),
		}

	def _rebuild_all_indexes(self) -> None:
		"""
		Rebuild nodes and relation indexes

		:return: None
		"""
		self.node_by_type.clear()
		self.relations_by_type.clear()
		self.relations_by_from.clear()
		self.relations_by_to.clear()

		for node_instance in self.nodes.values():
			self.node_by_type[node_instance.type_name].add(node_instance)

		for rel_id, rel in self.relations.items():
			self.relations_by_type[rel.type_name].add(rel_id)
			self.relations_by_from[rel.from_node].add(rel_id)
			self.relations_by_to[rel.to_node].add(rel_id)

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

	def stats(self) -> dict[str, Any]:
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
