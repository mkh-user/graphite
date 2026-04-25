"""
Unit tests for serialization
"""
import json
from collections import defaultdict
from datetime import date
from enum import Enum

from src.graphite import (
	DataType, Field, GraphiteJSONEncoder, Node, NodeType, Relation, RelationType,
)

class TestGraphiteJSONEncoder:
	"""Test GraphiteJSONEncoder class"""

	def test_encode_date(self):
		"""Test encoding date objects"""
		test_date = date(2023, 12, 1)

		result = json.dumps(test_date, cls=GraphiteJSONEncoder)
		data = json.loads(result)

		assert data["__graphite_type__"] == "datetime"
		assert data["value"] == "2023-12-01"
		assert data["is_date"] is True

	def test_encode_datatype_enum(self):
		"""Test encoding DataType enum"""
		encoder = GraphiteJSONEncoder()

		result = encoder.default(DataType.STRING)

		assert result["__graphite_type__"] == "datatype"
		assert result["value"] == "string"

	def test_encode_field(self):
		"""Test encoding Field objects"""
		field = Field("name", DataType.STRING, "default")

		encoder = GraphiteJSONEncoder()
		result = encoder.default(field)

		assert result["__graphite_type__"] == "Field"
		assert result["name"] == "name"
		assert result["dtype"] == "string"
		assert result["default"] == "default"

	def test_encode_node_type(self):
		"""Test encoding NodeType objects"""
		node_type = NodeType(
			name="Person",
			fields=[Field("name", DataType.STRING)],
			parent=None
		)

		encoder = GraphiteJSONEncoder()
		result = encoder.default(node_type)

		assert result["__graphite_type__"] == "NodeType"
		assert result["name"] == "Person"
		assert len(result["fields"]) == 1
		assert "parent" in result

	def test_encode_node_type_with_parent(self):
		"""Test encoding NodeType with parent reference"""
		parent = NodeType("Entity", [])
		child = NodeType("Person", [], parent)

		encoder = GraphiteJSONEncoder()
		result = encoder.default(child)

		assert result["__graphite_type__"] == "NodeType"
		assert result["name"] == "Person"
		assert result["parent"] == "Entity"  # Should store name, not object

	def test_encode_relation_type(self):
		"""Test encoding RelationType objects"""
		rel_type = RelationType(
			name="WORKS_AT",
			from_type="Person",
			to_type="Company",
			fields=[Field("since", DataType.DATE)],
			reverse_name="EMPLOYS",
			is_bidirectional=False
		)

		encoder = GraphiteJSONEncoder()
		result = encoder.default(rel_type)

		assert result["__graphite_type__"] == "RelationType"
		assert result["name"] == "WORKS_AT"
		assert result["from_type"] == "Person"
		assert result["to_type"] == "Company"
		assert result["reverse_name"] == "EMPLOYS"
		assert result["is_bidirectional"] is False

	def test_encode_node(self):
		"""Test encoding Node objects"""
		# pylint: disable=duplicate-code
		node = Node(
			type_name="Person",
			id="person1",
			values={"name": "Alice", "age": 30},
			type_ref=None
		)

		encoder = GraphiteJSONEncoder()
		result = encoder.default(node)

		assert result["__graphite_type__"] == "Node"
		assert result["type_name"] == "Person"
		assert result["id"] == "person1"
		assert result["values"] == {"name": "Alice", "age": 30}

	def test_encode_relation(self):
		"""Test encoding Relation objects"""
		relation = Relation(
			type_name="WORKS_AT",
			from_node="person1",
			to_node="company1",
			values={"since": date(2021, 1, 1)},
			type_ref=None
		)

		encoder = GraphiteJSONEncoder()
		result = encoder.default(relation)

		assert result["__graphite_type__"] == "Relation"
		assert result["type_name"] == "WORKS_AT"
		assert result["from_node"] == "person1"
		assert result["to_node"] == "company1"
		# Date in values should be encoded as datetime
		assert isinstance(result["values"]["since"], date)

	def test_encode_defaultdict(self):
		"""Test encoding defaultdict objects"""
		ddict = defaultdict(list)
		ddict["key1"].append("value1")
		ddict["key2"].append("value2")

		encoder = GraphiteJSONEncoder()
		result = encoder.default(ddict)

		assert result["__graphite_type__"] == "defaultdict"
		assert result["__default_factory"] == "list"
		assert result["key1"] == ["value1"]
		assert result["key2"] == ["value2"]

	def test_encode_defaultdict_dict(self):
		"""Test encoding defaultdict with dict factory"""
		ddict = defaultdict(dict)
		ddict["key1"]["subkey"] = "value"

		encoder = GraphiteJSONEncoder()
		result = encoder.default(ddict)

		assert result["__graphite_type__"] == "defaultdict"
		assert result["__default_factory"] == "dict"
		assert result["key1"]["subkey"] == "value"

	def test_encode_regular_dict(self):
		"""Test encoding regular dictionaries"""
		regular_dict = {"key": "value", "number": 42}

		encoder = GraphiteJSONEncoder()
		result = encoder.default(regular_dict)

		# Should fall back to parent class
		assert result == regular_dict

	def test_encode_list(self):
		"""Test encoding regular lists"""
		regular_list = [1, 2, 3, "test"]

		encoder = GraphiteJSONEncoder()
		result = encoder.default(regular_list)

		# Should fall back to parent class
		assert result == regular_list

	def test_encode_other_enum(self):
		"""Test encoding other enum types (not DataType)"""
		class TestEnum(Enum):
			"""Enum for test"""
			VALUE1 = "value1"
			VALUE2 = "value2"

		encoder = GraphiteJSONEncoder()
		result = encoder.default(TestEnum.VALUE1)

		assert result["__graphite_type__"] == "enum"
		assert result["enum_class"] == "TestEnum"
		assert result["value"] == "value1"
