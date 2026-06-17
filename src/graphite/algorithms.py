"""
Implemented standard graph algorithms for Graphite graph database.
"""
from collections import deque
from typing import Callable, cast, TYPE_CHECKING

from .instances import Node, Relation
from .query import Direction

if TYPE_CHECKING:
	from .engine import GraphiteEngine

# pylint: disable=too-many-locals, too-many-positional-arguments, too-many-arguments
# pylint: disable=too-many-branches
def bfs(
	engine: 'GraphiteEngine',
	start: Node | str,
	end: Node | str | Callable[[list[tuple[Relation, Node]]], bool] | None = None,
	stop_at_first: bool = True,
	direction: Direction = Direction.OUTGOING,
	relation_type: str | None = None,
	max_depth: int | None = None,
	include_start:bool = False,
	allow_direction_switch: bool = False,
	visited: set[str] | None = None,
	max_results: int | None = None
) -> list[tuple[str, int, list[tuple[Relation, Node]]]]:
	"""
	Highly customizable Breadth-First Search in graph

	Note: Steps are sorted by distance (it's logical order too). When using INCOMING or BOTH
	directions, results contain founded paths with a pattern like this:
	``'end', depth_int, [(Relation(Type:other->start), Node(Type:other)), ...,
	(Relation(Type:end->another), Node(Type:end))]``

	:param engine: Engine to use
	:param start: Starting node
	:param end: End target, node, node ID, or a callable ((path) -> bool) to match on path
	:param stop_at_first: If True and ``end`` is provided, stops at first match
	:param direction: Direction to traverse
	:param relation_type: Type of relations to traverse
	:param max_depth: Maximum depth to traverse
	:param include_start: If True check starting node on result
	:param allow_direction_switch: If True allow direction switch in a path when ``direction =
	Direction.BOTH``
	:param visited: Optional visited set to ignore
	:param max_results: Maximum number of results to return
	:return: An empty list or a list of found paths with each item as: (node_id, path_depth,
	list(path_steps)), where ``path_steps`` is (relation, node)
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
	queue.append((start, 0, [], {start} | (visited if visited is not None else set())))
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
				continue # Exact match on node ID, this branch hasn't anything else to find
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

def shortest_path( # pylint: disable=too-many-positional-arguments, too-many-arguments
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
	"""
	Shortest path from ``from_node`` to ``to_end``

	Non-weighted mode uses BFS. Weighted mode is not implemented yet.

	:param engine: Engine to use
	:param from_node: Starting node
	:param to_end: End node, node ID, or function to call (list(steps) -> bool) or None to get one
	of nearest neighbors
	:param direction: Direction to traverse
	:param relation_type: Type of relations to traverse
	:param max_depth: Maximum depth to traverse
	:param allow_direction_switch: If True allow direction switch in a path when ``direction =
	Direction.BOTH``
	:param ignore_nodes: Nodes to ignore
	:param weight: Optional field name to weighted pathfinding (Not implemented yet)
	:return: Target node ID, Distance, List of steps where each step is a (Relation, Node) pair
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
			ignore_nodes
		)
		return None if len(result) == 0 else result[0]
	raise NotImplementedError("Weighted shortest path is not implemented yet.")

def all_shortest_paths( # pylint: disable=too-many-positional-arguments, too-many-arguments
	engine: 'GraphiteEngine',
	from_node: Node | str,
	to_end: Node | str | Callable[[list[tuple[Relation, Node]]], bool] | None = None,
	direction: Direction = Direction.OUTGOING,
	relation_type: str | None = None,
	max_depth: int | None = None,
	allow_direction_switch: bool = False,
	ignore_nodes: set[str] | None = None,
	weight: str | None = None
) -> list[tuple[str, int, list[tuple[Relation, Node]]]]:
	"""
	All shortest paths from ``from_node`` to ``to_end``

	Non-weighted mode uses BFS. Weighted mode is not implemented yet.

	:param engine: Engine to use
	:param from_node: Starting node
	:param to_end: End node, node ID, or function to call (list(steps) -> bool) or None to match
	:param direction: Direction to traverse
	:param relation_type: Relation types to traverse
	:param max_depth: Maximum depth to traverse
	:param allow_direction_switch: If True allow direction switch in a path when ``direction =
	Direction.BOTH``
	:param ignore_nodes: Nodes to ignore
	:param weight: Optional weight field name to weighted pathfinding (Not implemented yet)
	:return: List of result paths like shortest_path(), where items are sorted by distance / cost
	and cycles are trimmed
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
			ignore_nodes
		)
		if not paths:
			return []
		min_depth = paths[0][1]
		return [p for p in paths if p[1] == min_depth]
	raise NotImplementedError("Weighted all shortest paths is not implemented yet.")

def connected_components( # pylint: disable=too-many-positional-arguments, too-many-arguments
	engine: 'GraphiteEngine',
	nodes: Node | str | set[Node | str] | None = None,
	return_all_nodes: bool = False,
	direction: Direction = Direction.OUTGOING,
	relation_type: str | None = None,
	allow_direction_switch: bool = False,
	ignore_nodes: set[str] | None = None
) -> list[set[str]]:
	"""
	Split given nodes to connected components

	:param engine: Engine to use
	:param nodes: One or a set of nodes / node IDs to group, or None to get all nodes from engine
	:param return_all_nodes: If True return all nodes in component, not just intersection with
	``nodes``
	:param direction: Direction to traverse
	:param relation_type: Type of relations to traverse
	:param allow_direction_switch: If True allow direction switch in a path when ``direction =
	Direction.BOTH``
	:param ignore_nodes: Nodes to ignore
	:return: List of component nodes
	"""
	if nodes is None:
		_nodes = set(engine.nodes.keys())
	elif not isinstance(nodes, set):
		_nodes = {nodes if isinstance(nodes, str) else nodes.id}
	else:
		_nodes = {node.id if isinstance(node, Node) else node for node in nodes}

	if ignore_nodes is not None:
		_nodes -= ignore_nodes

	result: list[set[str]] = []
	visited = set()
	for node in _nodes:
		# Skip currently found nodes when max depth not provided
		if node in visited:
			continue

		step_result = {r[0] for r in bfs(
			engine,
			str(node),
			direction=direction,
			relation_type=relation_type,
			include_start=True,
			allow_direction_switch=allow_direction_switch,
			visited=ignore_nodes
		)}

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

def neighborhood( # pylint: disable=too-many-positional-arguments, too-many-arguments
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
	"""
	Get neighbors of ``start`` in given ``max_distance``

	:param engine: Engine to use
	:param start: Starting node object or ID
	:param max_distance: Maximum distance to traverse
	:param filter_method: Optional callable to filter neighbors
	:param max_results: Maximum number of results to return
	:param direction: Direction to traverse
	:param relation_type: Type of relations to traverse
	:param allow_direction_switch: If True allow direction switch in a path when ``direction =
	Direction.BOTH``
	:param ignore_nodes: Nodes to ignore
	:return: Set of neighbors (including ``start``) with their distance to ``start``, and set of
	relations in neighborhood
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
