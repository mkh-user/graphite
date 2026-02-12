"""
Possible exceptions in Graphite
"""
from typing import Any

from .types import Field

class GraphiteError(Exception):
	"""Base exception for all Graphite errors"""

class SchemaError(GraphiteError):
	"""Schema-related errors"""
	def __init__(self, message: str, line: int = None, column: int = None):
		self.line = line
		self.column = column
		super().__init__(message)

class ValidationError(GraphiteError):
	"""Data validation errors"""
	def __init__(self, message: str, field: str = None, value: Any = None):
		self.field = field
		self.value = value
		super().__init__(message)

class QueryError(GraphiteError):
	"""Query parsing/execution errors"""

class NotFoundError(GraphiteError):
	"""Resource not found errors"""
	def __init__(self, resource_type: str, resource_id: str):
		self.resource_type = resource_type
		self.resource_id = resource_id
		super().__init__(f"{resource_type} '{resource_id}' not found")

class InvalidPropertiesError(GraphiteError):
	"""Invalid properties error"""
	def __init__(self, valid_properties: list[Field], got_count: int):
		self.valid_properties = valid_properties
		self.got_count = got_count
		# pylint: disable=consider-using-f-string
		super().__init__(
			"Expected {} properties ({}), got {}".format(len(valid_properties), valid_properties, got_count)
		)

class FieldError(GraphiteError):
	"""Field error"""
	def __init__(self, field: Field, value: Any):
		self.field = field
		self.value = value
		super().__init__(
			f"Field {field.name} must be '{str(field.dtype)}', got {type(value)} ({value})"
		)

class DateParseError(GraphiteError):
	"""Date parsing error"""
	def __init__(self, date_str: str, expected_format: str = "%Y-%m-%d"):
		self.date_str = date_str
		self.expected_format = expected_format
		super().__init__(
			f"Failed to parse date '{date_str}'. Expected format: {expected_format}"
		)

class FileSizeError(GraphiteError):
	"""File size error"""
	def __init__(self, file_size: float, max_size: int):
		self.file_size = file_size
		self.max_size = max_size
		super().__init__(f"File is too large: {file_size:.1f}MB > {max_size}MB limit")

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
