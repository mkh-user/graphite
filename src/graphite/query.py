"""Query engine and object for Graphite"""
import warnings
from collections import defaultdict
from collections.abc import Callable
from enum import Enum
from functools import reduce
from typing import Any, TYPE_CHECKING, cast

from typing_extensions import deprecated

from .dsl_parser import parse_value
from .exceptions import ConditionError, NotFoundError
from .instances import Node, Relation
from .types import RelationType

if TYPE_CHECKING:
	from .graphite_engine import GraphiteEngine

class Direction(Enum):
	"""Traverse direction types.

	Attributes:
		OUTGOING: Traverse on relations where current node is source node.
		INCOMING: Traverse on relations where current node is target node.
		BOTH: Mix of `OUTGOING` and `INCOMING`.

	!!! Warning "Subject To Change"
	    This enum may be replaced by literals.
	"""
	OUTGOING = "outgoing"
	INCOMING = "incoming"
	BOTH = "both"

# pylint: disable=too-many-public-methods
# Reason: This functions help users to reduce hacks, direct access, lines of code,
# error robustness. Providing a more advanced and optimized query system can fix this issue.
class QueryResult:
	"""Represents a query result that can be chained

	Args:
	    graph_engine: Graphite engine instance
	    nodes: including nodes
	    edges: including edges
	"""

	def __init__(
		self, graph_engine: 'GraphiteEngine', nodes: set[Node], edges: set[Relation] | None = None
	):
		self.engine = graph_engine
		self.nodes = nodes
		self.edges: set[Relation] = edges or set()
		self.current_relation: RelationType | None = None

	def set_val(self, **values: Any) -> 'QueryResult':
		"""Change result nodes' values

		**Note:** Field validation happens before any mutation.

		**Note:** This query mutates nodes in-place and changes will be applied to engine directly.

		**Note:** This query raises ``NotFoundError`` for nodes without compatible fields, use
		``.with_fields()`` to ensure all fields are valid.

		Args:
		    **values: field=value pairs

		Returns:
		    self

		Raises:
		    NotFoundError: if any field was invalid for any node
		"""
		for processing_node in self.nodes:
			for field in values:
				if field not in processing_node.values:
					raise NotFoundError(
						f"Field (for node {processing_node.id})",
						field
					)
		for processing_node in self.nodes:
			for field, value in values.items():
				processing_node.set(field, value)
		return self

	def remove(self) -> 'QueryResult':
		"""Remove current result nodes

		**Note:** Just valid nodes will be removed from engine.

		**Note:** This query mutates nodes in-place and changes will be applied to engine directly.

		Returns:
		    A new query with remaining valid edges and no nodes
		"""
		self.engine.remove_nodes(self.validate().nodes)
		return self.validate()

	def remove_relations(self) -> 'QueryResult':
		"""Remove current result relations

		**Note:** Just valid relations will be removed from engine.

		**Note:** This query mutates relations in-place and changes will be applied to engine directly.

		Returns:
		    A new query with current nodes and no relations

		Raises:
		    NotFoundError: if any relations not found in engine
		"""
		self.engine.remove_relations(self.edges)
		return QueryResult(self.engine, self.nodes, None)

	def validate(self) -> 'QueryResult':
		"""Removes invalid nodes and relations (remove additional items compared to engine)

		Returns:
		    A new query with valid nodes and relations
		"""
		return QueryResult(
			self.engine,
			{ node for node in self.nodes if node.id in self.engine.nodes },
			{ relation for relation in self.edges if id(relation) in self.engine.relations },
		)

	def where(self, condition: str | Callable[[Node], bool]) -> 'QueryResult':
		"""Filter nodes based on condition

		Args:
		    condition: condition string or lambda callable

		Returns:
		    new query with nodes filtered based on condition

		Raises:
		    ConditionError: if fail on executing condition
		"""
		filtered_nodes: set[Node] = set()

		if callable(condition):
			# Lambda function
			cond = cast(Callable[[Node], bool], condition)
			for processing_node in self.nodes:
				try:
					if cond(processing_node):
						filtered_nodes.add(processing_node)
				except Exception as e:
					raise ConditionError(str(condition)) from e
		else:
			# String condition like "age > 18"
			filtered_nodes = self._evaluate_condition(self.nodes, condition)

		return QueryResult(self.engine, filtered_nodes, self.edges)

	@staticmethod
	def _evaluate_condition(target_nodes: set[Node], condition: str) -> set[Node]:
		"""Evaluate a condition string on a node

		Args:
		    target_nodes: target nodes
		    condition: condition string

		Returns:
		    bool, evaluated condition

		Raises:
		    ConditionError: if fail on executing condition
		"""
		operators = {
			'>=': lambda a, b: a >= b,
			'<=': lambda a, b: a <= b,
			'!=': lambda a, b: a != b,
			'==': lambda a, b: a == b,
			'=': lambda a, b: a == b,
			'>': lambda a, b: a > b,
			'<': lambda a, b: a < b,
		}

		for op in sorted(operators.keys(), key=len, reverse=True):
			if op in condition:
				left, right = condition.split(op, 1)
				left = left.strip()
				right = parse_value(right.strip())

				try:
					return {
						n for n in target_nodes
						if n.get(left) is not None and operators[op](n.get(left), right)
					}
				except TypeError as e:
					raise ConditionError(condition) from e

		raise ConditionError(condition)

	def with_type(self, node_type: str, include_parent_types: bool = True) -> 'QueryResult':
		"""Filter nodes based on type

		**Note:** This query uses ``engine.is_node_from_type()`` when ``include_parent_types`` is
		True. So invalid nodes will be ignored in this situation.

		Args:
		    node_type: node type to filter
		    include_parent_types: whether to include parent types or not

		Returns:
		    a new query with nodes filtered based on type
		"""
		if include_parent_types:
			type_nodes = self.engine.get_nodes_of_type(node_type, True)
			n = { node for node in self.nodes if node in type_nodes }
		else:
			n = { node for node in self.nodes if node.type_name == node_type }
		return QueryResult(self.engine, n, self.edges)

	def with_fields(self, *fields: str) -> 'QueryResult':
		"""Filter nodes with given fields

		Args:
		    *fields: fields to filter

		Returns:
		    a new query with nodes filtered based on fields
		"""
		return QueryResult(
			self.engine,
			{ node for node in self.nodes if all(field in node.values for field in fields) },
			self.edges
		)

	def traverse(
		self, relation_type: str | None = None, direction: Direction = Direction.OUTGOING
	) -> 'QueryResult':
		"""Traverse relations from current nodes

		**Note:** Invalid nodes will be removed while traversing relations.

		Args:
		    relation_type: optional relation type for valid traverses
		    direction: traverse direction

		Returns:
		    a new query with result nodes and traversed relations

		Raises:
		    NotFoundError: if relation_type is invalid for engine
		"""
		result_nodes: set[Node] = set()
		result_edges: set[Relation] = set()

		if relation_type and relation_type not in self.engine.relation_types:
			raise NotFoundError(
				"Relation type",
				relation_type
			)

		for processing_node in self.nodes:
			if direction in (Direction.OUTGOING, Direction.OUTGOING.value):
				edges = self.engine.get_relations_from(processing_node.id, relation_type)
			elif direction in (Direction.INCOMING, Direction.INCOMING.value):
				edges = self.engine.get_relations_to(processing_node.id, relation_type)
			elif direction in (Direction.BOTH, Direction.BOTH.value):
				edges = (self.engine.get_relations_from(processing_node.id, relation_type).union(
					self.engine.get_relations_to(processing_node.id, relation_type)
				))
			else:
				raise NotImplementedError(direction)

			result_edges.update(edges)
			for edge in edges:
				if direction == Direction.OUTGOING:
					target_id = edge.to_node
				elif direction == Direction.INCOMING:
					target_id = edge.from_node
				else:
					target_id = (
						edge.to_node
						if edge.from_node == processing_node.id
						else edge.from_node
					)

				result_nodes.add(self.engine.nodes[target_id])

		return QueryResult(self.engine, result_nodes, result_edges)

	def outgoing(self, relation_type: str | None = None) -> 'QueryResult':
		"""Traverse outgoing relations

		Args:
		    relation_type: optional relation type for valid traverses

		Returns:
		    a new query with result nodes and traversed relations
		"""
		return self.traverse(relation_type, Direction.OUTGOING)

	def incoming(self, relation_type: str | None = None) -> 'QueryResult':
		"""Traverse incoming relations

		Args:
		    relation_type: optional relation type for valid traverses

		Returns:
		    a new query with result nodes and traversed relations
		"""
		return self.traverse(relation_type, Direction.INCOMING)

	def both(self, relation_type: str | None = None) -> 'QueryResult':
		"""Traverse both directions

		Args:
		    relation_type: optional relation type for valid traverses

		Returns:
		    a new query with result nodes and traversed relations
		"""
		return self.traverse(relation_type, Direction.BOTH)

	def limit(
		self,
		n: int,
		order_by_field: str | None = None,
		descending: bool = False
	) -> 'QueryResult':
		"""Limit number of results (just nodes)

		**Note:** Before slicing, nodes will be sorted by IDs or given field.

		Args:
		    n: number of results to return
		    order_by_field: optional field to order results by it before
		        slicing
		    descending: sort results in descending order before slicing

		Returns:
		    a new query with all relations and limited nodes
		"""
		return QueryResult(
			self.engine,
			set(
				sorted(
					self.nodes,
					key=lambda node: node.get(order_by_field) if order_by_field else node.id,
					reverse=descending
				)[:n]
			),
			self.edges
		)

	def paginate(
		self,
		page: int,
		per_page: int,
		order_by_field: str | None = None,
		descending: bool = False
	) -> 'QueryResult':
		"""Limit number of results to specified page

		**Note:** Before slicing, nodes will be sorted by IDs or given field.

		Args:
		    page: page number (from 0)
		    per_page: number of results in each page
		    order_by_field: optional field to order results by it before
		        slicing
		    descending: sort results in descending order before slicing

		Returns:
		    a new query with all relations and paged nodes
		"""
		if per_page <= 0:
			return QueryResult(self.engine, set(), self.edges)
		if page < 1:
			return self.limit(per_page, order_by_field, descending)
		start = (page - 1) * per_page
		end = start + per_page
		return QueryResult(
			self.engine,
			set(
				sorted(
					self.nodes,
					key=lambda node: node.get(order_by_field) if order_by_field else node.id,
					reverse=descending
				)[start:end]
			),
			self.edges,
		)

	def union(self, query: 'QueryResult') -> 'QueryResult':
		"""Merge query results (nodes and relations)

		Args:
		    query: query to merge

		Returns:
		    a new query with merged nodes and relation
		"""
		return QueryResult(
			self.engine,
			self.nodes | query.nodes,
			self.edges | query.edges
		)

	def exclude(self, query: 'QueryResult') -> 'QueryResult':
		"""Removes result of given query from current nodes and relations

		Args:
		    query: query to exclude

		Returns:
		    a new query with excluded nodes and relations
		"""
		return QueryResult(self.engine, self.nodes - query.nodes, self.edges - query.edges)

	def intersect(self, query: 'QueryResult') -> 'QueryResult':
		"""Just keeps shared nodes and relations between current and given queries

		Args:
		    query: query to intersect

		Returns:
		    a new query with intersected nodes and relations
		"""
		return QueryResult(self.engine, self.nodes & query.nodes, self.edges & query.edges)

	@deprecated("Query results are unique since Graphite 0.4")
	def distinct(self) -> 'QueryResult':
		"""Get distinct nodes (remove duplicates)

		Returns:
		    a new query with distinct nodes and original relations
		"""
		warnings.warn(
			"distinct() is deprecated and unnecessary",
			DeprecationWarning
		)
		return self

	def order_by(self, by_field: str, descending: bool = False) -> list[Node]:
		"""Order nodes by field

		Args:
		    by_field: field name
		    descending: whether to sort by ascending or descending

		Returns:
		    a list of sorted nodes
		"""

		def get_key(from_node: Node) -> tuple[bool, Any]:
			val = from_node.get(by_field)
			return val is None, val

		return sorted(self.nodes, key=get_key, reverse=descending)

	def sum(self, field: str) -> float:
		"""Sum of a field values in nodes

		**Note:** This query skips non-numeric values.

		Args:
		    field: field name

		Returns:
		    sum of field
		"""
		return reduce(
			lambda x, y: x + (y.get(field) if isinstance(y.get(field), (float, int)) else 0),
			self.nodes,
			0
		)

	def avg(self, field: str) -> float:
		"""Average value of a field in result

		**Note:** This query skips non-numeric values.

		Args:
		    field: field name

		Returns:
		    average of field

		Raises:
		    TypeError: If there isn't any numeric value in given field
		"""
		numeric_count = reduce(
			lambda x, y: x + (1 if isinstance(y.get(field), (float, int)) else 0),
			self.nodes,
			0
		)
		if numeric_count == 0:
			raise TypeError(f"There is no node with numeric value for field {field}!")
		return self.sum(field) / numeric_count

	def min(self, field: str) -> float:
		"""Minimum value of a field in result nodes

		Args:
		    field: field name

		Returns:
		    minimum value

		Raises:
		    TypeError: If there isn't any numeric value in given field
		"""
		nodes = { n for n in self.nodes if isinstance(n.get(field), (float, int)) }
		if not nodes:
			raise TypeError(f"There is no node with numeric value for field {field}!")
		return reduce(
			lambda x, y: x if x.get(field) < y.get(field) else y,
			nodes
		).get(field)

	def max(self, field: str) -> float:
		"""Maximum value of a field in result nodes

		Args:
		    field: field name

		Returns:
		    maximum value

		Raises:
		    TypeError: If there isn't any numeric value in given field
		"""
		nodes = { n for n in self.nodes if isinstance(n.get(field), (float, int)) }
		if not nodes:
			raise TypeError(f"There is no node with numeric value for field {field}!")
		return reduce(
			lambda x, y: x if x.get(field) > y.get(field) else y,
			nodes
		).get(field)

	def count(self) -> int:
		"""Count nodes

		Returns:
		    number of nodes
		"""
		return len(self.nodes)

	def get(self) -> set[Node]:
		"""Get all nodes

		Returns:
		    set of nodes
		"""
		return self.nodes.copy()

	def group_by(self, field: str) -> dict[Any, set[Node]]:
		"""Group nodes by field

		Args:
		    field: field name

		Returns:
		    dict of nodes grouped by field value
		"""
		groups = defaultdict(set)
		for processing_node in self.nodes:
			value = processing_node.get(field)
			groups[value].add(processing_node)
		return dict(groups)

	def relations(self) -> set[Relation]:
		"""Get all relations

		Returns:
		    set of relations
		"""
		return self.edges.copy()

	def first(
		self,
		order_by_field: str | None = None,
		descending: bool = False
	) -> Node | None:
		"""Get first node by ID or given field

		Args:
		    order_by_field: optional field to order before slicing
		    descending: sort results in descending order before slicing

		Returns:
		    first node or None
		"""
		return sorted(
			self.nodes,
			key=lambda node: node.get(order_by_field) if order_by_field else node.id,
			reverse=descending
		)[0] if self.nodes else None

	def ids(self) -> set[str]:
		"""Get node IDs

		Returns:
		    list of node IDs
		"""
		return { n.id for n in self.nodes }

class QueryBuilder:
	"""Builder for creating queries"""

	def __init__(self, graphite_engine: 'GraphiteEngine'):
		self.engine = graphite_engine

	def __getattribute__(self, name: str) -> QueryResult:
		"""Allow starting query from node type: engine.query.User"""
		try:
			return super().__getattribute__(name)
		except AttributeError as e:
			if name in self.engine.node_types:
				nodes = self.engine.get_nodes_of_type(name)
				return QueryResult(self.engine, nodes, None)
			raise e

	def all(self) -> QueryResult:
		"""Allow starting query from all nodes"""
		return QueryResult(
			self.engine,
			set(self.engine.nodes.values()),
			set(self.engine.relations.values())
		)
