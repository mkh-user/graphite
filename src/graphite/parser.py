"""
Parser for Graphite DSL
"""
import re
from typing import Any, List, Optional, Tuple

from .exceptions import SchemaError
from .types import DataType, Field

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
			raise SchemaError(f"Invalid relation type format: {participants_line}")

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
			raise SchemaError(f"Invalid relation format: {line}")

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
