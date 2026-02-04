"""
Configuration and fixtures for Graphite tests
"""
import sys
import os
sys.path.insert(0, os.path.abspath('..'))

import pytest
import tempfile
from src.graphite import GraphiteEngine

@pytest.fixture
def clean_engine():
	"""Create a fresh GraphiteEngine instance"""
	engine = GraphiteEngine()
	yield engine
	# Cleanup if needed

@pytest.fixture
def populated_engine():
	"""Create engine with sample data"""
	engine = GraphiteEngine()

	# Define node types
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
    employees: int
    """
	)

	engine.define_node(
		"""
    node Project
    title: string
    budget: float
    active: bool
    """
	)

	# Define relation types
	engine.define_relation(
		"""
    relation WORKS_AT
    Person -> Company
    position: string
    since: date
    """
	)

	engine.define_relation(
		"""
    relation MANAGES
    Person -> Project
    role: string
    """
	)

	# Create nodes
	engine.create_node("Person", "person1", "Alice", 30, "alice@email.com")
	engine.create_node("Person", "person2", "Bob", 25, "bob@email.com")
	engine.create_node("Company", "company1", "TechCorp", "2020-01-01", 500)
	engine.create_node("Project", "project1", "Alpha", 100000.50, True)

	# Create relations
	engine.create_relation("person1", "company1", "WORKS_AT", "Engineer", "2021-03-15")
	engine.create_relation("person2", "company1", "WORKS_AT", "Manager", "2020-06-01")
	engine.create_relation("person1", "project1", "MANAGES", "Lead")

	return engine

@pytest.fixture
def temp_json_file():
	"""Create a temporary JSON file for testing"""
	with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
		temp_path = f.name

	yield temp_path

	# Cleanup
	if os.path.exists(temp_path):
		os.unlink(temp_path)

@pytest.fixture
def engine_with_inheritance():
	"""Create engine with inheritance hierarchy"""
	engine = GraphiteEngine()

	engine.define_node(
		"""
    node Entity
    id: string
    created: date
    """
	)

	engine.define_node(
		"""
    node User from Entity
    username: string
    password: string
    active: bool
    """
	)

	engine.define_node(
		"""
    node Admin from User
    permissions: string
    """
	)

	engine.create_node("Entity", "ent1", "base_entity", "2023-01-01")
	engine.create_node("User", "user1", "user_entity", "2023-02-01", "john", "pass123", True)
	engine.create_node("Admin", "admin1", "admin_entity", "2023-03-01", "admin", "admin123", True, "all")

	return engine
