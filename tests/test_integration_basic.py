"""
Integration tests for basic Graphite functionality
"""
from datetime import date

class TestGraphiteBasicIntegration:
	"""Test basic integration scenarios"""

	def test_complete_workflow(self, clean_engine):
		"""Test complete CRUD workflow"""
		engine = clean_engine

		# 1. Define schema
		engine.define_node(
			"""
        node Person
        name: string
        age: int
        email: string
        """
		)

		engine.define_node(
			"""
        node Company
        name: string
        founded: date
        """
		)

		engine.define_relation(
			"""
        relation WORKS_AT
        Person -> Company
        position: string
        since: date
        """
		)

		# 2. Create data
		engine.create_node("Person", "p1", "Alice", 30, "alice@email.com")
		engine.create_node("Person", "p2", "Bob", 25, "bob@email.com")
		engine.create_node("Company", "c1", "TechCorp", "2020-01-01")

		engine.create_relation("p1", "c1", "WORKS_AT", "Engineer", "2021-03-15")
		engine.create_relation("p2", "c1", "WORKS_AT", "Manager", "2020-06-01")

		# 3. Query data
		# Get all people
		all_people = engine.get_nodes_of_type("Person")
		assert len(all_people) == 2

		# Get Alice's workplace
		alice_works = list(engine.get_relations_from("p1", "WORKS_AT"))
		assert len(alice_works) == 1
		assert alice_works[0].to_node == "c1"
		assert alice_works[0]["position"] == "Engineer"

		# Get company employees
		company_employees = engine.get_relations_to("c1", "WORKS_AT")
		assert len(company_employees) == 2

		# 4. Use query builder
		young_employees = (engine.query.Person
		                   .where("age < 30")
		                   .outgoing("WORKS_AT")
		                   .get())

		assert len(young_employees) == 1
		assert next(iter(young_employees)).id == "c1"

	def test_inheritance_workflow(self, engine_with_inheritance):
		"""Test inheritance workflow"""
		engine = engine_with_inheritance

		# Get all entities
		all_entities = engine.query.Entity.get()
		assert len(all_entities) == 3  # Entity + User + Admin

		# Get only users (including admins)
		users = engine.query.User.get()
		assert len(users) == 2  # User + Admin

		# Get only admins
		admins = engine.query.Admin.get()
		assert len(admins) == 1

		# Check inherited fields
		admin = engine.get_node("admin1")
		assert admin is not None
		# Should have fields from Entity, User, and Admin
		assert admin["id"] == "admin_entity"
		assert admin["username"] == "admin"
		assert admin["permissions"] == "all"

		# Check date field conversion
		assert isinstance(admin["created"], date)

	def test_bidirectional_relations(self, clean_engine):
		"""Test bidirectional relations workflow"""
		engine = clean_engine

		engine.define_node("node Person\nname: string")

		engine.define_relation(
			"""
        relation FRIENDS_WITH both
        Person - Person
        since: date
        """
		)

		engine.create_node("Person", "p1", "Alice")
		engine.create_node("Person", "p2", "Bob")
		engine.create_node("Person", "p3", "Charlie")

		# Create friendship between p1 and p2
		engine.create_relation("p1", "p2", "FRIENDS_WITH", "2020-01-01")

		# Should create two relations (bidirectional)
		assert len(engine.relations) == 2

		# Both should see each other as friends
		p1_friends = engine.get_relations_from("p1", "FRIENDS_WITH")
		p2_friends = engine.get_relations_from("p2", "FRIENDS_WITH")

		assert len(p1_friends) == 1
		assert len(p2_friends) == 1

		# Create another friendship
		engine.create_relation("p2", "p3", "FRIENDS_WITH", "2021-01-01")

		# Should add 2 more relations
		assert len(engine.relations) == 4

		# Bob should have 2 friends now
		bobs_friends = engine.get_relations_from("p2", "FRIENDS_WITH")
		assert len(bobs_friends) == 2

	def test_complex_query_chaining(self, populated_engine):
		"""Test complex query chaining"""
		engine = populated_engine

		# Find all people who work at companies founded before 2021
		# and manage projects with budget over 50000
		result = (engine.query.Person
		          .outgoing("WORKS_AT")
		          .where("founded < '2021-01-01'")
		          .incoming("WORKS_AT")
		          .outgoing("MANAGES")
		          .where("budget > 50000")
		          .incoming("MANAGES")
		          .order_by("age"))

		assert len(result) >= 1
		assert result[0]["name"] == "Alice"

	def test_edge_cases(self, clean_engine):
		"""Test various edge cases"""
		engine = clean_engine

		# Empty node type
		engine.define_node("node EmptyType")
		engine.create_node("EmptyType", "empty1")

		assert engine.get_node("empty1") is not None
		assert engine.get_node("empty1").values == {}

		# Node with all data types
		engine.define_node(
			"""
        node AllTypes
        str_field: string
        int_field: int
        float_field: float
        date_field: date
        bool_field: bool
        """
		)

		engine.create_node(
			"AllTypes", "all1",
			"text", 42, 3.14, "2023-01-01", True
		)

		node = engine.get_node("all1")
		assert node["str_field"] == "text"
		assert node["int_field"] == 42
		assert node["float_field"] == 3.14
		assert isinstance(node["date_field"], date)
		assert node["bool_field"] is True

		# Query with all operators
		result = engine.query.AllTypes.where('int_field > 40')
		assert len(result.nodes) == 1

		result = engine.query.AllTypes.where('float_field < 4.0')
		assert len(result.nodes) == 1

		result = engine.query.AllTypes.where('bool_field = true')
		assert len(result.nodes) == 1

		result = engine.query.AllTypes.where("str_field = 'text'")
		assert len(result.nodes) == 1
