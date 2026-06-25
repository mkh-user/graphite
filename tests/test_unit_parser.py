"""
Unit tests for GraphiteParser
"""
from datetime import date, datetime

import pytest

from src.graphite import DataType, Field
from src.graphite.dsl_parser import (
	parse, parse_node_definition, parse_node_instance, parse_relation_definition,
	parse_relation_instance, parse_value, validate_field_value
)
from src.graphite.exceptions import ParseError, RelationTypeDefineError

class TestParseSchema:
	"""Test parsing schema"""

	def test_parser_error_propagation(self, clean_engine):
		"""Test parser errors propagation"""
		with pytest.raises(ParseError) as exc_info:
			parse(
				clean_engine, """
			node Person

			relation KNOWS
			Person -> Person

			Person, person1
			Person, person2

			person1 -[KNOWS]-> person2
			person1 -[KNOWS,]-> person3
			"""
			)

		assert "Additional comma in relation instance values" in str(exc_info.value)
		assert exc_info.value.line == 10

		with pytest.raises(ParseError) as exc_info:
			parse(
				clean_engine, """
			node Entity

			node Person from Human from Entity
			"""
			)

		assert "Invalid node definition" in str(exc_info.value)
		assert exc_info.value.line == 3

	def test_parse_node_definition_simple(self):
		"""Test parsing simple node definition"""
		definition = """
		node Person
		name: string
		age: int
		email: string
		"""

		node_name, fields, parent = parse_node_definition(definition)

		assert node_name == "Person"
		assert parent is None
		assert len(fields) == 3

		assert fields[0][0] == "name"
		assert fields[0][1] == "string"
		assert fields[1][0] == "age"
		assert fields[1][1] == "int"
		assert fields[2][0] == "email"
		assert fields[2][1] == "string"

	def test_parse_node_definition_with_inheritance(self):
		"""Test parsing node definition with inheritance"""
		definition = """
		node User from Entity
		username: string
		password: string
		"""

		node_name, fields, parent = parse_node_definition(definition)

		assert node_name == "User"
		assert parent == "Entity"
		assert len(fields) == 2

		assert fields[0][0] == "username"
		assert fields[0][1] == "string"
		assert fields[1][0] == "password"
		assert fields[1][1] == "string"

	def test_parse_node_definition_empty_fields(self):
		"""Test parsing node definition without fields"""
		definition = "node Tag"

		node_name, fields, parent = parse_node_definition(definition)

		assert node_name == "Tag"
		assert parent is None
		assert len(fields) == 0

	def test_parse_node_definition_no_node_prefix(self):
		"""Test parsing node definition without 'node ' prefix"""
		with pytest.raises(ParseError) as exc_info:
			parse_node_definition("Person\nname: string")

		assert "Invalid node definition" in str(exc_info.value)

	def test_parse_node_definition_wrong_from_usage(self):
		"""Test parsing node definition with wrong usage of ' from '"""
		with pytest.raises(ParseError) as exc_info:
			parse_node_definition("node Person from Human from Entity\nname: string")

		assert "Invalid node definition" in str(exc_info.value)

	def test_parse_node_definition_empty_line(self):
		"""Test parsing node definition with empty line"""
		with pytest.warns(SyntaxWarning):
			type_name, fields, parent = parse_node_definition(
				"node Person from Human\n\nname: string"
			)

		assert type_name == "Person"
		assert fields == [("name", "string")]
		assert parent == "Human"

	def test_parse_relation_definition_simple(self):
		"""Test parsing simple relation definition"""
		definition = """
		relation WORKS_AT
		Person -> Company
		position: string
		since: date
		"""

		(rel_name, from_type, to_type,
		fields, reverse_name, is_bidirectional) = parse_relation_definition(definition)

		assert rel_name == "WORKS_AT"
		assert from_type == "Person"
		assert to_type == "Company"
		assert reverse_name is None
		assert is_bidirectional is False
		assert len(fields) == 2

		assert fields[0][0] == "position"
		assert fields[0][1] == "string"
		assert fields[1][0] == "since"
		assert fields[1][1] == "date"

	def test_parse_relation_definition_with_reverse(self):
		"""Test parsing relation definition with reverse name"""
		definition = """
		relation WORKS_AT reverse EMPLOYS
		Person -> Company
		position: string
		"""

		(rel_name, from_type, to_type,
		_, reverse_name, is_bidirectional) = parse_relation_definition(definition)

		assert rel_name == "WORKS_AT"
		assert from_type == "Person"
		assert to_type == "Company"
		assert reverse_name == "EMPLOYS"
		assert is_bidirectional is False

	def test_parse_relation_definition_bidirectional(self):
		"""Test parsing bidirectional relation definition"""
		definition = """
		relation FRIENDS_WITH both
		Person - Person
		since: date
		"""

		(rel_name, from_type, to_type,
		_, reverse_name, is_bidirectional) = parse_relation_definition(definition)

		assert rel_name == "FRIENDS_WITH"
		assert from_type == "Person"
		assert to_type == "Person"
		assert reverse_name is None
		assert is_bidirectional is True

	def test_parse_relation_definition_single_line(self):
		"""Test parsing single line relation definition"""
		with pytest.raises(ParseError) as exc_info:
			parse_relation_definition("relation KNOWS")

		assert "expected at least two lines" in str(exc_info.value)

	def test_parse_relation_definition_no_relation_prefix(self):
		"""Test parsing relation definition with no 'relation ' prefix"""
		with pytest.raises(ParseError) as exc_info:
			parse_relation_definition("KNOWS\nPerson -> Person")

		assert "Invalid relation definition" in str(exc_info.value)

	def test_parse_relation_definition_wrong_reverse_usage(self):
		"""Test parsing relation definition with wrong usage of ' reverse '"""
		with pytest.raises(ParseError) as exc_info:
			parse_relation_definition("relation KNOWS reverse REL reverse OTHER\nPerson -> Person")

		assert "Invalid relation definition" in str(exc_info.value)

	def test_parse_relation_definition_bidirectional_with_reverse(self):
		"""Test parsing bidirectional relation definition with reverse name"""
		with pytest.raises(RelationTypeDefineError):
			parse_relation_definition("relation KNOWS both reverse REL\nPerson -> Person")

	def test_parse_relation_definition_invalid_pattern(self):
		"""Test parsing relation definition with invalid pattern"""
		error_message = "Invalid relation type format"

		with pytest.raises(ParseError) as exc_info:
			parse_relation_definition("relation KNOWS\nPerson > Person")

		assert error_message in str(exc_info.value)

		with pytest.raises(ParseError) as exc_info:
			parse_relation_definition("relation KNOWS\nPerson -> Person -> Person")

		assert error_message in str(exc_info.value)

		with pytest.raises(ParseError) as exc_info:
			parse_relation_definition("relation KNOWS\nPerson - - Person")

		assert error_message in str(exc_info.value)

	def test_parse_relation_definition_empty_line(self):
		"""Test parsing relation definition with empty line"""
		with pytest.warns(SyntaxWarning, match="in relation definition is empty"):
			parse_relation_definition("relation KNOWS\nPerson -> Person\n\nsince: date")

	def test_parse_fields_invalid_colons(self):
		"""Test parsing fields with invalid colons"""
		with pytest.raises(ParseError) as exc_info:
			parse_relation_definition("relation KNOWS\nPerson -> Person\nsince::")

		assert "Invalid field definition" in str(exc_info.value)

		with pytest.raises(ParseError) as exc_info:
			parse_relation_definition("relation KNOWS\nPerson -> Person\nsince:")

		assert "Invalid field definition" in str(exc_info.value)

class TestParseData:
	"""Test parsing data"""

	def test_parse_node_instance_strings(self):
		"""Test parsing node instance with strings"""
		line = 'User, user1, "Alice", 30, "alice@email.com"'

		node_type, node_id, values = parse_node_instance(line)

		assert node_type == "User"
		assert node_id == "user1"
		assert values == ["Alice", 30, "alice@email.com"]

	def test_parse_node_instance_numbers(self):
		"""Test parsing node instance with numbers"""
		line = "Product, prod1, 100, 19.99, true"

		node_type, node_id, values = parse_node_instance(line)

		assert node_type == "Product"
		assert node_id == "prod1"
		assert values == [100, 19.99, True]

	def test_parse_node_instance_date(self):
		"""Test parsing node instance with date"""
		line = 'Event, event1, "Conference", "2023-12-01"'

		node_type, node_id, values = parse_node_instance(line)

		assert node_type == "Event"
		assert node_id == "event1"
		assert values == ["Conference", "2023-12-01"]

	def test_parse_node_instance_negative_number(self):
		"""Test parsing node instance with negative number"""
		line = "Temp, temp1, -10, 25.5"

		node_type, node_id, values = parse_node_instance(line)

		assert node_type == "Temp"
		assert node_id == "temp1"
		assert values == [-10, 25.5]

	def test_parse_node_instance_inner_quotes(self):
		"""Test parsing node instance with inner quotes"""
		node_type, node_id, values = parse_node_instance(
			"Person, person, \"'some test'\", '\"some text\"'"
		)

		assert node_type == "Person"
		assert node_id == "person"
		assert values == ["'some test'", '"some text"']

	def test_parse_node_instance_invalid_comma(self):
		"""Test parsing node instance with invalid comma"""
		with pytest.raises(ParseError) as exc_info:
			parse_node_instance("Person, person, Alice,")

		assert "Additional comma in node instance values" in str(exc_info.value)

	def test_parse_relation_instance_forward(self):
		"""Test parsing forward relation instance"""
		line = "person1 -[WORKS_AT, Engineer, 2021-01-01]-> company1"

		from_id, to_id, rel_type, values = parse_relation_instance(line)

		assert from_id == "person1"
		assert to_id == "company1"
		assert rel_type == "WORKS_AT"
		assert values == ["Engineer", datetime.strptime("2021-01-01", "%Y-%m-%d").date()]

	def test_parse_relation_instance_no_attributes(self):
		"""Test parsing relation instance without attributes"""
		line = "person1 -[LIKES]-> post1"

		from_id, to_id, rel_type, values = parse_relation_instance(line)

		assert from_id == "person1"
		assert to_id == "post1"
		assert rel_type == "LIKES"
		assert not values

	def test_parse_relation_instance_bidirectional(self):
		"""Test parsing bidirectional relation instance"""
		line = "person1 -[FRIENDS_WITH, 2020-05-15]- person2"

		from_id, to_id, rel_type, values = parse_relation_instance(line)

		assert from_id == "person1"
		assert to_id == "person2"
		assert rel_type == "FRIENDS_WITH"
		assert values == [datetime.strptime("2020-05-15", "%Y-%m-%d").date()]

	def test_parse_invalid_relation_format(self):
		"""Test parsing invalid relation format"""
		line = "invalid format without brackets"

		with pytest.raises(ParseError):
			parse_relation_instance(line)

	def test_parse_relation_instance_inner_quotes(self):
		"""Test parsing relation instance with inner quotes"""
		source, target, rel_type, field_values = parse_relation_instance(
			"""
			person1 -[KNOWS, "'some test'", '"some text"']-> person2
			""".strip()
		)

		assert source == "person1"
		assert target == "person2"
		assert rel_type == "KNOWS"
		assert field_values == ["'some test'", '"some text"']

	def test_parse_relation_instance_invalid_comma(self):
		"""Test parsing relation instance with invalid comma"""
		with pytest.raises(ParseError) as exc_info:
			parse_relation_instance("person1 -[KNOWS,]-> person2")

		assert "Additional comma in relation instance values" in str(exc_info.value)


class TestParseFields:
	"""Test parsing fields for graphite"""

	def test_validate_auto_convert(self):
		"""Test automatic conversion in validation"""
		assert validate_field_value(12, Field("", DataType.STRING)) == "12"
		assert validate_field_value(12.9, Field("", DataType.INT)) == 12
		assert validate_field_value("2020-1-2", Field("", DataType.DATE)) == date(2020, 1, 2)
		assert validate_field_value(12, Field("", DataType.FLOAT)) == 12.0
		assert validate_field_value("True", Field("", DataType.BOOL)) is True
		assert validate_field_value(0, Field("", DataType.BOOL)) is False
		assert validate_field_value(
			datetime(2020, 1, 2, 10, 20, 54),
			Field("", DataType.DATE)
		) == date(2020, 1, 2)

	def test_parse_invalid_date_like(self):
		"""Test parsing invalid date-like format"""
		assert parse_value("100-2-1") == "100-2-1"
