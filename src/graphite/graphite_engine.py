"""Main graph database engine of Graphite"""
# pylint: disable=too-many-lines
# Reason: With documentation, this module can't be smaller.
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
	"""A database with its own data. Can be used multiple times to create multiple databases.

	Create a new instance with:
	```python
	import graphite

	engine = graphite.engine()
	```
	"""

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
		"""Provides a fast and standard way to query on the engine.
		Use `engine.query.all()` to query from all nodes, or `engine.query.ExampleNodeType` to start
		query from all nodes with `ExampleNodeType` (or another) type. In both cases, returned
		value is a new instance of ready-to-used [QueryResult](../query/#graphite.QueryResult) that
		can be chained to build complex queries. See [Query Engine Tutorials](../../query-engine/)
		for more information.
		"""

	# =============== SCHEMA DEFINITION ===============

	def define_node(
		self,
		node_type: str,
		*fields: tuple[str, str],
		parent: str | None = None
	) -> None:
		"""Defines a node type from DSL or directly. In DSL mode (when you just pass `node_type`
		parameter), only supports **one block** starting with `"node ..."` (Use [parse()](
		./#graphite.GraphiteEngine.parse) for multiple blocks).

		Example:
		    ```python
		    engine.define_node(\"\"\"
		        node Person
		            name: string
		            age: int
		    \"\"\")
		    # Same as above:
		    engine.define_node(
		        "Person",
		        ("name", "string"),
		        ("age", "int")
		    )
		    ```

		Args:
			node_type: Node definition string in Graphite DSL or type name.
			fields: Fields of node type: `(name, type)`.
			parent: Parent node type name, You must pass it positional.

		Raises:
			ParseError: If node type definition is not valid (When passing DSL string as
			    `node_type`).
			NotFoundError: If parent node type (`from ...`) is not found.
			NotFoundError: If any `type` (second) item of any `fields` values not found.
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
		"""Defines a relation type from DSL or direct creation. In DSL mode (when you just pass
		`relation_type` parameter), only supports **one block** starting with `"relation ..."`
		(Use [parse()](./#graphite.GraphiteEngine.parse) for multiple blocks).

		Example:
		    ```python
		    engine.define_relation(\"\"\"
		        node WORKS_AT
		            Person -> Company
		            position: string
		            salary: int
		            since: date
		    \"\"\")
		    # Same as above:
		    engine.define_relation(
		        "WORKS_AT",
		        "Person",
		        "Company",
		        ("position", "string"),
		        ("salary", "int"),
		        ("since", "date")
		    )
		    ```

		Args:
		    relation_type: Relation definition string in Graphite DSL or type
		        name.
		    source_type: Valid source node type name.
		    target_type: Valid target node type name.
		    *fields: Fields of relation type: `(name, type)`.
		    reverse_name: Reverse relation name (if any).
		    is_bidirectional: Is bidirectional relation or not.

		Raises:
		    ParseError: If relation definition is not valid.
		    ParseError: If omit `source_type` or `target_type` outside DSL
		        mode.
		    RelationTypeDefineError: If relation type DSL have both `reverse ...` section
		        and `both` flag.
		    NotFoundError: If source or target node types are not found.
		    NotFoundError: If any `type` (second) item of any `fields`
		        values not found.
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
		"""Creates a node instance.

		!!! Note
		    You can use DSL to create nodes, with [parse()](./#graphite.GraphiteEngine.parse)
		    method:
		    ```python
		    engine.parse(\"\"\"
		        Person, alice, 'Alice', 32, 'alice@emial.com'
		        Person, bob, "Bob", 28, 'bob.mail@email.com'
		    \"\"\")
		    ```
		    This is same as:
		    ```python
		    engine.create_node("Person", "alice", "Alice", 32, "alice@emial.com")
		    engine.create_node("Person", "bob", "Bob", 28, "bob.mail@email.com")
		    ```
		    Advantage is that you can do any number of node creation and other data manipulation
		    with passing a multi-line value to `parse()`.

		Args:
		    node_type: Node type name, defined with [define_node()](./#
			graphite.GraphiteEngine.define_node) or [parse()](./#graphite.GraphiteEngine.parse).
		    node_id: Node ID.
		    *values: Values for node fields.
		        !!! Note
		            Count of values passed to `values` must be same as node type definition. Node
		            types inheritance from base types define with `from ...` or `parent`
		            parameter in [define_node()](./#graphite.GraphiteEngine.define_node); So if you
		            have a `Person` node type and a `User` node type inherited from it like
		            this:
		            ```
		            node Person
			            name: string
			            age: int

		            node User from Person
			            username: string
			            email: string
		            ```
		            You should pass values as `<name>, <age>, <username>, <email>` (4 values) when
		            you need to create a node from `User` type.
		    parse_fields: If `True`, parse field values from raw strings.
		        !!! Note
		            Date values will be parsed automatically, even when `parse_fields` is `False`.

		Returns:
		    Node instance added to engine.

		Raises:
		    NotFoundError: If `node_type` not defined.
		    InvalidPropertiesError: If `values` count is not same as node type
		        field count.
		    FieldError: If `values` fail in parsing, converting, or validation.
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
		"""Creates a relation instance.

		Note:
		    You can use DSL to create relations, with [parse()](./#graphite.GraphiteEngine.parse)
		    method:
		    ```python
		    engine.parse("alice -[WORKS_AT, 'Designer', 120000, 2026-01-07]-> google")
		    ```
		    This is same as:
		    ```python
		    engine.create_relation(
		        "alice",
		        "google",
		        "WORKS_AT",
		        "Designer", 120000, 2026-01-07 # or date(2026, 1, 7), will be parsed automatically.
		    )
		    ```
		    Advantage is that you can do any number of relation creation and other data manipulation
		    with passing a multi-line value to `parse()`.

		Args:
		    from_id: Source node's ID.
		    to_id: Target node's ID.
		    rel_type: Relation type name, defined with [define_relation()](./#
			graphite.GraphiteEngine.define_relation) or [parse()](./#graphite.GraphiteEngine.parse).
		    *values: Values for relation fields.
		    parse_fields: If `True`, parse field values from raw strings.
		        !!! Note
		            Date values will be parsed automatically, even when `parse_fields` is
		            `False`.

		Returns:
		    Created relation instance, added to editor.

		Raises:
		    NotFoundError: If `rel_type`, `from_id`, or `to_id` not defined.
		    InvalidRelationError: When the type of source or target node doesn't match relation
		    type signature.
		    InvalidPropertiesError: If `values` count is not same as relation
		        type field count.
		        !!! Note
		            Relation types doesn't support inheritance, so instance's value count match
		            the exact number of relation type's fields.
		    FieldError: If `values` fail in parsing, converting, or validation.
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
		"""Returns `True` if given node is from given type.

		!!! Note
		    This method considers type inheritance, so in this database:
		    ```text
		    type Person
		        → type User
		            → instance alice
		    ```
		    Alice is from `User` type and any `User` is a `Person`, so `is_node_from_type(
		    'alice',
		    'Person')` returns `True`. If you need a direct inheritance check use
		    `alice.type_name == ...`, which returns `False` for `"Person"`.

		Args:
		    node_id: Node ID.
		    node_type: Node type name.

		Returns:
		    `True` if given node is from given type otherwise `False`.

		Raises:
		    NotFoundError: If given `node_id` or `node_type` not defined.
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
		"""Returns a node with its ID.

		Args:
		    node_id: Target node ID string.

		Returns:
		    Node object.

		Raises:
		    NotFoundError: If `node_id` not defined.
		"""
		if node_id not in self.nodes:
			raise NotFoundError(
				"Node",
				node_id,
			)
		return self.nodes[node_id]

	def get_nodes_of_type(self, node_type: str, with_subtypes: bool = True) -> set[Node]:
		"""Get all nodes of a specific type.

		Args:
		    node_type: Node type name.
		    with_subtypes: If `with_subtypes` is `True`, adds all subtypes of given node type
		        recursively to the result.

		Returns:
		    Set of node objects

		Raises:
		    NotFoundError: If `node_type` not defined.
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
		"""Returns relations from a node.

		Args:
		    node_id: Node ID string.
		    rel_type: Relation type to filter on, or ``None`` to accept all types.

		Returns:
		    Set of relations.

		Raises:
		    NotFoundError: If `rel_type` or `node_id` not defined.
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
		"""Returns relations to a node.

		Args:
		    node_id: Node ID string.
		    rel_type: Relation type to filter on, or ``None`` to accept all types.

		Returns:
		    Set of relations.

		Raises:
		    NotFoundError: if `rel_type` or `node_id` not defined
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
		"""Undefines a node type, remove all referenced node types, nodes, relations type,
		and relations.

		Args:
		    node_type: Node type name.

		Raises:
		    NotFoundError: If `node_type` not defined.
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
		"""Undefines a relation type and its reverse relation type (if any) and relations.

		Args:
		    relation_type: Relation type name.

		Other Args:
		    _is_reverse: For internal use to remove reverse direction relation type.
		        ??? Warning "Hack: Undefine a type without undefining its reverse relation type"
		            You can disable deletion of reverse relation type with passing `True` to this
		            parameter, but this can lead to unpredictable results.

		Raises:
		    NotFoundError: if `relation_type` not defined
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
		"""Removes given nodes and all their relations.

		!!! Important
		    When removing multiple nodes, this method is significantly faster than calling it
		    repeatedly because indexes are rebuilt only once.

		Args:
		    nodes: Node ID or object(s) to remove.

		Raises:
		    NotFoundError: If any node is not found.
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
		"""Removes given relations.

		Args:
		    relations: Relation object(s) to remove.

		Raises:
		    NotFoundError: If any relation is not found.
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
		"""Removes given nodes.

		!!! Deprecated
		    This method is deprecated, use [remove_nodes()](
		    ./#graphite.GraphiteEngine.remove_nodes) instead. Internally uses new method.
		"""
		warnings.warn(
			"engine.remove_node() is deprecated, use remove_nodes() instead.",
			DeprecationWarning,
			stacklevel=2
		)
		return self.remove_nodes(node)

	@deprecated("Use remove_relations() instead")
	def remove_relation(self, relation: Relation | set[Relation] | list[Relation]) -> None:
		"""Removes given relations.

		!!! Deprecated
		    This method is deprecated, use [remove_relations()](
		    ./#graphite.GraphiteEngine.remove_relations) instead. Internally uses new method.
		"""
		warnings.warn(
			"engine.remove_relation() is deprecated, use remove_relations() instead.",
			DeprecationWarning,
			stacklevel=2
		)
		return self.remove_relations(relation)

	# ============= BULK LOADING / DSL =============

	def parse(self, data: str) -> None:
		"""Parses and loads data from Graphite DSL to engine.

		See [DSL Reference](../dsl/) for syntax and specification.

		Args:
		    data: Data as Graphite DSL string.

		Raises:
		    ParseError: When failed to parse data.
		        !!! Note
		            This method is semi-atomic, it means it will apply changes for each block and
		            then goes to next block. When any errors occur in a block , blocks above it are
		            applied to the engine. So it's recommend to use this method just once for an
		            engine.
		    NotFoundError: If parent node type (`from ...`) is not found when defining a node type.
			NotFoundError: If any invalid data type used in fields when defining a node type or
			    relation type.
		    RelationTypeDefineError: If relation type DSL have both `reverse ...` section and
		        `both` flag when defining a relation type..
		    NotFoundError: If source or target node types are not found when defining a relation
		        type.
		    InvalidPropertiesError: If `values` count is not same as node type or relation type
		        field count when creating a node or relation.
		    FieldError: If `values` fail in parsing, converting, or validation when creating a
		        node or relation.
		    NotFoundError: If relation type, source node ID, or target node ID not found when
		        creating a relation.
		    InvalidRelationError: When the type of source or target node doesn't match relation
		        type signature when creating a relation.
		"""
		_parser.parse(self, data)

	@deprecated("Use parse() instead")
	def load_dsl(self, dsl: str) -> None:
		"""Loads Graphite DSL to the engine.

		!!! Deprecated
		    This method is deprecated, use [parse()](./#graphite.GraphiteEngine.parse) instead.
		    Internally uses new method.
		"""
		warnings.warn(
			"engine.load_dsl() is deprecated, use parse() instead.",
			DeprecationWarning,
			stacklevel=2
		)
		self.parse(dsl)

	# =============== PERSISTENCE ===============

	def save(self, file_path: str) -> None:
		"""Save the database to a single JSON file.

		Args:
		    file_path: File path to save.
		"""
		data = self._build_save_payload()
		with open(file_path, 'w', encoding='utf-8') as f:
			json.dump(data, f, cls=GraphiteJSONEncoder, indent=2, ensure_ascii=False)

	def _build_save_payload(self) -> dict[str, Any]:
		"""Build a JSON-serializable payload for persistence

		Returns:
		    Engine snapshot as JSON dictionary
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
		"""Rebuild nodes and relation indexes
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

	def load(
		self, file_path: str, max_size_mb: int | float | None = 100, validate_schema: bool = True,
		accept_any_extension: bool = False
	) -> None:
		"""Load database from a JSON file with security checks.

		!!! Caution
		    This method will call [clear()](./#graphite.GraphiteEngine.clear) before loading data to
		    database, it means all current data will be removed.

		Args:
		    file_path: File path to load.
		    max_size_mb: Maximum allowed file size in MB, or `None` to disable check.
		    validate_schema: Validates schema consistency if `True`.
		    accept_any_extension: If `True`, accept any file extension, otherwise just `.json` is
		        valid.

		Raises:
		    FileSizeError: For files bigger than `max_size_mb` when provided.
		    SafeLoadExtensionError: For files without `.json` extension when
		        `accept_any_extension` is `True`.
		    InvalidJSONError: For error at decoding process.
		    TooNestedJSONError: For recursion error (is almost impossible).
		    ValidationError: For invalid schema when schema `validate_schema` is `True`.
		"""
		# Check file size
		if max_size_mb is not None:
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

		# Clear existing data
		self.clear()

		node_types, relation_types, nodes, relations = _load_from_dict(data)
		self.node_types = node_types.copy()
		self.relation_types = relation_types.copy()
		self.nodes = nodes.copy()
		self.relations = relations.copy()

		# Rebuild all indexes
		self._rebuild_all_indexes()

	# =============== UTILITY METHODS ===============

	def clear(self) -> None:
		"""Clears all current structure and data."""
		self.node_types.clear()
		self.relation_types.clear()
		self.nodes.clear()
		self.relations.clear()
		self.node_by_type.clear()
		self.relations_by_type.clear()
		self.relations_by_from.clear()
		self.relations_by_to.clear()

	def stats(self) -> dict[str, Any]:
		"""Reports count of each type of data in database.

		Returns:
		    Dictionary of statistics:
		    ```python
		    {
		        'node_types': <count>,
		        'relation_types': <count>,
		        'nodes': <count>,
		        'relations': <count>,
		    }
		    ```
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
		"""Highly Customizable [**BFS**](https://en.wikipedia.org/wiki/Breadth-first_search)
		(Breadth-First Search) in the graph.

		!!! Note
		    Steps are sorted by distance in returned result.

		!!! Wrapper
		    This method is a wrapper for [algorithms.bfs()](../algorithms#graphite.algorithms.bfs).

		Args:
		    start: Starting node ID or object.
		    end: One of below:

		        - `None`: Match on all nodes in the result.
		        - Node ID or object: Match on all paths to given node.
		        - Callable (`(path) -> bool`): Match on a path when given callable returns `True`.

		    stop_at_first: If `True` and `end` is provided, stops at first match.
		    direction: Direction to traverse.
		    relation_type: Type of relations to limit traverse.
		    max_depth: Maximum depth to traverse.
		    include_start: If `True` check starting node on result.
		    allow_direction_switch: If `True` allow direction switch in a path when
		        `direction=Direction.BOTH`.
		    visited: Visited set of node IDs to ignore.
		    max_results: Maximum number of results to return.

		Returns:
		    An empty list or a list of found paths sorted by distance with each item as:
		        ```python
		        (destination_node_id, path_depth, [(step_relation_obj, step_node_obj), ...])
		                                          ^^^^^^^  path_to_destination_node  ^^^^^^^
		        ```
		        `path_depth` is `0` for starting node, it means this is equal to the size of
		        `path_to_destination_node`.
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
		"""Finds shortest path from `from_node` to `to_end`.

		Non-weighted mode uses [bfs()](./#graphite.GraphiteEngine.bfs) internally.

		!!! Wrapper
		    This method is a wrapper for [algorithms.shortest_path()](
		    ../algorithms#graphite.algorithms.shortest_path).

		!!! Bug "Not Implemented Completely"
		    Weighted mode is **not implemented yet**.

		Args:
		    from_node: Starting node Id or object.
		    to_end: One of below:

		        - `None`: Match on all nodes in the result. It means nearest neighbor.
		        - Node ID or object: Match on all paths to given node.
		        - Callable (`(path) -> bool`): Match on a path when given callable returns `True`.

		    direction: Direction to traverse.
		    relation_type: Type of relations to allow traverse.
		    max_depth: Maximum depth to traverse.
		    allow_direction_switch: If `True` allow direction switch in a path when `direction =
		        Direction.BOTH`.
		    ignore_nodes: Node IDs to ignore.
		    weight: Optional field name to weighted pathfinding. **(Not implemented yet)**

		Returns:
		    `None` or the shortest found path as:
		        ```python
		        (destination_node_id, path_depth, [(step_relation_obj, step_node_obj), ...])
		                                          ^^^^^^^  path_to_destination_node  ^^^^^^^
		        ```
		        `path_depth` is `0` for starting node, it means this is equal to the size of
		        `path_to_destination_node`.
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
		weight: str | None = None,
		max_results: int | None = None
	) -> list[tuple[str, int, list[tuple[Relation, Node]]]]:
		"""All shortest paths from `from_node` to `to_end`.

		Non-weighted mode uses [bfs()](./#graphite.GraphiteEngine.bfs) internally.

		!!! Wrapper
		    This method is a wrapper for [algorithms.all_shortest_paths()](
		    ../algorithms#graphite.algorithms.all_shortest_paths).

		!!! Bug "Not Implemented Completely"
		    Weighted mode is **not implemented yet**.

		Args:
		    from_node: Starting node ID or object.
		    to_end: One of below:

		        - `None`: Match on all nodes in the result. It means all (or `max_results`) nearest
		            neighbors.
		        - Node ID or object: Match on all paths to given node.
		        - Callable (`(path) -> bool`): Match on a path when given callable returns `True`.

		    direction: Direction to traverse.
		    relation_type: Type of relations to limit traverse.
		    max_depth: Maximum depth to traverse.
		    allow_direction_switch: If `True` allow direction switch in a path when
		        `direction=Direction.BOTH`.
		    ignore_nodes: Visited set of node IDs to ignore.
		    weight: Optional field name to weighted pathfinding.
		    max_results: Maximum number of results to return.

		Returns:
		    An empty list or a list of found paths sorted by distance with each item as:
		        ```python
		        (destination_node_id, path_depth, [(step_relation_obj, step_node_obj), ...])
		                                          ^^^^^^^  path_to_destination_node  ^^^^^^^
		        ```
		        `path_depth` is `0` for starting node, it means this is equal to the size of
		        `path_to_destination_node`.
		"""
		return _algorithms.all_shortest_paths(
			self, from_node, to_end, direction, relation_type, max_depth, allow_direction_switch,
			ignore_nodes, weight, max_results
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
		"""Splits given nodes to connected components.

		!!! Wrapper
		    This method is a wrapper for [algorithms.connected_components()](
		    ../algorithms#graphite.algorithms.connected_components).

		!!! Note
		    Uses [bfs()](./#graphite.GraphiteEngine.bfs) internally.

		Args:
		    nodes: One or a set of node (objects or IDs) to group, or `None` to get all nodes from
		        engine.
		    return_all_nodes: If `True`, includes all nodes in each component, not just intersection
		        of them with input `nodes`. Has no effect when `nodes = None`. `False` is unusual
		        when using a single node.
		    direction: Direction to traverse.
		    relation_type: Type of relations to allow traverse.
		    allow_direction_switch: If `True`, allow direction switch in a path when `direction
		        = Direction.BOTH`.
		    ignore_nodes: Node IDs to ignore.

		Returns:
		    List of component nodes.
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
		"""Returns neighbors of `start` in given `max_distance`.

		!!! Wrapper
		    This method is a wrapper for [algorithms.neighborhood()](
		    ../algorithms#graphite.algorithms.neighborhood).

		!!! Note
		    Uses [bfs()](./#graphite.GraphiteEngine.bfs) internally.

		Args:
		    start: Starting node object or ID.
		    max_distance: Maximum distance to traverse.
		    filter_method: Optional callable to filter neighbors (`(path) -> bool`).
		    max_results: Maximum number of results to return.
		    direction: Direction to traverse.
		    relation_type: Type of relations to allow
		        traverse.
		    allow_direction_switch: If `True`, allow direction switch in a path when `direction =
		        Direction.BOTH`.
		    ignore_nodes: Node IDs to ignore.

		Returns:
		    Set of neighbors (including `start`) with their distance to
		        `start`, and set of relations in neighborhood.
		"""
		return _algorithms.neighborhood(
			self, start, max_distance, filter_method, max_results, direction, relation_type,
			allow_direction_switch, ignore_nodes
		)
