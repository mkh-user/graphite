"""
Unit tests for Node and Relation instances
"""
from src.graphite import DataType, Field, Node, NodeType, Relation, RelationType

class TestNode:
	"""Test Node class"""

	def test_node_creation(self):
		"""Test creating a node"""
		node = Node(
			type_name="Person",
			id="person1",
			values={"name": "Alice", "age": 30},
			type_ref=None
		)

		assert node.type_name == "Person"
		assert node.id == "person1"
		assert node.values == {"name": "Alice", "age": 30}
		assert node.type_ref is None

	def test_node_get_field(self):
		"""Test getting field from node"""
		node = Node(
			type_name="Person",
			id="person1",
			values={"name": "Alice", "age": 30}
		)

		assert node.get("name") == "Alice"
		assert node.get("age") == 30
		assert node.get("nonexistent") is None

	def test_node_repr(self):
		"""Test node string representation"""
		node = Node(
			type_name="Person",
			id="person1",
			values={}
		)

		assert repr(node) == "Node(Person:person1)"

	def test_node_with_type_ref(self):
		"""Test node with type reference"""
		node_type = NodeType(
			"Person", [
				Field("name", DataType.STRING),
				Field("age", DataType.INT)
			]
		)

		node = Node(
			type_name="Person",
			id="person1",
			values={"name": "Alice", "age": 30},
			type_ref=node_type
		)

		assert node.type_ref == node_type
		assert node.type_ref.name == "Person"

class TestRelation:
	"""Test Relation class"""

	def test_relation_creation(self):
		"""Test creating a relation"""
		relation = Relation(
			type_name="WORKS_AT",
			from_node="person1",
			to_node="company1",
			values={"since": "2021-01-01", "position": "Engineer"},
			type_ref=None
		)

		assert relation.type_name == "WORKS_AT"
		assert relation.from_node == "person1"
		assert relation.to_node == "company1"
		assert relation.values == {"since": "2021-01-01", "position": "Engineer"}
		assert relation.type_ref is None

	def test_relation_get_field(self):
		"""Test getting field from relation"""
		relation = Relation(
			type_name="WORKS_AT",
			from_node="person1",
			to_node="company1",
			values={"since": "2021-01-01", "position": "Engineer"}
		)

		assert relation.get("since") == "2021-01-01"
		assert relation.get("position") == "Engineer"
		assert relation.get("nonexistent") is None

	def test_relation_repr(self):
		"""Test relation string representation"""
		relation = Relation(
			type_name="WORKS_AT",
			from_node="person1",
			to_node="company1",
			values={}
		)

		assert repr(relation) == "Relation(WORKS_AT:person1->company1)"

	def test_relation_with_type_ref(self):
		"""Test relation with type reference"""
		rel_type = RelationType(
			name="WORKS_AT",
			from_type="Person",
			to_type="Company",
			fields=[
				Field("since", DataType.DATE),
				Field("position", DataType.STRING)
			]
		)

		relation = Relation(
			type_name="WORKS_AT",
			from_node="person1",
			to_node="company1",
			values={"since": "2021-01-01", "position": "Engineer"},
			type_ref=rel_type
		)

		assert relation.type_ref == rel_type
		assert relation.type_ref.name == "WORKS_AT"
