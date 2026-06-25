"""
Unit tests for serialization
"""
import json
from datetime import date
from enum import Enum

import pytest

from src.graphite import (
	DataType, Field, GraphiteJSONEncoder, NodeType, Relation, RelationType,
)
from src.graphite.exceptions import InvalidJSONError, NotFoundError, ValidationError
from src.graphite.serialization import GRAPHITE_TYPE_FIELD, graphite_object_hook

class TestEncodeDecode:
	"""Test GraphiteJSONEncoder class and graphite_object_hook"""

	def test_date(self):
		"""Test date objects"""
		test_date = date(2023, 12, 1)

		result = json.dumps(test_date, cls=GraphiteJSONEncoder)
		data = json.loads(result)

		assert data["__graphite_type__"] == "date"
		assert data["value"] == "2023-12-01"

		value = graphite_object_hook(data)

		assert value == test_date

	def test_datatype_enum(self):
		"""Test DataType enum"""
		encoder = GraphiteJSONEncoder()

		result = encoder.default(DataType.STRING)

		assert result["__graphite_type__"] == "datatype"
		assert result["value"] == "string"

		value = graphite_object_hook(result)

		assert value == DataType.STRING

	def test_field(self):
		"""Test Field objects"""
		field = Field("name", DataType.STRING)

		encoder = GraphiteJSONEncoder()
		result = encoder.default(field)

		assert result["__graphite_type__"] == "Field"
		assert result["name"] == "name"
		assert result["dtype"] == DataType.STRING

		value = graphite_object_hook(result)

		assert value == field

	def test_node_type(self):
		"""Test NodeType objects"""
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

		value = graphite_object_hook(result)

		assert value == node_type

	def test_node_type_with_parent(self):
		"""Test NodeType with parent reference"""
		parent = NodeType("Entity", [])
		child = NodeType("Person", [], parent)

		encoder = GraphiteJSONEncoder()
		result = encoder.default(child)

		assert result["__graphite_type__"] == "NodeType"
		assert result["name"] == "Person"
		assert result["parent"] == "Entity"  # Should store name, not object

		value = graphite_object_hook(result)
		value.parent = parent

		assert value == child

	def test_relation_type(self):
		"""Test RelationType objects"""
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

		value = graphite_object_hook(result)

		assert value == rel_type

	def test_node(self, alice_node):
		"""Test Node objects"""
		node = alice_node

		encoder = GraphiteJSONEncoder()
		result = encoder.default(node)

		assert result["__graphite_type__"] == "Node"
		assert result["type_name"] == "Person"
		assert result["id"] == "person1"
		assert result["values"] == { "name": "Alice", "age": 30 }

		value = graphite_object_hook(result)

		assert value == node

	def test_relation(self):
		"""Test Relation objects"""
		relation = Relation(
			type_name="WORKS_AT",
			from_node="person1",
			to_node="company1",
			values={ "since": date(2021, 1, 1) },
			type_ref=None
		)

		encoder = GraphiteJSONEncoder()
		result = encoder.default(relation)

		assert result["__graphite_type__"] == "Relation"
		assert result["type_name"] == "WORKS_AT"
		assert result["from_node"] == "person1"
		assert result["to_node"] == "company1"
		# Date in values should be encoded as date
		assert isinstance(result["values"]["since"], date)

		value = graphite_object_hook(result)

		# Object must be changed, but content not
		assert value != relation
		assert relation.values == value.values
		assert relation.type_name == "WORKS_AT"
		assert relation.from_node == "person1"
		assert relation.to_node == "company1"

	def test_regular_dict(self):
		"""Test regular dictionaries"""
		regular_dict = { "key": "value", "number": 42 }

		encoder = GraphiteJSONEncoder()
		result = encoder.default(regular_dict)

		# Should fall back to parent class
		assert result == regular_dict

		value = graphite_object_hook(result)

		assert value == regular_dict

	def test_list(self):
		"""Test regular lists"""
		regular_list = [1, 2, 3, "test"]

		encoder = GraphiteJSONEncoder()
		result = encoder.default(regular_list)

		# Should fall back to parent class
		assert result == regular_list

		value = graphite_object_hook(result)

		assert value == regular_list

	def test_encode_invalid(self):
		"""Test encoding invalid types"""


		class TestClass:
			"""Test class"""

			def example(self):
				"""An example function"""
				print(self)

			def another_example(self):
				"""Another example function"""
				print(self, "test")


		class TestEnum(Enum):
			"""Enum for test"""
			VALUE1 = "value1"
			VALUE2 = "value2"


		encoder = GraphiteJSONEncoder()

		with pytest.raises(TypeError):
			encoder.default(TestClass())

		with pytest.raises(TypeError):
			encoder.default(TestEnum.VALUE1)

	def test_decode_invalid(self):
		"""Test decoding invalid types"""
		data = {
			GRAPHITE_TYPE_FIELD: "Invalid",
			"key": "value",
		}

		with pytest.raises(TypeError):
			graphite_object_hook(data)


class TestValidation:
	"""Test validation logic"""

	def test_no_schema_validate(self, populated_engine, clean_engine, temp_json_file):
		"""Test load_safe() without schema validation"""
		populated_engine.save(temp_json_file)

		clean_engine.load_safe(temp_json_file, validate_schema=False)

	def test_schema_validate(self, populated_engine, clean_engine, temp_json_file):
		"""Test load_safe() with schema validation"""
		populated_engine.save(temp_json_file)

		clean_engine.load_safe(temp_json_file, validate_schema=True)

	def test_invalid_data_content(self, temp_json_file, clean_engine):
		"""Test invalid data type for content"""
		with open(temp_json_file, "w", encoding="utf-8") as f:
			f.write('')

		with pytest.raises(InvalidJSONError):
			clean_engine.load_safe(temp_json_file)

	def test_missing_keys(self, temp_json_file, clean_engine):
		"""Test missing keys handling in load"""
		with open(temp_json_file, "w", encoding="utf-8") as f:
			f.write('{}')

		with pytest.raises(ValidationError) as exc_info:
			clean_engine.load_safe(temp_json_file)

		assert "Missing required key" in str(exc_info.value)

	def test_version_mismatch(self, temp_json_file, clean_engine):
		"""Test version mismatch in load"""
		with open(temp_json_file, "w", encoding="utf-8") as f:
			f.write(
				"""
				{
					"version": "2.0",
					"node_types": [],
					"relation_types": [],
					"nodes": [],
					"relations": []
				}
				"""
			)

		with pytest.raises(ValidationError) as exc_info:
			clean_engine.load_safe(temp_json_file)

		assert "Save file version" in str(exc_info.value)

	def test_keys_types(self, temp_json_file, clean_engine):
		"""Test invalid types for keys"""
		with open(temp_json_file, "w", encoding="utf-8") as f:
			f.write(
				"""
				{
					"version": "1.0",
					"node_types": {},
					"relation_types": [],
					"nodes": [],
					"relations": []
				}
				"""
			)

		with pytest.raises(ValidationError) as exc_info:
			clean_engine.load_safe(temp_json_file)

		assert "node_types must be a list" in str(exc_info.value)

		with open(temp_json_file, "w", encoding="utf-8") as f:
			f.write(
				"""
				{
					"version": "1.0",
					"node_types": [],
					"relation_types": {},
					"nodes": [],
					"relations": []
				}
				"""
			)

		with pytest.raises(ValidationError) as exc_info:
			clean_engine.load_safe(temp_json_file)

		assert "relation_types must be a list" in str(exc_info.value)

		with open(temp_json_file, "w", encoding="utf-8") as f:
			f.write(
				"""
				{
					"version": "1.0",
					"node_types": [],
					"relation_types": [],
					"nodes": {},
					"relations": []
				}
				"""
			)

		with pytest.raises(ValidationError) as exc_info:
			clean_engine.load_safe(temp_json_file)

		assert "nodes must be a list" in str(exc_info.value)

		with open(temp_json_file, "w", encoding="utf-8") as f:
			f.write(
				"""
				{
					"version": "1.0",
					"node_types": [],
					"relation_types": [],
					"nodes": [],
					"relations": {}
				}
				"""
			)

		with pytest.raises(ValidationError) as exc_info:
			clean_engine.load_safe(temp_json_file)

		assert "relations must be a list" in str(exc_info.value)

	def test_invalid_keys(self, temp_json_file, clean_engine):
		"""Test invalid keys handling in load"""
		with open(temp_json_file, "w", encoding="utf-8") as f:
			f.write(
				"""
				{
					"version": "1.0",
					"node_types": [],
					"relation_types": [],
					"nodes": [],
					"relations": [],
					"invalid": []
				}
				"""
			)

		with pytest.warns(UserWarning, match="Unexpected key in data"):
			clean_engine.load_safe(temp_json_file)

	def test_missing_node_type(self, temp_json_file, clean_engine):
		"""Test missing node types detection"""
		with open(temp_json_file, "w", encoding="utf-8") as f:
			f.write(
				"""
				{
					"version": "1.0",
					"node_types": [
						{
							"__graphite_type__": "NodeType",
							"name": "P",
							"parent": null,
							"fields": null
						}
					],
					"relation_types": [],
					"nodes": [
						{
							"__graphite_type__": "Node",
							"type_name": "Person",
							"id": "person",
							"values": {}
						}
					],
					"relations": []
				}
				"""
			)

		with pytest.raises(NotFoundError) as exc_info:
			clean_engine.load_safe(temp_json_file)

		assert "Node type" in str(exc_info.value)
