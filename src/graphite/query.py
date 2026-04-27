"""
Query engine and object for Graphite
"""
from collections import defaultdict
from datetime import date, datetime
from functools import reduce
from typing import Any, Callable, Dict, List, Optional, TYPE_CHECKING, Union

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
		self, graph_engine: 'GraphiteEngine', nodes: List[Node], edges: List[Relation] = None
	):
		self.engine = graph_engine
		self.nodes = nodes
		self.edges = edges or []
		self.current_relation: Optional[RelationType] = None
		self.direction: str = 'outgoing'

	def set(self, **values: Any) -> 'QueryResult':
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
		for processing_node in self.nodes:
			if processing_node.id in self.engine.nodes:
				self.engine.remove_node(processing_node)
		for relation in self.edges.copy():
			if relation not in self.engine.relations_by_type.get(relation.type_name, []):
				self.edges.remove(relation)
		return QueryResult(self.engine, [], self.edges)

	def remove_relations(self) -> 'QueryResult':
		"""
		Remove current result relations

		**Note:** Just valid relations will be removed from engine.

		**Note:** This query mutates relations in-place and changes will be applied to engine directly.

		:return: A new query with current nodes and no relations

		:raise NotFoundError: if any relations not found in engine
		"""
		for relation in self.edges:
			if relation in self.engine.relations_by_type.get(relation.type_name, []):
				self.engine.remove_relation(relation)
		return QueryResult(self.engine, self.nodes, [])

	def validate(self) -> 'QueryResult':
		"""
		Removes invalid nodes and relations (remove additional items compared to engine)

		:return: A new query with valid nodes and relations
		"""
		return QueryResult(
			self.engine,
			[node for node in self.nodes if node.id in self.engine.nodes],
			[relation for relation in self.edges if (
				relation in self.engine.relation_types.get(relation.type_name, [])
			)]
		)

	def where(self, condition: Union[str, Callable]) -> 'QueryResult':
		"""
		Filter nodes based on condition

		:param condition: condition string or lambda callable

		:return: new query with nodes filtered based on condition

		:except ConditionError: if fail on executing condition
		"""
		filtered_nodes = []

		if callable(condition):
			# Lambda function
			for processing_node in self.nodes:
				try:
					if condition(processing_node):
						filtered_nodes.append(processing_node)
				except Exception as e:
					raise ConditionError(str(condition)) from e
		else:
			# String condition like "age > 18"
			for processing_node in self.nodes:
				if self._evaluate_condition(processing_node, condition):
					filtered_nodes.append(processing_node)

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
			n = [
				node for node in self.nodes if (
					node in self.engine.nodes and
					self.engine.is_node_from_type(node.id, node_type)
				)
			]
		else:
			n = [node for node in self.nodes if node.type_name == node_type]
		return QueryResult(self.engine, n, self.edges)

	def with_fields(self, *fields: str) -> 'QueryResult':
		"""
		Filter nodes with given fields

		:param fields: fields to filter

		:return: a new query with nodes filtered based on fields
		"""
		return QueryResult(
			self.engine,
			[node for node in self.nodes if all(field in node.values for field in fields)],
			self.edges
		)

	def traverse(
		self, relation_type: Optional[str] = None, direction: str = 'outgoing'
	) -> 'QueryResult':
		"""
		Traverse relations from current nodes

		**Note:** Invalid nodes will be removed while traversing relations.

		:param relation_type: optional relation type for valid traverses
		:param direction: traverse direction

		:return: a new query with result nodes and traversed relations

		:except NotFoundError: if relation_type is invalid for engine
		"""
		result_nodes = []
		result_edges = []

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
				edges = (self.engine.get_relations_from(processing_node.id, relation_type) +
						 self.engine.get_relations_to(processing_node.id, relation_type))

			for edge in edges:
				result_edges.append(edge)
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
					result_nodes.append(target_node)

		# Remove duplicates
		result_nodes = list(dict((n.id, n) for n in result_nodes).values())
		return QueryResult(self.engine, result_nodes, result_edges)

	def outgoing(self, relation_type: Optional[str] = None) -> 'QueryResult':
		"""
		Traverse outgoing relations

		:param relation_type: optional relation type for valid traverses

		:return: a new query with result nodes and traversed relations
		"""
		return self.traverse(relation_type, 'outgoing')

	def incoming(self, relation_type: Optional[str] = None) -> 'QueryResult':
		"""
		Traverse incoming relations

		:param relation_type: optional relation type for valid traverses

		:return: a new query with result nodes and traversed relations
		"""
		return self.traverse(relation_type, 'incoming')

	def both(self, relation_type: Optional[str] = None) -> 'QueryResult':
		"""
		Traverse both directions

		:param relation_type: optional relation type for valid traverses

		:return: a new query with result nodes and traversed relations
		"""
		return self.traverse(relation_type, 'both')

	def limit(self, n: int) -> 'QueryResult':
		"""
		Limit number of results (just nodes)

		:param n: number of results to return

		:return: a new query with all relations and limited nodes
		"""
		return QueryResult(self.engine, self.nodes[:n], self.edges)

	def paginate(self, page: int, per_page: int) -> 'QueryResult':
		"""
		Limit number of results to specified page

		:param page: page number (from 0)
		:param per_page: number of results in each page

		:return: a new query with all relations and paged nodes
		"""
		if per_page <= 0:
			return self.limit(0)
		if page < 1:
			return self.limit(per_page)
		start = (page - 1) * per_page
		end = start + per_page
		return QueryResult(
			self.engine,
			self.nodes[start:end],
			self.edges,
		)

	def union(self, query: 'QueryResult', auto_distinct: bool = False) -> 'QueryResult':
		"""
		Merge query results (nodes and relations)

		**Note:** When ``auto_distinct`` is False, This query will produce duplicates if the same
		node exists in both results, you can use manual ``.distinct()`` to remove duplicates.

		:param query: query to merge
		:param auto_distinct: whether to automatically distinct

		:return: a new query with merged nodes and relation
		"""
		result = QueryResult(self.engine, self.nodes + query.nodes, self.edges + query.edges)
		return result.distinct() if auto_distinct else result

	def exclude(self, query: 'QueryResult') -> 'QueryResult':
		"""
		Removes result of given query from current nodes and relations

		:param query: query to exclude

		:return: a new query with excluded nodes and relations
		"""
		exclude_ids = {n.id for n in query.nodes}
		new_nodes = [n for n in self.nodes if n.id not in exclude_ids]
		new_edges = [e for e in self.edges if e not in query.edges]
		return QueryResult(self.engine, new_nodes, new_edges)

	def intersect(self, query: 'QueryResult') -> 'QueryResult':
		"""
		Just keeps shared nodes and relations between current and given queries

		:param query: query to intersect

		:return: a new query with intersected nodes and relations
		"""
		intersect_ids = {n.id for n in query.nodes}
		new_nodes = [n for n in self.nodes if n.id in intersect_ids]
		intersect_edges = query.edges
		new_edges = [e for e in self.edges if e in intersect_edges]
		return QueryResult(self.engine, new_nodes, new_edges)

	def distinct(self) -> 'QueryResult':
		"""
		Get distinct nodes (remove duplicates)

		:return: a new query with distinct nodes and original relations
		"""
		seen = set()
		distinct_nodes = []
		for processing_node in self.nodes:
			if processing_node.id not in seen:
				seen.add(processing_node.id)
				distinct_nodes.append(processing_node)
		return QueryResult(self.engine, distinct_nodes, self.edges)

	def order_by(self, by_field: str, descending: bool = False) -> 'QueryResult':
		"""
		Order nodes by field

		:param by_field: field name
		:param descending: whether to sort by ascending or descending

		:return: a new query with sorted nodes and all relations
		"""

		def get_key(from_node: Node) -> tuple[bool, Any]:
			val = from_node.get(by_field)
			return val is None, val

		sorted_nodes = sorted(self.nodes, key=get_key, reverse=descending)
		return QueryResult(self.engine, sorted_nodes, self.edges)

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
		count = len([None for n in self.nodes if isinstance(n.get(field), (float, int))])
		if count == 0:
			raise TypeError(f"There is no node with numeric value for field {field}!")
		return self.sum(field) / count

	def min(self, field: str) -> float:
		"""
		Minimum value of a field in result nodes

		:param field: field name

		:return: minimum value

		:raise TypeError: If there isn't any numeric value in given field
		"""
		nodes = [n for n in self.nodes if isinstance(n.get(field), (float, int))]
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
		nodes = [n for n in self.nodes if isinstance(n.get(field), (float, int))]
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

	def get(self) -> List[Node]:
		"""
		Get all nodes

		:return: list of nodes
		"""
		return self.nodes

	def group_by(self, field: str) -> Dict[Any, List[Node]]:
		"""
		Group nodes by field

		:param field: field name

		:return: dict of nodes grouped by field value
		"""
		groups = defaultdict(list)
		for processing_node in self.nodes:
			value = processing_node.get(field)
			groups[value].append(processing_node)
		return dict(groups)

	def relations(self) -> List[Relation]:
		"""
		Get all relations

		:return: list of relations
		"""
		return list(self.edges)

	def first(self) -> Optional[Node]:
		"""
		Get first node

		:return: first node or None
		"""
		return self.nodes[0] if self.nodes else None

	def ids(self) -> List[str]:
		"""
		Get node IDs

		:return: list of node IDs
		"""
		return [n.id for n in self.nodes]

class QueryBuilder:
	"""Builder for creating queries"""

	def __init__(self, graphite_engine: 'GraphiteEngine'):
		self.engine = graphite_engine

	def __getattr__(self, name: str) -> QueryResult:
		"""Allow starting query from node type: engine.query.User"""
		if name in self.engine.node_types:
			nodes = self.engine.get_nodes_of_type(name)
			return QueryResult(self.engine, nodes)
		raise NotFoundError(
			"Node type",
			name
		)

	def all(self) -> QueryResult:
		"""Allow starting query from all nodes"""
		return QueryResult(self.engine, list(self.engine.nodes.values()), list(self.engine.relations))
