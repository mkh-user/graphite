"""
Unit tests for Node and Relation instances
"""
from datetime import date

import pytest

from src.graphite import DataType, Field, Node, NodeType, Relation, RelationType
from src.graphite.exceptions import NotFoundError

class TestNode:
	"""Test Node class"""

	def test_node_creation(self, alice_node):
		"""Test creating a node"""
		node = alice_node

		assert node.type_name == "Person"
		assert node.id == "person1"
		assert node.values == { "name": "Alice", "age": 30 }
		assert node.type_ref is None

	def test_node_get_field(self):
		"""Test getting field from node"""
		node = Node(
			type_name="Person",
			id="person1",
			values={ "name": "Alice", "age": 30 }
		)

		assert node.get("name") == "Alice"
		assert node.get("age") == 30
		assert node.get("nonexistent") is None

	def test_node_repr(self):
		"""Test node string representation"""
		node = Node(
			type_name="Person",
			id="person1",
			values={ }
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
			values={ "name": "Alice", "age": 30 },
			type_ref=node_type
		)

		assert node.type_ref is not None
		assert node.type_ref == node_type
		assert node.type_ref.name == "Person"

	def test_node_set(self, simple_engine):
		"""Test node.set()"""
		engine = simple_engine

		node = engine.create_node("Person", "person1", "Alice")

		assert "person1" in engine.nodes
		assert node["name"] == "Alice"

		node.set("name", "Alicia")

		assert node["name"] == "Alicia"

	def test_node_set_invalid(self, simple_engine):
		"""Test node.set() with invalid field"""
		engine = simple_engine

		node = engine.create_node("Person", "person1", "Alice")

		with pytest.raises(NotFoundError) as exc_info:
			node.set("age", 13)

		assert "Field" in str(exc_info.value)

	def test_node_equality(self):
		"""Test node equality"""
		node1 = Node("Person", "person1", { "name": "Alice" })
		node2 = Node("Person", "person1", { "name": "Bob" })
		node3 = Node("Person", "person2", { "name": "Alice" })

		assert node1 == node2
		assert node1 != node3
		assert node2 != node3

	def test_node_equality_invalid(self):
		"""Test node equality with invalid object"""
		node = Node("Person", "person", { "name": "Alice" })

		assert node != 12


class TestRelation:
	"""Test Relation class"""

	def test_relation_creation(self):
		"""Test creating a relation"""
		relation = Relation(
			type_name="WORKS_AT",
			from_node="person1",
			to_node="company1",
			values={ "since": "2021-01-01", "position": "Engineer" },
			type_ref=None
		)

		assert relation.type_name == "WORKS_AT"
		assert relation.from_node == "person1"
		assert relation.to_node == "company1"
		assert relation.values == { "since": "2021-01-01", "position": "Engineer" }
		assert relation.type_ref is None

	def test_relation_get_field(self):
		"""Test getting field from relation"""
		relation = Relation(
			type_name="WORKS_AT",
			from_node="person1",
			to_node="company1",
			values={ "since": "2021-01-01", "position": "Engineer" }
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
			values={ }
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
			values={ "since": "2021-01-01", "position": "Engineer" },
			type_ref=rel_type
		)

		assert relation.type_ref is not None
		assert relation.type_ref == rel_type
		assert relation.type_ref.name == "WORKS_AT"

	def test_relation_set(self, clean_engine):
		"""Test relation.set()"""
		engine = clean_engine

		engine.define_node("node Person\nname: string")
		engine.define_relation("relation KNOWS\nPerson -> Person\nsince: date")

		engine.create_node("Person", "person1", "Alice")
		engine.create_node("Person", "person2", "Bob")
		relation = engine.create_relation("person1", "person2", "KNOWS", "2021-01-01")

		assert id(relation) in engine.relations
		assert relation["since"] == date(2021, 1, 1)

		relation.set("since", date(2050, 1, 1))

		assert relation["since"] == date(2050, 1, 1)

	def test_relation_set_invalid(self, clean_engine):
		"""Test relation.set() with invalid field"""
		engine = clean_engine

		engine.define_node("node Person\nname: string")
		engine.define_relation("relation KNOWS\nPerson -> Person\nsince: date")

		engine.create_node("Person", "person1", "Alice")
		engine.create_node("Person", "person2", "Bob")
		relation = engine.create_relation("person1", "person2", "KNOWS", "2021-01-01")

		with pytest.raises(NotFoundError) as exc_info:
			relation.set("age", 13)

		assert "Field" in str(exc_info.value)

	def test_relation_equality(self):
		"""Test relation equality"""
		relation1 = Relation("KNOWS", "person1", "person2", { })
		relation2 = Relation("KNOWS", "person1", "person2", { })

		assert relation1 != relation2

	def test_relation_equality_invalid(self):
		"""Test relation equality with invalid object"""
		relation_test = Relation("KNOWS", "person1", "person2", { })

		assert relation_test != 12
