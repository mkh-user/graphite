"""Possible exceptions in Graphite"""
from typing import Any

from .types import Field, RelationType

class GraphiteError(Exception):
	"""Base exception for all Graphite errors"""

class ParseError(GraphiteError):
	"""Schema-related errors

	Args:
	    message: error message
	    line: line number
	    column: column number
	"""

	def __init__(self, message: str, line: int | None = None, column: int | None = None):
		self.line = line
		self.column = column
		super().__init__(message)

class RelationTypeDefineError(GraphiteError):
	"""Relation type definition error

	Args:
	    relation_type: relation type
	"""

	def __init__(self, relation_type: str):
		super().__init__(
			f"{relation_type} can't be bidirectional and reverse named relation at the same time."
		)

class InvalidRelationError(GraphiteError):
	"""Try to create relation between nodes from invalid types

	Args:
	    relation_type: relation type
	    source_id: source node id
	    target_id: target node id
	"""

	def __init__(self, relation_type: RelationType, source_id: str, target_id: str):
		super().__init__(
			f"{relation_type.name} relation between {source_id} and {target_id} is invalid. " +
			f"(Valid pattern is {relation_type.from_type} -> {relation_type.to_type})"
		)

class ValidationError(GraphiteError):
	"""Data validation errors

	Args:
	    message: error message
	    field: field name
	    value: given value
	"""

	def __init__(self, message: str, field: str, value: Any = None):
		self.field = field
		self.value = value
		super().__init__(message)

class QueryError(GraphiteError):
	"""Query parsing or execution errors"""

class NotFoundError(GraphiteError):
	"""Resource not found errors

	Args:
	    resource_type: type of resource
	    resource_id: ID used to find resource
	"""

	def __init__(self, resource_type: str, resource_id: str):
		self.resource_type = resource_type
		self.resource_id = resource_id
		super().__init__(f"{resource_type} '{resource_id}' not found")

class InvalidPropertiesError(GraphiteError):
	"""Invalid properties error

	Args:
	    valid_properties: valid properties for node / relation
	    got_count: count of gotten properties
	"""

	def __init__(self, valid_properties: list[Field], got_count: int):
		self.valid_properties = valid_properties
		self.got_count = got_count
		super().__init__(
			f"Expected {len(valid_properties)} properties ({valid_properties}), got {got_count}"
		)

class FieldError(GraphiteError):
	"""Field error

	Args:
	    field: field name
	    value: given value
	"""

	def __init__(self, field: Field, value: Any):
		self.field = field
		self.value = value
		super().__init__(
			f"Field {field.name} must be '{str(field.dtype)}', got {type(value)} ({value})"
		)

class FileSizeError(GraphiteError):
	"""File size error

	Args:
	    file_size: size of given file (MB)
	    max_size: max valid size (MB)
	"""

	def __init__(self, file_size: float, max_size: int | float):
		self.file_size = file_size
		self.max_size = max_size
		super().__init__(f"File is too large: {file_size:.1f}MB > {max_size:.1f}MB limit")

class SafeLoadExtensionError(GraphiteError):
	"""Safe-load extension error"""

	def __init__(self):
		super().__init__("Only '.json' files are allowed for safe loading")

class InvalidJSONError(GraphiteError):
	"""Invalid JSON error"""

	def __init__(self):
		super().__init__("Invalid JSON")

class TooNestedJSONError(GraphiteError):
	"""Too Nested JSON error"""

	def __init__(self):
		super().__init__("JSON structure is too nested")

class ConditionError(QueryError):
	"""Condition error"""

	def __init__(self, condition: str):
		self.condition = condition
		super().__init__(f"Invalid condition string: {condition}")
