"""Implemented standard graph algorithms for Graphite graph database."""
from collections import deque
from typing import Callable, TYPE_CHECKING, cast

from .instances import Node, Relation
from .query import Direction

if TYPE_CHECKING:
	from .graphite_engine import GraphiteEngine

# pylint: disable=too-many-branches, too-many-locals, too-many-positional-arguments
# pylint: disable=too-many-arguments
# Reason: This BFS is a feature-rich and flexible implementation. It is mostly used as a
# low-level function to provide the necessary flexibility for other application-specific
# functions, so its complexity is decided.
def bfs(
	engine: 'GraphiteEngine',
	start: Node | str,
	end: Node | str | Callable[[list[tuple[Relation, Node]]], bool] | None = None,
	stop_at_first: bool = True,
	direction: Direction = Direction.OUTGOING,
	relation_type: str | None = None,
	max_depth: int | None = None,
	include_start: bool = False,
	allow_direction_switch: bool = False,
	visited: set[str] | None = None,
	max_results: int | None = None
) -> list[tuple[str, int, list[tuple[Relation, Node]]]]:
	"""Highly Customizable [**BFS**](https://en.wikipedia.org/wiki/Breadth-first_search)
	(Breadth-First Search) in the graph.

	!!! Note
	    Steps are sorted by distance in returned result.

	Args:
	    start: Starting node ID or object.
	    end: One of below:

	        - `None`: Match on all nodes in the result.
	        - Node ID or object: Match on all paths to given node.
	        - Callable (`(path) -> bool`): Match on a path when given callable returns `True`.

	    stop_at_first: If `True` and `end` is provided, stops at first match.
	    direction: Direction to traverse.
	    relation_type: Type of relations to limit traverse.
	    max_depth: Maximum depth to traverse.
	    include_start: If `True` check starting node on result.
	    allow_direction_switch: If `True` allow direction switch in a path when
	        `direction=Direction.BOTH`.
	    visited: Visited set of node IDs to ignore.
	    max_results: Maximum number of results to return.

	Returns:
	    An empty list or a list of found paths sorted by distance with each item as:
	        ```python
	        (destination_node_id, path_depth, [(step_relation_obj, step_node_obj), ...])
	                                          ^^^^^^^  path_to_destination_node  ^^^^^^^
	        ```
	        `path_depth` is `0` for starting node, it means this is equal to the size of
	        `path_to_destination_node`.
	"""
	if direction == Direction.BOTH and not allow_direction_switch:
		result_out = bfs(
			engine, start, end, stop_at_first, Direction.OUTGOING, relation_type, max_depth,
			include_start, False, visited, max_results
		)
		result_in = bfs(
			engine, start, end, stop_at_first, Direction.INCOMING, relation_type, max_depth,
			include_start, False, visited, max_results
		)
		result = sorted(result_in + result_out, key=lambda x: x[1])
		if stop_at_first and end is not None:
			return result[:1]
		return result[:max_results] if max_results is not None else result

	start: str = start.id if isinstance(start, Node) else start
	end: str | Callable[[list[tuple[Relation, Node]]], bool] | None = (
		end.id if isinstance(end, Node) else end
	)
	queue: deque[tuple[str, int, list[tuple[Relation, Node]], set[str]]] = deque()
	queue.append((start, 0, [], { start } | (visited if visited is not None else set())))
	result: list[tuple[str, int, list[tuple[Relation, Node]]]] = []
	if callable(end):
		end = cast(Callable[[list[tuple[Relation, Node]]], bool], end)

	while queue:
		current, depth, path, visited_nodes = queue.popleft()

		if include_start or depth > 0:
			if isinstance(end, str) and end == current:
				result.append((current, depth, path))
				if stop_at_first:
					break
				continue  # Exact match on node ID, this branch hasn't anything else to find
			if callable(end) and end(path):
				result.append((current, depth, path))
				if stop_at_first:
					break
			elif end is None:
				result.append((current, depth, path))

		if max_results is not None and len(result) >= max_results:
			break

		if max_depth is not None and depth >= max_depth:
			continue

		neighbors = _resolve_neighbors(engine, current, direction, relation_type)
		for relation, node in neighbors:
			if node.id not in visited_nodes:
				new_visited_nodes = visited_nodes.copy()
				new_visited_nodes.add(node.id)
				queue.append((node.id, depth + 1, [*path, (relation, node)], new_visited_nodes))

	return result[:max_results] if max_results is not None else result

# pylint: disable=too-many-positional-arguments, too-many-arguments
# Reason: This function provides complete flexibility of BFS usage (no weight mode) to reduce
# hacking need in finding the shortest path. Providing another wrapper based on most-used
# configuration is planned.
def shortest_path(
	engine: 'GraphiteEngine',
	from_node: Node | str,
	to_end: Node | str | Callable[[list[tuple[Relation, Node]]], bool] | None = None,
	direction: Direction = Direction.OUTGOING,
	relation_type: str | None = None,
	max_depth: int | None = None,
	allow_direction_switch: bool = False,
	ignore_nodes: set[str] | None = None,
	weight: str | None = None
) -> tuple[str, int, list[tuple[Relation, Node]]] | None:
	"""Finds shortest path from `from_node` to `to_end`.

	Non-weighted mode uses [bfs()](./#graphite.GraphiteEngine.bfs) internally.

	!!! Bug "Not Implemented Completely"
	    Weighted mode is **not implemented yet**.

	Args:
	    from_node: Starting node Id or object.
	    to_end: One of below:

	        - `None`: Match on all nodes in the result. It means nearest neighbor.
	        - Node ID or object: Match on all paths to given node.
	        - Callable (`(path) -> bool`): Match on a path when given callable returns `True`.

	    direction: Direction to traverse.
	    relation_type: Type of relations to allow traverse.
	    max_depth: Maximum depth to traverse.
	    allow_direction_switch: If `True` allow direction switch in a path when `direction =
	        Direction.BOTH`.
	    ignore_nodes: Node IDs to ignore.
	    weight: Optional field name to weighted pathfinding. **(Not implemented yet)**

	Returns:
	    `None` or the shortest found path as:
	        ```python
	        (destination_node_id, path_depth, [(step_relation_obj, step_node_obj), ...])
	                                          ^^^^^^^  path_to_destination_node  ^^^^^^^
	        ```
	        `path_depth` is `0` for starting node, it means this is equal to the size of
	        `path_to_destination_node`.
	"""
	if weight is None:
		result = bfs(
			engine,
			from_node,
			to_end,
			True,
			direction,
			relation_type,
			max_depth,
			False,
			allow_direction_switch,
			ignore_nodes,
			1
		)
		return None if len(result) == 0 else result[0]
	raise NotImplementedError("Weighted shortest path is not implemented yet.")

# pylint: disable=too-many-positional-arguments, too-many-arguments
# Reason: As described in shortest_path().
def all_shortest_paths(
	engine: 'GraphiteEngine',
	from_node: Node | str,
	to_end: Node | str | Callable[[list[tuple[Relation, Node]]], bool] | None = None,
	direction: Direction = Direction.OUTGOING,
	relation_type: str | None = None,
	max_depth: int | None = None,
	allow_direction_switch: bool = False,
	ignore_nodes: set[str] | None = None,
	weight: str | None = None,
	max_results: int | None = None
) -> list[tuple[str, int, list[tuple[Relation, Node]]]]:
	"""All shortest paths from `from_node` to `to_end`.

	Non-weighted mode uses [bfs()](./#graphite.GraphiteEngine.bfs) internally.

	!!! Bug "Not Implemented Completely"
	    Weighted mode is **not implemented yet**.

	Args:
	    from_node: Starting node ID or object.
	    to_end: One of below:

	        - `None`: Match on all nodes in the result. It means all (or `max_results`) nearest
	            neighbors.
	        - Node ID or object: Match on all paths to given node.
	        - Callable (`(path) -> bool`): Match on a path when given callable returns `True`.

	    direction: Direction to traverse.
	    relation_type: Type of relations to limit traverse.
	    max_depth: Maximum depth to traverse.
	    allow_direction_switch: If `True` allow direction switch in a path when
	        `direction=Direction.BOTH`.
	    ignore_nodes: Visited set of node IDs to ignore.
	    weight: Optional field name to weighted pathfinding.
	    max_results: Maximum number of results to return.

	Returns:
	    An empty list or a list of found paths sorted by distance with each item as:
	        ```python
	        (destination_node_id, path_depth, [(step_relation_obj, step_node_obj), ...])
	                                          ^^^^^^^  path_to_destination_node  ^^^^^^^
	        ```
	        `path_depth` is `0` for starting node, it means this is equal to the size of
	        `path_to_destination_node`.
	"""
	if weight is None:
		paths = bfs(
			engine,
			from_node,
			to_end,
			False,
			direction,
			relation_type,
			max_depth,
			False,
			allow_direction_switch,
			ignore_nodes,
			max_results
		)
		if not paths:
			return []
		min_depth = paths[0][1]
		return [p for p in paths if p[1] == min_depth]
	raise NotImplementedError("Weighted all shortest paths is not implemented yet.")

# pylint: disable=too-many-locals, too-many-positional-arguments, too-many-arguments
# Reason: As described in shortest_path().
def connected_components(
	engine: 'GraphiteEngine',
	nodes: Node | str | set[Node | str] | None = None,
	return_all_nodes: bool = False,
	direction: Direction = Direction.OUTGOING,
	relation_type: str | None = None,
	allow_direction_switch: bool = False,
	ignore_nodes: set[str] | None = None
) -> list[set[str]]:
	"""Splits given nodes to connected components.

	!!! Note
	    Uses [bfs()](./#graphite.GraphiteEngine.bfs) internally.

	Args:
	    nodes: One or a set of node (objects or IDs) to group, or `None` to get all nodes from
	        engine.
	    return_all_nodes: If `True`, includes all nodes in each component, not just intersection
	        of them with input `nodes`. Has no effect when `nodes = None`. `False` is unusual
	        when using a single node.
	    direction: Direction to traverse.
	    relation_type: Type of relations to allow traverse.
	    allow_direction_switch: If `True`, allow direction switch in a path when `direction
	        = Direction.BOTH`.
	    ignore_nodes: Node IDs to ignore.

	Returns:
	    List of component nodes.
	"""
	if nodes is None:
		_nodes = set(engine.nodes.keys())
	elif not isinstance(nodes, set):
		_nodes = { nodes.id if isinstance(nodes, Node) else nodes }
	else:
		_nodes = { node.id if isinstance(node, Node) else node for node in nodes }

	if ignore_nodes is not None:
		_nodes -= ignore_nodes

	result: list[set[str]] = []
	visited: set[str] = set()
	for node in _nodes:
		if node in visited:
			continue

		step_result = { r[0] for r in bfs(
			engine,
			str(node),
			direction=direction,
			relation_type=relation_type,
			include_start=True,
			allow_direction_switch=allow_direction_switch,
			visited=ignore_nodes
		) }

		if not return_all_nodes:
			step_result &= _nodes

		result.append(step_result)
		visited |= step_result

	merged_result: list[set[str]] = []

	for component in result:
		sets_to_merge = []
		for merged in merged_result:
			if merged.intersection(component):
				sets_to_merge.append(merged)
		new_component: set[str] = component.copy()
		if sets_to_merge:
			for merged in sets_to_merge:
				merged_result.remove(merged)
				new_component.update(merged)
		merged_result.append(new_component)

	return merged_result

# pylint: disable=too-many-locals, too-many-positional-arguments, too-many-arguments
# Reason: As described in shortest_path().
def neighborhood(
	engine: 'GraphiteEngine',
	start: Node | str,
	max_distance: int | None = None,
	filter_method: Callable[[list[tuple[Relation, Node]]], bool] | None = None,
	max_results: int | None = None,
	direction: Direction = Direction.OUTGOING,
	relation_type: str | None = None,
	allow_direction_switch: bool = False,
	ignore_nodes: set[str] | None = None
) -> tuple[set[tuple[Node, int]], set[Relation]]:
	"""Returns neighbors of `start` in given `max_distance`.

	!!! Note
	    Uses [bfs()](./#graphite.GraphiteEngine.bfs) internally.

	Args:
	    start: Starting node object or ID.
	    max_distance: Maximum distance to traverse.
	    filter_method: Optional callable to filter neighbors (`(path) -> bool`).
	    max_results: Maximum number of results to return.
	    direction: Direction to traverse.
	    relation_type: Type of relations to allow
	        traverse.
	    allow_direction_switch: If `True`, allow direction switch in a path when `direction =
	        Direction.BOTH`.
	    ignore_nodes: Node IDs to ignore.

	Returns:
	    Set of neighbors (including `start`) with their distance to
	        `start`, and set of relations in neighborhood.
	"""
	paths = bfs(
		engine,
		start,
		filter_method,
		False,
		direction,
		relation_type,
		max_distance,
		False,
		allow_direction_switch,
		ignore_nodes,
		max_results
	)

	result: tuple[set[tuple[Node, int]], set[Relation]] = (set(), set())
	result[0].add((start if isinstance(start, Node) else engine.get_node(start), 0))
	added_nodes: set[Node] = set()

	for _, distance, path in paths:
		node = path[-1][1]
		if node not in added_nodes:
			result[0].add((node, distance))
			added_nodes.add(node)
		for relation, _ in path:
			result[1].add(relation)

	return result

def _resolve_neighbors(
	engine: 'GraphiteEngine',
	current: str,
	direction: Direction,
	relation_type: str | None = None,
) -> list[tuple[Relation, Node]]:
	result: list[tuple[Relation, Node]] = []
	if direction in (Direction.OUTGOING, Direction.BOTH):
		for relation in engine.get_relations_from(current, relation_type):
			result.append((relation, engine.get_node(relation.to_node)))
	if direction in (Direction.INCOMING, Direction.BOTH):
		for relation in engine.get_relations_to(current, relation_type):
			result.append((relation, engine.get_node(relation.from_node)))
	return result
