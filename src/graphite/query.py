"""
Query engine and object for Graphite
"""
from collections import defaultdict
from datetime import date, datetime
from functools import reduce
from typing import Any, Dict, TYPE_CHECKING, List, Callable, Optional, Union

from .instances import Node, Relation
from .types import RelationType
from .exceptions import ConditionError, DateParseError, NotFoundError

if TYPE_CHECKING:
	from .engine import GraphiteEngine

class QueryResult: # pylint: disable=too-many-public-methods
	"""Represents a query result that can be chained"""

	def __init__(
		self, graph_engine: 'GraphiteEngine', nodes: List[Node], edges: List[Relation] = None
	):
		self.engine = graph_engine
		self.nodes = nodes
		self.edges = edges or []
		self.current_relation: Optional[RelationType] = None
		self.direction: str = 'outgoing'

	def set(self, **values: Any):
		"""
		Change result nodes' values

		**Note:** This query mutates nodes in-place and changes will be applied to engine directly.
		**Note:** This query raises ``NotFoundError`` for nodes without compatible fields, use
		``.with_fields()`` to ensure all fields are valid.
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

	def remove(self):
		"""Remove current result nodes"""
		for processing_node in self.nodes:
			self.engine.remove_node(processing_node)
		for relation in self.edges.copy():
			if relation not in self.engine.relations:
				self.edges.remove(relation)
		return QueryResult(self.engine, [], self.edges)

	def remove_relations(self):
		"""Remove current result relations"""
		for relation in self.edges:
			if relation in self.engine.relations:
				self.engine.remove_relation(relation)
		return QueryResult(self.engine, self.nodes, [])

	def where(self, condition: Union[str, Callable]):
		"""Filter nodes based on condition"""
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

	def with_type(self, node_type: str):
		"""Filter nodes based on type"""
		return QueryResult(
			self.engine,
			list(filter(lambda node: node.type_name == node_type, self.nodes)),
			self.edges
		)

	def with_fields(self, *fields: str):
		"""Filter nodes with given fields"""
		return QueryResult(
			self.engine,
			list(filter(lambda node: all(field in node.values for field in fields), self.nodes)),
			self.edges
		)

	# pylint: disable=too-many-branches
	@staticmethod
	def _evaluate_condition(target_node: Node, condition: str) -> bool:
		"""Evaluate a condition string on a node"""
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
					raise e
				if result is None:
					raise ConditionError(condition)
				return result

		raise ConditionError(condition)

	def traverse(self, relation_type: Optional[str] = None, direction: str = 'outgoing'):
		"""Traverse relations from current nodes"""
		result_nodes = []
		result_edges = []

		for processing_node in self.nodes:
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

	def outgoing(self, relation_type: Optional[str] = None):
		"""Traverse outgoing relations"""
		return self.traverse(relation_type, 'outgoing')

	def incoming(self, relation_type: Optional[str] = None):
		"""Traverse incoming relations"""
		return self.traverse(relation_type, 'incoming')

	def both(self, relation_type: Optional[str] = None):
		"""Traverse both directions"""
		return self.traverse(relation_type, 'both')

	def limit(self, n: int):
		"""Limit number of results"""
		return QueryResult(self.engine, self.nodes[:n], self.edges)

	def paginate(self, page: int, per_page: int):
		"""Limit number of results to specified page"""
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

	def union(self, query):
		"""
		Merge query results

		**Note:** This query will produce duplicates if the same node exists in both results, use
		``.distinct()`` to remove duplicates.
		"""
		if not isinstance(query, QueryResult):
			raise TypeError('Query must be an instance of QueryResult')
		return QueryResult(self.engine, self.nodes + query.nodes, self.edges + query.edges)

	def exclude(self, query):
		"""Removes result of given query from current nodes and relations"""
		if not isinstance(query, QueryResult):
			raise TypeError('Query must be an instance of QueryResult')
		exclude_ids = {n.id for n in query.nodes}
		new_nodes = [n for n in self.nodes if n.id not in exclude_ids]
		new_edges = [e for e in self.edges if e not in query.edges]
		return QueryResult(self.engine, new_nodes, new_edges)

	def intersect(self, query):
		"""Just keeps shared nodes and relations between current and given queries"""
		if not isinstance(query, QueryResult):
			raise TypeError('Query must be an instance of QueryResult')
		intersect_ids = {n.id for n in query.nodes}
		new_nodes = [n for n in self.nodes if n.id in intersect_ids]
		intersect_edges = query.edges
		new_edges = [e for e in self.edges if e in intersect_edges]
		return QueryResult(self.engine, new_nodes, new_edges)

	def distinct(self):
		"""Get distinct nodes"""
		seen = set()
		distinct_nodes = []
		for processing_node in self.nodes:
			if processing_node.id not in seen:
				seen.add(processing_node.id)
				distinct_nodes.append(processing_node)
		return QueryResult(self.engine, distinct_nodes, self.edges)

	def order_by(self, by_field: str, descending: bool = False):
		"""Order nodes by field"""

		def get_key(from_node):
			val = from_node.get(by_field)
			return val is None, val

		sorted_nodes = sorted(self.nodes, key=get_key, reverse=descending)
		return QueryResult(self.engine, sorted_nodes, self.edges)

	def sum(self, field: str) -> float:
		"""
		Sum of a field values in nodes

		**Note:** This query skips non-numeric values.
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
		"""
		count = len([n for n in self.nodes if isinstance(n.get(field), (float, int))])
		if count == 0:
			return 0.0
		return self.sum(field) / count

	def min(self, field: str) -> float:
		"""Node with minimum value of a field in result"""
		nodes = [n for n in self.nodes if isinstance(n.get(field), (float, int))]
		if not nodes:
			return 0.0
		return reduce(
			lambda x, y: x if x.get(field) < y.get(field) else y,
			nodes
		).get(field)

	def max(self, field: str) -> float:
		"""Node with maximum value of a field in result"""
		nodes = [n for n in self.nodes if isinstance(n.get(field), (float, int))]
		if not nodes:
			return 0.0
		return reduce(
			lambda x, y: x if x.get(field) > y.get(field) else y,
			nodes
		).get(field)

	def count(self) -> int:
		"""Count nodes"""
		return len(self.nodes)

	def get(self) -> List[Node]:
		"""Get all nodes"""
		return self.nodes

	def group_by(self, field: str) -> Dict[Any, List[Node]]:
		"""Group nodes by field"""
		groups = defaultdict(list)
		for processing_node in self.nodes:
			value = processing_node.get(field)
			groups[value].append(processing_node)
		return dict(groups)

	def relations(self) -> List[Relation]:
		"""Get all relations"""
		return list(self.edges)

	def first(self) -> Optional[Node]:
		"""Get first node"""
		return self.nodes[0] if self.nodes else None

	def ids(self) -> List[str]:
		"""Get node IDs"""
		return [n.id for n in self.nodes]

class QueryBuilder:  # pylint: disable=too-few-public-methods
	"""Builder for creating queries"""

	def __init__(self, graphite_engine: 'GraphiteEngine'):
		self.engine = graphite_engine

	def __getattr__(self, name: str) -> QueryResult:
		"""Allow starting query from node type: engine.User"""
		if name in self.engine.node_types:
			nodes = self.engine.get_nodes_of_type(name)
			return QueryResult(self.engine, nodes)
		raise NotFoundError(
			"Node type",
			name
		)

	def all(self) -> QueryResult:
		"""Allow starting query from all nodes"""
		return QueryResult(self.engine, list(self.engine.nodes.values()))
