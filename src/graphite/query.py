"""
Query engine and object for Graphite
"""
from datetime import date, datetime
from typing import TYPE_CHECKING, List, Callable, Optional, Union

from .instances import Node, Relation
from .types import RelationType
from .exceptions import ConditionError, DateParseError, NotFoundError

if TYPE_CHECKING:
	from .engine import GraphiteEngine

class QueryResult:
	"""Represents a query result that can be chained"""

	def __init__(
		self, graph_engine: 'GraphiteEngine', nodes: List[Node], edges: List[Relation] = None
	):
		self.engine = graph_engine
		self.nodes = nodes
		self.edges = edges or []
		self.current_relation: Optional[RelationType] = None
		self.direction: str = 'outgoing'

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

	def traverse(self, relation_type: str, direction: str = 'outgoing'):
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

	def outgoing(self, relation_type: str):
		"""Traverse outgoing relations"""
		return self.traverse(relation_type, 'outgoing')

	def incoming(self, relation_type: str):
		"""Traverse incoming relations"""
		return self.traverse(relation_type, 'incoming')

	def both(self, relation_type: str):
		"""Traverse both directions"""
		return self.traverse(relation_type, 'both')

	def limit(self, n: int):
		"""Limit number of results"""
		return QueryResult(self.engine, self.nodes[:n], self.edges[:n])

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

	def count(self) -> int:
		"""Count nodes"""
		return len(self.nodes)

	def get(self) -> List[Node]:
		"""Get all nodes"""
		return self.nodes

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
