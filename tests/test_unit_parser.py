"""
Unit tests for GraphiteParser
"""
from datetime import datetime

import pytest

from src.graphite import DataType, GraphiteParser
from src.graphite.exceptions import ParseError

class TestGraphiteParser: # pylint: disable=attribute-defined-outside-init
	"""Test GraphiteParser class"""

	def setup_method(self):
		"""Setup parser for each test"""
		self.parser = GraphiteParser()

	def test_parse_node_definition_simple(self):
		"""Test parsing simple node definition"""
		definition = """
        node Person
        name: string
        age: int
        email: string
        """

		node_name, fields, parent = self.parser.parse_node_definition(definition)

		assert node_name == "Person"
		assert parent is None
		assert len(fields) == 3

		assert fields[0].name == "name"
		assert fields[0].dtype == DataType.STRING
		assert fields[1].name == "age"
		assert fields[1].dtype == DataType.INT
		assert fields[2].name == "email"
		assert fields[2].dtype == DataType.STRING

	def test_parse_node_definition_with_inheritance(self):
		"""Test parsing node definition with inheritance"""
		definition = """
        node User from Entity
        username: string
        password: string
        """

		node_name, fields, parent = self.parser.parse_node_definition(definition)

		assert node_name == "User"
		assert parent == "Entity"
		assert len(fields) == 2

		assert fields[0].name == "username"
		assert fields[0].dtype == DataType.STRING
		assert fields[1].name == "password"
		assert fields[1].dtype == DataType.STRING

	def test_parse_node_definition_empty_fields(self):
		"""Test parsing node definition without fields"""
		definition = "node Tag"

		node_name, fields, parent = self.parser.parse_node_definition(definition)

		assert node_name == "Tag"
		assert parent is None
		assert len(fields) == 0

	def test_parse_relation_definition_simple(self):
		"""Test parsing simple relation definition"""
		definition = """
        relation WORKS_AT
        Person -> Company
        position: string
        since: date
        """

		(rel_name, from_type, to_type,
		fields, reverse_name, is_bidirectional) = self.parser.parse_relation_definition(definition)

		assert rel_name == "WORKS_AT"
		assert from_type == "Person"
		assert to_type == "Company"
		assert reverse_name is None
		assert is_bidirectional is False
		assert len(fields) == 2

		assert fields[0].name == "position"
		assert fields[0].dtype == DataType.STRING
		assert fields[1].name == "since"
		assert fields[1].dtype == DataType.DATE

	def test_parse_relation_definition_with_reverse(self):
		"""Test parsing relation definition with reverse name"""
		definition = """
        relation WORKS_AT reverse EMPLOYS
        Person -> Company
        position: string
        """

		(rel_name, from_type, to_type,
		_, reverse_name, is_bidirectional) = self.parser.parse_relation_definition(definition)

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
		_, reverse_name, is_bidirectional) = self.parser.parse_relation_definition(definition)

		assert rel_name == "FRIENDS_WITH"
		assert from_type == "Person"
		assert to_type == "Person"
		assert reverse_name is None
		assert is_bidirectional is True

	def test_parse_node_instance_strings(self):
		"""Test parsing node instance with strings"""
		line = 'User, user1, "Alice", 30, "alice@email.com"'

		node_type, node_id, values = self.parser.parse_node_instance(line)

		assert node_type == "User"
		assert node_id == "user1"
		assert values == ["Alice", 30, "alice@email.com"]

	def test_parse_node_instance_numbers(self):
		"""Test parsing node instance with numbers"""
		line = "Product, prod1, 100, 19.99, true"

		node_type, node_id, values = self.parser.parse_node_instance(line)

		assert node_type == "Product"
		assert node_id == "prod1"
		assert values == [100, 19.99, True]

	def test_parse_node_instance_date(self):
		"""Test parsing node instance with date"""
		line = 'Event, event1, "Conference", "2023-12-01"'

		node_type, node_id, values = self.parser.parse_node_instance(line)

		assert node_type == "Event"
		assert node_id == "event1"
		assert values == ["Conference", "2023-12-01"]

	def test_parse_node_instance_negative_number(self):
		"""Test parsing node instance with negative number"""
		line = "Temp, temp1, -10, 25.5"

		node_type, node_id, values = self.parser.parse_node_instance(line)

		assert node_type == "Temp"
		assert node_id == "temp1"
		assert values == [-10, 25.5]

	def test_parse_relation_instance_forward(self):
		"""Test parsing forward relation instance"""
		line = "person1 -[WORKS_AT, Engineer, 2021-01-01]-> company1"

		from_id, to_id, rel_type, values, direction = self.parser.parse_relation_instance(line)

		assert from_id == "person1"
		assert to_id == "company1"
		assert rel_type == "WORKS_AT"
		assert values == ["Engineer", datetime.strptime("2021-01-01", "%Y-%m-%d").date()]
		assert direction == "forward"

	def test_parse_relation_instance_no_attributes(self):
		"""Test parsing relation instance without attributes"""
		line = "person1 -[LIKES]-> post1"

		from_id, to_id, rel_type, values, _ = self.parser.parse_relation_instance(line)

		assert from_id == "person1"
		assert to_id == "post1"
		assert rel_type == "LIKES"
		assert not values

	def test_parse_relation_instance_bidirectional(self):
		"""Test parsing bidirectional relation instance"""
		line = "person1 -[FRIENDS_WITH, 2020-05-15]- person2"

		from_id, to_id, rel_type, values, direction = self.parser.parse_relation_instance(line)

		assert from_id == "person1"
		assert to_id == "person2"
		assert rel_type == "FRIENDS_WITH"
		assert values == [datetime.strptime("2020-05-15", "%Y-%m-%d").date()]
		assert direction == "bidirectional"

	def test_parse_invalid_relation_format(self):
		"""Test parsing invalid relation format"""
		line = "invalid format without brackets"

		with pytest.raises(ParseError):
			self.parser.parse_relation_instance(line)
