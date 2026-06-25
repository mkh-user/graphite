"""
Main graph database engine of Graphite
"""
import json
import os
import warnings
from collections import defaultdict
from typing import Any, Callable, cast

from typing_extensions import deprecated

from . import algorithms as _algorithms, dsl_parser as _parser
from .exceptions import (
	FileSizeError, InvalidJSONError, InvalidPropertiesError, InvalidRelationError,
	NotFoundError, ParseError, RelationTypeDefineError, SafeLoadExtensionError, TooNestedJSONError,
)
from .instances import Node, Relation
from .query import Direction, QueryBuilder
from .serialization import (
	GraphiteJSONEncoder, SAVE_FILE_VERSION, _load_from_dict, _validate_loaded_data,
	graphite_object_hook
)
from .types import DataType, Field, NodeType, RelationType

# pylint: disable=too-many-public-methods, too-many-instance-attributes
# Reason: GraphiteEngine is main entry point of Graphite, so count of its members is reasonable.
class GraphiteEngine:
	"""Main graph database engine"""

	def __init__(self):
		self.node_types: dict[str, NodeType] = { }
		self.relation_types: dict[str, RelationType] = { }
		self.nodes: dict[str, Node] = { }
		self.relations: dict[int, Relation] = { }
		self.node_by_type: dict[str, set[str]] = defaultdict(set)
		self.relations_by_type: dict[str, set[int]] = defaultdict(set)
		self.relations_by_from: dict[str, set[int]] = defaultdict(set)
		self.relations_by_to: dict[str, set[int]] = defaultdict(set)
		self.query: QueryBuilder = QueryBuilder(self)

	# =============== SCHEMA DEFINITION ===============

	def define_node(
		self,
		node_type: str,
		*fields: tuple[str, str],
		parent: str | None = None
	) -> None:
		"""
		Define a node type from DSL / direct creation

		:param node_type: Node definition string in Graphite DSL or type name
		:param fields: Fields of node type: (name, type)
		:param parent: Parent node type name

		:return: None

		:except GraphiteError: if node definition is not valid
		:except NotFoundError: if parent node definition (from ...) is not found
		"""
		node_type = node_type.strip()
		if node_type.startswith('node '):
			node_type, _fields, parent = _parser.parse_node_definition(node_type)
			fields = tuple(_fields)

		if parent is not None:
			if parent not in self.node_types:
				raise NotFoundError(
					"Parent node type",
					parent,
				)
			parent: NodeType = self.node_types[parent]

		final_fields: list[Field] = []
		for name, data_type in fields:
			try:
				final_fields.append(Field(name, DataType(data_type)))
			except ValueError as e:
				raise NotFoundError(
					"Data type",
					data_type
				) from e
		node_type_obj = NodeType(node_type, final_fields, parent)
		self.node_types[node_type] = node_type_obj

	# pylint: disable=too-many-positional-arguments, too-many-arguments, keyword-arg-before-vararg
	# Reason: Arguments are just relation type fields, and order of them is based on usage.
	def define_relation(
		self,
		relation_type: str,
		source_type: str | None = None,
		target_type: str | None = None,
		*fields: tuple[str, str],
		reverse_name: str | None = None,
		is_bidirectional: bool = False
	) -> None:
		"""
		Define a relation type from DSL / direct creation

		:param relation_type: Relation definition string in Graphite DSL / relation type name
		:param source_type: Source node type name
		:param target_type: Target node type name
		:param fields: Fields of relation type: (name, type)
		:param reverse_name: Reverse relation name
		:param is_bidirectional: Is bidirectional relation

		:return: None

		:except ParseError: if relation definition is not valid
		:except RelationTypeDefineError: if relation type have both 'reverse ...' and 'both' flags
		:except NotFoundError: if source or target node types are not found
		"""
		relation_type = relation_type.strip()
		if relation_type.startswith('relation '):
			(relation_type, source_type, target_type, _fields,
			reverse_name, is_bidirectional) = _parser.parse_relation_definition(relation_type)
			fields = tuple(_fields)

		if source_type is None or target_type is None:
			raise ParseError(
				"Source and target node type is required for relation types"
			)
		if reverse_name is not None and is_bidirectional:
			raise RelationTypeDefineError(relation_type)
		# Validate node types exist
		if source_type not in self.node_types:
			raise NotFoundError(
				"Node type",
				source_type,
			)
		if target_type not in self.node_types:
			raise NotFoundError(
				"Node type",
				target_type,
			)

		final_fields: list[Field] = []
		for name, data_type in fields:
			try:
				final_fields.append(Field(name, DataType(data_type)))
			except ValueError as e:
				raise NotFoundError(
					"Data type",
					data_type
				) from e

		relation_type_obj = RelationType(
			relation_type, source_type, target_type,
			final_fields, reverse_name, is_bidirectional
		)
		self.relation_types[relation_type] = relation_type_obj

		# Register reverse relation if specified
		if reverse_name:
			reverse_rel = RelationType(
				reverse_name, target_type, source_type,
				final_fields, relation_type, is_bidirectional
			)
			self.relation_types[reverse_name] = reverse_rel

	# =============== DATA MANIPULATION ===============

	def create_node(
		self, node_type: str, node_id: str, *values: Any, parse_fields: bool = False
	) -> Node:
		"""
		Create a node instance

		:param node_type: Node type
		:param node_id: Node ID
		:param values: Values for node fields
		:param parse_fields: Whatever to parse field values or not

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
		node_values = { }
		if parse_fields:
			for current_field, value in zip(all_fields, values):
				node_values[current_field.name] = _parser.parse_field_value(value, current_field)
		else:
			for current_field, value in zip(all_fields, values):
				node_values[current_field.name] = _parser.validate_field_value(
					value,
					current_field
				)

		new_node = Node(node_type, node_id, node_values, node_type_obj)
		self.nodes[node_id] = new_node
		self.node_by_type[node_type].add(node_id)
		return new_node

	def create_relation(
		self, from_id: str, to_id: str, rel_type: str, *values: Any, parse_fields: bool = False
	) -> Relation:
		"""
		Create a relation instance

		:param from_id: Source ID
		:param to_id: Target ID
		:param rel_type: Relation type
		:param values: Values for relation fields
		:param parse_fields: Whatever to parse field values or not

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
		rel_values = { }
		if parse_fields:
			for current_field, value in zip(rel_type_obj.fields, values):
				rel_values[current_field.name] = _parser.parse_field_value(value, current_field)
		else:
			for current_field, value in zip(rel_type_obj.fields, values):
				rel_values[current_field.name] = _parser.validate_field_value(
					value,
					current_field
				)

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
		return self.nodes[node_id]

	def get_nodes_of_type(self, node_type: str, with_subtypes: bool = True) -> set[Node]:
		"""
		Get all nodes of a specific type

		:param node_type: Node type string
		:param with_subtypes: If `with_subtypes` is True, adds all subtypes of node type recursively

		:return: Set of Node objects

		:except NotFoundError: if `node_type` not defined
		"""
		return { self.nodes[n] for n in self._get_nodes_of_type_ids(node_type, with_subtypes) }

	def _get_nodes_of_type_ids(self, node_type: str, with_subtypes: bool = True) -> set[str]:
		if node_type not in self.node_types:
			raise NotFoundError(
				"Node type",
				node_type
			)

		nodes = self.node_by_type[node_type]
		if with_subtypes:
			nodes.update(
				*[self._get_nodes_of_type_ids(ntype, True)
					for ntype in self._get_subtypes(node_type)]
			)
		return nodes

	def _get_subtypes(self, node_type: str) -> set[str]:
		result: set[str] = set()
		for ntype in self.node_types.values():
			current = ntype
			while current.parent:
				if current.parent.name == node_type:
					result.add(ntype.name)
					break
				current = current.parent
		return result

	def get_relations_from(self, node_id: str, rel_type: str | None = None) -> set[Relation]:
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
			result_ids = { r for r in result_ids if r in self.relations_by_type[rel_type] }
		return { self.relations[rel_id] for rel_id in result_ids }

	def get_relations_to(self, node_id: str, rel_type: str | None = None) -> set[Relation]:
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
			result_ids = { r for r in result_ids if r in self.relations_by_type[rel_type] }
		return { self.relations[rel_id] for rel_id in result_ids }

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
		for ntype in list(self.node_types.values()):
			if ntype.parent and ntype.parent.name == node_type:
				self.undefine_node(ntype.name)
		for rtype in list(self.relation_types.values()):
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
		reverse_name = self.relation_types[relation_type].reverse_name
		if not _is_reverse and reverse_name:
			self.undefine_relation(reverse_name, True)
		self.remove_relations({ self.relations[r] for r in self.relations_by_type[relation_type] })
		del self.relation_types[relation_type]
		self.relations_by_type.pop(relation_type)

	def remove_nodes(
		self,
		nodes: Node | str | set[Node | str] | list[Node | str]
		       | set[Node] | set[str] | list[Node] | list[str]
	) -> None:
		"""
		Remove given nodes and all their relations

		**Note:** When removing multiple nodes, this method is significantly faster than
        calling it repeatedly because indexes are rebuilt only once.

		:param nodes: Set, list, or one of node ID strings or node objects

		:return: None

		:except NotFoundError: if any node is not found
		"""
		if isinstance(nodes, (str, Node)):
			_nodes = { nodes if isinstance(nodes, str) else nodes.id }
		else:
			_nodes = { n if isinstance(n, str) else n.id for n in nodes }

		missing = { nid for nid in _nodes if nid not in self.nodes }
		if missing:
			raise NotFoundError("Node", f"{next(iter(missing))} (and {len(missing) - 1} others)")

		relations_to_remove = self._collect_relations(_nodes)
		self.remove_relations(relations_to_remove)

		for node in _nodes:
			n = self.nodes.pop(node)
			self.node_by_type[n.type_name].discard(node)
			del self.relations_by_to[node]
			del self.relations_by_from[node]

	def _collect_relations(self, nodes: set[str]) -> set[Relation]:
		relations: set[int] = set()
		for node in nodes:
			relations.update(self.relations_by_from[node])
			relations.update(self.relations_by_to[node])
		return { self.relations[r] for r in relations }

	def remove_relations(self, relations: Relation | set[Relation] | list[Relation]) -> None:
		"""
		Removes given relations

		:param relations: Set, list, or one of relation objects

		:return: None

		:except NotFoundError: if any relation is not found
		"""
		if isinstance(relations, list):
			relations = cast(set[Relation], set(relations))
		elif isinstance(relations, Relation):
			relations = { relations }

		for rel in relations:
			if id(rel) not in self.relations:
				raise NotFoundError("Relation", str(rel))

		for rel in relations:
			rel_id = id(rel)
			del self.relations[rel_id]
			self.relations_by_type[rel.type_name].discard(rel_id)
			self.relations_by_from[rel.from_node].discard(rel_id)
			self.relations_by_to[rel.to_node].discard(rel_id)

	@deprecated("Use remove_nodes() instead")
	def remove_node(self, node: Node | str | list[Node | str]) -> None:
		"""
		Deprecated: Use remove_nodes() instead
		"""
		warnings.warn(
			"engine.remove_node() is deprecated, use remove_nodes() instead.",
			DeprecationWarning,
			stacklevel=2
		)
		return self.remove_nodes(node)

	@deprecated("Use remove_relations() instead")
	def remove_relation(self, relation: Relation | set[Relation] | list[Relation]) -> None:
		"""
		Deprecated: Use remove_relations() instead
		"""
		warnings.warn(
			"engine.remove_relation() is deprecated, use remove_relations() instead.",
			DeprecationWarning,
			stacklevel=2
		)
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
		_parser.parse(self, data)

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
		warnings.warn(
			"engine.load_dsl() is deprecated, use parse() instead.",
			DeprecationWarning,
			stacklevel=2
		)
		self.parse(dsl)

	# =============== PERSISTENCE ===============

	def save(self, file_path: str) -> None:
		"""
		Save database to a single file using JSON

		:param file_path: File path
		"""
		data = self._build_save_payload()
		with open(file_path, 'w', encoding='utf-8') as f:
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
			_validate_loaded_data(data)

		# Load normally
		self._load_from_dict(data)


	def _load_from_dict(self, data: dict[str, Any]) -> None:
		"""
		Internal method to load from dictionary (used by both load and load_safe)

		:param data: Dictionary of loaded data

		:return: None
		"""
		# Clear existing data
		self.clear()

		node_types, relation_types, nodes, relations = _load_from_dict(data)
		self.node_types = node_types.copy()
		self.relation_types = relation_types.copy()
		self.nodes = nodes.copy()
		self.relations = relations.copy()

		# Rebuild all indexes
		self._rebuild_all_indexes()

	def _build_save_payload(self) -> dict[str, Any]:
		"""
		Build a JSON-serializable payload for persistence

		:return: Engine snapshot as JSON dictionary
		"""
		return {
			"version": SAVE_FILE_VERSION,
			"node_types": list(self.node_types.values()),
			"relation_types": list(self.relation_types.values()),
			"nodes": list(self.nodes.values()),
			"relations": sorted(
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

		for node_id, node_instance in self.nodes.items():
			self.node_by_type[node_instance.type_name].add(node_id)

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
		# Legacy unsafe loading (for backward compatibility)
		if not safe_mode:
			warnings.warn(
				"Unsafe loading mode will be deprecated in next versions. Use safe_mode=True for security. "
				"You can use 'graphite.Migration.convert_pickle_to_json()' to update your database.",
				PendingDeprecationWarning
			)
			self._load_unsafe(filename)
			return

		self.load_safe(filename)

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
			'node_types': len(self.node_types),
			'relation_types': len(self.relation_types),
			'nodes': len(self.nodes),
			'relations': len(self.relations),
		}

	# ================== ALGORITHMS =================

	# pylint: disable=too-many-positional-arguments, too-many-arguments
	# Reason: See main function.
	def bfs(
		self,
		start: Node | str,
		end: Node | str | Callable[[list[tuple[Relation, Node]]], bool] | None = None,
		stop_at_first: bool = True,
		direction: Direction = Direction.OUTGOING,
		relation_type: str | None = None,
		max_depth: int | None = None,
		include_start: bool = False,
		allow_direction_switch: bool = False,
		visited: set[str] | None = None,
		max_results: int | None = None
	) -> list[tuple[str, int, list[tuple[Relation, Node]]]]:
		"""
		Highly customizable Breadth-First Search in graph

		Note: Steps are sorted by distance (it's logical order too). When using INCOMING or BOTH
		directions, results contain founded paths with a pattern like this:
		``'end', depth_int, [(Relation(Type:other->start), Node(Type:other)), ...,
		(Relation(Type:end->another), Node(Type:end))]``

		:param start: Starting node
		:param end: End target, node, node ID, or a callable ((path) -> bool) to match on path
		:param stop_at_first: If True and ``end`` is provided, stops at first match
		:param direction: Direction to traverse
		:param relation_type: Type of relations to traverse
		:param max_depth: Maximum depth to traverse
		:param include_start: If True check starting node on result
		:param allow_direction_switch: If True allow direction switch in a path when ``direction =
		Direction.BOTH``
		:param visited: Optional visited set to ignore
		:param max_results: Maximum number of results to return
		:return: An empty list or a list of found paths with each item as: (node_id, path_depth,
		list(path_steps)), where ``path_steps`` is (relation, node)
		"""
		return _algorithms.bfs(
			self, start, end, stop_at_first, direction, relation_type, max_depth, include_start,
			allow_direction_switch, visited, max_results
		)

	# pylint: disable=too-many-positional-arguments, too-many-arguments
	# Reason: See main function.
	def shortest_path(
		self,
		from_node: Node | str,
		to_end: Node | str | Callable[[list[tuple[Relation, Node]]], bool] | None = None,
		direction: Direction = Direction.OUTGOING,
		relation_type: str | None = None,
		max_depth: int | None = None,
		allow_direction_switch: bool = False,
		ignore_nodes: set[str] | None = None,
		weight: str | None = None
	) -> tuple[str, int, list[tuple[Relation, Node]]] | None:
		"""
		Shortest path from ``from_node`` to ``to_end``

		Non-weighted mode uses BFS. Weighted mode is not implemented yet.

		:param from_node: Starting node
		:param to_end: End node, node ID, or function to call (list(steps) -> bool) or None to get one
		of nearest neighbors
		:param direction: Direction to traverse
		:param relation_type: Type of relations to traverse
		:param max_depth: Maximum depth to traverse
		:param allow_direction_switch: If True allow direction switch in a path when ``direction =
		Direction.BOTH``
		:param ignore_nodes: Nodes to ignore
		:param weight: Optional field name to weighted pathfinding (Not implemented yet)
		:return: Target node ID, Distance, List of steps where each step is a (Relation, Node) pair
		"""
		return _algorithms.shortest_path(
			self, from_node, to_end, direction, relation_type, max_depth, allow_direction_switch,
			ignore_nodes, weight
		)

	# pylint: disable=too-many-positional-arguments, too-many-arguments
	# Reason: See main function.
	def all_shortest_paths(
		self,
		from_node: Node | str,
		to_end: Node | str | Callable[[list[tuple[Relation, Node]]], bool] | None = None,
		direction: Direction = Direction.OUTGOING,
		relation_type: str | None = None,
		max_depth: int | None = None,
		allow_direction_switch: bool = False,
		ignore_nodes: set[str] | None = None,
		weight: str | None = None
	) -> list[tuple[str, int, list[tuple[Relation, Node]]]]:
		"""
		All shortest paths from ``from_node`` to ``to_end``

		Non-weighted mode uses BFS. Weighted mode is not implemented yet.

		:param from_node: Starting node
		:param to_end: End node, node ID, or function to call (list(steps) -> bool) or None to match
		:param direction: Direction to traverse
		:param relation_type: Relation types to traverse
		:param max_depth: Maximum depth to traverse
		:param allow_direction_switch: If True allow direction switch in a path when ``direction =
		Direction.BOTH``
		:param ignore_nodes: Nodes to ignore
		:param weight: Optional weight field name to weighted pathfinding (Not implemented yet)
		:return: List of result paths like shortest_path(), where items are sorted by distance / cost
		and cycles are trimmed
		"""
		return _algorithms.all_shortest_paths(
			self, from_node, to_end, direction, relation_type, max_depth, allow_direction_switch,
			ignore_nodes, weight
		)

	# pylint: disable=too-many-positional-arguments, too-many-arguments
	# Reason: See main function.
	def connected_components(
		self,
		nodes: Node | str | set[Node | str] | None = None,
		return_all_nodes: bool = False,
		direction: Direction = Direction.OUTGOING,
		relation_type: str | None = None,
		allow_direction_switch: bool = False,
		ignore_nodes: set[str] | None = None
	) -> list[set[str]]:
		"""
		Split given nodes to connected components

		:param nodes: One or a set of nodes / node IDs to group, or None to get all nodes from engine
		:param return_all_nodes: If True return all nodes in component, not just intersection with
		``nodes``
		:param direction: Direction to traverse
		:param relation_type: Type of relations to traverse
		:param allow_direction_switch: If True allow direction switch in a path when ``direction =
		Direction.BOTH``
		:param ignore_nodes: Nodes to ignore
		:return: List of component nodes
		"""
		return _algorithms.connected_components(
			self, nodes, return_all_nodes, direction, relation_type, allow_direction_switch,
			ignore_nodes
		)

	# pylint: disable=too-many-positional-arguments, too-many-arguments
	# Reason: See main function.
	def neighborhood(
		self,
		start: Node | str,
		max_distance: int | None = None,
		filter_method: Callable[[list[tuple[Relation, Node]]], bool] | None = None,
		max_results: int | None = None,
		direction: Direction = Direction.OUTGOING,
		relation_type: str | None = None,
		allow_direction_switch: bool = False,
		ignore_nodes: set[str] | None = None
	) -> tuple[set[tuple[Node, int]], set[Relation]]:
		"""
		Get neighbors of ``start`` in given ``max_distance``

		:param start: Starting node object or ID
		:param max_distance: Maximum distance to traverse
		:param filter_method: Optional callable to filter neighbors
		:param max_results: Maximum number of results to return
		:param direction: Direction to traverse
		:param relation_type: Type of relations to traverse
		:param allow_direction_switch: If True allow direction switch in a path when ``direction =
		Direction.BOTH``
		:param ignore_nodes: Nodes to ignore
		:return: Set of neighbors (including ``start``) with their distance to ``start``, and set of
		relations in neighborhood
		"""
		return _algorithms.neighborhood(
			self, start, max_distance, filter_method, max_results, direction, relation_type,
			allow_direction_switch, ignore_nodes
		)
