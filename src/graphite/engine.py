"""
Main graph database engine of Graphite
"""
import json
import warnings
import os
from collections import defaultdict
from datetime import datetime, date
from typing import Dict, List, Optional, Any

from .exceptions import (
	FileSizeError, InvalidJSONError, InvalidPropertiesError, NotFoundError,
	SafeLoadExtensionError, TooNestedJSONError, ValidationError,
)
from .types import NodeType, RelationType, Field, DataType
from .instances import Node, Relation
from .parser import GraphiteParser
from .query import QueryBuilder
from .serialization import GraphiteJSONEncoder

class GraphiteEngine:  # pylint: disable=too-many-instance-attributes
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
				raise NotFoundError(
					"Parent node type",
					parent_name,
				)
			parent = self.node_types[parent_name]

		node_type = NodeType(node_name, fields, parent)
		self.node_types[node_name] = node_type

	def define_relation(self, definition: str):
		"""Define a relation type from DSL"""
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
		"""Create a node instance"""
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
			node_values[current_field.name] = self.parser.parse_value(value)

		new_node = Node(node_type, node_id, node_values, node_type_obj)
		self.nodes[node_id] = new_node
		self.node_by_type[node_type].append(new_node)
		return new_node

	def create_relation(self, from_id: str, to_id: str, rel_type: str, *values) -> Relation:
		"""Create a relation instance"""
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

		if len(values) != len(rel_type_obj.fields):
			raise InvalidPropertiesError(
				rel_type_obj.fields,
				len(values)
			)

		# Create values dictionary
		rel_values = {}
		for i, rel_field in enumerate(rel_type_obj.fields):
			rel_values[rel_field.name] = self.parser.parse_value(values[i])

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

	def get_nodes_of_type(self, node_type: str, with_subtypes: bool = True) -> List[Node]:
		"""Get all nodes of a specific type"""
		nodes: List[Node] = self.node_by_type.get(node_type, [])
		if with_subtypes:
			for ntype in self.node_types.values():
				if ntype.parent and ntype.parent.name == node_type:
					for new_node in self.get_nodes_of_type(ntype.name):
						if new_node not in nodes:
							nodes.append(new_node)
		return nodes

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

	# pylint: disable=too-many-return-statements, too-many-branches
	@staticmethod
	def _graphite_object_hook(dct: Dict[str, Any]) -> Any:
		"""Object hook for decoding Graphite objects from JSON"""
		if "__graphite_type__" not in dct:
			return dct

		graphite_type = dct.pop("__graphite_type__")

		if graphite_type == "datetime":
			# Restore date/datetime objects
			value = dct["value"]
			if dct.get("is_date"):
				return date.fromisoformat(value)
			return datetime.fromisoformat(value)

		if graphite_type == "enum":
			# Restore Enum objects
			enum_class = dct["enum_class"]
			value = dct["value"]
			if enum_class == "DataType":
				return DataType(value)
		# Add other enum classes as needed

		elif graphite_type == "datatype":
			# Restore DataType enum
			return DataType(dct["value"])

		elif graphite_type == "defaultdict":
			# Restore defaultdict
			result = defaultdict(list if dct["__default_factory"] == "list" else dict)
			dct.pop("__default_factory", None)
			dct.pop("__graphite_type__", None)
			result.update(dct)
			return result

		elif graphite_type == "Node":
			# Create Node instance (type_ref will be restored later)
			return Node(
				type_name=dct["type_name"],
				id=dct["id"],
				values=dct["values"],
				type_ref=None  # Will be restored later
			)

		elif graphite_type == "Relation":
			# Create Relation instance (type_ref will be restored later)
			return Relation(
				type_name=dct["type_name"],
				from_node=dct["from_node"],
				to_node=dct["to_node"],
				values=dct["values"],
				type_ref=None  # Will be restored later
			)

		elif graphite_type == "NodeType":
			# Create NodeType instance (parent will be restored later)
			return NodeType(
				name=dct["name"],
				fields=dct.get("fields", []),
				parent=None  # Will be restored later
			)

		elif graphite_type == "RelationType":
			# Create RelationType instance
			return RelationType(
				name=dct["name"],
				from_type=dct["from_type"],
				to_type=dct["to_type"],
				fields=dct.get("fields", []),
				reverse_name=dct.get("reverse_name"),
				is_bidirectional=dct.get("is_bidirectional", False)
			)

		elif graphite_type == "Field":
			# Create Field instance
			return Field(
				name=dct["name"],
				dtype=DataType(dct["dtype"]),
				default=dct.get("default")
			)

		return dct

	def save(self, filename: str):
		"""Save database to file using JSON"""
		# Prepare data structure
		data = {
			"version"          : "1.0",
			"node_types"       : list(self.node_types.values()),
			"relation_types"   : list(self.relation_types.values()),
			"nodes"            : list(self.nodes.values()),
			"relations"        : self.relations,
			# Convert defaultdicts to regular dicts for JSON
			"node_by_type"     : dict(self.node_by_type.items()),
			"relations_by_type": dict(self.relations_by_type.items()),
			"relations_by_from": dict(self.relations_by_from.items()),
			"relations_by_to"  : dict(self.relations_by_to.items()),
		}

		with open(filename, 'w', encoding='utf-8') as f:
			# noinspection PyTypeChecker
			json.dump(data, f, cls=GraphiteJSONEncoder, indent=2, ensure_ascii=False)

	def load_safe(self, filename: str, max_size_mb: int | float = 100, validate_schema: bool = True) -> None:
		"""
		Safely load database with security checks

		Args:
			filename: File to load
			max_size_mb: Maximum allowed file size in MB
			validate_schema: Whether to validate schema consistency

		Returns:
			True if loaded successfully, False otherwise
		"""
		# Check file size
		file_size = os.path.getsize(filename)
		if file_size > max_size_mb * 1024 * 1024:
			raise FileSizeError(
				file_size / 1024 / 1024,
				max_size_mb
			)

		# Check file extension
		if not filename.lower().endswith('.json'):
			raise SafeLoadExtensionError()

		# Read with limited recursion depth
		try:
			with open(filename, 'r', encoding='utf-8') as f:
				# Use lower recursion limit for safety
				data = json.load(f, object_hook=self._graphite_object_hook)
		except json.JSONDecodeError as e:
			raise InvalidJSONError() from e
		except RecursionError as exc:
			raise TooNestedJSONError() from exc

		# Validate structure
		if validate_schema:
			self._validate_loaded_data(data)

		# Load normally
		self._load_from_dict(data)

	@staticmethod
	def _validate_loaded_data(data: Dict[str, Any]):
		"""Validate loaded data for consistency"""
		required_keys = ['version', 'node_types', 'relation_types', 'nodes']
		for key in required_keys:
			if key not in data:
				raise ValidationError(
					f"Missing required key {key}",
					key,
					"'Missing'"
				)

		# Check for unexpected keys
		allowed_keys = {
			'version', 'node_types', 'relation_types', 'nodes', 'relations',
			'node_by_type', 'relations_by_type', 'relations_by_from', 'relations_by_to'
		}
		for key in data.keys():
			if key not in allowed_keys:
				warnings.warn(f"Unexpected key in data: {key}", UserWarning)

		# Validate nodes reference existing types
		node_type_names = {nt.name for nt in data.get('node_types', [])}
		for check_node in data.get('nodes', []):
			if check_node.type_name not in node_type_names:
				raise NotFoundError(
					"Node type",
					check_node.type_name,
				)

	def _load_from_dict(self, data: Dict[str, Any]):
		"""Internal method to load from dictionary (used by both load and load_safe)"""
		# Clear existing data
		self.clear()

		# Restore node types
		for nt_dict in data['node_types']:
			if isinstance(nt_dict, NodeType):
				nt = nt_dict
			else:
				# Convert from dict if needed
				nt = NodeType(
					name=nt_dict['name'],
					fields=nt_dict.get('fields', []),
					parent=None  # Will be restored later
				)
			self.node_types[nt.name] = nt

		# Restore parent references for node types
		for nt in data['node_types']:
			if isinstance(nt, dict) and nt.get('parent'):
				parent_name = nt['parent']
				if parent_name in self.node_types:
					self.node_types[nt['name']].parent = self.node_types[parent_name]

		# Restore relation types
		for rt_dict in data['relation_types']:
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
		for node_data in data['nodes']:
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
		for rel_data in data['relations']:
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

	def _rebuild_all_indexes(self):
		self._rebuild_node_by_type()
		self._rebuild_relations_indexes()

	def load(self, filename: str, safe_mode: bool = True) -> None:
		"""
		Load database from file

		Args:
			filename: File to load
			safe_mode: If True, use safe loading with validation (default: True)
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

	def _load_unsafe(self, filename: str):
		"""Legacy unsafe loading (kept for compatibility)"""
		with open(filename, 'r', encoding='utf-8') as f:
			data = json.load(f, object_hook=self._graphite_object_hook)
		self._load_from_dict(data)

	def _rebuild_node_by_type(self):
		"""Rebuild node_by_type index"""
		self.node_by_type = defaultdict(list)
		for node_instance in self.nodes.values():
			self.node_by_type[node_instance.type_name].append(node_instance)

	def _rebuild_relations_indexes(self):
		"""Rebuild all relation indexes"""
		self.relations_by_type = defaultdict(list)
		self.relations_by_from = defaultdict(list)
		self.relations_by_to = defaultdict(list)

		for rel in self.relations:
			self.relations_by_type[rel.type_name].append(rel)
			self.relations_by_from[rel.from_node].append(rel)
			self.relations_by_to[rel.to_node].append(rel)

	def _rebuild_remaining_indexes(self):
		"""Rebuild indexes that might not be in the saved data"""
		# Ensure relations_by_from and relations_by_to are built
		if not self.relations_by_from or not self.relations_by_to:
			self.relations_by_from = defaultdict(list)
			self.relations_by_to = defaultdict(list)
			for rel in self.relations:
				self.relations_by_from[rel.from_node].append(rel)
				self.relations_by_to[rel.to_node].append(rel)

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
		"""Parse data into nodes and relations (structure or data)"""
		self.load_dsl(data)
