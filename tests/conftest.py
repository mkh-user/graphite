"""
Configuration and fixtures for Graphite tests
"""
import os
import sys
import tempfile
import types

from pytest import fixture

try:
	sys.path.insert(0, os.path.abspath('..'))
	from src.graphite import GraphiteEngine, Node
except ImportError:
	from graphite import GraphiteEngine, Node

@fixture
def clean_engine() -> GraphiteEngine:
	"""Create a fresh GraphiteEngine instance"""
	engine = GraphiteEngine()
	return engine

@fixture
def simple_engine() -> GraphiteEngine:
	"""Create a simple GraphiteEngine instance with schema"""
	engine = GraphiteEngine()

	engine.parse(
		"""
			node Person
			name: string
			
			relation KNOWS
			Person -> Person
			"""
	)

	return engine

@fixture
def populated_engine() -> GraphiteEngine:
	"""Create engine with sample data"""
	engine = GraphiteEngine()

	engine.parse(
		"""
			# Define node types
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
		
			# Define relation types
			relation WORKS_AT
			Person -> Company
			position: string
			since: date
			
			relation MANAGES
			Person -> Project
			role: string
			
			# Create nodes
			Person, person1, Alice, 30, alice@email.com
			Person, person2, Bob, 25, bob@email.com
			Company, company1, TechCorp, 2020-1-1, 500
			Project, project1, Alpha, 100000.50, true
			
			# Create relations
			person1 -[WORKS_AT, Engineer, 2021-03-15]-> company1
			person2 -[WORKS_AT, Manager, 2020-06-01]-> company1
			person1 -[MANAGES, Lead]-> project1
			"""
	)

	return engine

@fixture
def temp_json_file() -> types.GeneratorType:
	"""Create a temporary JSON file for testing"""
	with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
		temp_path = f.name

	yield temp_path

	# Cleanup
	if os.path.exists(temp_path):
		os.unlink(temp_path)

@fixture
def engine_with_inheritance():
	"""Create engine with inheritance hierarchy"""
	engine = GraphiteEngine()

	engine.parse(
		"""
			node Entity
			id: string
			created: date
			
			node User from Entity
			username: string
			password: string
			active: bool
			
			node Admin from User
			permissions: string
			"""
	)

	engine.create_node("Entity", "ent1", "base_entity", "2023-01-01")
	engine.create_node(
		"User", "user1", "user_entity", "2023-02-01",
		"john", "pass123", True
	)
	engine.create_node(
		"Admin", "admin1", "admin_entity", "2023-03-01",
		"admin", "admin123", True, "all"
	)

	return engine

@fixture
def alice_node():
	"""Returns a node with Person type, person1 ID, name = Alice, age = 30, without type
	reference."""
	return Node(
		type_name="Person",
		id="person1",
		values={ "name": "Alice", "age": 30 },
		type_ref=None
	)
