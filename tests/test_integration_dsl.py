"""
Integration tests for DSL parsing and loading
"""
from datetime import date

class TestDSLIntegration:
	"""Test DSL integration scenarios"""

	def test_load_complete_dsl(self, clean_engine):
		"""Test loading complete DSL with schema and data"""
		engine = clean_engine

		dsl = """
        # Node type definitions
        node Person
        name: string
        age: int
        email: string

        node Company
        name: string
        founded: date
        employees: int

        node Project
        title: string
        budget: float
        active: bool

        # Relation type definitions
        relation WORKS_AT
        Person -> Company
        position: string
        since: date

        relation MANAGES
        Person -> Project
        role: string

        relation FRIENDS_WITH both
        Person - Person
        since: date

        # Data instances
        Person, person1, "Alice", 30, "alice@email.com"
        Person, person2, "Bob", 25, "bob@email.com"
        Person, person3, "Charlie", 35, "charlie@email.com"

        Company, company1, "TechCorp", "2020-01-01", 500
        Company, company2, "StartupInc", "2022-03-15", 50

        Project, project1, "Alpha", 100000.50, true
        Project, project2, "Beta", 75000.00, false

        # Relation instances
        person1 -[WORKS_AT, "Engineer", "2021-03-15"]-> company1
        person2 -[WORKS_AT, "Manager", "2020-06-01"]-> company1
        person3 -[WORKS_AT, "CEO", "2022-01-01"]-> company2

        person1 -[MANAGES, "Lead"]-> project1
        person2 -[MANAGES, "Coordinator"]-> project2

        person2 -[FRIENDS_WITH, "2020-08-10"]- person3
        person1 -[FRIENDS_WITH, "2019-05-20"]- person2
        """

		engine.load_dsl(dsl)

		# Verify schema was loaded
		assert "Person" in engine.node_types
		assert "Company" in engine.node_types
		assert "Project" in engine.node_types
		assert "WORKS_AT" in engine.relation_types
		assert "MANAGES" in engine.relation_types
		assert "FRIENDS_WITH" in engine.relation_types

		# Verify data was loaded
		assert len(engine.nodes) == 7  # 3 persons + 2 companies + 2 projects
		# 3 WORKS_AT + 2 MANAGES + 2 FRIENDS_WITH (but bidirectional creates 2 each)
		assert len(engine.relations) == 9

		# Verify specific data
		alice = engine.get_node("person1")
		assert alice["name"] == "Alice"
		assert alice["age"] == 30

		# Verify relations
		alice_works_at = engine.get_relations_from("person1", "WORKS_AT")
		assert len(alice_works_at) == 1
		assert alice_works_at[0].to_node == "company1"
		assert alice_works_at[0]["position"] == "Engineer"
		assert isinstance(alice_works_at[0]["since"], date)

		# Verify bidirectional relations created both directions
		friendships = engine.get_relations_from("person1", "FRIENDS_WITH")
		assert len(friendships) == 1

		# Actually bidirectional creates reverse automatically, so there should be 2
		all_friendships = engine.relations_by_type["FRIENDS_WITH"]
		assert len(all_friendships) == 4  # 2 friendships × 2 directions

	def test_load_dsl_with_inheritance(self, clean_engine):
		"""Test loading DSL with inheritance"""
		engine = clean_engine

		dsl = """
        node Entity
        id: string
        created: date

        node User from Entity
        username: string
        password: string

        node Admin from User
        permissions: string

        Entity, ent1, "entity_1", "2023-01-01"
        User, user1, "user_1", "2023-02-01", "john", "pass123"
        Admin, admin1, "admin_1", "2023-03-01", "admin", "admin123", "all"
        """

		engine.load_dsl(dsl)

		# Verify inheritance hierarchy
		admin_type = engine.node_types["Admin"]
		assert admin_type.parent is not None
		assert admin_type.parent.name == "User"

		user_type = engine.node_types["User"]
		assert user_type.parent is not None
		assert user_type.parent.name == "Entity"

		# Verify nodes
		admin = engine.get_node("admin1")
		assert admin["id"] == "admin_1"
		assert admin["username"] == "admin"
		assert admin["permissions"] == "all"
		assert isinstance(admin["created"], date)

	def test_load_dsl_with_comments_and_whitespace(self, clean_engine):
		"""Test loading DSL with comments and extra whitespace"""
		engine = clean_engine

		dsl = """
        # This is a comment

        node Person
          # person's name
          name: string
          # person's age
          age: int 


        # Another comment
        node Company
        name: string
        founded: date


        Person, p1, "Alice", 30
        Person, p2, "Bob", 25

        Company, c1, "TechCorp", "2020-01-01"
        """

		engine.load_dsl(dsl)

		assert "Person" in engine.node_types
		assert "Company" in engine.node_types
		assert len(engine.nodes) == 3

	def test_load_dsl_multiline_definitions(self, clean_engine):
		"""Test loading DSL with multiline definitions"""
		engine = clean_engine

		dsl = """node Person
        name: string
        age: int
        email: string

        node Company
        name: string
        founded: date
        employees: int
        industry: string
        location: string

        relation WORKS_AT
        Person -> Company
        position: string
        department: string
        since: date
        salary: float

        Person, p1, "Alice", 30, "alice@email.com"
        Company, c1, "TechCorp", "2020-01-01", 500, "Technology", "SF"

        p1 -[WORKS_AT, "Engineer", "Engineering", "2021-03-15", 85000.50]-> c1
        """

		engine.load_dsl(dsl)

		# Verify all fields were parsed
		person_type = engine.node_types["Person"]
		assert len(person_type.fields) == 3

		company_type = engine.node_types["Company"]
		assert len(company_type.fields) == 5

		works_at_type = engine.relation_types["WORKS_AT"]
		assert len(works_at_type.fields) == 4

		# Verify relation
		relation = engine.get_relations_from("p1", "WORKS_AT")[0]
		assert relation["position"] == "Engineer"
		assert relation["department"] == "Engineering"
		assert relation["salary"] == 85000.50

	def test_parse_method_sugar(self, clean_engine):
		"""Test parse method as syntax sugar for load_dsl"""
		engine = clean_engine

		dsl = """
        node Person
        name: string
        age: int

        Person, p1, "Alice", 30
        Person, p2, "Bob", 25
        """

		engine.parse(dsl)  # Should be same as load_dsl

		assert "Person" in engine.node_types
		assert len(engine.nodes) == 2
