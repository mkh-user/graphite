"""
Unit tests for graph algorithms in algorithms.py
"""
from datetime import date

import pytest

from src.graphite import Direction
from src.graphite.exceptions import NotFoundError

class TestBFS:
	"""Test BFS algorithm implementation"""

	def test_bfs_simple_path(self, populated_engine):
		"""Test BFS finding a simple path"""
		engine = populated_engine

		# BFS from person1 to company1
		result = engine.bfs(
			start="person1",
			end="company1",
			direction=Direction.OUTGOING,
			relation_type="WORKS_AT"
		)

		assert len(result) == 1
		node_id, depth, path = result[0]
		assert node_id == "company1"
		assert depth == 1
		assert len(path) == 1
		assert path[0][0].type_name == "WORKS_AT"
		assert path[0][1].id == "company1"

	def test_bfs_multiple_paths(self, simple_engine):
		"""Test BFS finding multiple paths"""
		engine = simple_engine

		engine.create_node("Person", "p1", "Alice")
		engine.create_node("Person", "p2", "Bob")
		engine.create_node("Person", "p3", "Charlie")
		engine.create_node("Person", "p4", "David")

		engine.create_relation("p1", "p3", "KNOWS")
		engine.create_relation("p1", "p2", "KNOWS")
		engine.create_relation("p2", "p3", "KNOWS")
		engine.create_relation("p2", "p4", "KNOWS")
		engine.create_relation("p4", "p3", "KNOWS")

		# BFS from p1 to p3
		result = engine.bfs(
			start="p1",
			end="p3",
			direction=Direction.OUTGOING,
			stop_at_first=False
		)

		# Should find 3 paths: p1 -> p3, p1 -> p2 -> p3, p1 -> p2 -> p4 -> p3
		assert len(result) == 3

	def test_bfs_no_path(self, populated_engine):
		"""Test BFS when no path exists"""
		engine = populated_engine

		# Create isolated node
		engine.define_node("node Isolated\nname: string")
		engine.create_node("Isolated", "iso1", "Isolated")

		result = engine.bfs(
			start="person1",
			end="iso1",
			direction=Direction.OUTGOING,
			max_depth=5
		)

		assert len(result) == 0

	def test_bfs_max_depth(self, simple_engine):
		"""Test BFS with max depth limit"""
		engine = simple_engine

		engine.create_node("Person", "p1", "Alice")
		engine.create_node("Person", "p2", "Bob")
		engine.create_node("Person", "p3", "Charlie")

		engine.create_relation("p1", "p2", "KNOWS")
		engine.create_relation("p2", "p3", "KNOWS")

		result = engine.bfs(
			start="p1",
			end="p3",
			max_depth=1,
		)

		assert len(result) == 0

		result = engine.bfs(
			start="p1",
			end="p3",
			max_depth=2,
		)

		assert len(result) == 1

	def test_bfs_include_start(self, populated_engine):
		"""Test BFS with include_start=True"""
		engine = populated_engine

		result = engine.bfs(
			start="person1",
			end=None,
			direction=Direction.OUTGOING,
			include_start=True,
			max_depth=0
		)

		assert len(result) == 1
		assert result[0][0] == "person1"
		assert result[0][1] == 0
		assert result[0][2] == []

	def test_bfs_with_callable_end(self, populated_engine):
		"""Test BFS with callable end condition"""
		engine = populated_engine

		# Find any node with name "TechCorp"
		def is_tech_corp(path):
			return path and path[-1][1].get("name") == "TechCorp"

		result = engine.bfs(
			start="person1",
			end=is_tech_corp,
			direction=Direction.OUTGOING,
			stop_at_first=True
		)

		assert len(result) == 1
		assert result[0][0] == "company1"
		assert result[0][1] == 1

	def test_bfs_incoming_direction(self, populated_engine):
		"""Test BFS with incoming direction"""
		engine = populated_engine

		# Find people who work at company1 (incoming to company1)
		result = engine.bfs(
			start="company1",
			end=None,
			direction=Direction.INCOMING,
			relation_type="WORKS_AT",
			max_depth=1
		)

		assert len(result) == 2
		# Both person1 and person2 work at company1
		node_ids = { r[0] for r in result }
		assert node_ids == { "person1", "person2" }

	def test_bfs_bidirectional_direction(self, simple_engine):
		"""Test BFS with both directions"""
		engine = simple_engine

		engine.create_node("Person", "p1", "Alice")
		engine.create_node("Person", "p2", "Bob")
		engine.create_node("Person", "p3", "Charlie")

		engine.create_relation("p1", "p2", "KNOWS")
		engine.create_relation("p3", "p1", "KNOWS")

		# BFS from p1 in both directions should find both p2 and p3
		result = engine.bfs(
			start="p1",
			end=None,
			direction=Direction.BOTH,
			max_depth=1
		)

		node_ids = { r[0] for r in result }
		assert node_ids == { "p2", "p3" }

	def test_bfs_direction_switch(self, simple_engine):
		"""Test BFS with direction switch"""
		engine = simple_engine

		engine.create_node("Person", "p1", "Alice")
		engine.create_node("Person", "p2", "Bob")
		engine.create_node("Person", "p3", "Charlie")

		engine.create_relation("p1", "p2", "KNOWS")
		engine.create_relation("p3", "p2", "KNOWS")

		# BFS with direction switch should find:
		# p1 -------> p3
		# p1 -> p2 <- p3
		result = engine.bfs(
			start="p1",
			end="p3",
			direction=Direction.BOTH,
			allow_direction_switch=True
		)

		assert len(result) == 1
		assert result[0][0] == "p3"

	def test_bfs_visited_set(self, populated_engine):
		"""Test BFS with visited set"""
		engine = populated_engine

		# Ignore company1
		result = engine.bfs(
			start="person1",
			end=None,
			direction=Direction.OUTGOING,
			relation_type="WORKS_AT",
			visited={ "company1" },
			max_depth=1
		)

		# person1 should not find company1 as it's in visited
		assert len(result) == 0

	def test_bfs_relation_type_filter(self, populated_engine):
		"""Test BFS with relation type filter"""
		engine = populated_engine

		# Only traverse WORKS_AT relations
		result = engine.bfs(
			start="person1",
			end=None,
			direction=Direction.OUTGOING,
			relation_type="WORKS_AT",
			max_depth=1
		)

		assert len(result) == 1
		assert result[0][0] == "company1"

		# Only traverse MANAGES relations
		result = engine.bfs(
			start="person1",
			end=None,
			direction=Direction.OUTGOING,
			relation_type="MANAGES",
			max_depth=1
		)

		assert len(result) == 1
		assert result[0][0] == "project1"

	def test_bfs_max_results(self, populated_engine):
		"""Test BFS with max_results limit"""
		engine = populated_engine

		# Add more people to get more results
		engine.create_node("Person", "person3", "Charlie", 40, "charlie@email.com")
		engine.create_relation("person3", "company1", "WORKS_AT", "Intern", date(2022, 1, 1))

		result = engine.bfs(
			start="company1",
			end=None,
			direction=Direction.INCOMING,
			relation_type="WORKS_AT",
			max_depth=1,
			max_results=1
		)

		assert len(result) == 1

	def test_bfs_stop_at_first_no_direction_switch(self, simple_engine):
		"""Test BFS with stop at first in Direction.BOTH without direction switch"""
		engine = simple_engine

		engine.create_node("Person", "p1", "Alice")
		engine.create_node("Person", "p2", "Bob")

		engine.create_relation("p1", "p2", "KNOWS")
		# Second relation to add in reverse direction to produce two results in BFS
		engine.create_relation("p2", "p1", "KNOWS")

		result = engine.bfs(
			start="p1",
			end="p2",
			direction=Direction.BOTH,
			stop_at_first=True,
			allow_direction_switch=False
		)

		assert len(result) == 1


class TestShortestPath:
	"""Test shortest_path algorithm"""

	def test_shortest_path_direct(self, populated_engine):
		"""Test shortest path between directly connected nodes"""
		engine = populated_engine

		result = engine.shortest_path(
			from_node="person1",
			to_end="company1",
			direction=Direction.OUTGOING,
			relation_type="WORKS_AT"
		)

		assert result is not None
		node_id, depth, path = result
		assert node_id == "company1"
		assert depth == 1
		assert len(path) == 1

	def test_shortest_path_indirect(self, clean_engine):
		"""Test shortest path between indirectly connected nodes"""
		engine = clean_engine

		engine.define_node("node Person\nname: string")
		engine.define_node("node Company\nname: string")
		engine.define_relation("relation WORKS_AT\nPerson -> Company")
		engine.define_relation("relation MANAGED_BY\nPerson -> Person")

		engine.create_node("Person", "p1", "Alice")
		engine.create_node("Person", "p2", "Bob")
		engine.create_node("Person", "p3", "Charlie")
		engine.create_node("Company", "c1", "TechCorp")

		engine.create_relation("p1", "p2", "MANAGED_BY")
		engine.create_relation("p2", "c1", "WORKS_AT")

		result = engine.shortest_path(
			from_node="p1",
			to_end="c1",
			direction=Direction.OUTGOING
		)

		assert result is not None
		node_id, depth, path = result
		assert node_id == "c1"
		assert depth == 2
		assert len(path) == 2
		assert path[0][0].type_name == "MANAGED_BY"
		assert path[1][0].type_name == "WORKS_AT"

	def test_shortest_path_no_path(self, populated_engine):
		"""Test shortest path when no path exists"""
		engine = populated_engine

		# Create isolated node
		engine.define_node("node Isolated\nname: string")
		engine.create_node("Isolated", "iso1", "Isolated")

		result = engine.shortest_path(
			from_node="person1",
			to_end="iso1",
			direction=Direction.OUTGOING,
			max_depth=5
		)

		assert result is None

	def test_shortest_path_with_callable_end(self, populated_engine):
		"""Test shortest path with callable end condition"""
		engine = populated_engine

		def is_tech_corp(_path):
			return _path and _path[-1][1].get("name") == "TechCorp"

		result = engine.shortest_path(
			from_node="person1",
			to_end=is_tech_corp,
			direction=Direction.OUTGOING
		)

		assert result is not None
		node_id, depth, _ = result
		assert node_id == "company1"
		assert depth == 1

	def test_shortest_path_weighted_not_implemented(self, populated_engine):
		"""Test weighted the shortest path raises NotImplementedError"""
		engine = populated_engine

		with pytest.raises(NotImplementedError):
			engine.shortest_path(
				from_node="person1",
				to_end="company1",
				weight="some_weight"
			)


class TestAllShortestPaths:
	"""Test all_shortest_paths algorithm"""

	def test_all_shortest_paths_single(self, populated_engine):
		"""Test all shortest paths when there is only one"""
		engine = populated_engine

		result = engine.all_shortest_paths(
			from_node="person1",
			to_end="company1",
			direction=Direction.OUTGOING,
			relation_type="WORKS_AT"
		)

		assert len(result) == 1
		assert result[0][0] == "company1"
		assert result[0][1] == 1

	def test_all_shortest_paths_multiple(self, clean_engine):
		"""Test all shortest paths when there are multiple equal-length paths"""
		engine = clean_engine

		engine.define_node("node Person\nname: string")
		engine.define_node("node Company\nname: string")
		engine.define_relation(
			"""
			relation WORKS_AT
			Person -> Company
			"""
		)
		engine.define_relation(
			"""
			relation CONNECTS
			Person -> Person
			"""
		)

		engine.create_node("Person", "p1", "Alice")
		engine.create_node("Person", "p2", "Bob")
		engine.create_node("Person", "p3", "Charlie")
		engine.create_node("Company", "c1", "TechCorp")

		# Two paths from p1 to c1: p1->p2->c1 and p1->p3->c1
		engine.create_relation("p1", "p2", "CONNECTS")
		engine.create_relation("p2", "c1", "WORKS_AT")
		engine.create_relation("p1", "p3", "CONNECTS")
		engine.create_relation("p3", "c1", "WORKS_AT")

		result = engine.all_shortest_paths(
			from_node="p1",
			to_end="c1",
			direction=Direction.OUTGOING
		)

		assert len(result) == 2
		assert result[0][1] == 2
		assert result[1][1] == 2

	def test_all_shortest_paths_no_path(self, populated_engine):
		"""Test all shortest paths when no path exists"""
		engine = populated_engine

		engine.define_node("node Isolated\nname: string")
		engine.create_node("Isolated", "iso1", "Isolated")

		result = engine.all_shortest_paths(
			from_node="person1",
			to_end="iso1",
			direction=Direction.OUTGOING,
			max_depth=5
		)

		assert len(result) == 0

	def test_all_shortest_paths_weighted_not_implemented(self, populated_engine):
		"""Test weighted all_shortest_paths raises NotImplementedError"""
		engine = populated_engine

		with pytest.raises(NotImplementedError):
			engine.all_shortest_paths(
				from_node="person1",
				to_end="company1",
				weight="some_weight"
			)


class TestConnectedComponents:
	"""Test connected_components algorithm"""

	def test_connected_components_all_nodes(self, populated_engine):
		"""Test connected components on all nodes"""
		engine = populated_engine

		# All nodes should be in one component (person1, person2, company1, project1)
		components = engine.connected_components()

		# Should have one component
		assert len(components) == 1
		# The main component should have 4 nodes
		assert len(components[0]) == 4

	def test_connected_components_specific_nodes(self, simple_engine):
		"""Test connected components on specific nodes"""
		engine = simple_engine

		engine.create_node("Person", "p1", "Alice")
		engine.create_node("Person", "p2", "Bob")
		engine.create_node("Person", "p3", "Charlie")
		engine.create_node("Person", "p4", "David")

		# p1 connected to p2, p3 connected to p4 (separate components)
		engine.create_relation("p1", "p2", "KNOWS")
		engine.create_relation("p3", "p4", "KNOWS")

		components = engine.connected_components(
			nodes={ "p1", "p3" },
			return_all_nodes=True
		)

		assert len(components) == 2
		# Find the component containing p1
		p1_component = next(c for c in components if "p1" in c)
		assert p1_component == { "p1", "p2" }
		# Find the component containing p3
		p3_component = next(c for c in components if "p3" in c)
		assert p3_component == { "p3", "p4" }

	def test_connected_components_single_node(self, simple_engine):
		"""Test connected components on single node"""
		engine = simple_engine

		engine.create_node("Person", "p1", "Alice")
		engine.create_node("Person", "p2", "Bob")
		engine.create_node("Person", "p3", "Charlie")
		engine.create_node("Person", "p4", "David")

		# p1 connected to p2, p3 connected to p4 (separate components)
		engine.create_relation("p1", "p2", "KNOWS")
		engine.create_relation("p3", "p4", "KNOWS")

		components = engine.connected_components(
			nodes="p1",
			return_all_nodes=True
		)

		assert len(components) == 1
		# Find the component containing p1
		assert components[0] == { "p1", "p2" }

	def test_connected_components_invalid_node(self, simple_engine):
		"""Test connected components on an invalid node"""
		engine = simple_engine

		engine.create_node("Person", "p1", "Alice")
		engine.create_node("Person", "p2", "Bob")
		engine.create_node("Person", "p3", "Charlie")
		engine.create_node("Person", "p4", "David")

		# p1 connected to p2, p3 connected to p4 (separate components)
		engine.create_relation("p1", "p2", "KNOWS")
		engine.create_relation("p3", "p4", "KNOWS")

		with pytest.raises(NotFoundError):
			engine.connected_components(
				nodes={ "p5" },
				return_all_nodes=True
			)

	def test_connected_components_isolated_nodes(self, populated_engine):
		"""Test connected components with isolated nodes"""
		engine = populated_engine

		# Add isolated nodes
		engine.define_node("node Isolated\nname: string")
		engine.create_node("Isolated", "iso1", "Isolated")
		engine.create_node("Isolated", "iso2", "Isolated")

		components = engine.connected_components(
			nodes={ "person1", "iso1", "iso2" },
			return_all_nodes=True
		)

		# Should have 3 components (or more, depending on existing connections)
		# The isolated nodes should each be in their own component
		iso_components = [c for c in components if len(c) == 1 and "iso" in next(iter(c))]
		assert len(iso_components) == 2

	def test_connected_components_ignore_nodes(self, populated_engine):
		"""Test connected components with ignore_nodes"""
		engine = populated_engine

		components = engine.connected_components(
			nodes=None,
			return_all_nodes=True,
			ignore_nodes={ "person1" }
		)

		# person1 should not appear in any component
		for component in components:
			assert "person1" not in component

	def test_connected_components_return_all_nodes_false(self, simple_engine):
		"""Test connected components with return_all_nodes=False"""
		engine = simple_engine

		engine.create_node("Person", "p1", "Alice")
		engine.create_node("Person", "p2", "Bob")
		engine.create_node("Person", "p3", "Charlie")

		engine.create_relation("p1", "p2", "KNOWS")
		# p3 is isolated

		components = engine.connected_components(
			nodes={ "p1", "p3" },
			return_all_nodes=False
		)

		# Should only return the specified nodes, not the connected ones
		assert len(components) == 2
		# p1's component should only include p1 (not p2)
		p1_component = next(c for c in components if "p1" in c)
		assert p1_component == { "p1" }
		p3_component = next(c for c in components if "p3" in c)
		assert p3_component == { "p3" }

	def test_connected_components_visited_coverage(self, simple_engine):
		"""Test connected components visited feature"""
		engine = simple_engine

		engine.parse(
			"""
			Person, p1, Person1
			Person, p2, Person2
			Person, p3, Person3
			Person, p4, Person4
			"""
		)

		engine.parse(
			"""
			p1 -[KNOWS]-> p2
			p1 -[KNOWS]-> p3
			p1 -[KNOWS]-> p4
			"""
		)

		result = engine.connected_components(
			None,
			True,
		)

		assert len(result) == 1



class TestNeighborhood:
	"""Test neighborhood algorithm"""

	def test_neighborhood_depth_1(self, populated_engine):
		"""Test neighborhood with depth 1"""
		engine = populated_engine

		nodes, _ = engine.neighborhood(
			start="person1",
			max_distance=1,
			direction=Direction.OUTGOING
		)

		# Should include person1 and all direct neighbors
		node_ids = { n.id for n, _ in nodes }
		assert "person1" in node_ids
		assert "company1" in node_ids
		assert "project1" in node_ids

	def test_neighborhood_depth_2(self, clean_engine):
		"""Test neighborhood with depth 2"""
		engine = clean_engine

		engine.define_node("node Person\nname: string")
		engine.define_node("node Company\nname: string")
		engine.define_relation(
			"""
			relation WORKS_AT
			Person -> Company
			"""
		)
		engine.define_relation(
			"""
			relation MANAGES
			Person -> Person
			"""
		)

		engine.create_node("Person", "p1", "Alice")
		engine.create_node("Person", "p2", "Bob")
		engine.create_node("Company", "c1", "TechCorp")

		engine.create_relation("p1", "p2", "MANAGES")
		engine.create_relation("p2", "c1", "WORKS_AT")

		nodes, _ = engine.neighborhood(
			start="p1",
			max_distance=2,
			direction=Direction.OUTGOING
		)

		node_ids = { n.id for n, _ in nodes }
		assert "p1" in node_ids
		assert "p2" in node_ids
		assert "c1" in node_ids

		# Check distances
		p1_distance = next(d for n, d in nodes if n.id == "p1")
		assert p1_distance == 0
		p2_distance = next(d for n, d in nodes if n.id == "p2")
		assert p2_distance == 1
		c1_distance = next(d for n, d in nodes if n.id == "c1")
		assert c1_distance == 2

	def test_neighborhood_with_filter(self, populated_engine):
		"""Test neighborhood with filter method"""
		engine = populated_engine

		# Only include paths that end with company nodes
		def filter_company(path):
			return path and path[-1][1].type_name == "Company"

		nodes, _ = engine.neighborhood(
			start="person1",
			max_distance=2,
			filter_method=filter_company,
			direction=Direction.OUTGOING
		)

		node_ids = { n.id for n, _ in nodes }
		# Should include person1 and company1, but not project1
		assert "person1" in node_ids
		assert "company1" in node_ids
		assert "project1" not in node_ids

	def test_neighborhood_max_results(self, populated_engine):
		"""Test neighborhood with max_results"""
		engine = populated_engine

		# Create more nodes to exceed max_results
		engine.create_node("Person", "person3", "Charlie", 40, "charlie@email.com")
		engine.create_relation("person3", "company1", "WORKS_AT", "Intern", date(2022, 1, 1))

		nodes, _ = engine.neighborhood(
			start="company1",
			max_distance=1,
			direction=Direction.INCOMING,
			max_results=1
		)

		# Only 1 result (plus start node)
		assert len(nodes) <= 2  # start + 1 result

	def test_neighborhood_incoming_direction(self, populated_engine):
		"""Test neighborhood with incoming direction"""
		engine = populated_engine

		nodes, _ = engine.neighborhood(
			start="company1",
			max_distance=1,
			direction=Direction.INCOMING,
			relation_type="WORKS_AT"
		)

		node_ids = { n.id for n, _ in nodes }
		assert "company1" in node_ids
		assert "person1" in node_ids
		assert "person2" in node_ids

	def test_neighborhood_ignore_nodes(self, populated_engine):
		"""Test neighborhood with ignore_nodes"""
		engine = populated_engine

		nodes, _ = engine.neighborhood(
			start="person1",
			max_distance=1,
			direction=Direction.OUTGOING,
			ignore_nodes={ "company1" }
		)

		node_ids = { n.id for n, _ in nodes }
		# company1 should be ignored
		assert "company1" not in node_ids

	def test_neighborhood_duplicates(self, simple_engine):
		"""Test neighborhood with duplicates"""
		engine = simple_engine

		engine.create_node("Person", "p1", "Alice")
		engine.create_node("Person", "p2", "Bob")
		engine.create_node("Person", "p3", "Charlie")
		engine.create_node("Person", "p4", "David")

		engine.create_relation("p1", "p2", "KNOWS")
		engine.create_relation("p2", "p1", "KNOWS")
		engine.create_relation("p3", "p1", "KNOWS")
		engine.create_relation("p2", "p3", "KNOWS")

		# Should find:
		# p1 in 1 path
		# p2 in 2 path
		# p3 in 2 path
		nodes, relations = engine.neighborhood(
			start="p1",
			direction=Direction.BOTH  # Catch reverses
		)

		assert len(nodes) == 3  # p1, p2, p3
		assert len(relations) == 4  # All relations


class TestAlgorithmEdgeCases:
	"""Test edge cases for algorithms"""

	def test_bfs_with_nonexistent_start(self, populated_engine):
		"""Test BFS with non-existent start node"""
		engine = populated_engine

		with pytest.raises(NotFoundError):
			engine.bfs(
				start="nonexistent",
				end=None
			)

	def test_bfs_with_nonexistent_end(self, populated_engine):
		"""Test BFS with non-existent end node"""
		engine = populated_engine

		result = engine.bfs(
			start="person1",
			end="nonexistent"
		)

		assert len(result) == 0

	def test_bfs_cycle_detection(self, simple_engine):
		"""Test BFS handles cycles correctly"""
		engine = simple_engine

		engine.create_node("Person", "p1", "Alice")
		engine.create_node("Person", "p2", "Bob")
		engine.create_node("Person", "p3", "Charlie")

		# Create a cycle: p1 -> p2 -> p3 -> p1
		engine.create_relation("p1", "p2", "KNOWS")
		engine.create_relation("p2", "p3", "KNOWS")
		engine.create_relation("p3", "p1", "KNOWS")

		# BFS should not get stuck in infinite loop
		result = engine.bfs(
			start="p1",
			end=None,
			direction=Direction.OUTGOING,
			max_depth=5
		)

		# Should find all nodes
		node_ids = { r[0] for r in result }
		assert node_ids == { "p2", "p3" }

	def test_neighborhood_empty_graph(self, simple_engine):
		"""Test neighborhood on empty graph"""
		engine = simple_engine

		engine.create_node("Person", "p1", "Alice")

		nodes, relations = engine.neighborhood(
			start="p1",
			max_distance=1
		)

		assert len(nodes) == 1
		assert nodes == { (engine.get_node("p1"), 0) }
		assert len(relations) == 0

	def test_connected_components_empty(self, clean_engine):
		"""Test connected components on empty graph"""
		engine = clean_engine

		components = engine.connected_components(
			nodes=None
		)

		assert len(components) == 0
