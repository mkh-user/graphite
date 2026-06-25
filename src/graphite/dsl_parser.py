"""
Parser for Graphite DSL
"""
import re
import warnings
from datetime import date, datetime
from typing import Any, TYPE_CHECKING

from .exceptions import (
	FieldError, GraphiteError, ParseError,
	RelationTypeDefineError,
)
from .types import DataType, DataTypePython, Field

if TYPE_CHECKING:
	from .engine import GraphiteEngine

def parse_field_value(value: Any, field: Field) -> Any:
	"""
	Parse a raw value for a field (node or relation) and return it.

	**Note:** Value will be validated with field information, use ``parse_value()``
	to ignore validation.

	:param value: Value to parse
	:param field: Field to convert and validate

	:return: Parsed and validated value
	"""
	if isinstance(value, str) and field.dtype == DataType.STRING:
		return value
	value = parse_value(value)
	return validate_field_value(value, field)

def validate_field_value(value: Any, field: Field) -> None | str | int | float | bool | date:
	"""
	Converts given value to field's data type.

	:param value: Parsed value to validate
	:param field: Field to validate

	:return: Converted and validated value

	:raise FieldError: Field value cannot be converted
	"""
	# pylint: disable=unidiomatic-typecheck
	# Reason: Python type of each data type is predefined, so using an type instead of instance
	# is an enhancement.
	if value is None or type(value) == DataTypePython[field.dtype.name].value:
		return value
	try:
		if field.dtype == DataType.BOOL and isinstance(value, str):
			return value.lower() == 'true'
		if field.dtype == DataType.DATE:
			if isinstance(value, datetime):
				return value.date()
			return datetime.strptime(value, "%Y-%m-%d").date()
		# pylint: disable=unnecessary-dunder-call
		# Reason: __call__ is necessary for type checking pass.
		return DataTypePython[field.dtype.name].value.__call__(value)
	except Exception as e:
		raise FieldError(
			field,
			value
		) from e

def parse_value(value: Any) -> Any:
	"""
	Parses a raw value (usually ``str``) into correct type (by guessing type).

	:param value: Value to parse

	:return: Parsed value
	"""
	if isinstance(value, str):
		value = value.strip()
		if ((value.startswith('"') and value.endswith('"'))
				or (value.startswith("'") and value.endswith("'"))):
			return value[1:-1]
		if value.replace('-', '').isdigit() and value.count("-") == 2:  # Date-like
			try:
				return datetime.strptime(value, "%Y-%m-%d").date()
			except ValueError:
				pass
		if value.isdigit() or (value.startswith('-') and value[1:].isdigit()):
			return int(value)
		if value.replace('.', '').isdigit() and value.count('.') == 1:
			return float(value)
		if value.lower() in ('true', 'false'):
			return value.lower() == 'true'
	return value

def parse_node_definition(definition: str) -> tuple[str, list[tuple[str, str]], str | None]:
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
	first_line = lines[0].strip()

	if not first_line.startswith('node '):
		raise ParseError(
			"Invalid node definition, expected 'node <node type> ...' pattern"
		)

	# Parse inheritance
	if ' from ' in first_line:
		parts = first_line.split(' from ')

		if len(parts) != 2:
			raise ParseError(
				"Invalid node definition, expected 'node <node type> from <base type>' pattern",
				None,
				first_line.find(' from ')
			)

		node_name = parts[0].replace('node ', '', 1).strip()
		parent = parts[1].strip()
	else:
		node_name = first_line.replace('node ', '', 1).strip()
		parent = None

	fields = _fetch_fields(lines[1:])

	return node_name, fields, parent

def parse_relation_definition(
	definition: str
) -> tuple[str, str, str, list[tuple[str, str]], str | None, bool]:
	"""
	Parse relation definition

	:param definition: Relation definition string in Graphite DSL

	:return: relation type name, source type name, target type name, fields, optional reverse
	type name, is bidirectional or not

	:except ParseError: empty or invalid definition
	"""
	lines = definition.strip().split('\n')

	if len(lines) < 2:
		raise ParseError("Invalid relation definition, expected at least two lines.")

	first_line = lines[0].strip()

	if not first_line.startswith('relation '):
		raise ParseError(
			"Invalid relation definition, expected 'relation <type name> ...' pattern"
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
				None,
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
		elif '-' in participants_line:
			participants_line = participants_line.replace('--', '-')
			parts = participants_line.split('-')
		else:
			raise GraphiteError
		if len(parts) != 2:
			raise GraphiteError
		from_type = parts[0].strip()
		to_type = parts[1].strip()
	except GraphiteError as e:
		raise ParseError(
			"Invalid relation type format, expected '<node type> -[-,>] <node type>' pattern"
		) from e

	fields = _fetch_fields(lines[2:])

	return relation_name, from_type, to_type, fields, reverse_name, is_bidirectional

def parse_node_instance(line: str) -> tuple[str, str, list[Any]]:
	"""
	Parse node instance: 'User, user_1, "Joe Doe", 32, "joe4030"'

	:param line: node instance string in Graphite DSL

	:return: node type name, node id, parsed field values
	"""
	parts = parse_value_list(line, "node instance")

	node_type = parts[0].strip()
	node_id = parts[1].strip()
	values = list(map(parse_value, parts[2:]))

	return node_type, node_id, values

def parse_relation_instance(line: str) -> tuple[str, str, str, list[Any]]:
	"""
	Parse relation instance: 'user_1 -[OWNER, 2000-10-04]-> notebook'

	:param line: relation instance string in Graphite DSL

	:return: source node id, target node id, relation type name, field values
	"""
	# Extract relation type and attributes
	pattern = r'^(\w+)\s*(-\[([^\]]+)\]\s*[->-]\s*|\s*[->-]\s*\[([^\]]+)\]\s*->\s*)(\w+)$'
	match = re.search(pattern, line)
	if not match:
		raise ParseError(f"Invalid relation format: {line}")

	from_node = match.group(1)
	to_node = match.group(5)

	# Get relation type and attributes
	rel_part = match.group(3) or match.group(4)
	rel_parts = parse_value_list(rel_part, "relation instance")
	rel_type = rel_parts[0]
	attributes = list(map(parse_value, rel_parts[1:]) if len(rel_parts) > 1 else [])

	return from_node, to_node, rel_type, attributes

# pylint: disable=too-many-locals
# Reason: As main responsible of DSL parsing complexity of this function is reasonable and
# relavily low.
def parse(engine: 'GraphiteEngine', data: str) -> None:
	"""
	Parse and load data from Graphite DSL to engine

	:param engine: engine instance
	:param data: data as Graphite DSL string

	:return: None

	:except ParseError: if parsing fails
	:except NotFoundError: using any undefined object (node type, relation type, node, relation)
	:except ValueError: if a used data type not found
	"""
	lines = data.strip().split('\n')

	i = 0
	try:
		while i < len(lines):
			line = lines[i].strip()
			if not line or line.startswith('#'):
				i += 1
				continue

			if line.startswith('node ') or line.startswith('relation '):
				# Collect multiline node definition
				type_def = [line]
				i += 1
				while (
						i < len(lines)
						and lines[i].strip()
						and not lines[i].strip().startswith(('node ', 'relation '))
				):
					if lines[i].strip().startswith('#'):
						i += 1
						continue
					type_def.append(lines[i])
					i += 1
				if line.startswith('node '):
					type_name, fields, parent_name = parse_node_definition('\n'.join(type_def))
					engine.define_node(
						type_name,
						*fields,
						parent=parent_name
					)
				else:
					(type_name, source_type, target_type, fields, reverse_name,
					is_bidirectional) = parse_relation_definition('\n'.join(type_def))
					engine.define_relation(
						type_name,
						source_type,
						target_type,
						*fields,
						reverse_name=reverse_name,
						is_bidirectional=is_bidirectional
					)

			elif '-[' in line and (']->' in line or ']-' in line):
				# Relation instance
				i += 1
				from_id, to_id, rel_type, values = parse_relation_instance(line)
				engine.create_relation(from_id, to_id, rel_type, *values, parse_fields=True)

			else:
				# Node instance
				i += 1
				node_type, node_id, values = parse_node_instance(line)
				engine.create_node(node_type, node_id, *values, parse_fields=True)
	except ParseError as e:
		e.line = i
		if e.column is None:
			e.column = 0
		raise e

def parse_value_list(line: str, definition: str) -> list[str]:
	"""Parse a sequence of comma-separated values, robust to both double and single quotes"""
	result = []
	current = ''
	quote_char = None
	for char in line:
		if char in ('"', "'"):
			if quote_char is None:
				quote_char = char
			elif quote_char == char:
				quote_char = None
			current += char
		elif char == ',' and quote_char is None:
			result.append(current.strip())
			current = ''
		else:
			current += char
	if not current:
		raise ParseError(f"Additional comma in {definition} values")
	result.append(current.strip())
	return result

def _fetch_fields(lines: list[str]) -> list[tuple[str, str]]:
	fields = []
	for line_number, field_line in enumerate(lines):
		field_line = field_line.strip()
		if not field_line:
			warnings.warn(
				f"Line {line_number + 2} in relation definition is empty, skipped.",
				SyntaxWarning,
				stacklevel=3
			)
			continue
		name_type = field_line.split(':')

		if len(name_type) != 2:
			raise ParseError(
				"Invalid field definition, expected '<field name>: <data type>' pattern"
			)

		name = name_type[0].strip()
		dtype = name_type[1].strip()

		if not name or not dtype:
			raise ParseError(
				"Invalid field definition, expected '<field name>: <data type>' pattern"
			)

		fields.append((name, dtype))
	return fields
