"""
Query engine and object for Graphite
"""
from collections import defaultdict
from datetime import date, datetime
from functools import reduce
from typing import TYPE_CHECKING, Any
from collections.abc import Callable

from typing_extensions import deprecated

from .exceptions import ConditionError, DateParseError, NotFoundError
from .instances import Node, Relation
from .types import RelationType

if TYPE_CHECKING:
	from .engine import GraphiteEngine

# pylint: disable=too-many-public-methods
class QueryResult:
	"""
	Represents a query result that can be chained

	:param graph_engine: Graphite engine instance
	:param nodes: including nodes
	:param edges: including edges
	"""

	def __init__(
		self, graph_engine: 'GraphiteEngine', nodes: set[Node], edges: set[int] = None
	):
		self.engine = graph_engine
		self.nodes = nodes
		self.edges: set[int] = edges or set() # keep relation IDs
		self.current_relation: RelationType | None = None
		self.direction: str = 'outgoing'

	def set_val(self, **values: Any) -> 'QueryResult':
		"""
		Change result nodes' values

		**Note:** Field validation happens before any mutation.

		**Note:** This query mutates nodes in-place and changes will be applied to engine directly.

		**Note:** This query raises ``NotFoundError`` for nodes without compatible fields, use
		``.with_fields()`` to ensure all fields are valid.

		:param values: field=value pairs

		:return: self

		:except NotFoundError: if any field was invalid for any node
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
		"""
		Remove current result nodes

		**Note:** Just valid nodes will be removed from engine.

		**Note:** This query mutates nodes in-place and changes will be applied to engine directly.

		:return: A new query with remaining valid edges and no nodes
		"""
		self.engine.remove_nodes(self.validate().nodes)
		return self.validate()

	def remove_relations(self) -> 'QueryResult':
		"""
		Remove current result relations

		**Note:** Just valid relations will be removed from engine.

		**Note:** This query mutates relations in-place and changes will be applied to engine directly.

		:return: A new query with current nodes and no relations

		:raise NotFoundError: if any relations not found in engine
		"""
		self.engine.remove_relations({self.engine.relations[r] for r in self.validate().edges})
		return QueryResult(self.engine, self.nodes, None)

	def validate(self) -> 'QueryResult':
		"""
		Removes invalid nodes and relations (remove additional items compared to engine)

		:return: A new query with valid nodes and relations
		"""
		return QueryResult(
			self.engine,
			{node for node in self.nodes if node.id in self.engine.nodes},
			{relation for relation in self.edges if relation in self.engine.relations},
		)

	def where(self, condition: str | Callable) -> 'QueryResult':
		"""
		Filter nodes based on condition

		:param condition: condition string or lambda callable

		:return: new query with nodes filtered based on condition

		:except ConditionError: if fail on executing condition
		"""
		filtered_nodes: set[Node] = set()

		if callable(condition):
			# Lambda function
			for processing_node in self.nodes:
				try:
					if condition(processing_node):
						filtered_nodes.add(processing_node)
				except Exception as e:
					raise ConditionError(str(condition)) from e
		else:
			# String condition like "age > 18"
			for processing_node in self.nodes:
				if self._evaluate_condition(processing_node, condition):
					filtered_nodes.add(processing_node)

		return QueryResult(self.engine, filtered_nodes, self.edges)

	# pylint: disable=too-many-branches
	@staticmethod
	def _evaluate_condition(target_node: Node, condition: str) -> bool:
		"""
		Evaluate a condition string on a node

		:param target_node: target node
		:param condition: condition string

		:return: bool, evaluated condition

		:except ConditionError: if fail on executing condition
		"""
		# Simple condition parser
		ops = ['>=', '<=', '!=', '==', '>', '<', '=']

		for op in ops:
			if op in condition:
				left, right = condition.split(op)
				left = left.strip()
				right = right.strip()

				# Get value from node
				node_value = target_node.get(left)
				if node_value is None:
					return False

				# Parse right side
				if right[0] in ('"', "'") and right[-1] in ('"', "'"):
					right_value = right[1:-1]
				elif right.isdigit():
					right_value = int(right)
				elif right.replace('.', '').isdigit() and right.count('.') == 1:
					right_value = float(right)
				else:
					right_value = right

				if right_value == "true":
					right_value = True
				elif right_value == "false":
					right_value = False

				if isinstance(node_value, date):
					try:
						right_value = datetime.strptime(right_value, "%Y-%m-%d").date()
					except Exception as e:
						raise DateParseError(right_value) from e

				# Apply operation
				result = None
				try:
					if op in ('=', '=='):
						result = node_value == right_value
					if op == '!=':
						result = node_value != right_value
					if op == '>':
						result = node_value > right_value
					if op == '<':
						result = node_value < right_value
					if op == '>=':
						result = node_value >= right_value
					if op == '<=':
						result = node_value <= right_value
				except TypeError as e:
					raise ConditionError(condition) from e
				if result is None:
					raise ConditionError(condition)
				return result

		raise ConditionError(condition)

	def with_type(self, node_type: str, include_parent_types: bool = True) -> 'QueryResult':
		"""
		Filter nodes based on type

		**Note:** This query uses ``engine.is_node_from_type()`` when ``include_parent_types`` is
		True. So invalid nodes will be ignored in this situation.

		:param node_type: node type to filter
		:param include_parent_types: whether to include parent types or not

		:return: a new query with nodes filtered based on type
		"""
		if include_parent_types:
			type_nodes = self.engine.get_nodes_of_type(node_type, True)
			n = {node for node in self.nodes if node in type_nodes}
		else:
			n = {node for node in self.nodes if node.type_name == node_type}
		return QueryResult(self.engine, n, self.edges)

	def with_fields(self, *fields: str) -> 'QueryResult':
		"""
		Filter nodes with given fields

		:param fields: fields to filter

		:return: a new query with nodes filtered based on fields
		"""
		return QueryResult(
			self.engine,
			{node for node in self.nodes if all(field in node.values for field in fields)},
			self.edges
		)

	def traverse(
		self, relation_type: str | None = None, direction: str = 'outgoing'
	) -> 'QueryResult':
		"""
		Traverse relations from current nodes

		**Note:** Invalid nodes will be removed while traversing relations.

		:param relation_type: optional relation type for valid traverses
		:param direction: traverse direction

		:return: a new query with result nodes and traversed relations

		:except NotFoundError: if relation_type is invalid for engine
		"""
		result_nodes: set[Node] = set()
		result_edges: set[int] = set()

		if relation_type and relation_type not in self.engine.relation_types:
			raise NotFoundError(
				"Relation type",
				relation_type
			)

		for processing_node in self.nodes:
			if processing_node.id not in self.engine.nodes:
				continue

			if direction == 'outgoing':
				edges = self.engine.get_relations_from(processing_node.id, relation_type)
			elif direction == 'incoming':
				edges = self.engine.get_relations_to(processing_node.id, relation_type)
			else:  # both
				edges = (self.engine.get_relations_from(processing_node.id, relation_type).union(
					self.engine.get_relations_to(processing_node.id, relation_type)
				))

			result_edges.update({id(r) for r in edges})
			for edge in edges:
				if direction == 'outgoing':
					target_id = edge.to_node
				elif direction == 'incoming':
					target_id = edge.from_node
				else:
					target_id = (
						edge.to_node
						if edge.from_node == processing_node.id
						else edge.from_node
					)

				target_node = self.engine.get_node(target_id)
				if target_node:
					result_nodes.add(target_node)

		return QueryResult(self.engine, result_nodes, result_edges)

	def outgoing(self, relation_type: str | None = None) -> 'QueryResult':
		"""
		Traverse outgoing relations

		:param relation_type: optional relation type for valid traverses

		:return: a new query with result nodes and traversed relations
		"""
		return self.traverse(relation_type, 'outgoing')

	def incoming(self, relation_type: str | None = None) -> 'QueryResult':
		"""
		Traverse incoming relations

		:param relation_type: optional relation type for valid traverses

		:return: a new query with result nodes and traversed relations
		"""
		return self.traverse(relation_type, 'incoming')

	def both(self, relation_type: str | None = None) -> 'QueryResult':
		"""
		Traverse both directions

		:param relation_type: optional relation type for valid traverses

		:return: a new query with result nodes and traversed relations
		"""
		return self.traverse(relation_type, 'both')

	def limit(
		self,
		n: int,
		order_by_field: str | None = None,
		descending: bool = False
	) -> 'QueryResult':
		"""
		Limit number of results (just nodes)

		**Note:** Before slicing, nodes will be sorted by IDs or given field.

		:param n: number of results to return
		:param order_by_field: optional field to order results by it before slicing
		:param descending: sort results in descending order before slicing

		:return: a new query with all relations and limited nodes
		"""
		return QueryResult(
			self.engine,
			set(sorted(
				self.nodes,
				key=lambda node: node.get(order_by_field) if order_by_field else node.id,
				reverse=descending
			)[:n]),
			self.edges
		)

	def paginate(
		self,
		page: int,
		per_page: int,
		order_by_field: str | None = None,
		descending: bool = False
	) -> 'QueryResult':
		"""
		Limit number of results to specified page

		**Note:** Before slicing, nodes will be sorted by IDs or given field.

		:param page: page number (from 0)
		:param per_page: number of results in each page
		:param order_by_field: optional field to order results by it before slicing
		:param descending: sort results in descending order before slicing

		:return: a new query with all relations and paged nodes
		"""
		if per_page <= 0:
			return QueryResult(self.engine, set(), self.edges)
		if page < 1:
			return self.limit(per_page, order_by_field, descending)
		start = (page - 1) * per_page
		end = start + per_page
		return QueryResult(
			self.engine,
			set(sorted(
				self.nodes,
				key=lambda node: node.get(order_by_field) if order_by_field else node.id,
				reverse=descending
			)[start:end]),
			self.edges,
		)

	def union(self, query: 'QueryResult') -> 'QueryResult':
		"""
		Merge query results (nodes and relations)

		:param query: query to merge

		:return: a new query with merged nodes and relation
		"""
		return QueryResult(
			self.engine,
			self.nodes.union(query.nodes),
			self.edges.union(query.edges)
		)

	def exclude(self, query: 'QueryResult') -> 'QueryResult':
		"""
		Removes result of given query from current nodes and relations

		:param query: query to exclude

		:return: a new query with excluded nodes and relations
		"""
		return QueryResult(self.engine, self.nodes - query.nodes, self.edges - query.edges)

	def intersect(self, query: 'QueryResult') -> 'QueryResult':
		"""
		Just keeps shared nodes and relations between current and given queries

		:param query: query to intersect

		:return: a new query with intersected nodes and relations
		"""
		return QueryResult(self.engine, self.nodes & query.nodes, self.edges & query.edges)

	@deprecated("Query results are unique since Graphite 0.4")
	def distinct(self) -> 'QueryResult':
		"""
		Get distinct nodes (remove duplicates)

		:return: a new query with distinct nodes and original relations
		"""
		return self

	def order_by(self, by_field: str, descending: bool = False) -> list[Node]:
		"""
		Order nodes by field

		:param by_field: field name
		:param descending: whether to sort by ascending or descending

		:return: a list of sorted nodes
		"""

		def get_key(from_node: Node) -> tuple[bool, Any]:
			val = from_node.get(by_field)
			return val is None, val
		return sorted(self.nodes, key=get_key, reverse=descending)

	def sum(self, field: str) -> float:
		"""
		Sum of a field values in nodes

		**Note:** This query skips non-numeric values.

		:param field: field name

		:return: sum of field
		"""
		return reduce(
			lambda x, y: x + (y.get(field) if isinstance(y.get(field), (float, int)) else 0),
			self.nodes,
			0
		)

	def avg(self, field: str) -> float:
		"""
		Average value of a field in result

		**Note:** This query skips non-numeric values.

		:param field: field name

		:return: average of field

		:raise TypeError: If there isn't any numeric value in given field
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
		"""
		Minimum value of a field in result nodes

		:param field: field name

		:return: minimum value

		:raise TypeError: If there isn't any numeric value in given field
		"""
		nodes = {n for n in self.nodes if isinstance(n.get(field), (float, int))}
		if not nodes:
			raise TypeError(f"There is no node with numeric value for field {field}!")
		return reduce(
			lambda x, y: x if x.get(field) < y.get(field) else y,
			nodes
		).get(field)

	def max(self, field: str) -> float:
		"""
		Maximum value of a field in result nodes

		:param field: field name

		:return: maximum value

		:raise TypeError: If there isn't any numeric value in given field
		"""
		nodes = {n for n in self.nodes if isinstance(n.get(field), (float, int))}
		if not nodes:
			raise TypeError(f"There is no node with numeric value for field {field}!")
		return reduce(
			lambda x, y: x if x.get(field) > y.get(field) else y,
			nodes
		).get(field)

	def count(self) -> int:
		"""
		Count nodes

		:return: number of nodes
		"""
		return len(self.nodes)

	def get(self) -> set[Node]:
		"""
		Get all nodes

		:return: set of nodes
		"""
		return self.nodes

	def group_by(self, field: str) -> dict[Any, set[Node]]:
		"""
		Group nodes by field

		:param field: field name

		:return: dict of nodes grouped by field value
		"""
		groups = defaultdict(set)
		for processing_node in self.nodes:
			value = processing_node.get(field)
			groups[value].add(processing_node)
		return dict(groups)

	def relations(self) -> set[Relation]:
		"""
		Get all relations

		:return: set of relations
		"""
		return {self.engine.relations[r] for r in self.edges}

	def first(
		self,
		order_by_field: str | None = None,
		descending: bool = False
	) -> Node | None:
		"""
		Get first node by ID or given field

		:param order_by_field: optional field to order before slicing
		:param descending: sort results in descending order before slicing

		:return: first node or None
		"""
		return sorted(
			self.nodes,
			key=lambda node: node.get(order_by_field) if order_by_field else node.id,
			reverse=descending
		)[0] if self.nodes else None

	def ids(self) -> set[str]:
		"""
		Get node IDs

		:return: list of node IDs
		"""
		return {n.id for n in self.nodes}

class QueryBuilder:
	"""Builder for creating queries"""

	def __init__(self, graphite_engine: 'GraphiteEngine'):
		self.engine = graphite_engine

	def __getattr__(self, name: str) -> QueryResult | None:
		"""Allow starting query from node type: engine.query.User"""
		if name in self.engine.node_types:
			nodes = self.engine.get_nodes_of_type(name)
			return QueryResult(self.engine, nodes, None)
		return None

	def all(self) -> QueryResult:
		"""Allow starting query from all nodes"""
		return QueryResult(
			self.engine,
			set(self.engine.nodes.values()),
			set(self.engine.relations.keys())
		)
