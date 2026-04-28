"""
Parser for Graphite DSL
"""
import re
import warnings
from datetime import datetime
from typing import Any, List, Optional, Tuple

from .exceptions import (
	DateParseError, FieldError, GraphiteError, NotFoundError, ParseError,
	RelationTypeDefineError,
)
from .types import DataType, Field

class GraphiteParser:
	"""Parser for Graphite DSL"""

	def parse_field_value(self, value: Any, field: Field) -> Any:
		"""
		Parse a raw value for a field (node or relation) and return it.

		**Note:** Value will be validated with field information, use ``parse_value()``
		to ignore validation.

		:param value: Value to parse
		:param field: Field to convert and validate

		:return: Parsed and validated value
		"""
		value = self.parse_value(value)
		return self.validate_field_value(value, field)

	# pylint: disable=broad-exception-caught, too-many-branches
	@staticmethod
	def validate_field_value(value: Any, field: Field) -> Any:
		"""
		Converts given value to field's data type.

		:param value: Parsed value to validate
		:param field: Field to validate

		:return: Converted and validated value

		:raise FieldError: Field value cannot be converted
		"""
		if value is None:
			return None
		try:
			if field.dtype == DataType.STRING:
				value = str(value)
			elif field.dtype == DataType.INT:
				value = int(value)
			elif field.dtype == DataType.DATE:
				if isinstance(value, datetime):
					value = value.date()
				elif isinstance(value, str):
					value = datetime.strptime(value, "%Y-%m-%d").date()
			elif field.dtype == DataType.FLOAT:
				value = float(value)
			elif field.dtype == DataType.BOOL:
				if isinstance(value, str):
					value = value.lower() == "true"
				else:
					value = bool(value)
			elif field.dtype not in DataType:
				raise NotFoundError(
					"Data type",
					str(field.dtype)
				)
		except NotFoundError as e:
			raise e
		except Exception as e:
			raise FieldError(
				field,
				value
			) from e
		return value

	# pylint: disable=too-many-return-statements
	@staticmethod
	def parse_value(value: Any) -> Any:
		"""
		Parses a raw value (usually ``str``) into correct type (by guessing type).

		:param value: Value to parse

		:return: Parsed value

		:raise DateParseError: Date parsing failed
		"""
		if not isinstance(value, str):
			return value
		value = value.strip()
		if value.startswith('"') and value.endswith('"'):
			return value[1:-1]
		if value.replace('-', '').isdigit() and value.count("-") == 2:  # Date-like
			try:
				return datetime.strptime(value, '%Y-%m-%d').date()
			except ValueError as e:
				raise DateParseError(value) from e
		if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
			return int(value)
		if value.replace('.', '').isdigit() and value.count('.') == 1:
			return float(value)
		if value.lower() in ('true', 'false'):
			return value.lower() == 'true'
		return value

	@staticmethod
	def parse_node_definition(definition: str) -> Tuple[str, List[Field], str]:
		"""
		Parse node type definition, for example:\n
		'''\n
		node Person\n
		name: string\n
		age: int\n
		'''\n

		:param definition: Node type definition string in Graphite DSL

		:return: node type name, fields, parent type name
		"""
		lines = definition.strip().split('\n')

		if len(lines) == 0:
			raise ParseError("Empty node definition, expected at least one line.", 1, 0)

		first_line = lines[0].strip()

		if not first_line.startswith('node '):
			raise ParseError(
				"Invalid node definition, expected 'node <node type> ...' pattern",
				1,
				0
			)

		# Parse inheritance
		if ' from ' in first_line:
			parts = first_line.split(' from ')

			if len(parts) != 2:
				raise ParseError(
					"Invalid node definition, expected 'node <node type> from <base type>' pattern",
					1,
					first_line.find(' from ')
				)

			node_name = parts[0].replace('node ', '', 1).strip()
			parent = parts[1].strip()
		else:
			node_name = first_line.replace('node ', '', 1).strip()
			parent = None

		fields = []
		for line_number, field_line in enumerate(lines[1:]):
			field_line = field_line.strip()

			if not field_line:
				warnings.warn(
					f"Line {line_number + 1} in node definition is empty, skipped.",
					SyntaxWarning
				)
				continue

			field_pair = field_line.split(':')

			if len(field_pair) != 2:
				raise ParseError(
					"Invalid field definition for node type, expected '<field name>: <data type>' pattern",
					line_number + 1,
					0
				)

			name = field_pair[0].strip()
			dtype_str = field_pair[1].strip()

			if not name or not dtype_str:
				raise ParseError(
					"Invalid field definition for node type, expected '<field name>: <data type>' pattern",
					line_number + 1,
					0
				)

			try:
				dtype = DataType(dtype_str)
			except ValueError as e:
				raise ParseError(
					f"Invalid field data type: {dtype_str}",
					line_number + 1,
					field_line.find(":") + 1
				) from e

			fields.append(Field(name, dtype))

		return node_name, fields, parent

	# pylint: disable=too-many-locals, too-many-statements
	@staticmethod
	def parse_relation_definition(
		definition: str
	) -> Tuple[str, str, str, List[Field], Optional[str], bool]:
		"""
		Parse relation definition

		:param definition: Relation definition string in Graphite DSL

		:return: relation type name, source type name, target type name, fields, optional reverse
		type name, is bidirectional or not

		:except ParseError: empty or invalid definition
		"""
		lines = definition.strip().split('\n')

		if len(lines) < 2:
			raise ParseError("Empty relation definition, expected at least two line.", 1, 0)

		first_line = lines[0].strip()

		if not first_line.startswith('relation '):
			raise ParseError(
				"Invalid relation definition, expected 'relation <type name> ...' pattern",
				1,
				0
			)

		# Check for 'both' keyword
		is_bidirectional = ' both' in first_line
		if is_bidirectional:
			first_line = first_line.replace(' both', '')

		# Parse reverse
		reverse_name = None
		if ' reverse ' in first_line:
			parts = first_line.split(' reverse ')

			if len(parts) != 2:
				raise ParseError(
					"Invalid relation definition, expected 'relation <type name> reverse <reverse name>' pattern",
					1,
					first_line.find(' reverse ') + 1
				)

			relation_name = parts[0].replace('relation ', '', 1).strip()
			reverse_name = parts[1].strip()
		else:
			relation_name = first_line.replace('relation ', '', 1).strip()

		if is_bidirectional and reverse_name:
			raise RelationTypeDefineError(relation_name)

		# Parse participants
		participants_line = lines[1].strip()
		try:
			if '->' in participants_line:
				parts = participants_line.split('->')
				from_type = parts[0].strip()
				to_type = parts[1].strip()
			elif '-' in participants_line:
				participants_line = participants_line.replace('--', '-')
				parts = participants_line.split('-')
				if len(parts) != 2:
					raise GraphiteError
				from_type = parts[0].strip()
				to_type = parts[-1].strip()
			else:
				raise GraphiteError
		except GraphiteError as e:
			raise ParseError(
				"Invalid relation type format, expected '<node type> -[-,>] <node type>' pattern",
				2,
				0
			) from e

		# Parse fields
		fields = []
		for line_number, field_line in enumerate(lines[2:]):
			field_line = field_line.strip()
			if not field_line:
				warnings.warn(
					f"Line {line_number + 2} in relation definition is empty, skipped.",
					SyntaxWarning
				)
				continue
			name_type = field_line.split(':')

			if len(name_type) != 2:
				raise ParseError(
					"Invalid field definition for relation type, expected '<field name>: <data type>' pattern",
					line_number + 2,
					0
				)

			name = name_type[0].strip()
			dtype_str = name_type[1].strip()

			if not name or not dtype_str:
				raise ParseError(
					"Invalid field definition for relation type, expected '<field name>: <data type>' pattern",
					line_number + 2,
					0
				)

			try:
				dtype = DataType(dtype_str)
			except ValueError as e:
				raise ParseError(
					f"Invalid field data type: {dtype_str}",
					line_number + 2,
					field_line.find(":") + 1
				) from e

			fields.append(Field(name, dtype))

		return relation_name, from_type, to_type, fields, reverse_name, is_bidirectional

	@staticmethod
	def parse_node_instance(line: str) -> Tuple[str, str, List[Any]]:
		"""
		Parse node instance: 'User, user_1, "Joe Doe", 32, "joe4030"'

		:param line: node instance string in Graphite DSL

		:return: node type name, node id, parsed field values
		"""
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
		values = list(map(GraphiteParser.parse_value, parts[2:]))

		return node_type, node_id, values

	@staticmethod
	def parse_relation_instance(
		line: str
	) -> tuple[str, str, str, list[Any], str]:
		"""
		Parse relation instance: 'user_1 -[OWNER, 2000-10-04]-> notebook'

		:param line: relation instance string in Graphite DSL

		:return: source node id, target node id, relation type name, field values, direction
		"""
		# Extract relation type and attributes
		pattern = r'(\w+)\s*(-\[([^\]]+)\]\s*[->-]\s*|\s*[->-]\s*\[([^\]]+)\]\s*->\s*)(\w+)'
		match = re.search(pattern, line)
		if not match:
			raise ParseError(f"Invalid relation format: {line}")

		from_node = match.group(1)
		to_node = match.group(5)

		# Get relation type and attributes
		rel_part = match.group(3) or match.group(4)
		rel_parts = [p.strip() for p in rel_part.split(',')]
		rel_type = rel_parts[0]
		attributes = list(map(GraphiteParser.parse_value, rel_parts[1:]) if len(rel_parts) > 1 else [])

		# Parse direction
		if '->' in line:
			direction = 'forward'
		elif '-[' in line and ']-' in line:
			direction = 'bidirectional'
		else:
			direction = 'forward'

		return from_node, to_node, rel_type, attributes, direction
