"""
Unit tests for Graphite type classes
"""
import pytest

from src.graphite import DataType, Field, NodeType, RelationType

class TestDataType:
	"""Test DataType enum"""

	def test_data_type_values(self):
		"""Test DataType enum values"""
		assert DataType.STRING.value == "string"
		assert DataType.INT.value == "int"
		assert DataType.DATE.value == "date"
		assert DataType.FLOAT.value == "float"
		assert DataType.BOOL.value == "bool"

	def test_data_type_from_string(self):
		"""Test creating DataType from string"""
		assert DataType("string") == DataType.STRING
		assert DataType("int") == DataType.INT
		assert DataType("date") == DataType.DATE
		assert DataType("float") == DataType.FLOAT
		assert DataType("bool") == DataType.BOOL

	def test_invalid_data_type(self):
		"""Test invalid data type raises error"""
		with pytest.raises(ValueError):
			DataType("invalid_type")

class TestField:
	"""Test Field class"""

	def test_field_creation(self):
		"""Test creating a field"""
		field = Field("name", DataType.STRING)
		assert field.name == "name"
		assert field.dtype == DataType.STRING

class TestNodeType:
	"""Test NodeType class"""

	def test_node_type_creation(self):
		"""Test creating a node type"""
		fields = [
			Field("name", DataType.STRING),
			Field("age", DataType.INT)
		]
		node_type = NodeType("Person", fields)

		assert node_type.name == "Person"
		assert len(node_type.fields) == 2
		assert node_type.parent is None

	def test_node_type_with_parent(self):
		"""Test node type with inheritance"""
		parent_fields = [Field("id", DataType.STRING)]
		child_fields = [Field("name", DataType.STRING)]

		parent = NodeType("Entity", parent_fields)
		child = NodeType("Person", child_fields, parent)

		assert child.name == "Person"
		assert child.parent == parent

	def test_get_all_fields_without_parent(self):
		"""Test get_all_fields without inheritance"""
		fields = [
			Field("name", DataType.STRING),
			Field("age", DataType.INT)
		]
		node_type = NodeType("Person", fields)

		all_fields = node_type.get_all_fields()
		assert len(all_fields) == 2
		assert all_fields[0].name == "name"
		assert all_fields[1].name == "age"

	def test_get_all_fields_with_parent(self):
		"""Test get_all_fields with inheritance"""
		parent_fields = [Field("id", DataType.STRING)]
		child_fields = [Field("name", DataType.STRING)]

		parent = NodeType("Entity", parent_fields)
		child = NodeType("Person", child_fields, parent)

		all_fields = child.get_all_fields()
		assert len(all_fields) == 2
		# Parent fields come first
		assert all_fields[0].name == "id"
		assert all_fields[1].name == "name"

	def test_node_type_hash(self):
		"""Test NodeType hash function"""
		node_type1 = NodeType("Person", [])
		node_type2 = NodeType("Person", [])
		node_type3 = NodeType("Company", [])

		# Same name should have same hash
		assert hash(node_type1) == hash(node_type2)
		# Different name should have different hash
		assert hash(node_type1) != hash(node_type3)

class TestRelationType:
	"""Test RelationType class"""

	def test_relation_type_creation(self):
		"""Test creating a relation type"""
		fields = [Field("since", DataType.DATE)]
		rel_type = RelationType(
			name="WORKS_AT",
			from_type="Person",
			to_type="Company",
			fields=fields,
			reverse_name="EMPLOYS",
			is_bidirectional=False
		)

		assert rel_type.name == "WORKS_AT"
		assert rel_type.from_type == "Person"
		assert rel_type.to_type == "Company"
		assert len(rel_type.fields) == 1
		assert rel_type.reverse_name == "EMPLOYS"
		assert rel_type.is_bidirectional is False

	def test_relation_type_without_reverse(self):
		"""Test relation type without reverse name"""
		rel_type = RelationType(
			name="LIKES",
			from_type="Person",
			to_type="Post",
			fields=[],
			reverse_name=None,
			is_bidirectional=False
		)

		assert rel_type.name == "LIKES"
		assert rel_type.reverse_name is None

	def test_relation_type_bidirectional(self):
		"""Test bidirectional relation type"""
		rel_type = RelationType(
			name="FRIENDS_WITH",
			from_type="Person",
			to_type="Person",
			fields=[Field("since", DataType.DATE)],
			reverse_name=None,
			is_bidirectional=True
		)

		assert rel_type.is_bidirectional is True

	def test_relation_type_hash(self):
		"""Test RelationType hash function"""
		rel_type1 = RelationType("WORKS_AT", "Person", "Company", [])
		rel_type2 = RelationType("WORKS_AT", "Person", "Company", [])
		rel_type3 = RelationType("MANAGES", "Person", "Company", [])

		# Same name should have same hash
		assert hash(rel_type1) == hash(rel_type2)
		# Different name should have different hash
		assert hash(rel_type1) != hash(rel_type3)
