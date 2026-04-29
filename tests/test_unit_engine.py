"""
Unit tests for GraphiteEngine core functionality
"""
from datetime import date

import pytest

from src.graphite.exceptions import FieldError, InvalidPropertiesError, NotFoundError

class TestGraphiteEngineSchema:
	"""Test GraphiteEngine schema definition methods"""

	def test_define_node_simple(self, clean_engine):
		"""Test defining a simple node type"""
		engine = clean_engine

		engine.define_node(
			"""
        node Person
        name: string
        age: int
        """
		)

		assert "Person" in engine.node_types
		node_type = engine.node_types["Person"]
		assert node_type.name == "Person"
		assert len(node_type.fields) == 2
		assert node_type.fields[0].name == "name"
		assert node_type.fields[1].name == "age"

	def test_define_node_with_inheritance(self, clean_engine):
		"""Test defining node type with inheritance"""
		engine = clean_engine

		# Define parent first
		engine.define_node(
			"""
        node Entity
        id: string
        created: date
        """
		)

		# Define child
		engine.define_node(
			"""
        node User from Entity
        username: string
        password: string
        """
		)

		assert "User" in engine.node_types
		user_type = engine.node_types["User"]
		assert user_type.name == "User"
		assert user_type.parent is not None
		assert user_type.parent.name == "Entity"

		# Check inherited fields
		all_fields = user_type.get_all_fields()
		assert len(all_fields) == 4
		assert all_fields[0].name == "id"
		assert all_fields[1].name == "created"
		assert all_fields[2].name == "username"

	def test_define_node_inheritance_parent_not_found(self, clean_engine):
		"""Test defining node with non-existent parent"""
		engine = clean_engine

		with pytest.raises(NotFoundError) as exc_info:
			engine.define_node(
				"""
            node User from NonExistent
            username: string
            """
			)

		assert "Parent node type" in str(exc_info.value)
		assert "NonExistent" in str(exc_info.value)

	def test_define_relation_simple(self, clean_engine):
		"""Test defining a simple relation type"""
		engine = clean_engine

		# Define node types first
		engine.define_node("node Person")
		engine.define_node("node Company")

		engine.define_relation(
			"""
        relation WORKS_AT
        Person -> Company
        position: string
        since: date
        """
		)

		assert "WORKS_AT" in engine.relation_types
		rel_type = engine.relation_types["WORKS_AT"]
		assert rel_type.name == "WORKS_AT"
		assert rel_type.from_type == "Person"
		assert rel_type.to_type == "Company"
		assert len(rel_type.fields) == 2
		assert rel_type.fields[0].name == "position"
		assert rel_type.fields[1].name == "since"

	def test_define_relation_with_reverse(self, clean_engine):
		"""Test defining relation with reverse name"""
		engine = clean_engine

		engine.define_node("node Person")
		engine.define_node("node Company")

		engine.define_relation(
			"""
        relation WORKS_AT reverse EMPLOYS
        Person -> Company
        """
		)

		assert "WORKS_AT" in engine.relation_types
		assert "EMPLOYS" in engine.relation_types

		works_at = engine.relation_types["WORKS_AT"]
		employs = engine.relation_types["EMPLOYS"]

		assert works_at.reverse_name == "EMPLOYS"
		assert employs.reverse_name == "WORKS_AT"
		assert works_at.from_type == "Person"
		assert works_at.to_type == "Company"
		assert employs.from_type == "Company"
		assert employs.to_type == "Person"

	def test_define_relation_bidirectional(self, clean_engine):
		"""Test defining bidirectional relation"""
		engine = clean_engine

		engine.define_node("node Person")

		engine.define_relation(
			"""
        relation FRIENDS_WITH both
        Person - Person
        since: date
        """
		)

		rel_type = engine.relation_types["FRIENDS_WITH"]
		assert rel_type.is_bidirectional is True

	def test_define_relation_node_type_not_found(self, clean_engine):
		"""Test defining relation with non-existent node types"""
		engine = clean_engine

		with pytest.raises(NotFoundError) as exc_info:
			engine.define_relation(
				"""
            relation WORKS_AT
            Person -> Company
            """
			)

		assert "Node type" in str(exc_info.value)

class TestGraphiteEngineDataManipulation:
	"""Test GraphiteEngine data manipulation methods"""

	def test_create_node_simple(self, clean_engine):
		"""Test creating a node"""
		engine = clean_engine

		engine.define_node(
			"""
        node Person
        name: string
        age: int
        email: string
        """
		)

		node = engine.create_node("Person", "person1", "Alice", 30, "alice@email.com")

		assert node.id == "person1"
		assert node.type_name == "Person"
		assert node.values == {
			"name" : "Alice",
			"age"  : 30,
			"email": "alice@email.com"
		}
		assert "person1" in engine.nodes
		assert node in engine.node_by_type["Person"]

	def test_create_node_with_date(self, clean_engine):
		"""Test creating a node with date field"""
		engine = clean_engine

		engine.define_node(
			"""
        node Event
        title: string
        event_date: date
        """
		)

		node = engine.create_node("Event", "event1", "Conference", "2023-12-01")

		assert node.id == "event1"
		# Date should be converted to date object
		assert isinstance(node.values["event_date"], date)
		assert node.values["event_date"] == date(2023, 12, 1)

	def test_create_node_invalid_date(self, clean_engine):
		"""Test creating node with invalid date string"""
		engine = clean_engine

		engine.define_node(
			"""
        node Event
        title: string
        event_date: date
        """
		)

		with pytest.raises(FieldError):
			engine.create_node("Event", "event1", "Conference", "invalid-date")

	def test_create_node_wrong_property_count(self, clean_engine):
		"""Test creating node with wrong number of properties"""
		engine = clean_engine

		engine.define_node(
			"""
        node Person
        name: string
        age: int
        email: string
        """
		)

		with pytest.raises(InvalidPropertiesError) as exc_info:
			engine.create_node("Person", "person1", "Alice", 30)
		# Missing email

		assert "Expected 3 properties" in str(exc_info.value)

	def test_create_node_type_not_found(self, clean_engine):
		"""Test creating node of non-existent type"""
		engine = clean_engine

		with pytest.raises(NotFoundError) as exc_info:
			engine.create_node("NonExistent", "node1", "value")

		assert "Node type" in str(exc_info.value)

	def test_create_relation_simple(self, clean_engine):
		"""Test creating a relation"""
		engine = clean_engine

		# Setup
		engine.define_node("node Person\nname: string")
		engine.define_node("node Company\nname: string")
		engine.define_relation(
			"""
        relation WORKS_AT
        Person -> Company
        position: string
        since: date
        """
		)

		engine.create_node("Person", "person1", "Alice")
		engine.create_node("Company", "company1", "TechCorp")

		# Create relation
		relation = engine.create_relation(
			"person1", "company1", "WORKS_AT",
			"Engineer", "2021-01-01"
		)

		assert relation.type_name == "WORKS_AT"
		assert relation.from_node == "person1"
		assert relation.to_node == "company1"
		assert relation.values == {
			"position": "Engineer",
			"since"   : date(2021, 1, 1)
		}

		# Check indexes
		rel_id = id(relation)
		assert rel_id in engine.relations
		assert rel_id in engine.relations_by_type["WORKS_AT"]
		assert rel_id in engine.relations_by_from["person1"]
		assert rel_id in engine.relations_by_to["company1"]

	def test_create_relation_bidirectional(self, clean_engine):
		"""Test creating bidirectional relation"""
		engine = clean_engine

		engine.define_node("node Person\nname: string")
		engine.define_relation(
			"""
        relation FRIENDS_WITH both
        Person - Person
        since: date
        """
		)

		engine.create_node("Person", "person1", "Alice")
		engine.create_node("Person", "person2", "Bob")

		engine.create_relation(
			"person1", "person2", "FRIENDS_WITH",
			"2020-05-15"
		)

		# Should create two relations (forward and reverse)
		assert len(engine.relations) == 2
		assert len(engine.relations_by_type["FRIENDS_WITH"]) == 2
		assert len(engine.relations_by_from["person1"]) == 1
		assert len(engine.relations_by_from["person2"]) == 1
		assert len(engine.relations_by_to["person1"]) == 1
		assert len(engine.relations_by_to["person2"]) == 1

	def test_create_relation_node_not_found(self, clean_engine):
		"""Test creating relation with non-existent nodes"""
		engine = clean_engine

		engine.define_node("node Person\nname: string")
		engine.define_node("node Company")
		engine.define_relation("relation WORKS_AT\nPerson -> Company")

		engine.create_node("Person", "person1", "Alice")

		with pytest.raises(NotFoundError) as exc_info:
			engine.create_relation("person1", "non_existent", "WORKS_AT")

		assert "Node" in str(exc_info.value)
		assert "non_existent" in str(exc_info.value)

	def test_create_relation_type_not_found(self, clean_engine):
		"""Test creating relation of non-existent type"""
		engine = clean_engine

		engine.define_node("node Person\nname: string")
		engine.define_node("node Company\nname: string")

		engine.create_node("Person", "person1", "Alice")
		engine.create_node("Company", "company1", "TechCorp")

		with pytest.raises(NotFoundError) as exc_info:
			engine.create_relation("person1", "company1", "NonExistent")

		assert "Relation type" in str(exc_info.value)

class TestGraphiteEngineQueryMethods:
	"""Test GraphiteEngine query methods"""

	def test_get_node(self, populated_engine):
		"""Test getting node by ID"""
		engine = populated_engine

		node = engine.get_node("person1")
		assert node is not None
		assert node.id == "person1"
		assert node.values["name"] == "Alice"

		# Non-existent node
		with pytest.raises(NotFoundError):
			engine.get_node("non_existent")

	def test_get_nodes_of_type(self, populated_engine):
		"""Test getting all nodes of a type"""
		engine = populated_engine

		person_nodes = engine.get_nodes_of_type("Person")
		company_nodes = engine.get_nodes_of_type("Company")

		assert len(person_nodes) == 2
		assert len(company_nodes) == 1

		# Check node IDs
		person_ids = {node.id for node in person_nodes}
		assert person_ids == {"person1", "person2"}

	def test_get_relations_from(self, populated_engine):
		"""Test getting relations from a node"""
		engine = populated_engine

		# Get all relations from person1
		relations = engine.get_relations_from("person1")
		assert len(relations) == 2  # WORKS_AT and MANAGES

		# Get specific relation type
		works_at_relations = engine.get_relations_from("person1", "WORKS_AT")
		assert len(works_at_relations) == 1
		assert next(iter(works_at_relations)).type_name == "WORKS_AT"

		# Non-existent node
		with pytest.raises(NotFoundError):
			engine.get_relations_from("non_existent")

	def test_get_relations_to(self, populated_engine):
		"""Test getting relations to a node"""
		engine = populated_engine

		# Get all relations to company1
		relations = engine.get_relations_to("company1")
		assert len(relations) == 2  # Both persons work there

		# Get specific relation type
		works_at_relations = engine.get_relations_to("company1", "WORKS_AT")
		assert len(works_at_relations) == 2

		# Non-existent node returns empty list
		with pytest.raises(NotFoundError):
			engine.get_relations_to("non_existent")

	def test_clear_method(self, populated_engine):
		"""Test clearing all data"""
		engine = populated_engine

		assert len(engine.nodes) > 0
		assert len(engine.relations) > 0

		engine.clear()

		assert len(engine.nodes) == 0
		assert len(engine.relations) == 0
		assert len(engine.node_types) == 0
		assert len(engine.relation_types) == 0
		assert len(engine.node_by_type) == 0
		assert len(engine.relations_by_type) == 0

	def test_stats_method(self, populated_engine):
		"""Test getting database statistics"""
		engine = populated_engine

		stats = engine.stats()

		assert stats["node_types"] == 3
		assert stats["relation_types"] == 2
		assert stats["nodes"] == 4
		assert stats["relations"] == 3  # person1 has 2 relations, person2 has 1
