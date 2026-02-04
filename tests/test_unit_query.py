"""
Unit tests for QueryBuilder and QueryResult
"""
import pytest
from src.graphite.exceptions import NotFoundError, ConditionError
from src.graphite.query import QueryResult

class TestQueryBuilder:
	"""Test QueryBuilder class"""

	def test_query_builder_getattr(self, populated_engine):
		"""Test accessing node types via QueryBuilder"""
		engine = populated_engine

		# Access node type as attribute
		person_query = engine.query.Person
		assert person_query is not None
		assert len(person_query.nodes) == 2

		# Check we got correct nodes
		node_ids = {node.id for node in person_query.nodes}
		assert node_ids == {"person1", "person2"}

	def test_query_builder_invalid_node_type(self, populated_engine):
		"""Test accessing non-existent node type via QueryBuilder"""
		engine = populated_engine

		with pytest.raises(NotFoundError) as exc_info:
			_ = engine.query.NonExistent

		assert "Node type" in str(exc_info.value)

class TestQueryResult: # pylint: disable=too-many-public-methods
	"""Test QueryResult class"""

	def test_query_result_creation(self, populated_engine):
		"""Test creating QueryResult"""
		engine = populated_engine

		nodes = engine.get_nodes_of_type("Person")
		result = engine.query.Person

		assert len(result.nodes) == len(nodes)
		assert result.engine == engine
		assert result.edges == []

	def test_where_lambda(self, populated_engine):
		"""Test where with lambda condition"""
		result = populated_engine.query.Person

		# Filter with lambda
		filtered = result.where(lambda n: n["age"] > 25)

		assert len(filtered.nodes) == 1
		assert filtered.nodes[0]["name"] == "Alice"

	def test_where_string_condition(self, populated_engine):
		"""Test where with string condition"""
		result = populated_engine.query.Person

		# Filter with string condition
		filtered = result.where("age > 25")

		assert len(filtered.nodes) == 1
		assert filtered.nodes[0]["name"] == "Alice"

	def test_where_string_equality(self, populated_engine):
		"""Test where with equality condition"""
		result = populated_engine.query.Person

		# Filter with equality
		filtered = result.where('name = "Alice"')

		assert len(filtered.nodes) == 1
		assert filtered.nodes[0]["name"] == "Alice"

		# Alternative equality syntax
		filtered2 = result.where('name == "Alice"')
		assert len(filtered2.nodes) == 1

	def test_where_string_inequality(self, populated_engine):
		"""Test where with inequality condition"""
		result = populated_engine.query.Person

		filtered = result.where('name != "Alice"')

		assert len(filtered.nodes) == 1
		assert filtered.nodes[0]["name"] == "Bob"

	def test_where_comparison_operators(self, populated_engine):
		"""Test where with various comparison operators"""
		result = populated_engine.query.Person

		# Greater than or equal
		filtered_ge = result.where("age >= 30")
		assert len(filtered_ge.nodes) == 1

		# Less than
		filtered_lt = result.where("age < 30")
		assert len(filtered_lt.nodes) == 1

		# Less than or equal
		filtered_le = result.where("age <= 25")
		assert len(filtered_le.nodes) == 1

	def test_where_invalid_condition(self, populated_engine):
		"""Test where with invalid condition string"""
		result = populated_engine.query.Person

		with pytest.raises(ConditionError):
			result.where("invalid condition format")

	def test_where_nonexistent_field(self, populated_engine):
		"""Test where condition with non-existent field"""
		result = populated_engine.query.Person

		# Should return empty result, not raise error
		filtered = result.where("nonexistent = 10")
		assert len(filtered.nodes) == 0

	def test_traverse_outgoing(self, populated_engine):
		"""Test traversing outgoing relations"""
		result = populated_engine.query.Person.where('name = "Alice"')

		# Traverse WORKS_AT relation
		works_at_result = result.traverse("WORKS_AT", "outgoing")

		assert len(works_at_result.nodes) == 1
		assert works_at_result.nodes[0].type_name == "Company"
		assert works_at_result.nodes[0]["name"] == "TechCorp"

		# Check edges were captured
		assert len(works_at_result.edges) == 1
		assert works_at_result.edges[0].type_name == "WORKS_AT"

	def test_outgoing_method(self, populated_engine):
		"""Test outgoing shortcut method"""
		result = populated_engine.query.Person.where('name = "Alice"')

		works_at_result = result.outgoing("WORKS_AT")

		assert len(works_at_result.nodes) == 1
		assert works_at_result.nodes[0].type_name == "Company"

	def test_incoming_method(self, populated_engine):
		"""Test incoming shortcut method"""
		# Get company and see who works there
		result = populated_engine.query.Company

		employees_result = result.incoming("WORKS_AT")

		assert len(employees_result.nodes) == 2
		assert all(node.type_name == "Person" for node in employees_result.nodes)

	def test_both_method(self, populated_engine):
		"""Test both shortcut method"""
		# For bidirectional relations, both would return all connected nodes
		# Since we don't have bidirectional in sample, test with incoming+outgoing
		result = populated_engine.query.Person.where('name = "Alice"')

		all_relations = result.both("WORKS_AT")
		# Alice has outgoing WORKS_AT, no incoming WORKS_AT
		assert len(all_relations.nodes) == 1

	def test_limit(self, populated_engine):
		"""Test limiting results"""
		result = populated_engine.query.Person

		limited = result.limit(1)

		assert len(limited.nodes) == 1
		# Should preserve original order (first created)
		assert limited.nodes[0]["name"] == "Alice"

	def test_distinct(self, populated_engine):
		"""Test getting distinct nodes"""
		# Create duplicate references
		engine = populated_engine

		# Get Alice through multiple paths
		alice = engine.get_node("person1")
		result = engine.query.Person.where('name = "Alice"')

		# Manually create duplicate nodes in result

		duplicate_result = QueryResult(engine, [alice, alice, alice], [])

		distinct_result = duplicate_result.distinct()

		assert len(result.nodes) == 1
		assert result.nodes[0]["name"] == "Alice"
		assert len(distinct_result.nodes) == 1
		assert distinct_result.nodes[0]["name"] == "Alice"

	def test_order_by_ascending(self, populated_engine):
		"""Test ordering results ascending"""
		result = populated_engine.query.Person

		ordered = result.order_by("age")

		assert len(ordered.nodes) == 2
		# Bob (25) should come before Alice (30)
		assert ordered.nodes[0]["name"] == "Bob"
		assert ordered.nodes[1]["name"] == "Alice"

	def test_order_by_descending(self, populated_engine):
		"""Test ordering results descending"""
		result = populated_engine.query.Person

		ordered = result.order_by("age", descending=True)

		assert len(ordered.nodes) == 2
		# Alice (30) should come before Bob (25)
		assert ordered.nodes[0]["name"] == "Alice"
		assert ordered.nodes[1]["name"] == "Bob"

	def test_order_by_none_values(self, clean_engine):
		"""Test ordering with None values"""
		engine = clean_engine

		engine.define_node(
			"""
        node Item
        name: string
        priority: int
        """
		)

		engine.create_node("Item", "item1", "A", 2)
		engine.create_node("Item", "item2", "B", None)
		engine.create_node("Item", "item3", "C", 1)

		result = engine.query.Item.order_by("priority")

		# Items with None should come last
		assert result.nodes[0]["name"] == "C"
		assert result.nodes[1]["name"] == "A"
		assert result.nodes[2]["name"] == "B"

	def test_count(self, populated_engine):
		"""Test counting results"""
		result = populated_engine.query.Person

		count = result.count()

		assert count == 2

	def test_get(self, populated_engine):
		"""Test getting all nodes"""
		result = populated_engine.query.Person

		nodes = result.get()

		assert len(nodes) == 2
		assert all(node.type_name == "Person" for node in nodes)

	def test_first(self, populated_engine):
		"""Test getting first node"""
		result = populated_engine.query.Person

		first_node = result.first()

		assert first_node is not None
		assert first_node["name"] == "Alice"

		# Empty result
		empty_result = populated_engine.query.Person.where("age > 100")
		assert empty_result.first() is None

	def test_ids(self, populated_engine):
		"""Test getting node IDs"""
		result = populated_engine.query.Person

		ids = result.ids()

		assert len(ids) == 2
		assert "person1" in ids
		assert "person2" in ids

	def test_chained_queries(self, populated_engine):
		"""Test chaining multiple query operations"""
		# Complex query: Get young employees who work at companies
		result = (populated_engine.query.Person
		          .where("age < 30")
		          .outgoing("WORKS_AT")
		          .order_by("founded"))

		assert len(result.nodes) == 1
		assert result.nodes[0].type_name == "Company"

		# Even more complex
		complex_result = (populated_engine.query.Person
		                  .where('name = "Alice"')
		                  .outgoing("WORKS_AT")
		                  .incoming("WORKS_AT")
		                  .where("age > 20")
		                  .order_by("age", descending=True)
		                  .limit(2))

		# This should get all people who work at the same company as Alice
		assert len(complex_result.nodes) == 2
		assert all(node.type_name == "Person" for node in complex_result.nodes)
