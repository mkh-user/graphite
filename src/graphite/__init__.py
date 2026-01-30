"""
Graphite: A clean, embedded graph database engine for Python.

This is graphite module (installation: ``pip install graphitedb``).
You can use it with ``import graphite``.
"""
from __future__ import annotations

import pickle
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

# =============== TYPE SYSTEM ===============

class DataType(Enum):
	"""
	Valid data types in graphite. Used in nodes and relations properties.
	"""
	STRING = "string"
	INT = "int"
	DATE = "date"
	FLOAT = "float"
	BOOL = "bool"

@dataclass
class Field:
	"""
	A data field (property) for nodes and relations.
	"""
	name: str
	dtype: DataType
	default: Any = None

@dataclass
class NodeType:
	"""
	A defined node type (with ``node ...`` block in dsl or ``GraphiteEngine.define_node()``).
	Each node type has a name (in snake_case usually), and optional list of fields (properties).
	Supports optional parent node type.
	"""
	name: str
	fields: List[Field] = field(default_factory=list)
	parent: Optional[NodeType] = None

	def get_all_fields(self) -> List[Field]:
		"""Get all fields including inherited ones"""
		fields = self.fields.copy()
		if self.parent:
			fields = self.parent.get_all_fields() + fields
		return fields

	def __hash__(self):
		return hash(self.name)

@dataclass
class RelationType:
	"""
	A defined relation type (with ``relation ...`` block in dsl or
	``GraphiteEngine.define_relation()``). Each relation type has a name (in UPPER_SNAKE_CASE
	usually), and optional list of fields (properties). A relation type can be from one node
	type to another.
	"""
	name: str
	from_type: str
	to_type: str
	fields: List[Field] = field(default_factory=list)
	reverse_name: Optional[str] = None
	is_bidirectional: bool = False

	def __hash__(self):
		return hash(self.name)

# =============== INSTANCES ===============

@dataclass
class Node:
	"""
	A node in database. Has a base type, id, and properties from base type (and it's parent
	type recursively).
	"""
	type_name: str
	id: str
	values: Dict[str, Any]
	_type_ref: Optional[NodeType] = None

	def get(self, field_name: str) -> Any:
		"""Get a field from this node."""
		return self.values.get(field_name)

	def __getitem__(self, key):
		return self.get(key)

	def __repr__(self):
		return f"Node({self.type_name}:{self.id})"

@dataclass
class Relation:
	"""
	A relation between two nodes in database. Has a base type, source and target node IDs,
	and properties from base type.
	"""
	type_name: str
	from_node: str  # node id
	to_node: str  # node id
	values: Dict[str, Any]
	_type_ref: Optional[RelationType] = None

	def get(self, field_name: str) -> Any:
		"""Get a field from this relation."""
		return self.values.get(field_name)

	def __repr__(self):
		return f"Relation({self.type_name}:{self.from_node}->{self.to_node})"

# =============== PARSER ===============

class GraphiteParser:
	"""Parser for Graphite DSL"""

	@staticmethod
	def parse_node_definition(line: str) -> Tuple[str, List[Field], str]:
		"""Parse node type definition: 'node Person\nname: string\nage: int'"""
		lines = line.strip().split('\n')
		first_line = lines[0].strip()

		# Parse inheritance
		if ' from ' in first_line:
			parts = first_line.split(' from ')
			node_name = parts[0].replace('node', '').strip()
			parent = parts[1].strip()
			fields_start = 1
		else:
			node_name = first_line.replace('node', '').strip()
			parent = None
			fields_start = 1

		fields = []
		for field_line in lines[fields_start:]:
			field_line = field_line.strip()
			if not field_line:
				continue
			name_type = field_line.split(':')
			if len(name_type) == 2:
				name = name_type[0].strip()
				dtype_str = name_type[1].strip()
				dtype = DataType(dtype_str)
				fields.append(Field(name, dtype))

		return node_name, fields, parent

	# pylint: disable=too-many-locals
	@staticmethod
	def parse_relation_definition(line: str) -> Tuple[str, str, str, List[Field], Optional[str], bool]:
		"""Parse relation definition"""
		lines = line.strip().split('\n')
		first_line = lines[0].strip()

		# Check for 'both' keyword
		is_bidirectional = ' both' in first_line
		if is_bidirectional:
			first_line = first_line.replace(' both', '')

		# Parse reverse
		reverse_name = None
		if ' reverse ' in first_line:
			parts = first_line.split(' reverse ')
			relation_name = parts[0].replace('relation', '').strip()
			reverse_name = parts[1].strip()
			first_line = parts[0]
		else:
			relation_name = first_line.replace('relation', '').strip()

		# Parse participants
		participants_line = lines[1].strip()
		if '->' in participants_line:
			from_to = participants_line.split('->')
			from_type = from_to[0].strip()
			to_type = from_to[1].strip()
		elif '-' in participants_line:
			parts = participants_line.split('-')
			from_type = parts[0].strip()
			to_type = parts[2].strip() if len(parts) > 2 else parts[1].strip()
		else:
			raise ValueError(f"Invalid relation format: {participants_line}")

		# Parse fields
		fields = []
		for field_line in lines[2:]:
			field_line = field_line.strip()
			if not field_line:
				continue
			name_type = field_line.split(':')
			if len(name_type) == 2:
				name = name_type[0].strip()
				dtype_str = name_type[1].strip()
				dtype = DataType(dtype_str)
				fields.append(Field(name, dtype))

		return relation_name, from_type, to_type, fields, reverse_name, is_bidirectional

	@staticmethod
	def parse_node_instance(line: str) -> Tuple[str, str, List[Any]]:
		"""Parse node instance: 'User, user_1, "Joe Doe", 32, "joe4030"'"""
		# Handle quoted strings
		parts = []
		current = ''
		in_quotes = False
		for char in line:
			if char == '"':
				in_quotes = not in_quotes
				current += char
			elif char == ',' and not in_quotes:
				parts.append(current.strip())
				current = ''
			else:
				current += char
		if current:
			parts.append(current.strip())

		node_type = parts[0].strip()
		node_id = parts[1].strip()
		values = []

		for val in parts[2:]:
			val = val.strip()
			if val.startswith('"') and val.endswith('"'):
				values.append(val[1:-1])
			elif val.replace('-', '').isdigit() and '-' in val:  # Date-like
				values.append(val)
			elif val.isdigit() or (val.startswith('-') and val[1:].isdigit()):
				values.append(int(val))
			elif val.replace('.', '').isdigit() and val.count('.') == 1:
				values.append(float(val))
			elif val.lower() in ('true', 'false'):
				values.append(val.lower() == 'true')
			else:
				values.append(val)

		return node_type, node_id, values

	@staticmethod
	def parse_relation_instance(line: str) -> tuple[str | Any, str | Any, Any, list[Any], str]:
		"""Parse relation instance: 'user_1 -[OWNER, 2000-10-04]-> notebook'"""
		# Extract relation type and attributes
		pattern = r'(\w+)\s*(-\[([^\]]+)\]\s*[->-]\s*|\s*[->-]\s*\[([^\]]+)\]\s*->\s*)(\w+)'
		match = re.search(pattern, line)
		if not match:
			raise ValueError(f"Invalid relation format: {line}")

		from_node = match.group(1)
		to_node = match.group(5)

		# Get relation type and attributes
		rel_part = match.group(3) or match.group(4)
		rel_parts = [p.strip() for p in rel_part.split(',')]
		rel_type = rel_parts[0]
		attributes = rel_parts[1:] if len(rel_parts) > 1 else []

		# Parse direction
		if '->' in line:
			direction = 'forward'
		elif '-[' in line and ']-' in line:
			direction = 'bidirectional'
		else:
			direction = 'forward'

		return from_node, to_node, rel_type, attributes, direction

# =============== QUERY ENGINE ===============

class QueryResult:
	"""Represents a query result that can be chained"""

	def __init__(self, graph_engine: GraphiteEngine, nodes: List[Node], edges: List[Relation] = None):
		self.engine = graph_engine
		self.nodes = nodes
		self.edges = edges or []
		self.current_relation: Optional[RelationType] = None
		self.direction: str = 'outgoing'

	def where(self, condition: Union[str, Callable]) -> QueryResult:
		"""Filter nodes based on condition"""
		filtered_nodes = []

		if callable(condition):
			# Lambda function
			for processing_node in self.nodes:
				try:
					if condition(processing_node):
						filtered_nodes.append(processing_node)
				except Exception as e: # pylint: disable=broad-exception-caught
					print(f"Graphite Warn: 'where' condition failed for node {processing_node}: {e}")
		else:
			# String condition like "age > 18"
			for processing_node in self.nodes:
				if self._evaluate_condition(processing_node, condition):
					filtered_nodes.append(processing_node)

		return QueryResult(self.engine, filtered_nodes, self.edges)

	# pylint: disable=too-many-branches
	def _evaluate_condition(self, target_node: Node, condition: str) -> bool:
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
				if right.startswith('"') and right.endswith('"'):
					right_value = right[1:-1]
				elif right.isdigit():
					right_value = int(right)
				elif right.replace('.', '').isdigit() and right.count('.') == 1:
					right_value = float(right)
				else:
					right_value = right

				# Apply operation
				result = None
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
				if result is None:
					raise ValueError(f"Invalid condition string: {condition}")
				return result

		return False

	def traverse(self, relation_type: str, direction: str = 'outgoing') -> QueryResult:
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
				target_id = edge.to_node if direction == 'outgoing' else edge.from_node
				target_node = self.engine.get_node(target_id)
				if target_node:
					result_nodes.append(target_node)

		# Remove duplicates
		result_nodes = list(dict((n.id, n) for n in result_nodes).values())
		return QueryResult(self.engine, result_nodes, result_edges)

	def outgoing(self, relation_type: str) -> QueryResult:
		"""Traverse outgoing relations"""
		return self.traverse(relation_type, 'outgoing')

	def incoming(self, relation_type: str) -> QueryResult:
		"""Traverse incoming relations"""
		return self.traverse(relation_type, 'incoming')

	def both(self, relation_type: str) -> QueryResult:
		"""Traverse both directions"""
		return self.traverse(relation_type, 'both')

	def limit(self, n: int) -> QueryResult:
		"""Limit number of results"""
		return QueryResult(self.engine, self.nodes[:n], self.edges[:n])

	def distinct(self) -> QueryResult:
		"""Get distinct nodes"""
		seen = set()
		distinct_nodes = []
		for processing_node in self.nodes:
			if processing_node.id not in seen:
				seen.add(processing_node.id)
				distinct_nodes.append(processing_node)
		return QueryResult(self.engine, distinct_nodes, self.edges)

	def order_by(self, by_field: str, descending: bool = False) -> QueryResult:
		"""Order nodes by field"""

		def get_key(from_node):
			val = from_node.get(by_field)
			return (val is None, val)

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

class QueryBuilder: # pylint: disable=too-few-public-methods
	"""Builder for creating queries"""

	def __init__(self, graphite_engine: GraphiteEngine):
		self.engine = graphite_engine

	def __getattr__(self, name: str) -> QueryResult:
		"""Allow starting query from node type: engine.User"""
		if name in self.engine.node_types:
			nodes = self.engine.get_nodes_of_type(name)
			return QueryResult(self.engine, nodes)
		raise AttributeError(f"No node type '{name}' found")

# =============== MAIN ENGINE ===============

class GraphiteEngine: # pylint: disable=too-many-instance-attributes
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

	def define_node(self, definition: str):
		"""Define a node type from DSL"""
		node_name, fields, parent_name = self.parser.parse_node_definition(definition)

		parent = None
		if parent_name:
			if parent_name not in self.node_types:
				raise ValueError(f"Parent node type '{parent_name}' not found")
			parent = self.node_types[parent_name]

		node_type = NodeType(node_name, fields, parent)
		self.node_types[node_name] = node_type

	def define_relation(self, definition: str):
		"""Define a relation type from DSL"""
		(rel_name, from_type, to_type, fields,
		reverse_name, is_bidirectional) = self.parser.parse_relation_definition(definition)

		# Validate node types exist
		if from_type not in self.node_types:
			raise ValueError(f"Node type '{from_type}' not found")
		if to_type not in self.node_types:
			raise ValueError(f"Node type '{to_type}' not found")

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
		"""Create a node instance"""
		if node_type not in self.node_types:
			raise ValueError(f"Node type '{node_type}' not defined")

		node_type_obj = self.node_types[node_type]
		all_fields = node_type_obj.get_all_fields()

		if len(values) != len(all_fields):
			raise ValueError(f"Expected {len(all_fields)} values, got {len(values)}")

		# Create values dictionary
		node_values = {}
		for current_field, value in zip(all_fields, values):
			# Convert string dates to date objects
			if current_field.dtype == DataType.DATE and isinstance(value, str):
				try:
					value = datetime.strptime(value, "%Y-%m-%d").date()
				except Exception as e:
					raise ValueError(f"'{e}' while parsing date string: {value}") from e
			node_values[current_field.name] = value

		new_node = Node(node_type, node_id, node_values, node_type_obj)
		self.nodes[node_id] = new_node
		self.node_by_type[node_type].append(new_node)
		return new_node

	def create_relation(self, from_id: str, to_id: str, rel_type: str, *values) -> Relation:
		"""Create a relation instance"""
		if rel_type not in self.relation_types:
			raise ValueError(f"Relation type '{rel_type}' not defined")

		rel_type_obj = self.relation_types[rel_type]

		# Check if nodes exist
		if from_id not in self.nodes:
			raise ValueError(f"Node '{from_id}' not found")
		if to_id not in self.nodes:
			raise ValueError(f"Node '{to_id}' not found")

		# Create values dictionary
		rel_values = {}
		for i, rel_field in enumerate(rel_type_obj.fields):
			if i < len(values):
				value = values[i]
				if rel_field.dtype == DataType.DATE and isinstance(value, str):
					try:
						value = datetime.strptime(value, "%Y-%m-%d").date()
					except Exception as e:
						raise ValueError(f"'{e}' while parsing date string: {value}") from e
				rel_values[rel_field.name] = value

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

	# =============== QUERY METHODS ===============

	def get_node(self, node_id: str) -> Optional[Node]:
		"""Get node by ID"""
		return self.nodes.get(node_id)

	def get_nodes_of_type(self, node_type: str) -> List[Node]:
		"""Get all nodes of a specific type"""
		return self.node_by_type.get(node_type, [])

	def get_relations_from(self, node_id: str, rel_type: str = None) -> List[Relation]:
		"""Get relations from a node"""
		all_rels = self.relations_by_from.get(node_id, [])
		if rel_type:
			return [r for r in all_rels if r.type_name == rel_type]
		return all_rels

	def get_relations_to(self, node_id: str, rel_type: str = None) -> List[Relation]:
		"""Get relations to a node"""
		all_rels = self.relations_by_to.get(node_id, [])
		if rel_type:
			return [r for r in all_rels if r.type_name == rel_type]
		return all_rels

	# =============== BULK LOADING ===============

	def load_dsl(self, dsl: str):
		"""Load Graphite DSL"""
		lines = dsl.strip().split('\n')
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
					rel_def.append(lines[i])
					i += 1
				self.define_relation('\n'.join(rel_def))

			elif '[' not in line:
				# Node instance
				node_type, node_id, values = self.parser.parse_node_instance(line)
				self.create_node(node_type, node_id, *values)
				i += 1

			elif '-[' in line and (']->' in line or ']-' in line):
				# Relation instance
				from_id, to_id, rel_type, values, _ = self.parser.parse_relation_instance(line)
				self.create_relation(from_id, to_id, rel_type, *values)
				i += 1
			else:
				i += 1

	# =============== PERSISTENCE ===============

	def save(self, filename: str):
		"""Save database to file"""
		with open(filename, 'wb') as f:
			data = {
				'node_types'       : self.node_types,
				'relation_types'   : self.relation_types,
				'nodes'            : self.nodes,
				'relations'        : self.relations,
				'node_by_type'     : self.node_by_type,
				'relations_by_type': self.relations_by_type,
				'relations_by_from': self.relations_by_from,
				'relations_by_to'  : self.relations_by_to,
			}
			# noinspection PyTypeChecker
			pickle.dump(data, f)

	def load(self, filename: str):
		"""Load database from file"""
		with open(filename, 'rb') as f:
			data = pickle.load(f)
			self.node_types = data['node_types']
			self.relation_types = data['relation_types']
			self.nodes = data['nodes']
			self.relations = data['relations']
			self.node_by_type = data['node_by_type']
			self.relations_by_type = data['relations_by_type']
			self.relations_by_from = data['relations_by_from']
			self.relations_by_to = data['relations_by_to']

	# =============== UTILITY METHODS ===============

	def clear(self):
		"""Clear all data"""
		self.node_types.clear()
		self.relation_types.clear()
		self.nodes.clear()
		self.relations.clear()
		self.node_by_type.clear()
		self.relations_by_type.clear()
		self.relations_by_from.clear()
		self.relations_by_to.clear()

	def stats(self) -> Dict[str, Any]:
		"""Get database statistics"""
		return {
			'node_types'    : len(self.node_types),
			'relation_types': len(self.relation_types),
			'nodes'         : len(self.nodes),
			'relations'     : len(self.relations),
		}

	# =============== SYNTAX SUGAR ===============

	def parse(self, data: str):
		"""Parse data into nodes and relations (strcuture or data)"""
		self.load_dsl(data)

# =============== SYNTAX SUGAR ===============

def node(node_type: str, **fields) -> str:
	"""Helper function to create node definitions"""
	lines = [f"node {node_type}"]
	for field_name, field_type in fields.items():
		lines.append(f"{field_name}: {field_type}")
	return "\n".join(lines)

def relation(name: str, from_type: str, to_type: str, **kwargs) -> str:
	"""Helper function to create relation definitions"""
	lines = [f"relation {name}"]
	if kwargs.get('both'):
		lines[0] += " both"
	if kwargs.get('reverse'):
		lines[0] += f" reverse {kwargs['reverse']}"

	direction = "->" if not kwargs.get('both') else "-"
	lines.append(f"{from_type} {direction} {to_type}")

	for field_name, field_type in kwargs.get('fields', {}).items():
		lines.append(f"{field_name}: {field_type}")

	return "\n".join(lines)

# ================ PUBLIC API ================

def engine() -> GraphiteEngine:
	"""Create graphite engine instance"""
	return GraphiteEngine()
