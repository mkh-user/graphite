"""
Tests for utility functions
"""
from src.graphite.utils import node, relation, engine, SecurityWarning

class TestUtils:
	"""Test utility functions"""

	def test_node_helper(self):
		"""Test node helper function"""
		result = node("Person", name="string", age="int", email="string")

		expected = """node Person
name: string
age: int
email: string"""

		assert result.strip() == expected

	def test_relation_helper_simple(self):
		"""Test relation helper function simple case"""
		result = relation("WORKS_AT", "Person", "Company")

		expected = """relation WORKS_AT
Person -> Company"""

		assert result.strip() == expected

	def test_relation_helper_with_fields(self):
		"""Test relation helper with fields"""
		result = relation(
			"WORKS_AT", "Person", "Company",
			fields={"position": "string", "since": "date"}
		)

		expected = """relation WORKS_AT
Person -> Company
position: string
since: date"""

		assert result.strip() == expected

	def test_relation_helper_bidirectional(self):
		"""Test relation helper with bidirectional"""
		result = relation("FRIENDS_WITH", "Person", "Person", both=True)

		expected = """relation FRIENDS_WITH both
Person - Person"""

		assert result.strip() == expected

	def test_relation_helper_with_reverse(self):
		"""Test relation helper with reverse"""
		result = relation("WORKS_AT", "Person", "Company", reverse="EMPLOYS")

		expected = """relation WORKS_AT reverse EMPLOYS
Person -> Company"""

		assert result.strip() == expected

	def test_engine_helper(self):
		"""Test engine helper function"""
		from src.graphite.engine import GraphiteEngine

		result = engine()

		assert isinstance(result, GraphiteEngine)

	def test_security_warning(self):
		"""Test SecurityWarning class"""
		warning = SecurityWarning("Test warning")

		assert isinstance(warning, Warning)
		assert "Test warning" in str(warning)
